#!/usr/bin/env python3
"""Upstream checker: did any kernel source get new commits since the last check?

  upstream_check.py <sources.conf> <state.json>
  upstream_check.py start <state.json> <plan.json> <owner/repo> <branch>

Watched:
  mzggr kernel  KERNEL_REPO / KERNEL_REF of KERNEL_SOURCE=mzggr
  aigis kernel  KERNEL_REPO / KERNEL_REF of KERNEL_SOURCE=aigis
                Both kernels: commits that only touch their root module or
                NoMount (the KernelSU / BakaSU / KSUN / SukiSU / NoMount
                submodules or folders, .gitmodules) or only docs (README,
                *.md, docs/, .github/) are ignored. The build replaces the
                root module with xxKSU and builds NoMount itself, so those do
                not change our kernel. Every other kernel change counts.
  xxksu         KSU_REPO / KSU_REF
  susfs         SUSFS_REPO / SUSFS_REF, only commits that touched SUSFS_PATCH
                (the 4.14 patch the build uses; the rest of that repo is
                other devices and does not change the kernel)
  nomount       NOMOUNT_REPO, master branch only (manual builds still default
                to dev). Commits that only touch docs (README, *.md, docs/,
                .github/) are ignored.

Only what changed is rebuilt (written as plan= to $GITHUB_OUTPUT, a JSON list
of Build Kernel runs). xxKSU or SUSFS: both kernels. One kernel tree: only that
kernel. NoMount: only the NoMount modules (NoMount only, from the saved kernel
kits) of the kernels that are not rebuilt anyway. Every automatic build uses
NoMount master. Unchanged files are taken from the earlier run listed in the
state file ("files").

The state file keeps the newest commit seen of each source and a short
history of the changes found. The first check only saves the commits
(nothing to compare with yet). Writes changed=true|false and first=true|false
to $GITHUB_OUTPUT (moved=true when any commit is new, even if all were
ignored), the new commits to changes.md, the ignored ones to ignored.md and
the commits seen to sources.md.
"""
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

MAX_LIST = 20
MAX_HISTORY = 50


def conf(path, source):
    """Values of sources.conf for one KERNEL_SOURCE (the file is bash)."""
    keys = ["KERNEL_REPO", "KERNEL_REF", "KSU_REPO", "KSU_REF", "SUSFS_REPO", "SUSFS_REF", "SUSFS_PATCH", "NOMOUNT_REPO"]
    script = f'KERNEL_SOURCE={source}; . "$1" >/dev/null; ' + "; ".join(f'echo "{k}=${{{k}}}"' for k in keys)
    out = subprocess.check_output(["bash", "-c", script, "conf", path], text=True,
                                  env={k: v for k, v in os.environ.items()
                                       if not k.startswith(("KERNEL_", "KSU_", "SUSFS_", "NOMOUNT_"))})
    return dict(line.split("=", 1) for line in out.splitlines() if "=" in line)


def slug(url):
    return url.rstrip("/").removeprefix("https://github.com/").removesuffix(".git")


def api(path):
    return json.loads(subprocess.check_output(["gh", "api", path], text=True))


def head(repo, ref, path=None):
    if path:
        commits = api(f"repos/{repo}/commits?sha={ref}&path={path}&per_page=1")
        if not commits:
            sys.exit(f"::error::{repo}@{ref} has no commit touching {path}")
        c = commits[0]
    else:
        c = api(f"repos/{repo}/commits/{ref}")
    return {
        "commit": c["sha"],
        "date": c["commit"]["committer"]["date"],
        "subject": c["commit"]["message"].splitlines()[0],
    }


def new_commits(repo, old, new, path=None):
    """Lines for the commits in old..new (newest first) and their count."""
    try:
        if path:
            out = []
            for c in api(f"repos/{repo}/commits?sha={new}&path={path}&per_page=100"):
                if c["sha"] == old:
                    break
                out.append(c)
            total = len(out)
        else:
            data = api(f"repos/{repo}/compare/{old}...{new}")
            out = list(reversed(data.get("commits", [])))
            total = data.get("total_commits", len(out))
    except subprocess.CalledProcessError:
        # For example a force-push removed the old commit.
        return [f"- (could not list the commits since `{old[:12]}`, the branch was probably rewritten)"], 0
    lines = [f"- [`{c['sha'][:8]}`](https://github.com/{repo}/commit/{c['sha']}) {c['commit']['message'].splitlines()[0]}"
             for c in out[:MAX_LIST]]
    if total > MAX_LIST:
        lines.append(f"- ... and {total - MAX_LIST} more")
    return lines, total


# A path segment with one of these names is a root module or NoMount.
# resukisu is BakaSU's old name (still in the Aigis .gitmodules).
IGNORED_SEGMENTS = re.compile(r"^(kernelsu([-_].*)?|ksu|ksun|kernelsu-next|bakasu|sukisu.*|resukisu|"
                              r"apatch|magisk|nomount)$", re.I)


def ignored_path(path):
    """True for files that do not change our kernel build."""
    parts = path.split("/")
    if path == ".gitmodules" or parts[0] in (".github", "docs"):
        return True
    if path.lower().endswith(".md") or parts[-1].upper().startswith("README"):
        return True
    return any(IGNORED_SEGMENTS.match(p) for p in parts)


def docs_path(path):
    """True for files that are only docs (for NoMount)."""
    parts = path.split("/")
    return parts[0] in (".github", "docs") or path.lower().endswith(".md") or parts[-1].upper().startswith("README")


def kernel_commits(repo, old, new, ignore=ignored_path):
    """Split the commits in old..new into (relevant, ignored) commit lists,
    or None when they cannot be listed (rewritten branch, too many)."""
    try:
        data = api(f"repos/{repo}/compare/{old}...{new}")
    except subprocess.CalledProcessError:
        return None
    commits = list(reversed(data.get("commits", [])))
    if data.get("total_commits", len(commits)) > len(commits) or len(commits) > 100:
        return None
    relevant, ignored = [], []
    for c in commits:
        files = [f["filename"] for f in api(f"repos/{repo}/commits/{c['sha']}").get("files", [])]
        # A commit with no files listed (for example a merge) counts.
        (ignored if files and all(ignore(f) for f in files) else relevant).append(c)
    return relevant, ignored


def commit_line(repo, c):
    return f"- [`{c['sha'][:8]}`](https://github.com/{repo}/commit/{c['sha']}) {c['commit']['message'].splitlines()[0]}"


def emit(pairs):
    path = os.environ.get("GITHUB_OUTPUT")
    lines = "".join(f"{k}={v}\n" for k, v in pairs.items())
    if path:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(lines)
    print(lines, end="")


def main(conf_path, state_path):
    mz, ag = conf(conf_path, "mzggr"), conf(conf_path, "aigis")
    watched = {
        "mzggr": ("mzggr kernel", slug(mz["KERNEL_REPO"]), mz["KERNEL_REF"], None),
        "aigis": ("Aigis kernel", slug(ag["KERNEL_REPO"]), ag["KERNEL_REF"], None),
        "xxksu": ("xxKSU", slug(mz["KSU_REPO"]), mz["KSU_REF"], None),
        "susfs": ("Jack's SUSFS (4.14 patch)", slug(mz["SUSFS_REPO"]), mz["SUSFS_REF"], mz["SUSFS_PATCH"]),
        # NoMount: master only (the Build Kernel default stays dev for manual builds).
        "nomount": ("NoMount", slug(mz["NOMOUNT_REPO"]), "master", None),
    }
    state_file = Path(state_path)
    state = json.loads(state_file.read_text()) if state_file.exists() else {}
    old = state.get("sources", {})
    first = not old
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    sources, report, changed, ignored_report = {}, [], [], []
    for key, (label, repo, ref, path) in watched.items():
        cur = head(repo, ref, path)
        cur.update({"name": label, "repo": f"https://github.com/{repo}", "branch": ref})
        if path:
            cur["path"] = path
        sources[key] = cur
        prev = old.get(key)
        if prev is None and not first:
            # A source watched for the first time: save it, nothing to compare yet.
            print(f"{label}: {repo}@{ref} {cur['commit'][:12]} (now watched, saved)")
            continue
        if prev and (prev.get("repo") != cur["repo"] or prev.get("branch") != ref):
            prev = None  # the build now uses another repo or branch: start over for it
        if prev is None:
            if not first:
                changed.append(key)
                report += [f"### {label}: now watching {repo} `{ref}`", f"- `{cur['commit'][:8]}` {cur['subject']}", ""]
            print(f"{label}: {repo}@{ref} {cur['commit'][:12]} (saved)")
        elif prev["commit"] != cur["commit"] and key in ("mzggr", "aigis", "nomount") and \
                (split := kernel_commits(repo, prev["commit"], cur["commit"],
                                         docs_path if key == "nomount" else ignored_path)) is not None:
            relevant, ignored = split
            why = "docs only" if key == "nomount" else "root module, NoMount or docs only"
            skipped = [commit_line(repo, c) + f" (ignored: {why})" for c in ignored]
            if relevant:
                changed.append(key)
                n = len(relevant)
                report += [f"### {label}: {n} new commit{'s' if n != 1 else ''} on `{ref}`"] + \
                    [commit_line(repo, c) for c in relevant[:MAX_LIST]] + \
                    ([f"- ... and {n - MAX_LIST} more"] if n > MAX_LIST else []) + skipped[:MAX_LIST] + [""]
                print(f"{label}: {prev['commit'][:12]} -> {cur['commit'][:12]} ({n} kernel commits, {len(ignored)} ignored)")
            else:
                ignored_report.append(f"### {label}: only {why.replace(' only', '')} commits, ignored")
                ignored_report += skipped[:MAX_LIST] + [""]
                print(f"{label}: {prev['commit'][:12]} -> {cur['commit'][:12]}, ignored ({len(ignored)} commits: {why})")
        elif prev["commit"] != cur["commit"]:
            lines, total = new_commits(repo, prev["commit"], cur["commit"], path)
            changed.append(key)
            report += [f"### {label}: {total or 'new'} new commit{'s' if total != 1 else ''} on `{ref}`"] + lines + [""]
            print(f"{label}: {prev['commit'][:12]} -> {cur['commit'][:12]}")
        else:
            print(f"{label}: no change ({cur['commit'][:12]})")
    state["note"] = "Saved by the Upstream check workflow. Newest commit seen of each watched source."
    state["checked"] = now
    state["sources"] = sources
    if changed:
        history = state.get("history", [])
        history.insert(0, {"found": now, "changed": changed,
                           "commits": {k: sources[k]["commit"] for k in changed}})
        state["history"] = history[:MAX_HISTORY]
    elif first:
        state.setdefault("history", [])
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps(state, indent=2) + "\n")
    Path("changes.md").write_text("\n".join(report) + "\n" if report else "")
    Path("ignored.md").write_text("\n".join(ignored_report) + "\n" if ignored_report else "")
    Path("sources.md").write_text("".join(
        f"- {v['name']}: {v['repo']} `{v['branch']}` @ `{v['commit'][:12]}` ({v['date']})\n" for v in sources.values()))
    # moved: some commit is new, even when every new commit was ignored (saved, no build).
    moved = any(old.get(k, {}).get("commit") != v["commit"] for k, v in sources.items())
    plan = build_plan(changed)
    Path("plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    for b in plan:
        print(f"Build: Kernel {b['kernel']}{' (NoMount only)' if b['nomount_only'] else ''} -> {', '.join(b['files'])}")
    emit({"changed": str(bool(changed)).lower(), "first": str(first).lower(), "changed_list": " ".join(changed),
          "moved": str(moved).lower(), "plan": json.dumps(plan, separators=(",", ":"))})


KERNELS = ("aigis", "mzggr")  # build order: the main kernel first


def build_plan(changed):
    """Build Kernel runs for what changed; everything else is reused."""
    full = set(KERNELS) if {"xxksu", "susfs"} & set(changed) else set()
    full |= {k for k in KERNELS if k in changed}
    plan = []
    kernels = [k for k in KERNELS if k in full]
    if kernels:
        plan.append({"kernel": "both" if len(kernels) == 2 else kernels[0], "nomount_only": False,
                     "files": [f"{k}-kernel" for k in kernels] + [f"{k}-nomount" for k in kernels]})
    rest = [k for k in KERNELS if k not in full]
    if "nomount" in changed and rest:
        plan.append({"kernel": "both" if len(rest) == 2 else rest[0], "nomount_only": True,
                     "files": [f"{k}-nomount" for k in rest]})
    return plan


FILE_NAMES = {
    "aigis-kernel": "Main kernel ZIP (Aigis)",
    "mzggr-kernel": "Alt. kernel ZIP (mzggr)",
    "aigis-nomount": "NoMount module for Aigis",
    "mzggr-nomount": "NoMount module for mzggr",
}


def title_ok(b, title):
    """Is this run-name the Build Kernel run that was planned?"""
    first = "A325X NoMount master LKM only" if b["nomount_only"] else "A325X xxKSU + SUSFS kernel"
    tag = {"both": "(Aigis + mzggr)", "aigis": "(Aigis)", "mzggr": ""}[b["kernel"]]
    return title.startswith(first) and (tag in title if tag else "(Aigis" not in title) \
        and "NoMount lkm-master" in title and "(Latest)" in title


def start(state_path, plan_path, repo, ref):
    """Start the Build Kernel runs of plan.json, one after the other, and save
    in the state file which run holds each file. Writes builds.md."""
    plan = json.loads(Path(plan_path).read_text())
    state = json.loads(Path(state_path).read_text())
    files = state.setdefault("files", {})
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    seen = set(subprocess.check_output(
        ["gh", "run", "list", "--repo", repo, "--workflow", "kernel.yml", "--limit", "20",
         "--json", "url", "--jq", ".[].url"], text=True).split())
    started = []
    for b in plan:
        args = ["gh", "workflow", "run", "kernel.yml", "--repo", repo, "--ref", ref,
                "-f", f"kernel_source={b['kernel']}", "-f", "commit_mode=Latest", "-f", "release_type=CI",
                "-f", "nomount_branch=master", "-f", f"nomount_only={str(b['nomount_only']).lower()}"]
        subprocess.check_call(args)
        url = title = ""
        for _ in range(12):
            time.sleep(5)
            runs = json.loads(subprocess.check_output(
                ["gh", "run", "list", "--repo", repo, "--workflow", "kernel.yml", "--branch", ref,
                 "--event", "workflow_dispatch", "--limit", "10", "--json", "url,displayTitle"], text=True))
            new = [r for r in runs if r["url"] not in seen]
            if new:
                url, title = new[-1]["url"], new[-1]["displayTitle"]
                seen.add(url)
                break
        what = f"Kernel {b['kernel']}" + (" (NoMount only)" if b["nomount_only"] else "")
        print(f"{what}: {url or 'started'} {title}")
        if url and not title_ok(b, title):
            sys.exit(f"::error::The started build is not the one planned ({what}): {title}")
        for f in b["files"]:
            files[f] = {"run": url or "started", "date": now}
        started.append({"build": what, "run": url or "started", "files": b["files"]})
    if state.get("history"):
        state["history"][0]["builds"] = started
    Path(state_path).write_text(json.dumps(state, indent=2) + "\n")
    new_files = {f for b in plan for f in b["files"]}
    md = ["| File | From run | |", "|---|---|---|"]
    for f, label in FILE_NAMES.items():
        info = files.get(f)
        where = f"[{info['date'][:10]}]({info['run']})" if info and info["run"].startswith("http") else \
            (info["run"] if info else "no automatic build yet")
        md.append(f"| {label} | {where} | {'new build' if f in new_files else 'no update, reused'} |")
    Path("builds.md").write_text("\n".join(md) + "\n")


if __name__ == "__main__":
    if len(sys.argv) == 6 and sys.argv[1] == "start":
        start(*sys.argv[2:])
    elif len(sys.argv) == 3:
        main(sys.argv[1], sys.argv[2])
    else:
        sys.exit(__doc__)
