#!/usr/bin/env python3
"""Resolve upstream commits, or save them as the verified pins.

  resolve_commits.py resolve
    COMMIT_MODE=Latest|Verified|Promoted
    Writes kernel_ref, ksu_ref, susfs_ref, the matching *_branch values and
    commit_mode to $GITHUB_OUTPUT (and to stdout).

    KERNEL_SOURCE=mzggr|aigis|aigis-bakasu picks the kernel (default mzggr).
    Latest and Promoted use the branch tips in scripts/sources.conf.
    Verified uses configs/verified.json and fails if a pin is missing: the
    top-level kernel/xxksu/susfs entries for mzggr, the "aigis" entry for Aigis,
    the "aigis-bakasu" entry for Aigis BakaSU ("xxksu" there = BakaSU).

  resolve_commits.py promote <configs/verified.json> <sources.json>...
    Rewrites the verified pins from the commits that were actually built.
    Each sources.json updates the pins of its own kernel (found by its kernel
    repo, or its "source" field); the pins of a kernel that was not built stay
    as they were.
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# key in sources.json, repo variable, branch variable in sources.conf
SOURCES = (
    ("kernel", "KERNEL_REPO", "KERNEL_REF", "kernel_ref", "kernel_branch"),
    ("xxksu", "KSU_REPO", "KSU_REF", "ksu_ref", "ksu_branch"),
    ("susfs", "SUSFS_REPO", "SUSFS_REF", "susfs_ref", "susfs_branch"),
)


# Kernels whose pins are a nested entry of verified.json (mzggr = top level).
NESTED = {"aigis": "Aigis", "aigis-bakasu": "Aigis BakaSU"}


def kernel_of(src):
    """Which kernel a sources.json is for: its "source" field (newer builds),
    else by kernel repo (older builds were xxKSU: aigis or mzggr)."""
    if src.get("source"):
        return src["source"]
    repo = ((src.get("kernel") or {}).get("repo") or "").lower()
    return "aigis" if "aigis" in repo else "mzggr"


def fail(message):
    print(f"::error::{message}", file=sys.stderr)
    print(message, file=sys.stderr)
    sys.exit(1)


def load_conf(source=None):
    env = dict(os.environ)
    if source:
        env["KERNEL_SOURCE"] = source
    script = (
        'set -a; . "$1"; set +a; '
        'python3 -c "import json,os,sys; keys=sys.argv[1:]; '
        'print(json.dumps({k: os.environ[k] for k in keys}))" '
        + " ".join(name for _, repo, ref, _, _ in SOURCES for name in (repo, ref))
        + " SUSFS_PATCH"
    )
    raw = subprocess.check_output(["bash", "-c", script, "bash", str(ROOT / "scripts/sources.conf")], text=True, env=env)
    return json.loads(raw)


def tip(repo, branch):
    out = subprocess.check_output(["git", "ls-remote", repo, f"refs/heads/{branch}"], text=True).strip()
    if not out:
        fail(f"No branch {branch} in {repo}")
    return out.split()[0]


def emit(pairs):
    lines = "".join(f"{key}={value}\n" for key, value in pairs.items())
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(lines)
    print(lines, end="")


def is_sha(value):
    return bool(value) and len(value) >= 7 and all(c in "0123456789abcdef" for c in value.lower())


def resolve():
    mode = os.environ.get("COMMIT_MODE", "")
    if mode not in ("Latest", "Verified", "Promoted"):
        fail(f"Unknown commit mode '{mode}'. Use Latest, Verified or Promoted.")
    conf = load_conf()
    out = {"commit_mode": mode}
    # A caller already chose the exact commits (the release's NoMount build).
    preset = {}
    for _, _, _, ref_out, branch_out in SOURCES:
        ref = os.environ.get(ref_out.upper(), "").strip()
        if ref:
            preset[ref_out] = ref
            preset[branch_out] = os.environ.get(branch_out.upper(), "").strip()
    if preset:
        missing = [ref_out for _, _, _, ref_out, _ in SOURCES if ref_out not in preset]
        if missing:
            fail("Preset commits are missing for " + ", ".join(missing))
        out.update(preset)
        emit(out)
        return
    if mode == "Verified":
        path = ROOT / "configs/verified.json"
        if not path.exists():
            fail("No verified commits yet. Run a build with commit mode Promoted after one you have tested.")
        data = json.loads(path.read_text())
        source = os.environ.get("KERNEL_SOURCE", "mzggr")
        if source in NESTED:
            data = data.get(source) or {}
            if not data:
                fail(f"No verified {NESTED[source]} commits yet. Run a Latest build of it, then Promoted with the same Kernel and Root flavor.")
        missing = []
        for key, repo_var, ref_var, ref_out, branch_out in SOURCES:
            item = data.get(key) or {}
            commit = (item.get("commit") or "").strip()
            repo = (item.get("repo") or "").rstrip("/")
            expected = conf[repo_var].rstrip("/")
            if not is_sha(commit):
                missing.append(key)
                continue
            if repo and repo != expected:
                fail(f"Verified {key} repo is {repo}, but sources.conf has {expected}. Run Promoted again.")
            out[ref_out] = commit
            out[branch_out] = item.get("branch") or conf[ref_var]
        if missing:
            fail(
                "No verified commits yet for "
                + ", ".join(missing)
                + ". Run a build with commit mode Promoted after one you have tested."
            )
    else:
        for _, repo_var, ref_var, ref_out, branch_out in SOURCES:
            branch = conf[ref_var]
            out[branch_out] = branch
            out[ref_out] = tip(conf[repo_var], branch)
    emit(out)


def pins(src, conf):
    out = {}
    for key, repo_var, ref_var, _, _ in SOURCES:
        item = src.get(key)
        if not isinstance(item, dict):
            fail(f"sources.json has no {key}")
        commit = (item.get("commit") or "").strip()
        if not is_sha(commit):
            fail(f"Refusing to pin an empty commit for {key}")
        branch = item.get("branch") or item.get("ref") or conf[ref_var]
        if is_sha(branch):
            branch = conf[ref_var]
        entry = {"repo": item.get("repo") or conf[repo_var], "branch": branch, "commit": commit}
        if key == "susfs":
            entry["path"] = item.get("path") or conf.get("SUSFS_PATCH", "")
        out[key] = entry
    # A future root flavor added to sources.json is pinned too.
    for key, item in src.items():
        if key in out or key == "build_repo" or not isinstance(item, dict):
            continue
        commit = (item.get("commit") or "").strip()
        if is_sha(commit):
            out[key] = {"repo": item.get("repo", ""), "branch": item.get("branch") or item.get("ref", ""), "commit": commit}
    return out


def promote(verified_path, *sources_paths):
    old = {}
    if Path(verified_path).exists():
        old = json.loads(Path(verified_path).read_text())
    data = {
        "note": "Pinned by commit mode Promoted after a successful build. A full Release must use these commits.",
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "run": "",
    }
    server = os.environ.get("GITHUB_SERVER_URL", "")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    if server and repo and run_id:
        data["run"] = f"{server}/{repo}/actions/runs/{run_id}"
    # Promoted pins the commits of an earlier Latest run; point at that run.
    if os.environ.get("SOURCE_RUN_URL"):
        data["run"] = os.environ["SOURCE_RUN_URL"]
    # Keep the pins of the kernel that was not built this time.
    mzggr = {k: v for k, v in old.items() if k not in ("note", "updated", "run", *NESTED)}
    nested = {k: old[k] for k in NESTED if old.get(k)}
    for path in sources_paths:
        src = json.loads(Path(path).read_text())
        source = kernel_of(src)
        if source in NESTED:
            nested[source] = pins(src, load_conf(source))
            nested[source]["run"] = data["run"]
        else:
            mzggr = pins(src, load_conf("mzggr"))
    data.update(mzggr)
    data.update(nested)
    Path(verified_path).write_text(json.dumps(data, indent=2) + "\n")
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "resolve":
        resolve()
    elif len(sys.argv) >= 4 and sys.argv[1] == "promote":
        promote(sys.argv[2], *sys.argv[3:])
    else:
        sys.exit(__doc__)
