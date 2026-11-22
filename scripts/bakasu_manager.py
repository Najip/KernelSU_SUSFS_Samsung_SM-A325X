#!/usr/bin/env python3
"""Get the BakaSU manager APK that matches the BakaSU commit of the kernel.

  bakasu_manager.py <BakaSU commit> <branch> <out folder>

BakaSU has no releases for every commit: its manager is built by its own
"Build Manager" workflow (.github/workflows/build-manager.yml) on every push.
That run's "Manager-release" artifact has the APKs, named like
BakaSU_v4.2.0-rc3_35284-arm64-v8a-release.apk (the same file BakaSU posts to
Telegram). The kernel and the manager of the same commit have the same
version code (30000 + commit count + 700).

  1. A successful push run of exactly that commit: used.
  2. That run is still building: waited for (up to 45 minutes).
  3. No run for that commit (BakaSU only builds the manager when manager/,
     kernel/ or userspace/ changed): the newest successful run of an earlier
     commit of the same branch is used, with a warning.
Otherwise it fails. Writes <out>/<apk> (original name, arm64-v8a release) and
<out>/manager-bakasu.json; apk=<name> to $GITHUB_OUTPUT.
"""
import hashlib
import io
import json
import os
import subprocess
import sys
import time
import zipfile
from pathlib import Path

REPO = os.environ.get("BAKASU_REPO", "Baka-SU/BakaSU")
WORKFLOW = "build-manager.yml"
ARTIFACT = "Manager-release"
WAIT_MINUTES = 45


def api(path, raw=False):
    out = subprocess.check_output(["gh", "api", path], text=not raw)
    return out if raw else json.loads(out)


def fail(message):
    print(f"::error title=BakaSU manager::{message}")
    sys.exit(1)


def emit(pairs):
    path = os.environ.get("GITHUB_OUTPUT")
    lines = "".join(f"{k}={v}\n" for k, v in pairs.items())
    if path:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(lines)
    print(lines, end="")


def runs(branch):
    q = f"repos/{REPO}/actions/workflows/{WORKFLOW}/runs?event=push&per_page=50"
    if branch:
        q += f"&branch={branch}"
    return api(q).get("workflow_runs", [])


def pick(commit, branch):
    waited = 0
    while True:
        mine = [r for r in runs(branch) if r["head_sha"] == commit]
        done = [r for r in mine if r.get("conclusion") == "success"]
        if done:
            return done[0], True
        busy = [r for r in mine if r.get("status") in ("queued", "in_progress", "waiting", "pending", "requested")]
        if busy and waited < WAIT_MINUTES:
            print(f"BakaSU manager build for {commit[:12]} is still running ({busy[0]['html_url']}), waiting...")
            time.sleep(60)
            waited += 1
            continue
        break
    for r in runs(branch):
        if r.get("conclusion") != "success":
            continue
        status = api(f"repos/{REPO}/compare/{r['head_sha']}...{commit}").get("status")
        if status in ("ahead", "identical"):
            print(f"::warning title=BakaSU manager::No BakaSU manager build for commit {commit[:12]} "
                  f"(BakaSU builds it only when manager/, kernel/ or userspace/ change). Using the one of the "
                  f"earlier commit {r['head_sha'][:12]}: {r['html_url']}")
            return r, False
    fail(f"No successful BakaSU Build Manager run for commit {commit[:12]} or an earlier commit"
         f"{' on ' + branch if branch else ''}. See https://github.com/{REPO}/actions/workflows/{WORKFLOW}")


def main(commit, branch, out):
    if not commit:
        fail("No BakaSU commit given.")
    run, exact = pick(commit, branch)
    arts = api(f"repos/{REPO}/actions/runs/{run['id']}/artifacts?per_page=100").get("artifacts", [])
    art = next((a for a in arts if a["name"] == ARTIFACT and not a.get("expired")), None)
    if not art:
        fail(f"The BakaSU run {run['html_url']} has no {ARTIFACT} artifact (expired?).")
    try:
        data = api(f"repos/{REPO}/actions/artifacts/{art['id']}/zip", raw=True)
    except subprocess.CalledProcessError:
        # The workflow token may not be allowed to download another repo's
        # artifacts; nightly.link serves artifacts of public repos.
        import urllib.request
        url = f"https://nightly.link/{REPO}/actions/artifacts/{art['id']}.zip"
        print(f"GitHub API download refused, trying {url}")
        with urllib.request.urlopen(url, timeout=300) as resp:
            data = resp.read()
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names = [n for n in z.namelist() if n.endswith("-arm64-v8a-release.apk")]
        if len(names) != 1:
            fail(f"Expected one *-arm64-v8a-release.apk in {ARTIFACT}, found: {', '.join(z.namelist())}")
        apk = os.path.basename(names[0])
        (out / apk).write_bytes(z.read(names[0]))
    with zipfile.ZipFile(out / apk) as z:
        if "AndroidManifest.xml" not in z.namelist():
            fail(f"{apk} is not an Android app.")
    sha = hashlib.sha256((out / apk).read_bytes()).hexdigest()
    info = {
        "repo": f"https://github.com/{REPO}",
        "tag": f"Build Manager #{run['run_number']}",
        "url": run["html_url"],
        "date": run.get("created_at", ""),
        "branch": run.get("head_branch", branch),
        "commit": run["head_sha"],
        "kernel_commit": commit,
        "exact": exact,
        "apk": apk,
        "sha256": sha,
    }
    (out / "manager-bakasu.json").write_text(json.dumps(info, indent=2) + "\n")
    print(json.dumps(info, indent=2))
    emit({"apk": apk})
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write(f"### BakaSU manager: `{apk}`\n"
                         f"From [{info['tag']}]({run['html_url']}) of BakaSU `{run['head_sha'][:12]}`"
                         f"{'' if exact else f' (no build for the kernel commit `{commit[:12]}`, earlier one used)'}"
                         f", SHA256 `{sha}`\n")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    main(*sys.argv[1:])
