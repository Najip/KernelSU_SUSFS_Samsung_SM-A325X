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


def load(path):
    """A sources.json; builds before 24 Nov 2026 named the root module "xxksu"."""
    data = json.load(open(path))
    if "ksu" not in data and "xxksu" in data:
        data["ksu"] = data.pop("xxksu")
    return data


def slug(url):
    return url.rstrip("/").removeprefix("https://github.com/").removesuffix(".git")


def line(repo, c):
    sha = c["sha"]
    msg = c["commit"]["message"].splitlines()[0]
    return f"- [`{sha[:8]}`](https://github.com/{repo}/commit/{sha}) {msg}"


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
    """A rewritten branch (some upstreams rebase on every update): the
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
    kept, dropped, updated = drop_rebased(repo, old, new, data, commits)
    if dropped:
        lines = [line(repo, c).replace(") ", ") updated: ", 1) if c["sha"] in updated else line(repo, c)
                 for c in kept] or ["- No new commits."]
        return lines + [f"- ({dropped} older commits were only rebased and are left out.)"], len(kept)
    return [line(repo, c) for c in commits], data.get("total_commits", len(commits))


SOURCES = [
    ("kernel", "Kernel source", None),
    ("ksu", "BakaSU", None),  # key "ksu" = the root module
    ("susfs", "SUSFS patch (JackA1ltman)", "path"),
    ("build_repo", "This build repo", None),
]


def notes(cur_path, prev_path, info_path, out_path):
    cur = load(cur_path)
    prev = load(prev_path) if prev_path != "-" and os.path.exists(prev_path) else None
    md = ["## What's new since the last release" if prev else "## First release", ""]
    for key, title, path_key in SOURCES:
        if key not in cur:
            continue
        s = cur[key]
        repo = slug(s["repo"])
        if key == "ksu":
            title = cur.get("root") or title  # the root module (BakaSU)
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


def kernel_of(src):
    """Kernel of a sources.json: its "source" field, else by repo (older builds)."""
    if src.get("source"):
        return src["source"]
    return "aigis" if "aigis" in src["kernel"]["repo"].lower() else "mzggr"


# How the kernel is named in the README: Aigis with BakaSU, the only kernel.
KERNEL_ROLES = [
    ("aigis-bakasu", "Main kernel: Aigis (BakaSU)"),
]


def readme(readme_path, tag, *paths):
    """One sources table: the kernel (Aigis BakaSU), then BakaSU, the SUSFS
    patch and the BakaSU manager app. manager-bakasu.json sits next to the
    first sources.json."""
    rows = ["| Part | Used by | Source | Branch / version | Commit | Commit date |",
            "|---|---|---|---|---|---|"]

    def row(part, used_by, s, version):
        repo = slug(s["repo"])
        rows.append(f"| {part} | {used_by} | [{repo}](https://github.com/{repo}) | {version} | "
                    f"[`{s['commit'][:12]}`](https://github.com/{repo}/commit/{s['commit']}) | "
                    f"{(s.get('date') or s.get('patch_date') or '')[:10]} |")

    def ref_of(s):
        return s.get("branch") or s.get("ref") or ""

    found = {}
    for path in paths:
        cur = load(path)
        found[kernel_of(cur)] = cur
    present = [(key, title) for key, title in KERNEL_ROLES if key in found]
    for key, title in KERNEL_ROLES:
        if key in found:
            k = found[key]["kernel"]
            row("Kernel", title, k, f"`{ref_of(k)}`, Linux {k.get('version', '')}")
    def used_by(group):
        if len(group) == 1:
            return group[0][1]
        return "Both kernels" if len(group) == 2 else "All kernels"

    root_version = lambda x: f"`{ref_of(x)}`, KSU_VERSION {x.get('ksu_version', '')}, tag {x.get('tag', '')}"
    # Root module: BakaSU.
    groups = [("BakaSU (root)", present, "bakasu")]
    shared = [(part, group, "ksu", root_version) for part, group, _ in groups if group]
    shared.append(("SUSFS patch", present, "susfs", lambda f: f"`{ref_of(f)}`, SUSFS {f.get('version', '')}, `{f['path']}`"))
    for part, group, name, version in shared:
        commits = {found[key][name]["commit"] for key, _ in group}
        if len(commits) == 1:
            s = found[group[0][0]][name]
            row(part, used_by(group), s, version(s))
        else:
            for key, title in group:
                row(part, title, found[key][name], version(found[key][name]))
    folder = os.path.dirname(paths[0])
    for part, group, flavor in groups:
        if not group:
            continue
        # manager-bakasu.json sits next to the first sources.json.
        manager = os.path.join(folder, "manager-bakasu.json")
        if not os.path.exists(manager):
            continue
        m = json.load(open(manager))
        repo = slug(m["repo"])
        name = part.replace(" (root)", "")
        kind = "Actions build"
        commit = m.get("commit") or ""
        commit_cell = f"[`{commit[:12]}`](https://github.com/{repo}/commit/{commit})" if commit else "-"
        rows.append(f"| {name} manager app | {used_by(group)} | [{repo}](https://github.com/{repo}) | "
                    f"{kind} [{m['tag']}]({m['url']}), `{m['apk']}` | {commit_cell} | {m.get('date', '')[:10]} |")
    block = ["<!-- SOURCES:START -->",
             f"Last release: [{tag}](../../releases/tag/{tag})", ""] + rows + ["<!-- SOURCES:END -->"]
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
