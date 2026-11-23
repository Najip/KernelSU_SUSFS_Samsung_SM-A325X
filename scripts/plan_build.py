#!/usr/bin/env python3
"""Plan a Build Kernel run: which kernels are built, with which commits.

  plan_build.py

Environment (set by the workflow's pick job):
  Only one kernel: Aigis with BakaSU (source aigis-bakasu). xxKSU (archived
  22 Nov 2026) and the mzggr kernel are in the xxksu branch.
  COMMIT_MODE    Latest, Verified or Promoted
  NM_ONLY        true = NoMount module only
  REUSE          (Upstream check) JSON, per kernel {"mode": kernel|nomount|reuse,
                 "run": <run id or run link>}: kernel = build it; nomount = keep
                 the kernel files of that run and build only NoMount (from its
                 kernel kit); reuse = keep all its files.
                 By hand also just a run link or number (= auto: keep the
                 kernel, and keep its NoMount module too when it has one from
                 the chosen NoMount branch, else build one), "nomount <run link>"
                 (always build a new NoMount) or "all <run link>" (= auto).
  NOMOUNT_MODE, NOMOUNT_REF, NETWORK_FIX,
  VALHALL_GPU, AIGIS_COMPILER, BRANCH

Writes to $GITHUB_OUTPUT:
  matrix        JSON list for the build job, one entry per kernel that has
                work to do (source, commits, hook "inline", network fix,
                kit_id, kernel_release, build_nomount, first)
  build_any     true when the build job has anything to do
  build_kernel  true when kernel ZIPs are built (not Promoted / NoMount only)
  promote_ok    true for a Promoted run that found a Latest build
  sources       the kernels of this run: "aigis-bakasu"
  bakasu_ref, bakasu_branch  BakaSU commit / branch of Aigis BakaSU (empty
                when it is not in this run): its manager APK must match it
  source_run, source_url, checkout_sha  (Promoted)
  collect_sources, collect_runs  kernels whose files come from an earlier run
                (Promoted, reuse) and that run per kernel (JSON)
"""
import json
import re
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
REF_KEYS = ("kernel_ref", "ksu_ref", "susfs_ref", "kernel_branch", "ksu_branch", "susfs_branch")


def fail(message):
    print(f"::error::{message}", file=sys.stderr)
    sys.exit(1)


def run(args, **env):
    """Runs a helper script and returns what it wrote to $GITHUB_OUTPUT."""
    with tempfile.NamedTemporaryFile("r", delete=False) as out:
        path = out.name
    full = dict(os.environ, **{k: str(v) for k, v in env.items()}, GITHUB_OUTPUT=path)
    code = subprocess.call([sys.executable, str(SCRIPTS / args[0]), *args[1:]], env=full)
    text = Path(path).read_text()
    os.unlink(path)
    if code:
        sys.exit(code)
    return dict(line.split("=", 1) for line in text.splitlines() if "=" in line)


def emit(pairs):
    lines = "".join(f"{k}={v}\n" for k, v in pairs.items())
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(lines)
    print(lines, end="")


def summary(text):
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(text + "\n")


RUN_RE = re.compile(r"(?:github\.com/([^/\s]+/[^/\s]+)/actions/runs/)?(\d{6,})")


def run_of(value, repo):
    """Run id from a run number or a pasted run link (.../actions/runs/<id>[/job/...])."""
    m = RUN_RE.search(str(value))
    if not m:
        fail(f"reuse: '{value}' is not a run link or run number.")
    if m.group(1) and repo and m.group(1).lower() != repo.lower():
        fail(f"reuse: that run is from {m.group(1)}, not {repo}.")
    return m.group(2)


def parse_reuse(text, sources, repo):
    """The reuse box: JSON (Upstream check), or a run link / number by hand."""
    text = text.strip()
    if not text:
        return {}
    if text.startswith("{"):
        plan = json.loads(text)
        for v in plan.values():
            if v.get("run"):
                v["run"] = run_of(v["run"], repo)
        return plan
    mode = "auto"
    word = text.split()[0].lower()
    if word in ("all", "reuse", "auto", "nomount"):
        mode = "nomount" if word == "nomount" else "auto"
        text = text[len(word):]
    rid = run_of(text, repo)
    summary(f"reuse: keep the kernel of run {rid}, " + ("build a new NoMount module" if mode == "nomount"
            else "and its NoMount module when it fits (else build one)"))
    return {src: {"mode": mode, "run": rid} for src in sources}


def main():
    e = os.environ
    sources = ["aigis-bakasu"]
    mode = e.get("COMMIT_MODE", "Latest")
    nm_only = e.get("NM_ONLY") == "true"
    nomount_mode = e.get("NOMOUNT_MODE", "lkm")
    nomount_ref = e.get("NOMOUNT_REF", "master")
    out = {"sources": " ".join(sources), "promote_ok": "false", "source_run": "", "source_url": "",
           "checkout_sha": e.get("GITHUB_SHA", ""), "build_kernel": "false",
           "collect_sources": "", "collect_runs": "{}"}
    entries = []
    reuse = parse_reuse(e.get("REUSE", ""), sources, e.get("GITHUB_REPOSITORY", ""))

    if mode == "Promoted":
        found = run(["promoted_source.py", "find"], SOURCES=" ".join(sources))
        if found.get("found") != "true":
            # find already printed the warning; nothing else runs.
            emit(dict(out, matrix="[]", build_any="false"))
            return
        out.update(promote_ok="true", source_run=found["source_run"], source_url=found["source_url"],
                   collect_sources=" ".join(sources),
                   collect_runs=json.dumps({s: str(found["source_run"]) for s in sources}, separators=(",", ":")))
        summary(f"### Promoted from {found['source_url']}\n{found.get('source_title', '')}\n")
        subprocess.check_call([sys.executable, str(SCRIPTS / "promoted_source.py"), "download",
                               found["source_run"], "source"])
        for src in sources:
            info = run(["promoted_source.py", "inspect", f"source/{src}"])
            out["checkout_sha"] = info.get("build_sha") or out["checkout_sha"]
            # Reuse the module of the Latest run when it was built from the chosen branch.
            build_nm = nomount_mode == "lkm" and info.get("nomount_branch") != nomount_ref
            kit = ""
            if build_nm:
                kit = run(["kernel_kit.py", "in-run", found["source_run"]], KERNEL_SOURCE=src).get("kit_id", "")
            entries.append({
                "source": src, **{k: info.get(k, "") for k in REF_KEYS},
                "ksu_hook": info.get("hook", "manual"), "perf_tuning": info.get("tuning", "false"),
                "network_fix": info.get("network_fix", "true"), "kernel_release": info.get("kernel_release", ""),
                "valhall_gpu": info.get("valhall_gpu", "false"),
                "kernel_tag": info.get("kernel_tag", ""),
                "kit_id": kit, "build_nomount": str(build_nm).lower(), "build_kernel": "false",
            })
            summary(f"{src}: NoMount {'built now' + (' from the saved kernel kit' if kit else '') if build_nm else ('not included' if nomount_mode == 'no' else 'taken from that run')}")
    else:
        kernel = not nm_only
        out["build_kernel"] = str(kernel).lower()
        if nm_only:
            # Tree ids for the kit key.
            subprocess.call(["git", "-C", str(ROOT), "fetch", "-q", "--depth=1", "origin", e.get("GITHUB_SHA", "HEAD")])
        kept = {}
        for src in sources:
            want = reuse.get(src, {"mode": "kernel"})
            if want["mode"] in ("nomount", "reuse", "auto"):
                # Upstream check: this kernel had no update; keep its files.
                rid = str(want["run"])
                subprocess.check_call([sys.executable, str(SCRIPTS / "promoted_source.py"), "download", rid, f"source-{src}"],
                                      env=dict(os.environ, ONLY=src))
                info = run(["promoted_source.py", "inspect", f"source-{src}/{src}"])
                if not info.get("kernel_release"):
                    fail(f"Run {rid} has no {src} kernel files left; build it instead.")
                build_nm = want["mode"] == "nomount"
                if want["mode"] == "auto":
                    # Keep the run's NoMount module when it has one from the chosen branch.
                    has = info.get("has_nomount") == "true" and info.get("nomount_branch") == nomount_ref
                    build_nm = nomount_mode == "lkm" and not has
                    summary(f"{src}: run {rid} " + (f"has a NoMount {nomount_ref} module, kept" if has else
                            f"has no NoMount {nomount_ref} module (it has: {info.get('nomount_branch') or 'none'}), building one"))
                kit = run(["kernel_kit.py", "in-run", rid], KERNEL_SOURCE=src).get("kit_id", "") if build_nm else ""
                kept[src] = rid
                entries.append({
                    "source": src, **{k: info.get(k, "") for k in REF_KEYS},
                    "ksu_hook": info.get("hook", "manual"), "perf_tuning": info.get("tuning", "false"),
                    "network_fix": info.get("network_fix", "true"), "kernel_release": info.get("kernel_release", ""),
                    "valhall_gpu": info.get("valhall_gpu", "false"), "kernel_tag": info.get("kernel_tag", ""),
                    "kit_id": kit, "build_nomount": str(build_nm).lower(), "build_kernel": "false",
                    "checkout_sha": info.get("build_sha", ""),
                })
                summary(f"{src}: no update, kernel files kept from run {rid}; NoMount "
                        + ("built now" + (" from its kernel kit" if kit else "") if build_nm else "kept too"))
                continue
            refs = run(["resolve_commits.py", "resolve"], KERNEL_SOURCE=src)
            kit = ""
            if nm_only:
                key_env = dict(KERNEL_SOURCE=src, NOMOUNT_PART="separate", KSU_HOOK="inline",
                               KERNEL_REF=refs["kernel_ref"], KSU_REF=refs["ksu_ref"], SUSFS_REF=refs["susfs_ref"])
                full = dict(os.environ, **key_env)
                k = subprocess.check_output([sys.executable, str(SCRIPTS / "kernel_kit.py"), "key"],
                                            env=full, text=True).strip()
                print(f"{src} kit key: {k}")
                kit = run(["kernel_kit.py", "find", k]).get("kit_id", "")
                summary(f"{src}: NoMount " + ("built from the saved kernel kit (no kernel compile)." if kit
                                              else "no kernel kit found, the kernel is compiled once to match it."))
            entries.append({
                "source": src, **{k: refs.get(k, "") for k in REF_KEYS},
                # BakaSU always uses its SUSFS inline hooks ("inline").
                "ksu_hook": "inline", "perf_tuning": "false",
                "network_fix": e.get("NETWORK_FIX", "true"), "kernel_release": "",
                "valhall_gpu": e.get("VALHALL_GPU", "false"),
                "kernel_tag": e.get("KERNEL_TAG", ""),
                "kit_id": kit, "build_nomount": str(nomount_mode == "lkm").lower(),
                "build_kernel": str(kernel).lower(),
            })
        if kept:
            out.update(collect_sources=" ".join(kept), collect_runs=json.dumps(kept, separators=(",", ":")))

    for x in entries:
        if x["source"] == "aigis-bakasu":
            x["ksu_hook"] = "inline"  # BakaSU: always its SUSFS inline hooks
    matrix = [x for x in entries if x["build_kernel"] == "true" or x["build_nomount"] == "true"]
    for i, x in enumerate(matrix):
        x["first"] = "true" if i == 0 else "false"
        print(f"{x['source']}: kernel ZIP {x['build_kernel']}, NoMount LKM build {x['build_nomount']}, "
              f"kernel kit {x['kit_id'] or 'none'}")
    # Manager app of this run: BakaSU, from the BakaSU build of the same commit.
    out["bakasu_ref"] = next((x["ksu_ref"] for x in entries if x["source"] == "aigis-bakasu"), "")
    out["bakasu_branch"] = next((x["ksu_branch"] for x in entries if x["source"] == "aigis-bakasu"), "")
    out["matrix"] = json.dumps(matrix, separators=(",", ":"))
    out["build_any"] = str(bool(matrix)).lower()
    emit(out)


if __name__ == "__main__":
    main()
