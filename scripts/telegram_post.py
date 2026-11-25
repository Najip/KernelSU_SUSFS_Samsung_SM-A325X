#!/usr/bin/env python3
"""Make a short Telegram post for a full Release.

  telegram_post.py <notes.md> <release-tag> <release-url> <out.txt>   (used by the workflow)
  telegram_post.py --release <tag> [out.txt]                          (by hand, needs gh)

The post has:
  - what the kernel is (one line),
  - my news: the entries of docs/xda-updates.txt dated after the previous
    full Release (so old news is not repeated),
  - the notable upstream changes from the release notes (Aigis kernel and
    BakaSU; version bumps, translations and merge commits are left out),
  - the download link and how to flash.
It writes three files next to each other:
  Telegram-post-<tag>.txt      plain text, links written out
  Telegram-post-<tag>.html     open it in a browser, tap "Copy post" and paste
                               in Telegram: bold and named links stay
  Telegram-post-<tag>.tg.html  the same in Telegram's HTML, sent by the bot
It fits in one Telegram message (4096 visible characters; the upstream list is
cut when needed).
"""
import html
import os
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from xda_posts import gh_json, older_releases, parse_versions, version_parts, ROOT, RELEASES  # noqa: E402

LIMIT = 4096
MAX_UPSTREAM = 8
XDA = "https://xdaforums.com/t/kernel-a325f-m-n-stable-ish-kernelsu-bakasu-susfs-2-4-0-samsung-a32-4g.4809753/"
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


# A post is a list of lines; a line is a list of parts (text, style, url).
# style: "" or "b". url: None or a link. One source, three outputs: plain text,
# a copy page (HTML, keeps bold and links when pasted) and the bot's HTML.
def T(text, style="", url=None, plain_url=True):
    """plain_url=False: the plain text shows only the words (the link is
    already written out elsewhere in the post)."""
    return (text, style, url if plain_url else None, url)


def make_lines(md, tag, url, date):
    # The full Release before this one (by tag: build-YYYYMMDD-<run number>).
    num = lambda t: tuple(int(x) for x in re.findall(r"-(\d{8})-(\d+)$", t)[0]) if re.search(r"-\d{8}-\d+$", t) else (0, 0)
    older = [(t, d) for t, d in older_releases(tag) if num(t) < num(tag)]
    since = max(older, key=lambda r: num(r[0]))[1] if older else ""
    bakasu_p, susfs_p, nomount_p = version_parts(parse_versions(md))
    head = [
        [T(f"KernelSU ({bakasu_p}) + {susfs_p} + {nomount_p}", "b")],
        [T("Samsung Galaxy A32 4G (SM-A325F / A325M / A325N, MT6768)")],
        [],
        [T("Update: "), T(tag, "b", url, plain_url=False), T(f" ({date})")],
        [],
        [T(f"Aigis kernel (SlamZDank) with {bakasu_p} root, {susfs_p} and {nomount_p}, "
           "for the Galaxy A32 4G (SM-A325F/M/N). Tested by me on A325F with LumiROM 9.")],
    ]
    news = my_news(since)
    if news:
        head += [[], [T("From me:", "b")]]
        head += [[T(n, "b")] if n.endswith(":") and not n.startswith("- ") else [T(n)] for n in news]
    tail = [
        [],
        [T("Download (kernel ZIP + BakaSU manager)", "b", url)],
        [T("XDA thread", "", XDA), T(" | "), T("All releases", "", RELEASES)],
        [T("Flash in TWRP or OrangeFox, back up boot first. The ZIP also installs the NoMount and JPEG fix modules.")],
    ]
    ups = upstream(md)
    while True:
        body = list(head)
        if ups:
            body += [[], [T("Upstream changes:", "b")], *[[T(u)] for u in ups[:MAX_UPSTREAM]]]
            if len(ups) > MAX_UPSTREAM:
                body.append([T(f"- ...and {len(ups) - MAX_UPSTREAM} more, see the "), T("release page", "", url, plain_url=False)])
        lines = body + tail
        # Telegram counts the visible text, not the link addresses.
        if len(to_visible(lines)) <= LIMIT or not ups:
            return lines
        ups = ups[:-1]


def to_visible(lines):
    return "\n".join("".join(p[0] for p in l) for l in lines)


def to_text(lines):
    """Plain text: links written out, for places without formatting."""
    out = []
    for l in lines:
        s = ""
        for t, _, u, _ in l:
            s += f"{t}: {u}" if u and t != u else t
        out.append(s.replace(" | ", "\n"))
    return "\n".join(out)


def to_tg_html(lines, sep="\n"):
    """Telegram HTML (<b>, <a>): what the bot sends, and the copy page body."""
    out = []
    for l in lines:
        s = ""
        for t, st, _, u in l:
            t = html.escape(t, quote=False)
            if st == "b":
                t = f"<b>{t}</b>"
            if u:
                t = f'<a href="{html.escape(u)}">{t}</a>'
            s += t
        out.append(s)
    return sep.join(out)


PAGE = """<!doctype html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Telegram post {tag}</title>
<style>
body {{ font: 16px/1.45 system-ui, sans-serif; margin: 16px; max-width: 640px; }}
button {{ font-size: 18px; padding: 10px 18px; margin-bottom: 14px; }}
#post {{ border: 1px solid #8884; border-radius: 8px; padding: 12px; }}
#ok {{ margin-left: 10px; }}
</style></head><body>
<button id="copy">Copy post</button><span id="ok"></span>
<div id="post">{body}</div>
<script>
document.getElementById("copy").onclick = async () => {{
  const el = document.getElementById("post"), ok = document.getElementById("ok");
  try {{
    await navigator.clipboard.write([new ClipboardItem({{
      "text/html": new Blob([el.innerHTML], {{type: "text/html"}}),
      "text/plain": new Blob([el.innerText], {{type: "text/plain"}})}})]);
  }} catch (e) {{
    const r = document.createRange(); r.selectNodeContents(el);
    const s = getSelection(); s.removeAllRanges(); s.addRange(r);
    document.execCommand("copy"); s.removeAllRanges();
  }}
  ok.textContent = "Copied. Paste it in Telegram.";
}};
</script></body></html>
"""


def to_page(lines, tag):
    return PAGE.format(tag=html.escape(tag), body=to_tg_html(lines, "<br>\n"))


def make(md, tag, url, date):
    return to_text(make_lines(md, tag, url, date))


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
    lines = make_lines(md, tag, url, date)
    base = out[:-4] if out.endswith(".txt") else out
    for path, text in ((out, to_text(lines)), (base + ".html", to_page(lines, tag)),
                       (base + ".tg.html", to_tg_html(lines))):
        with open(path, "w", encoding="utf-8") as f:
            f.write(text + "\n")
        print(f"Telegram post: {path}")


if __name__ == "__main__":
    main(sys.argv[1:])
