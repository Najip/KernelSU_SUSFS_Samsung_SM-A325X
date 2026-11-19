#!/usr/bin/env python3
"""Find and read the build that commit mode Promoted takes its files from.

  promoted_source.py find
    Finds the most recent successful "Build Kernel" run with commit mode
    Latest on $BRANCH whose kernel ZIP has not expired yet. Writes
    source_run, source_url and source_sha to $GITHUB_OUTPUT.

  promoted_source.py inspect <artifacts folder>
    Reads the downloaded artifacts of that run. Writes the commits
    (kernel_ref, ksu_ref, susfs_ref and *_branch), hook, tuning,
    kernel_release, build_sha and has_nomount to $GITHUB_OUTPUT.

  promoted_source.py collect <artifacts folder> <output folder>
    Copies the kernel ZIP, build-info.txt, sources.json and any NoMount files
    (into <output>/nomount) and writes SHA256SUMS.txt.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

WORKFLOW = "kernel.yml"


def fail(message):
    print(f"::error::{message}", file=sys.stderr)
    sys.exit(1)


def emit(pairs):
    lines = "".join(f"{key}={value}\n" for key, value in pairs.items())
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(lines)
    print(lines, end="")


def api(path):
    out = subprocess.check_output(["gh", "api", path], text=True)
    return json.loads(out)


def find():
    repo = os.environ["GITHUB_REPOSITORY"]
    branch = os.environ.get("BRANCH", "main")
    runs = api(f"repos/{repo}/actions/workflows/{WORKFLOW}/runs?branch={branch}&status=success&per_page=100")
    for run in runs.get("workflow_runs", []):
        title = run.get("display_title", "")
        # run-name contains "(Latest)" for commit mode Latest.
        if "(Latest)" not in title:
            continue
        arts = api(f"repos/{repo}/actions/runs/{run['id']}/artifacts?per_page=100").get("artifacts", [])
        live = [a["name"] for a in arts if not a.get("expired")]
        has_zip = any(n.startswith("A325X-") and n.endswith(".zip") for n in live) or "release-files" in live
        has_sources = "release-files" in live or any(n.startswith("build-logs-") for n in live)
        if not (has_zip and has_sources):
            print(f"Skipping run {run['id']} ({title}): its files have expired.")
            continue
        print(f"Taking the files of run {run['id']}: {title}")
        emit({
            "source_run": run["id"],
            "source_url": run["html_url"],
            "source_sha": run["head_sha"],
            "source_title": title.replace("\n", " "),
        })
        return
    fail(f"No successful Latest build with files left on {branch}. Run one with commit mode Latest first.")


def locate(folder):
    folder = Path(folder)
    zips = sorted({p.name: p for p in folder.rglob("A325X-*.zip")}.values())
    if not zips:
        fail("The Latest run has no kernel ZIP.")
    if len(zips) > 1:
        fail("The Latest run has more than one kernel ZIP: " + ", ".join(p.name for p in zips))
    sources = [p for p in folder.rglob("sources.json")]
    if not sources:
        fail("The Latest run has no sources.json.")
    # Prefer the packaged copy (it also has build_repo).
    sources.sort(key=lambda p: ("release-files" not in p.parts, len(p.parts)))
    infos = [p for p in folder.rglob("build-info.txt") if "nomount" not in p.parts]
    if not infos:
        fail("The Latest run has no build-info.txt.")
    nomount = sorted({p.name: p for p in folder.rglob("*") if p.is_file() and "nomount" in p.parts}.values())
    return zips[0], sources[0], infos[0], nomount


def info_value(text, label):
    for line in text.splitlines():
        if line.startswith(label + ":"):
            return line.split(":", 1)[1].strip()
    return ""


def inspect(folder):
    zip_path, sources_path, info_path, nomount = locate(folder)
    src = json.loads(sources_path.read_text())
    info = info_path.read_text()
    out = {}
    for key, ref_out, branch_out in (("kernel", "kernel_ref", "kernel_branch"),
                                     ("xxksu", "ksu_ref", "ksu_branch"),
                                     ("susfs", "susfs_ref", "susfs_branch")):
        item = src.get(key) or {}
        if not item.get("commit"):
            fail(f"sources.json of the Latest run has no {key} commit.")
        out[ref_out] = item["commit"]
        out[branch_out] = item.get("branch") or ""
    hook = info_value(info, "xxKSU hook style") or "manual"
    tuning = info_value(info, "Performance tuning") or "false"
    has_ko = any(p.suffix == ".ko" for p in nomount)
    has_nm_zip = any(p.name.startswith("NoMount-") and p.suffix == ".zip" for p in nomount)
    out.update({
        "zip_name": zip_path.stem,
        "hook": hook,
        "tuning": tuning,
        "kernel_release": info_value(info, "Kernel release"),
        "build_sha": (src.get("build_repo") or {}).get("commit", ""),
        "has_nomount": str(has_ko and has_nm_zip).lower(),
    })
    emit(out)


def collect(folder, dest):
    zip_path, sources_path, info_path, nomount = locate(folder)
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    for p in (zip_path, sources_path, info_path):
        shutil.copy2(p, dest / p.name)
    if nomount:
        (dest / "nomount").mkdir(exist_ok=True)
        for p in nomount:
            shutil.copy2(p, dest / "nomount" / p.name)
    digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    (dest / "SHA256SUMS.txt").write_text(f"{digest}  {zip_path.name}\n")
    for p in sorted(dest.rglob("*")):
        print(p.relative_to(dest))


if __name__ == "__main__":
    if sys.argv[1:2] == ["find"] and len(sys.argv) == 2:
        find()
    elif sys.argv[1:2] == ["inspect"] and len(sys.argv) == 3:
        inspect(sys.argv[2])
    elif sys.argv[1:2] == ["collect"] and len(sys.argv) == 4:
        collect(sys.argv[2], sys.argv[3])
    else:
        sys.exit(__doc__)
