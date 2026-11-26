#!/usr/bin/env python3
"""Which xxKSU release (Najip/xxKSU) to build with.

xxKSU publishes the newest rebase on tiann/KernelSU every day as a
pre-release. When the A32 kernel builds it, xxKSU promotes it to its Latest
release. So:

  newest = the newest xxKSU release (pre-releases too) that has a manager APK
  stable = the Latest release (the last xxKSU that built here)

The kernel uses newest; when that does not build, the build falls back to
stable (kernel.yml).

  xxksu_release.py newest|stable [repo]   -> JSON {tag, commit, apk, url, date}
  xxksu_release.py commit <sha> [repo]    -> the release of that commit (or {})

As a module: release("newest"|"stable"|<sha>, repo).
"""
import json
import subprocess
import sys

DEFAULT_REPO = "Najip/xxKSU"


def slug(repo):
    return repo.rstrip("/").removeprefix("https://github.com/").removesuffix(".git")


def _api(path):
    return json.loads(subprocess.check_output(["gh", "api", path], text=True))


def _tags(repo):
    out = subprocess.check_output(["git", "ls-remote", "--tags", f"https://github.com/{repo}"], text=True)
    tags = {}
    for line in out.splitlines():
        sha, ref = line.split("\t")
        name = ref.removeprefix("refs/tags/")
        if name.endswith("^{}"):
            tags[name[:-3]] = sha
        else:
            tags.setdefault(name, sha)
    return tags


def _apk(rel):
    names = [a["name"] for a in rel.get("assets", []) if a["name"].endswith(".apk")]
    names.sort(key=lambda n: not n.endswith("-release.apk"))
    return names[0] if names else ""


def _info(rel, tags):
    return {"tag": rel["tag_name"], "commit": tags.get(rel["tag_name"], ""), "apk": _apk(rel),
            "url": rel["html_url"], "date": rel.get("published_at") or rel.get("created_at", ""),
            "prerelease": rel.get("prerelease", False)}


def release(which, repo=DEFAULT_REPO):
    repo = slug(repo)
    tags = _tags(repo)
    if which == "stable":
        return _info(_api(f"repos/{repo}/releases/latest"), tags)
    rels = [r for r in _api(f"repos/{repo}/releases?per_page=30")
            if not r.get("draft") and r["tag_name"] in tags and _apk(r)]
    if which == "newest":
        if not rels:
            raise SystemExit(f"{repo} has no release with an APK")
        return _info(max(rels, key=lambda r: r.get("published_at") or ""), tags)
    for r in rels:
        if which and tags[r["tag_name"]].startswith(which):
            return _info(r, tags)
    return {}


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("newest", "stable", "commit"):
        sys.exit(__doc__)
    if sys.argv[1] == "commit":
        print(json.dumps(release(sys.argv[2], *(sys.argv[3:4] or [DEFAULT_REPO]))))
    else:
        print(json.dumps(release(sys.argv[1], *(sys.argv[2:3] or [DEFAULT_REPO]))))
