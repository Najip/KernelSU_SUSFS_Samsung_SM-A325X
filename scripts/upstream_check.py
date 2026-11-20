#!/usr/bin/env python3
"""Upstream checker: did any kernel source get new commits since the last check?

  upstream_check.py <sources.conf> <state.json>

Watched (NoMount is not watched):
  mzggr kernel  KERNEL_REPO / KERNEL_REF of KERNEL_SOURCE=mzggr
  aigis kernel  KERNEL_REPO / KERNEL_REF of KERNEL_SOURCE=aigis
  xxksu         KSU_REPO / KSU_REF
  susfs         SUSFS_REPO / SUSFS_REF, only commits that touched SUSFS_PATCH
                (the 4.14 patch the build uses; the rest of that repo is
                other devices and does not change the kernel)

The state file keeps the newest commit seen of each source and a short
history of the changes found. The first check only saves the commits
(nothing to compare with yet). Writes changed=true|false and first=true|false
to $GITHUB_OUTPUT, the new commits to changes.md and the commits seen to
sources.md.
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

MAX_LIST = 20
MAX_HISTORY = 50


def conf(path, source):
    """Values of sources.conf for one KERNEL_SOURCE (the file is bash)."""
    keys = ["KERNEL_REPO", "KERNEL_REF", "KSU_REPO", "KSU_REF", "SUSFS_REPO", "SUSFS_REF", "SUSFS_PATCH"]
    script = f'KERNEL_SOURCE={source}; . "$1" >/dev/null; ' + "; ".join(f'echo "{k}=${{{k}}}"' for k in keys)
    out = subprocess.check_output(["bash", "-c", script, "conf", path], text=True,
                                  env={k: v for k, v in os.environ.items()
                                       if not k.startswith(("KERNEL_", "KSU_", "SUSFS_"))})
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
    }
    state_file = Path(state_path)
    state = json.loads(state_file.read_text()) if state_file.exists() else {}
    old = state.get("sources", {})
    first = not old
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    sources, report, changed = {}, [], []
    for key, (label, repo, ref, path) in watched.items():
        cur = head(repo, ref, path)
        cur.update({"name": label, "repo": f"https://github.com/{repo}", "branch": ref})
        if path:
            cur["path"] = path
        sources[key] = cur
        prev = old.get(key)
        if prev and (prev.get("repo") != cur["repo"] or prev.get("branch") != ref):
            prev = None  # the build now uses another repo or branch: start over for it
        if prev is None:
            if not first:
                changed.append(key)
                report += [f"### {label}: now watching {repo} `{ref}`", f"- `{cur['commit'][:8]}` {cur['subject']}", ""]
            print(f"{label}: {repo}@{ref} {cur['commit'][:12]} (saved)")
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
    Path("sources.md").write_text("".join(
        f"- {v['name']}: {v['repo']} `{v['branch']}` @ `{v['commit'][:12]}` ({v['date']})\n" for v in sources.values()))
    emit({"changed": str(bool(changed)).lower(), "first": str(first).lower(), "changed_list": " ".join(changed)})


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
