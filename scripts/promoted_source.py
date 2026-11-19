#!/usr/bin/env python3
"""Find and read the build that commit mode Promoted takes its files from.

  promoted_source.py find
    Finds the most recent successful "Build Kernel" run with commit mode
    Latest and the default kernel options (hook branch_link, no tuning,
    NoMount not built in, not a NoMount-only run) on $BRANCH whose files
    have not expired yet. Runner, release type and whether the NoMount LKM
    was built do not matter. Writes
    source_run, source_url and source_sha to $GITHUB_OUTPUT.

  promoted_source.py download <run id> <artifacts folder>
    Downloads the kernel ZIP, build-info.txt, release-files and build logs of
    that run. Files uploaded unarchived (the kernel ZIP, build-info.txt) are
    kept byte for byte; the others are unpacked into a folder of their name.

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
        if "(tuning)" in title:
            print(f"Skipping run {run['id']} ({title}): built with tuning (releases are without tuning).")
            continue
        if "[branch_link]" not in title or "integrate" in title or "LKM only" in title:
            print(f"Skipping run {run['id']} ({title}): not the default options.")
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
            "found": "true",
            "source_run": run["id"],
            "source_url": run["html_url"],
            "source_sha": run["head_sha"],
            "source_title": title.replace("\n", " "),
        })
        return
    message = (f"Nothing to promote: no successful Latest build without tuning (hook branch_link, NoMount not "
               f"built in) with files left on {branch}. Run Build Kernel with commit mode Latest and "
               f"Performance tuning unticked first, then run Promoted again.")
    print(f"::warning title=Nothing promoted::{message}")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write(f"### Nothing promoted\n\n{message}\n")
    emit({"found": "false"})


def download(run_id, folder):
    import zipfile
    repo = os.environ["GITHUB_REPOSITORY"]
    folder = Path(folder)
    arts = api(f"repos/{repo}/actions/runs/{run_id}/artifacts?per_page=100").get("artifacts", [])
    for art in arts:
        name = art["name"]
        if art.get("expired"):
            continue
        raw = name.startswith("A325X-") and name.endswith(".zip") or name == "build-info.txt"
        if not (raw or name == "release-files" or name.startswith("build-logs-")):
            continue
        data = subprocess.check_output(["gh", "api", f"repos/{repo}/actions/artifacts/{art['id']}/zip"])
        target = folder / name
        target.mkdir(parents=True, exist_ok=True)
        if raw:
            (target / name).write_bytes(data)
        else:
            tmp = folder / f".{name}.zip"
            tmp.write_bytes(data)
            with zipfile.ZipFile(tmp) as z:
                z.extractall(target)
            tmp.unlink()
        print(f"Downloaded {name} ({len(data)} bytes)")


def locate(folder):
    folder = Path(folder)
    # Unarchived artifacts are downloaded as <name>/<name>, so only look at files.
    zips = sorted({p.name: p for p in folder.rglob("A325X-*.zip") if p.is_file()}.values())
    if not zips:
        fail("The Latest run has no kernel ZIP.")
    if len(zips) > 1:
        fail("The Latest run has more than one kernel ZIP: " + ", ".join(p.name for p in zips))
    sources = [p for p in folder.rglob("sources.json") if p.is_file()]
    if not sources:
        fail("The Latest run has no sources.json.")
    # Prefer the packaged copy (it also has build_repo).
    sources.sort(key=lambda p: ("release-files" not in p.parts, len(p.parts)))
    infos = [p for p in folder.rglob("build-info.txt") if p.is_file() and "nomount" not in p.parts]
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
    nm_line = info_value(info, "NoMount")
    if hook != "branch_link" or tuning != "false" or nm_line.startswith("built into"):
        fail(f"The Latest run does not use the default options (hook {hook}, tuning {tuning}, NoMount {nm_line or 'LKM'}).")
    has_ko = any(p.suffix == ".ko" for p in nomount)
    nm_zips = [p.name for p in nomount if p.name.startswith("NoMount-") and p.suffix == ".zip"]
    has_nm_zip = bool(nm_zips)
    nm_branch = ""
    if has_ko and nm_zips:
        import re
        m = re.match(r"NoMount-[^-]+-(dev|master)-lkm-", nm_zips[0])
        nm_branch = m.group(1) if m else ""
    out.update({
        "zip_name": zip_path.stem,
        "hook": hook,
        "tuning": tuning,
        "kernel_release": info_value(info, "Kernel release"),
        "build_sha": (src.get("build_repo") or {}).get("commit", ""),
        "has_nomount": str(has_ko and has_nm_zip).lower(),
        "nomount_branch": nm_branch,
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
    elif sys.argv[1:2] == ["download"] and len(sys.argv) == 4:
        download(sys.argv[2], sys.argv[3])
    elif sys.argv[1:2] == ["inspect"] and len(sys.argv) == 3:
        inspect(sys.argv[2])
    elif sys.argv[1:2] == ["collect"] and len(sys.argv) == 4:
        collect(sys.argv[2], sys.argv[3])
    else:
        sys.exit(__doc__)
