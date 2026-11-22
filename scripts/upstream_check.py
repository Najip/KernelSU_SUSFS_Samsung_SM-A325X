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
  bakasu        BakaSU (KSU_REPO / KSU_REF of KERNEL_SOURCE=aigis-bakasu, the
                BAKASU_BRANCH of sources.conf, sync-up by default), for Aigis BakaSU. When
                that branch is sync-up and it has been merged into BakaSU main,
                a warning says so (switch with "Switch BakaSU branch"; nothing
                is switched automatically).
  susfs         SUSFS_REPO / SUSFS_REF, only commits that touched SUSFS_PATCH
                (the 4.14 patch the build uses; the rest of that repo is
                other devices and does not change the kernel)
  nomount       NOMOUNT_REPO, master branch only (manual builds still default
                to dev). Commits that only touch docs (README, *.md, docs/,
                .github/) are ignored.

Only what changed is rebuilt, in one Build Kernel run (Kernel both, Root
flavor All, Latest, NoMount master) that publishes a Pre-release with every file. The plan
(plan= in $GITHUB_OUTPUT) says per kernel: kernel = build it (xxKSU or SUSFS
changed: both; one kernel tree changed: that one), nomount = keep its kernel
ZIP from the last automatic run and build only NoMount (NoMount changed),
reuse = keep all its files. "start" picks the earlier run (the last
automatic run, or the one that last built that kernel) and builds the kernel
anyway when that run did not succeed or its files have expired.

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


def patch_digest(repo, sha):
    """The code change of a commit (its added and removed lines per file, like
    git patch-id), so the same change rebased elsewhere gives the same value."""
    import hashlib
    files = api(f"repos/{repo}/commits/{sha}").get("files", [])
    h = hashlib.sha256()
    for f in sorted(files, key=lambda f: f["filename"]):
        h.update(f["filename"].encode() + b"\0" + f.get("status", "").encode() + b"\0")
        # Only the added and removed lines: nearby upstream code (context) may move.
        for ln in (f.get("patch") or "").splitlines():
            if ln[:1] in "+-":
                h.update(ln.encode() + b"\n")
    return h.hexdigest()


def drop_rebased(repo, old, new, data, commits):
    """A rewritten branch (backslashxx rebases xxKSU on every update): the
    compare lists the whole rebased stack again under new hashes. A commit
    whose title + author were already in the old commit's history is left out
    when its code change is the same, or marked "updated" when it changed.
    Returns (commits, number left out, set of updated shas)."""
    if data.get("status") != "diverged":
        return commits, 0, set()
    back = api(f"repos/{repo}/compare/{new}...{old}")
    key = lambda c: (c["commit"]["message"].splitlines()[0].strip(), c["commit"]["author"]["name"])
    before = {}
    for c in back.get("commits", []):
        before.setdefault(key(c), []).append(c["sha"])
    kept, updated, dropped = [], set(), 0
    for c in commits:
        olds = before.get(key(c))
        if not olds:
            kept.append(c)
            continue
        mine = patch_digest(repo, c["sha"])
        if any(patch_digest(repo, o) == mine for o in olds):
            dropped += 1
        else:
            kept.append(c)
            updated.add(c["sha"])
    return kept, dropped, updated


def new_commits(repo, old, new, path=None):
    """Lines for the commits in old..new (newest first) and their count."""
    dropped, updated = 0, set()
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
            out, dropped, updated = drop_rebased(repo, old, new, data, out)
            if dropped:
                total = len(out)
    except subprocess.CalledProcessError:
        # For example a force-push removed the old commit.
        return [f"- (could not list the commits since `{old[:12]}`, the branch was probably rewritten)"], 0
    lines = [f"- [`{c['sha'][:8]}`](https://github.com/{repo}/commit/{c['sha']}) "
             f"{'updated: ' if c['sha'] in updated else ''}{c['commit']['message'].splitlines()[0]}"
             for c in out[:MAX_LIST]]
    if total > MAX_LIST:
        lines.append(f"- ... and {total - MAX_LIST} more")
    if not path and dropped:
        lines.append(f"- ({dropped} older commits were only rebased and are left out.)")
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
    mz, ag, bk = conf(conf_path, "mzggr"), conf(conf_path, "aigis"), conf(conf_path, "aigis-bakasu")
    watched = {
        "mzggr": ("mzggr kernel", slug(mz["KERNEL_REPO"]), mz["KERNEL_REF"], None),
        "aigis": ("Aigis kernel", slug(ag["KERNEL_REPO"]), ag["KERNEL_REF"], None),
        "xxksu": ("xxKSU", slug(mz["KSU_REPO"]), mz["KSU_REF"], None),
        "bakasu": ("BakaSU", slug(bk["KSU_REPO"]), bk["KSU_REF"], None),
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
    merged = bakasu_merged(slug(bk["KSU_REPO"]), bk["KSU_REF"])
    if merged:
        print(f"::warning title=BakaSU sync-up merged into main::{merged}")
        Path("bakasu-merged.md").write_text(f"### BakaSU: sync-up is merged into main\n- {merged}\n")
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
    for k, mode in plan.items():
        print(f"Plan: {k} {mode}")
    emit({"changed": str(bool(changed)).lower(), "first": str(first).lower(), "changed_list": " ".join(changed),
          "moved": str(moved).lower(), "plan": json.dumps(plan, separators=(",", ":"))})


KERNELS = ("aigis", "aigis-bakasu", "mzggr")  # build order: the main kernel first


def bakasu_merged(repo, ref):
    """When the build uses BakaSU sync-up and sync-up is fully in main: a note."""
    if ref != "sync-up":
        return ""
    try:
        data = json.loads(subprocess.check_output(["gh", "api", f"repos/{repo}/compare/main...sync-up"], text=True))
    except subprocess.CalledProcessError:
        return ""
    if data.get("status") in ("behind", "identical"):
        return ("Every BakaSU sync-up commit is now in BakaSU main. Run Actions -> Switch BakaSU branch -> main "
                "when you want Aigis BakaSU to use main (nothing is switched automatically).")
    return ""


def build_plan(changed):
    """Per kernel: kernel (build), nomount (keep the kernel, build NoMount) or reuse."""
    c = set(changed)
    full = set(KERNELS) if "susfs" in c else set()
    if "xxksu" in c:
        full |= {"aigis", "mzggr"}
    if "bakasu" in c:
        full.add("aigis-bakasu")
    if "aigis" in c:
        full |= {"aigis", "aigis-bakasu"}  # the same Aigis tree
    if "mzggr" in c:
        full.add("mzggr")
    if not full and "nomount" not in changed:
        return {}
    return {k: "kernel" if k in full else ("nomount" if "nomount" in changed else "reuse") for k in KERNELS}


FILE_NAMES = {
    "aigis-kernel": "Main kernel ZIP (Aigis)",
    "aigis-bakasu-kernel": "Main kernel ZIP with BakaSU (Aigis BakaSU)",
    "mzggr-kernel": "Alt. kernel ZIP (mzggr)",
    "aigis-nomount": "NoMount module for Aigis",
    "aigis-bakasu-nomount": "NoMount module for Aigis BakaSU",
    "mzggr-nomount": "NoMount module for mzggr",
}


def title_ok(title):
    """Is this run-name the Build Kernel run the upstream check starts?"""
    return (title.startswith("A325X xxKSU/BakaSU + SUSFS kernel (Aigis + mzggr) (root All)") and "(Latest) (upstream)" in title
            and "NoMount lkm-master" in title and "+ Pre-release" in title)


def run_id(url):
    return url.rstrip("/").rsplit("/", 1)[-1] if url and url.startswith("http") else ""


def usable(repo, rid, kernel):
    """Did run rid succeed and are the files of this kernel still there?"""
    if not rid:
        return False
    run = json.loads(subprocess.check_output(["gh", "api", f"repos/{repo}/actions/runs/{rid}"], text=True))
    if run.get("conclusion") != "success":
        print(f"Run {rid}: {run.get('status')} {run.get('conclusion')}, not used for {kernel}.")
        return False
    arts = json.loads(subprocess.check_output(
        ["gh", "api", f"repos/{repo}/actions/runs/{rid}/artifacts?per_page=100"], text=True)).get("artifacts", [])
    name = "release-files" if kernel == "mzggr" else f"release-files-{kernel}"
    ok = any(a["name"] == name and not a.get("expired") for a in arts)
    if not ok:
        print(f"Run {rid}: {name} has expired, not used for {kernel}.")
    return ok


def start(state_path, plan_path, repo, ref):
    """Start the one Build Kernel run of plan.json (a Pre-release), and save in
    the state file which run built each file. Writes builds.md."""
    plan = json.loads(Path(plan_path).read_text())
    state = json.loads(Path(state_path).read_text())
    files = state.setdefault("files", {})
    last = run_id((state.get("last_build") or {}).get("run", ""))
    reuse = {}
    for k in KERNELS:
        mode = plan.get(k, "kernel")
        if mode != "kernel":
            built = run_id((files.get(f"{k}-kernel") or {}).get("run", ""))
            # nomount: the run that built this kernel has its kernel kit (no compile).
            # reuse: the last run has its newest NoMount module too.
            order = (built, last) if mode == "nomount" else (last, built)
            rid = next((r for r in order if usable(repo, r, k)), "")
            if not rid:
                print(f"{k}: no earlier run with its files, building it.")
                mode = "kernel"
            reuse[k] = {"mode": mode, "run": rid} if rid else {"mode": "kernel"}
        else:
            reuse[k] = {"mode": "kernel"}
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    seen = set(subprocess.check_output(
        ["gh", "run", "list", "--repo", repo, "--workflow", "kernel.yml", "--limit", "20",
         "--json", "url", "--jq", ".[].url"], text=True).split())
    subprocess.check_call(["gh", "workflow", "run", "kernel.yml", "--repo", repo, "--ref", ref,
                           "-f", "kernel_source=both", "-f", "root_flavor=All", "-f", "commit_mode=Latest", "-f", "release_type=Pre-release",
                           "-f", "nomount_branch=master", "-f", "nomount_only=false",
                           "-f", f"reuse={json.dumps(reuse, separators=(',', ':'))}"])
    url = title = ""
    for _ in range(12):
        time.sleep(5)
        runs = json.loads(subprocess.check_output(
            ["gh", "run", "list", "--repo", repo, "--workflow", "kernel.yml", "--branch", ref,
             "--event", "workflow_dispatch", "--limit", "10", "--json", "url,displayTitle"], text=True))
        new = [r for r in runs if r["url"] not in seen]
        if new:
            url, title = new[-1]["url"], new[-1]["displayTitle"]
            break
    print(f"Build Kernel: {url or 'started'} {title}")
    if url and not title_ok(title):
        sys.exit(f"::error::The started build is not the planned upstream Pre-release: {title}")
    rebuilt = set()
    for k, r in reuse.items():
        if r["mode"] == "kernel":
            rebuilt |= {f"{k}-kernel", f"{k}-nomount"}
        elif r["mode"] == "nomount":
            rebuilt.add(f"{k}-nomount")
    for f in rebuilt:
        files[f] = {"run": url or "started", "date": now}
    state["last_build"] = {"run": url or "started", "date": now, "plan": reuse}
    if state.get("history"):
        state["history"][0]["build"] = {"run": url or "started", "plan": reuse}
    Path(state_path).write_text(json.dumps(state, indent=2) + "\n")
    md = [f"Pre-release run: {url or 'started'}", "", "| File | Built in run | |", "|---|---|---|"]
    for f, label in FILE_NAMES.items():
        info = files.get(f)
        where = f"[{info['date'][:10]}]({info['run']})" if info and info["run"].startswith("http") else \
            (info["run"] if info else "-")
        md.append(f"| {label} | {where} | {'new build' if f in rebuilt else 'no update, reused'} |")
    Path("builds.md").write_text("\n".join(md) + "\n")


if __name__ == "__main__":
    if len(sys.argv) == 6 and sys.argv[1] == "start":
        start(*sys.argv[2:])
    elif len(sys.argv) == 3:
        main(sys.argv[1], sys.argv[2])
    else:
        sys.exit(__doc__)
