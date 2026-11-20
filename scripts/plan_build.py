#!/usr/bin/env python3
"""Plan a Build Kernel run: which kernels are built, with which commits.

  plan_build.py

Environment (set by the workflow's pick job):
  KERNEL_CHOICE  mzggr, aigis or both (the "Kernel" dropdown)
  COMMIT_MODE    Latest, Verified or Promoted
  NM_ONLY        true = NoMount module only
  NOMOUNT_MODE, NOMOUNT_REF, KSU_HOOK, PERF_TUNING, NETWORK_FIX,
  VALHALL_GPU, AIGIS_COMPILER, BRANCH

Writes to $GITHUB_OUTPUT:
  matrix        JSON list for the build job, one entry per kernel that has
                work to do (source, commits, hook, tuning, network fix,
                kit_id, kernel_release, build_nomount, first)
  build_any     true when the build job has anything to do
  build_kernel  true when kernel ZIPs are built (not Promoted / NoMount only)
  promote_ok    true for a Promoted run that found a Latest build
  sources       the kernels of this run, e.g. "mzggr aigis"
  source_run, source_url, checkout_sha  (Promoted)
"""
import json
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


def main():
    e = os.environ
    choice = e.get("KERNEL_CHOICE", "mzggr")
    sources = {"mzggr": ["mzggr"], "aigis": ["aigis"], "both": ["mzggr", "aigis"]}.get(choice)
    if not sources:
        fail(f"Unknown kernel '{choice}' (use mzggr, aigis or both).")
    mode = e.get("COMMIT_MODE", "Latest")
    nm_only = e.get("NM_ONLY") == "true"
    nomount_mode = e.get("NOMOUNT_MODE", "lkm")
    nomount_ref = e.get("NOMOUNT_REF", "dev")
    out = {"sources": " ".join(sources), "promote_ok": "false", "source_run": "", "source_url": "",
           "checkout_sha": e.get("GITHUB_SHA", ""), "build_kernel": "false"}
    entries = []

    if mode == "Promoted":
        found = run(["promoted_source.py", "find"], SOURCES=" ".join(sources))
        if found.get("found") != "true":
            # find already printed the warning; nothing else runs.
            emit(dict(out, matrix="[]", build_any="false"))
            return
        out.update(promote_ok="true", source_run=found["source_run"], source_url=found["source_url"])
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
                "kit_id": kit, "build_nomount": str(build_nm).lower(),
            })
            summary(f"{src}: NoMount {'built now' + (' from the saved kernel kit' if kit else '') if build_nm else ('not included' if nomount_mode == 'no' else 'taken from that run')}")
    else:
        kernel = not nm_only
        out["build_kernel"] = str(kernel).lower()
        if nm_only:
            # Tree ids for the kit key.
            subprocess.call(["git", "-C", str(ROOT), "fetch", "-q", "--depth=1", "origin", e.get("GITHUB_SHA", "HEAD")])
        for src in sources:
            refs = run(["resolve_commits.py", "resolve"], KERNEL_SOURCE=src)
            kit = ""
            if nm_only:
                key_env = dict(KERNEL_SOURCE=src, NOMOUNT_PART="separate",
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
                # Our tuning is for the mzggr kernel only (Aigis keeps its own).
                "ksu_hook": e.get("KSU_HOOK", "manual"),
                "perf_tuning": e.get("PERF_TUNING", "false") if src == "mzggr" else "false",
                "network_fix": e.get("NETWORK_FIX", "true"), "kernel_release": "",
                # Valhall GPU is for the Aigis kernel only.
                "valhall_gpu": e.get("VALHALL_GPU", "false") if src == "aigis" else "false",
                "kernel_tag": e.get("KERNEL_TAG", ""),
                "kit_id": kit, "build_nomount": str(nomount_mode == "lkm").lower(),
            })

    kernel = out["build_kernel"] == "true"
    matrix = [x for x in entries if kernel or x["build_nomount"] == "true"]
    for i, x in enumerate(matrix):
        x["first"] = "true" if i == 0 else "false"
        print(f"{x['source']}: kernel ZIP {str(kernel).lower()}, NoMount LKM build {x['build_nomount']}, "
              f"kernel kit {x['kit_id'] or 'none'}")
    out["matrix"] = json.dumps(matrix, separators=(",", ":"))
    out["build_any"] = str(bool(matrix)).lower()
    emit(out)


if __name__ == "__main__":
    main()
