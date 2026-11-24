#!/usr/bin/env python3
"""Make a short Telegram post for a full Release (plain text, copy and paste).

  telegram_post.py <notes.md> <release-tag> <release-url> <out.txt>   (used by the workflow)
  telegram_post.py --release <tag> [out.txt]                          (by hand, needs gh)

The post has:
  - what the kernel is (one line),
  - my news: the entries of docs/xda-updates.txt dated after the previous
    full Release (so old news is not repeated),
  - the notable upstream changes from the release notes (Aigis kernel and
    BakaSU; version bumps, translations and merge commits are left out),
  - the download link and how to flash.
Plain text on purpose: links show up as links when pasted, and it fits in one
Telegram message (4096 characters; the upstream list is cut when needed).
"""
import os
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from xda_posts import gh_json, older_releases, ROOT, RELEASES  # noqa: E402

LIMIT = 4096
MAX_UPSTREAM = 8
# Upstream commits that say nothing to a user.
SKIP = re.compile(r"^(chore|ci|docs?|build\(deps\)|Merge |Revert \"chore)|bump |translations?|Weblate|README", re.I)
# Release-notes sections worth listing, and how they are named in the post.
SECTIONS = {"Kernel source": "Aigis", "BakaSU": "BakaSU", "SUSFS patch": "SUSFS"}


def bbcode_to_text(s):
    s = re.sub(r"\[URL='([^']+)'\](.*?)\[/URL\]", r"\2 (\1)", s)
    s = re.sub(r"\[/?(B|I|U|ICODE|CODE|LIST|SIZE=\d|CENTER)\]", "", s)
    return s.replace("[*]", "- ").strip()


def my_news(since):
    """Entries of docs/xda-updates.txt dated after `since` (YYYY-MM-DD)."""
    text = open(os.path.join(ROOT, "docs", "xda-updates.txt"), encoding="utf-8").read()
    lines = [l for l in text.splitlines() if not l.startswith(">>")]
    out, keep = [], False
    for l in lines:
        m = re.match(r"\[B\](\d{4}-\d{2}-\d{2}): (.*)\[/B\]", l)
        if m:
            keep = not since or m.group(1) >= since
            if keep:
                out.append(f"{m.group(2)} ({m.group(1)}):")
            continue
        if l.startswith("[B]"):  # Known issues, Recommended modules: not news
            keep = False
        if keep and l.startswith("[*]") and "changelog post" not in l:  # XDA-only wording
            out.append(bbcode_to_text(l))
    return out


def upstream(md):
    out, name = [], None
    for l in md.splitlines():
        m = re.match(r"### ([^:]+):", l)
        if m:
            name = next((v for k, v in SECTIONS.items() if m.group(1).startswith(k)), None)
            continue
        if l.startswith("## "):
            name = None
        m = re.match(r"- (?:\S+ )?(?:updated: )?\[`[0-9a-f]+`\]\([^)]*\) (.*)", l)
        if name and m and not SKIP.search(m.group(1)):
            out.append(f"- {name}: {m.group(1).strip()}")
    return out


def make(md, tag, url, date):
    # The full Release before this one (by tag: build-YYYYMMDD-<run number>).
    num = lambda t: tuple(int(x) for x in t.split("-")[1:3])
    older = [(t, d) for t, d in older_releases(tag) if num(t) < num(tag)]
    since = max(older, key=lambda r: num(r[0]))[1] if older else ""
    head = [
        "KernelSU (BakaSU) + SUSFS 2.4.0 kernel",
        "Samsung Galaxy A32 4G (SM-A325F / A325M / A325N, MT6768)",
        "",
        f"Update: {tag} ({date})",
        "",
        "Aigis kernel (SlamZDank) with BakaSU root, SUSFS v2.4.0 and NoMount, "
        "for the Galaxy A32 4G (SM-A325F/M/N). Tested by me on A325F with LumiROM 9.",
    ]
    news = my_news(since)
    if news:
        head += ["", "From me:", *news]
    tail = [
        "",
        f"Download (kernel ZIP + BakaSU manager): {url}",
        "Flash in TWRP or OrangeFox, back up boot first. The ZIP also installs the NoMount and JPEG fix modules.",
        f"All releases: {RELEASES}",
    ]
    ups = upstream(md)
    while True:
        body = list(head)
        if ups:
            body += ["", "Upstream changes:", *ups[:MAX_UPSTREAM]]
            if len(ups) > MAX_UPSTREAM:
                body.append(f"- ...and {len(ups) - MAX_UPSTREAM} more, see the release page")
        text = "\n".join(body + tail)
        if len(text) <= LIMIT or not ups:
            return text
        ups = ups[:-1]


def main(argv):
    if len(argv) >= 2 and argv[0] == "--release":
        tag = argv[1]
        out = argv[2] if len(argv) > 2 else f"Telegram-post-{tag}.txt"
        rel = gh_json(["release", "view", tag, "--json", "body,url,publishedAt"])
        md, url, date = rel["body"], rel["url"], (rel.get("publishedAt") or "")[:10]
    elif len(argv) == 4:
        notes, tag, url, out = argv
        md = open(notes, encoding="utf-8").read()
        date = ""
    else:
        sys.exit(__doc__)
    date = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with open(out, "w", encoding="utf-8") as f:
        f.write(make(md, tag, url, date) + "\n")
    print(f"Telegram post: {out}")


if __name__ == "__main__":
    main(sys.argv[1:])
