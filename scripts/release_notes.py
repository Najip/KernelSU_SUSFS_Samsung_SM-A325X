#!/usr/bin/env python3
"""Release helper: writes release notes and refreshes the README sources table.

  release_notes.py notes  <sources.json> <previous-sources.json|-> <build-info.txt> <out.md>
  release_notes.py readme <README.md> <release-tag> <sources.json>...

"What's new" lists, for every upstream source, the commits added since the
sources.json that was attached to the previous release. For the SUSFS repo only
commits that touched the 4.14 patch file are listed.
"""
import json
import os
import sys
import urllib.request

API = "https://api.github.com/"
MAX_LIST = 60


def api(path):
    req = urllib.request.Request(API + path, headers={"Accept": "application/vnd.github+json"})
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def slug(url):
    return url.rstrip("/").removeprefix("https://github.com/").removesuffix(".git")


def line(repo, c):
    sha = c["sha"]
    msg = c["commit"]["message"].splitlines()[0]
    return f"- [`{sha[:8]}`](https://github.com/{repo}/commit/{sha}) {msg}"


def new_commits(repo, old, new, path=None):
    """Return (lines, total) of commits in old..new (newest first)."""
    if old == new:
        return [], 0
    if path:
        out, page = [], 1
        while page <= 5:
            batch = api(f"repos/{repo}/commits?sha={new}&path={path}&per_page=100&page={page}")
            if not batch:
                break
            for c in batch:
                if c["sha"] == old:
                    return [line(repo, x) for x in out], len(out)
                out.append(c)
            page += 1
        # old commit did not touch the path: stop at its date instead
        old_date = api(f"repos/{repo}/commits/{old}")["commit"]["committer"]["date"]
        out = [c for c in out if c["commit"]["committer"]["date"] > old_date]
        return [line(repo, x) for x in out], len(out)
    data = api(f"repos/{repo}/compare/{old}...{new}")
    commits = list(reversed(data.get("commits", [])))
    return [line(repo, c) for c in commits], data.get("total_commits", len(commits))


SOURCES = [
    ("kernel", "Kernel source", None),
    ("xxksu", "xxKSU", None),
    ("susfs", "SUSFS patch (JackA1ltman)", "path"),
    ("build_repo", "This build repo", None),
]


def notes(cur_path, prev_path, info_path, out_path):
    cur = json.load(open(cur_path))
    prev = json.load(open(prev_path)) if prev_path != "-" and os.path.exists(prev_path) else None
    md = ["## What's new since the last release" if prev else "## First release", ""]
    for key, title, path_key in SOURCES:
        if key not in cur:
            continue
        s = cur[key]
        repo = slug(s["repo"])
        head = f"### {title}: [`{s['commit'][:8]}`](https://github.com/{repo}/commit/{s['commit']})"
        md.append(head)
        old = prev.get(key, {}).get("commit") if prev else None
        old_repo = slug(prev.get(key, {}).get("repo", "")) if prev else ""
        if old and old_repo and old_repo != repo:
            md.append(f"- Source changed from [{old_repo}](https://github.com/{old_repo}) to this repo.")
            old = None
        if not old:
            detail = s.get("subject") or (f"patch last changed {s['patch_date'][:10]}" if s.get("patch_date") else "")
            md.append(f"- Current commit{': ' + detail if detail else '.'}")
        elif old == s["commit"]:
            md.append("- No new commits.")
        else:
            try:
                lines, total = new_commits(repo, old, s["commit"], s.get(path_key) if path_key else None)
            except Exception as exc:  # network / force-push: still publish
                lines, total = [f"- Could not list commits ({exc})."], 0
            if not lines and total == 0:
                lines = ["- No new commits that change the SUSFS 4.14 patch." if path_key else "- No new commits."]
            md.extend(lines[:MAX_LIST])
            if total > MAX_LIST:
                md.append(f"- ...and {total - MAX_LIST} more: "
                          f"https://github.com/{repo}/compare/{old[:12]}...{s['commit'][:12]}")
        md.append("")
    md += ["## Build info", "", "```", open(info_path).read().strip(), "```", ""]
    open(out_path, "w").write("\n".join(md))
    print("\n".join(md))


# How each kernel is named in the README. Aigis is the main kernel (the one the
# repo owner uses every day); mzggr is the alternative. Both are released.
KERNEL_ROLES = [
    ("aigis", "Main kernel: Aigis", "used every day by the repo owner"),
    ("mzggr", "Alternative kernel: mzggr", "also built and released"),
]


def readme(readme_path, tag, *paths):
    """Sources tables: the main kernel (Aigis) first, then the alternative
    kernel (mzggr), then the xxKSU manager APK (manager.json next to the first
    sources.json, when the release has it)."""
    rows = []
    head = ["| Part | Source | Branch / version | Commit | Commit date |", "|---|---|---|---|---|"]

    def row(name, s, version):
        repo = slug(s["repo"])
        rows.append(f"| {name} | [{repo}](https://github.com/{repo}) | {version} | "
                    f"[`{s['commit'][:12]}`](https://github.com/{repo}/commit/{s['commit']}) | "
                    f"{(s.get('date') or s.get('patch_date') or '')[:10]} |")

    def ref_of(s):
        return s.get("branch") or s.get("ref") or ""

    found = {}
    for path in paths:
        cur = json.load(open(path))
        found["aigis" if "aigis" in cur["kernel"]["repo"].lower() else "mzggr"] = cur
    for key, title, note in KERNEL_ROLES:
        rows += [f"### {title}", ""]
        cur = found.get(key)
        if not cur:
            rows += [f"Not in this release.", ""]
            continue
        rows += [f"{note[0].upper() + note[1:]}.", ""] + head
        k, x, f = cur["kernel"], cur["xxksu"], cur["susfs"]
        row("Kernel", k, f"`{ref_of(k)}`, Linux {k.get('version', '')}")
        row("xxKSU (root)", x, f"`{ref_of(x)}`, KSU_VERSION {x.get('ksu_version', '')}, tag {x.get('tag', '')}")
        row("SUSFS patch", f, f"`{ref_of(f)}`, SUSFS {f.get('version', '')}, `{f['path']}`")
        rows.append("")
    manager = os.path.join(os.path.dirname(paths[0]), "manager.json")
    if os.path.exists(manager):
        m = json.load(open(manager))
        repo = slug(m["repo"])
        rows += ["### Root manager app (for both kernels)", "", "Install this app to manage root.", ""] + head
        rows.append(f"| xxKSU manager | [{repo}](https://github.com/{repo}) | release [{m['tag']}]({m['url']}), "
                    f"`{m['apk']}` | - | {m.get('date', '')[:10]} |")
        rows.append("")
    block = ["<!-- SOURCES:START -->",
             f"Last release: [{tag}](../../releases/tag/{tag})", ""] + rows[:-1] + ["<!-- SOURCES:END -->"]
    text = open(readme_path).read()
    start, end = text.index("<!-- SOURCES:START -->"), text.index("<!-- SOURCES:END -->")
    text = text[:start] + "\n".join(block) + text[end + len("<!-- SOURCES:END -->"):]
    open(readme_path, "w").write(text)


if __name__ == "__main__":
    if sys.argv[1] == "notes":
        notes(*sys.argv[2:6])
    elif sys.argv[1] == "readme":
        readme(*sys.argv[2:])
    else:
        sys.exit(__doc__)
