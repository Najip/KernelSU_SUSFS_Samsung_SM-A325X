#!/usr/bin/env python3
"""Turn the release notes (Markdown) into an XDA changelog post (BBCode).

  xda_changelog.py <notes.md> <release-tag> <release-url> <out.txt>

The .txt is attached to every full Release. Open it, copy everything and
paste it into a reserved post of the XDA thread (the XDA editor accepts
BBCode as typed). The long "Build info" block goes into a spoiler.
"""
import re
import sys
from datetime import datetime, timezone


def inline(text):
    text = re.sub(r"\[`([^`]+)`\]\(([^)]+)\)", r"[URL='\2'][ICODE]\1[/ICODE][/URL]", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"[URL='\2']\1[/URL]", text)
    text = re.sub(r"`([^`]+)`", r"[ICODE]\1[/ICODE]", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"[B]\1[/B]", text)
    return text


def convert(md):
    out, in_list, in_code, table = [], False, False, []
    spoiler = None   # title of the section that goes into a spoiler

    def close_list():
        nonlocal in_list
        if in_list:
            out.append("[/LIST]")
            in_list = False

    def flush_table():
        if not table:
            return
        out.append("[TABLE]")
        for i, row in enumerate(table):
            cells = [c.strip() for c in row.strip().strip("|").split("|")]
            tag = "TH" if i == 0 else "TD"
            out.append("[TR]" + "".join(f"[{tag}]{inline(c)}[/{tag}]" for c in cells) + "[/TR]")
        out.append("[/TABLE]")
        table.clear()

    for raw in md.replace("\r\n", "\n").split("\n"):
        line = raw.rstrip()
        if line.startswith("```"):
            close_list()
            if in_code:
                out.append("[/CODE]")
            else:
                out.append("[CODE]")
            in_code = not in_code
            continue
        if in_code:
            out.append(line)
            continue
        if line.startswith("|"):
            close_list()
            if not re.fullmatch(r"\|[\s:|-]+\|?", line):
                table.append(line)
            continue
        flush_table()
        m = re.match(r"^(#{1,6})\s+(.*)", line)
        if m:
            close_list()
            level, title = len(m.group(1)), m.group(2)
            if level <= 2:
                if spoiler:
                    out.append("[/SPOILER]")
                    spoiler = None
                if title.lower().startswith(("build info", "source code")):
                    spoiler = title
                    out.append(f"[SPOILER='{title}']")
                    continue
                out.append(f"[SIZE=5][B]{inline(title)}[/B][/SIZE]")
            else:
                out.append(f"[B]{inline(title)}[/B]")
            continue
        m = re.match(r"^\s*[-*]\s+(.*)", line)
        if m:
            if not in_list:
                out.append("[LIST]")
                in_list = True
            out.append("[*]" + inline(m.group(1)))
            continue
        close_list()
        out.append(inline(line))
    close_list()
    flush_table()
    if in_code:
        out.append("[/CODE]")
    if spoiler:
        out.append("[/SPOILER]")
    text = "\n".join(out)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def main(notes, tag, url, target):
    md = open(notes, encoding="utf-8").read()
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    head = [
        f"[SIZE=6][B]{tag}[/B][/SIZE] ({date})",
        f"[B]Download:[/B] [URL='{url}']GitHub release {tag}[/URL]",
        "",
    ]
    tail = ["", "[I]Built automatically with GitHub Actions, set up with the help of Perplexity Computer.[/I]"]
    with open(target, "w", encoding="utf-8") as f:
        f.write("\n".join(head) + "\n" + convert(md) + "\n" + "\n".join(tail) + "\n")
    print(f"XDA changelog: {target}")


if __name__ == "__main__":
    if len(sys.argv) != 5:
        sys.exit(__doc__)
    main(*sys.argv[1:])
