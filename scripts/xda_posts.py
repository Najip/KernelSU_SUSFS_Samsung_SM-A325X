#!/usr/bin/env python3
"""Make XDA posts #2 (changelog) and #3 (updates) for a full Release, in BBCode.

  xda_posts.py <notes.md> <release-tag> <release-url> <out.txt>   (used by the workflow)
  xda_posts.py --release <tag> [out.txt]                          (by hand, needs gh)

Post #2 = the changelog: this release in full (from its release notes),
then a short list of the older full Releases with links.
Post #3 = the updates post: the text in docs/xda-updates.txt.
Open the file, copy each part and replace the whole post on XDA.
Post #1 (OP) and the title are in docs/xda-thread.txt and are pasted by hand.
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from xda_changelog import convert  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.environ.get("GITHUB_REPOSITORY", "Najip/KernelSU_SUSFS_Samsung_SM-A325X")
RELEASES = f"https://github.com/{REPO}/releases"
XDA_BANNER = f"https://raw.githubusercontent.com/{REPO}/main/assets/banner-xda.png"
TAG_RE = re.compile(r"^build-\d{8}-\d+$")


def gh_json(args):
    return json.loads(subprocess.check_output(["gh", *args, "--repo", REPO], text=True))


def older_releases(tag):
    """Full Releases of main (newest first), without this one."""
    try:
        rels = gh_json(["release", "list", "--exclude-pre-releases", "--exclude-drafts",
                        "--limit", "100", "--json", "tagName,publishedAt"])
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError):
        print("::warning::Could not list older releases; post #2 has only this one.")
        return []
    return [(r["tagName"], r["publishedAt"][:10]) for r in rels
            if r["tagName"] != tag and TAG_RE.match(r["tagName"])]


def updates_text():
    lines = open(os.path.join(ROOT, "docs", "xda-updates.txt"), encoding="utf-8").read().splitlines()
    return "\n".join(l for l in lines if not l.startswith(">>")).strip()


def parse_versions(md):
    """Extract BakaSU, SUSFS, and NoMount versions from release notes (notes.md)."""
    bakasu = ""
    m = re.search(r"^BakaSU:.*?\blatest tag\s+([^\s,)]+)", md, re.M)
    if m and m.group(1).lower() not in ("none", "unknown"):
        bakasu = m.group(1)
    else:
        m = re.search(r"^BakaSU:.*?\bKSU_VERSION\s+(\d+)", md, re.M)
        if m:
            bakasu = f"r{m.group(1)}"

    susfs = ""
    m = re.search(r"^SUSFS:\s*(v?\d[^\s]*)", md, re.M)
    if m:
        susfs = m.group(1)

    nomount = ""
    m = re.search(r"\bNoMount-(v?\d+(?:\.\d+)+[A-Za-z0-9._]*?)-(?:master|dev|main|lkm|[0-9a-f]{7,})", md)
    if not m:
        m = re.search(r"\bNoMount-(v?\d+(?:\.\d+)+)", md)
    if m:
        nomount = m.group(1)
    elif re.search(r"^NoMount:\s*built into the kernel", md, re.M):
        nomount = "built-in"

    return {"bakasu": bakasu, "susfs": susfs, "nomount": nomount}


def version_parts(v):
    b = f"BakaSU {v['bakasu']}" if v.get("bakasu") else "BakaSU"
    s = f"SUSFS {v['susfs']}" if v.get("susfs") else "SUSFS"
    n = f"NoMount {v['nomount']}" if v.get("nomount") else "NoMount"
    return b, s, n


def make(md, tag, url, date):
    v = parse_versions(md)
    bakasu_p, susfs_p, nomount_p = version_parts(v)
    xda_title = f"[KERNEL][A325F/M/N][STABLE] KernelSU ({bakasu_p}) + {susfs_p} + {nomount_p}"
    post2 = [
        "[CENTER][SIZE=6][B]Changelog[/B][/SIZE][/CENTER]",
        f"Newest first. Full details for each version are on its [URL='{RELEASES}']GitHub release[/URL] page.",
        "",
        f"[SIZE=6][B]{tag}[/B][/SIZE] ({date})",
        f"[B]Versions:[/B] {bakasu_p} | {susfs_p} | {nomount_p}",
        f"[B]Download:[/B] [URL='{url}']GitHub release {tag}[/URL]",
        "",
        convert(md),
    ]
    older = older_releases(tag)
    if older:
        post2 += ["", "[SIZE=5][B]Older versions[/B][/SIZE]", "[LIST]"]
        post2 += [f"[*][URL='{RELEASES}/tag/{t}']{t}[/URL] ({d})" for t, d in older]
        post2 += ["[/LIST]"]
    post2 += ["", "[I]Built automatically with GitHub Actions.[/I]"]
    post3 = [
        "[CENTER][SIZE=6][B]Updates and announcements[/B][/SIZE][/CENTER]",
        f"News, plans and known issues are posted here. Newest stable release: [URL='{url}']{tag}[/URL] ({date}) — {bakasu_p}, {susfs_p}, {nomount_p}.",
        "",
        updates_text(),
    ]
    return "\n".join([
        f"XDA TITLE AND POSTS #2 / #3 FOR {tag} (BBCode)",
        "Lines starting with \">>\" are notes, do not paste them.",
        "On XDA: update the thread title if versions changed, then edit post #2 and post #3.",
        "",
        ">> ==================== THREAD TITLE ====================",
        "",
        xda_title,
        "",
        ">> ==================== POST #2: CHANGELOG ====================",
        "",
        *post2,
        "",
        ">> ==================== POST #3: UPDATES ====================",
        "",
        *post3,
        "",
    ])


def make_title_banner(md, tag):
    v = parse_versions(md)
    bakasu_p, susfs_p, nomount_p = version_parts(v)
    xda_title = f"[KERNEL][A325F/M/N][STABLE] KernelSU ({bakasu_p}) + {susfs_p} + {nomount_p}"
    return "\n".join([
        f"XDA TITLE & OP BANNER FOR {tag} (BBCode)",
        'Lines starting with ">>" are notes, do not paste them.',
        "",
        ">> ==================== THREAD TITLE ====================",
        "",
        xda_title,
        "",
        ">> ==================== POST #1 (OP) BANNER & HEADER ====================",
        "",
        f"[CENTER][IMG]{XDA_BANNER}[/IMG]",
        "",
        f"[SIZE=7][B]KernelSU ({bakasu_p}) + {susfs_p} + {nomount_p}[/B][/SIZE]",
        "[SIZE=5]Samsung Galaxy A32 4G (SM-A325F / A325M / A325N, MT6768)[/SIZE][/CENTER]",
        "",
    ])


def main(argv):
    if len(argv) >= 2 and argv[0] == "--release":
        tag = argv[1]
        out = argv[2] if len(argv) > 2 else f"XDA-posts-{tag}.txt"
        rel = gh_json(["release", "view", tag, "--json", "body,url,publishedAt"])
        md, url, date = rel["body"], rel["url"], (rel.get("publishedAt") or "")[:10]
    elif len(argv) == 4:
        notes, tag, url, out = argv
        md = open(notes, encoding="utf-8").read()
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    else:
        sys.exit(__doc__)
    with open(out, "w", encoding="utf-8") as f:
        f.write(make(md, tag, url, date or datetime.now(timezone.utc).strftime("%Y-%m-%d")))
    print(f"XDA posts #2 and #3: {out}")
    banner_out = os.path.join(os.path.dirname(out), f"XDA-title-banner-{tag}.txt")
    with open(banner_out, "w", encoding="utf-8") as f:
        f.write(make_title_banner(md, tag))
    print(f"XDA title & banner: {banner_out}")


if __name__ == "__main__":
    main(sys.argv[1:])
