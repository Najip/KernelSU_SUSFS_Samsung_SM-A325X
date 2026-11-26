#!/usr/bin/env python3
"""Find and read the build that commit mode Promoted takes its files from.

  promoted_source.py find
    Finds the most recent successful "Build Kernel" run with commit mode
    Latest and the default kernel options (NoMount not built in, not a
    NoMount-only run, compiler aigis) on $BRANCH that built every kernel in
    $SOURCES ("aigis-bakasu aigis-xxksu"; older runs: "mzggr", "aigis") and whose
    files have not expired yet. Runner, release type, the Aigis GPU
    (Valhall or stock) and whether the NoMount LKM was built do not matter. Writes
    source_run, source_url and source_sha to $GITHUB_OUTPUT.

  promoted_source.py download <run id> <artifacts folder>
    Downloads the release-files-<kernel> artifacts of that run (aigis-bakasu,
    aigis-xxksu; older runs: mzggr, aigis) into <folder>/<kernel> (only the
    kernels in $ONLY when it is set).

  promoted_source.py inspect <artifacts folder>/<source>
    Reads the downloaded files of one kernel of that run. Writes the commits
    (kernel_ref, ksu_ref, susfs_ref and *_branch), hook, tuning, valhall_gpu,
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
# Artifact with the release files of each kernel.
ARTIFACT = {"mzggr": "release-files", "aigis": "release-files-aigis",
            "aigis-bakasu": "release-files-aigis-bakasu", "aigis-xxksu": "release-files-aigis-xxksu"}


def built_sources(title):
    """Kernels a Build Kernel run built, from its run-name (older runs: mzggr)."""
    # Runs since 26 Nov 2026: BakaSU and/or xxKSU on Aigis.
    if title.startswith("A325X BakaSU + xxKSU + SUSFS kernel (Aigis)"):
        return {"aigis-bakasu", "aigis-xxksu"}
    if title.startswith("A325X xxKSU + SUSFS kernel (Aigis)"):
        return {"aigis-xxksu"}
    # Runs since 23 Nov 2026 build Aigis BakaSU only.
    if title.startswith("A325X BakaSU + SUSFS kernel (Aigis)"):
        return {"aigis-bakasu"}
    if "(Aigis + mzggr)" in title or "(mzggr + Aigis)" in title:  # older runs: mzggr + Aigis
        built = {"mzggr", "aigis"}
    elif "(Aigis)" in title:
        built = {"aigis"}
    else:
        built = {"mzggr"}
    # Root flavor (newer runs): "(root BakaSU)" = Aigis BakaSU only,
    # "(root All)" = the older kernels plus Aigis BakaSU.
    if "(root BakaSU)" in title:
        return {"aigis-bakasu"} if "aigis" in built else set()
    if "(root All)" in title and "aigis" in built:
        built.add("aigis-bakasu")
    return built


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
    wanted = set(os.environ.get("SOURCES", "mzggr").split())
    for run in runs.get("workflow_runs", []):
        title = run.get("display_title", "")
        # run-name contains "(Latest)" for commit mode Latest.
        if "(Latest)" not in title:
            continue
        # Older runs: only the default options.
        if ("[syscall_table]" in title or "[branch_link]" in title or "integrate" in title or "LKM only" in title
                or "(main compiler)" in title):
            print(f"Skipping run {run['id']} ({title}): not the default options.")
            continue
        built = built_sources(title)
        if not wanted <= built:
            print(f"Skipping run {run['id']} ({title}): did not build {' and '.join(sorted(wanted - built))}.")
            continue
        arts = api(f"repos/{repo}/actions/runs/{run['id']}/artifacts?per_page=100").get("artifacts", [])
        live = {a["name"] for a in arts if not a.get("expired")}
        if not all(ARTIFACT[s] in live for s in wanted):
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
    kernels = " and ".join(sorted(wanted))
    message = (f"Nothing to promote: no successful Latest build of {kernels} with the default options "
               f"(NoMount not built in, compiler aigis) with files left on {branch}. Run Build Kernel with commit "
               f"mode Latest first, then run Promoted again.")
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
    only = os.environ.get("ONLY", "").split()
    for source, name in ARTIFACT.items():
        if only and source not in only:
            continue
        art = next((a for a in arts if a["name"] == name and not a.get("expired")), None)
        if not art:
            continue
        data = subprocess.check_output(["gh", "api", f"repos/{repo}/actions/artifacts/{art['id']}/zip"])
        target = folder / source / name
        target.mkdir(parents=True, exist_ok=True)
        tmp = folder / f".{name}.zip"
        tmp.write_bytes(data)
        with zipfile.ZipFile(tmp) as z:
            z.extractall(target)
        tmp.unlink()
        print(f"Downloaded {name} ({len(data)} bytes) to {target}")


def locate(folder):
    folder = Path(folder)
    # Unarchived artifacts are downloaded as <name>/<name>, so only look at files.
    every = sorted({p.name: p for p in folder.rglob("A325X-*.zip") if p.is_file()}.values())
    # The Aigis Valhall build also has <name>-valhall.zip next to the kernel ZIP.
    zips = [p for p in every if not p.name.endswith("-valhall.zip")]
    extras = [p for p in every if p.name.endswith("-valhall.zip")]
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
    return zips[0], sources[0], infos[0], nomount, extras


def info_value(text, label):
    for line in text.splitlines():
        if line.startswith(label + ":"):
            return line.split(":", 1)[1].strip()
    return ""


def inspect(folder):
    zip_path, sources_path, info_path, nomount, _ = locate(folder)
    src = json.loads(sources_path.read_text())
    if "ksu" not in src and "xxksu" in src:  # builds before 24 Nov 2026
        src["ksu"] = src.pop("xxksu")
    info = info_path.read_text()
    out = {}
    for key, ref_out, branch_out in (("kernel", "kernel_ref", "kernel_branch"),
                                     ("ksu", "ksu_ref", "ksu_branch"),
                                     ("susfs", "susfs_ref", "susfs_branch")):
        item = src.get(key) or {}
        if not item.get("commit"):
            fail(f"sources.json of the Latest run has no {key} commit.")
        out[ref_out] = item["commit"]
        out[branch_out] = item.get("branch") or ""
    hook = "manual"  # the only hook option of this workflow (BakaSU uses its SUSFS inline hooks)
    tuning = info_value(info, "Performance tuning") or "false"
    nm_line = info_value(info, "NoMount")
    if nm_line.startswith("built into"):
        fail(f"The Latest run does not use the default options (NoMount {nm_line}).")
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
        # Aigis GPU of that run (mzggr is always the stock GPU).
        "valhall_gpu": str(info_value(info, "GPU").startswith("Aigis Valhall")).lower(),
        "kernel_release": info_value(info, "Kernel release"),
        # Older runs had no uname tag.
        "kernel_tag": "" if info_value(info, "uname tag") in ("", "none") else info_value(info, "uname tag"),
        "build_sha": (src.get("build_repo") or {}).get("commit", ""),
        "has_nomount": str(has_ko and has_nm_zip).lower(),
        "network_fix": "false" if info_value(info, "Network fix (UDP GSO)") == "not applied" else "true",
        "nomount_branch": nm_branch,
    })
    emit(out)


def collect(folder, dest):
    zip_path, sources_path, info_path, nomount, extras = locate(folder)
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    for p in (zip_path, sources_path, info_path, *extras):
        shutil.copy2(p, dest / p.name)
    if nomount:
        (dest / "nomount").mkdir(exist_ok=True)
        for p in nomount:
            shutil.copy2(p, dest / "nomount" / p.name)
    sums = "".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n" for p in (zip_path, *extras))
    (dest / "SHA256SUMS.txt").write_text(sums)
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
