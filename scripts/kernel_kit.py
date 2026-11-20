#!/usr/bin/env python3
"""Kernel kit: the few files from a full kernel build that an out-of-tree
module needs (.config, Module.symvers, kernel.release). With them, the NoMount
LKM can be built for that exact kernel without compiling the kernel again.

  kernel_kit.py key
    Prints the kit key for the kernel described by the environment:
    KERNEL_REF, KSU_REF, SUSFS_REF (full commits), KSU_HOOK, PERF_TUNING,
    NOMOUNT_PART (separate, or integrate@<commit>) plus the build-repo files
    that change the kernel (patches, configs, build scripts).

  kernel_kit.py find <key>
    Finds the newest unexpired artifact kernel-kit-<key> in this repo and
    writes kit_id and kit_run to $GITHUB_OUTPUT (empty when none).

  kernel_kit.py in-run <run id>
    Same, for the kernel-kit-* artifact of one run.

  kernel_kit.py download <artifact id> <folder>
"""
import hashlib
import io
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Build-repo paths that change the compiled kernel.
TRACKED = ("patches", "configs", "scripts/prepare_sources.sh", "scripts/build_kernel.sh",
           "scripts/sources.conf", "scripts/aosp_clang14.conf",
           "scripts/zyc_clang14.conf", "scripts/fetch_zyc_clang.sh")


def emit(pairs):
    lines = "".join(f"{k}={v}\n" for k, v in pairs.items())
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(lines)
    print(lines, end="")


def api(path):
    return json.loads(subprocess.check_output(["gh", "api", path], text=True))


def key():
    e = os.environ
    parts = [f"kernel={e['KERNEL_REF']}", f"xxksu={e['KSU_REF']}", f"susfs={e['SUSFS_REF']}",
             f"hook={e.get('KSU_HOOK', 'branch_link')}", f"tuning={e.get('PERF_TUNING', 'false')}",
             f"nomount={e.get('NOMOUNT_PART', 'separate')}"]
    # Older kits were made before the network fix became optional (always on).
    if e.get("NETWORK_FIX", "true") != "true":
        parts.append("network_fix=false")
    if e.get("VALHALL_GPU", "false") == "true":
        parts.append("gpu=valhall")
    if e.get("KERNEL_TOOLCHAIN", "zyc") == "aosp":
        parts.append("cc=aosp")
    for path in TRACKED:
        oid = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", f"HEAD:{path}"], text=True).strip()
        parts.append(f"{path}={oid}")
    digest = hashlib.sha256("\n".join(parts).encode()).hexdigest()[:20]
    print(digest)


def pick(arts, test):
    live = [a for a in arts if not a.get("expired") and test(a["name"])]
    live.sort(key=lambda a: a.get("created_at", ""), reverse=True)
    if live:
        a = live[0]
        emit({"kit_id": a["id"], "kit_run": a.get("workflow_run", {}).get("id", "")})
    else:
        emit({"kit_id": "", "kit_run": ""})


def find(k):
    repo = os.environ["GITHUB_REPOSITORY"]
    arts = api(f"repos/{repo}/actions/artifacts?name=kernel-kit-{k}&per_page=20").get("artifacts", [])
    pick(arts, lambda n: n == f"kernel-kit-{k}")


def in_run(run_id):
    repo = os.environ["GITHUB_REPOSITORY"]
    arts = api(f"repos/{repo}/actions/runs/{run_id}/artifacts?per_page=100").get("artifacts", [])
    pick(arts, lambda n: n.startswith("kernel-kit-"))


def download(art_id, folder):
    repo = os.environ["GITHUB_REPOSITORY"]
    data = subprocess.check_output(["gh", "api", f"repos/{repo}/actions/artifacts/{art_id}/zip"])
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        z.extractall(folder)
    for name in (".config", "Module.symvers", "kernel.release"):
        if not (folder / name).is_file():
            sys.exit(f"::error::Kernel kit has no {name}")
    print("Kernel kit for", (folder / "kernel.release").read_text().strip())


if __name__ == "__main__":
    a = sys.argv[1:]
    if a == ["key"]:
        key()
    elif len(a) == 2 and a[0] == "find":
        find(a[1])
    elif len(a) == 2 and a[0] == "in-run":
        in_run(a[1])
    elif len(a) == 3 and a[0] == "download":
        download(a[1], a[2])
    else:
        sys.exit(__doc__)
