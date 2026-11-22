#!/usr/bin/env python3
"""Make a short version of a GitHub Actions build log, with only the parts
that matter when a build fails.

How to get the log: open the failed job in Actions, click the gear icon at
the top right -> "View raw logs", then save the page (usually job-logs.txt).

How to use: double-click this file (or run "python extract_log.py"). A window
asks for the log file. The short version is saved next to this script as
<log name>-important.txt; send me that file.
You can also give the log on the command line: python extract_log.py job-logs.txt

Needs only Python 3 (on Windows, from python.org; the file picker is tkinter,
which comes with it).
"""
import os
import re
import sys
from collections import OrderedDict

# Lines worth keeping, wherever they are.
IMPORTANT = re.compile("|".join([
    r"##\[error\]", r"::error", r"##\[warning\]", r"::warning",
    r"\berror:", r"\bfatal error\b", r"\bError \d+\b", r"make(\[\d+\])?: \*\*\*",  # compiler / make
    r"undefined reference", r"undefined symbol", r"multiple definition",    # linker
    r"implicit declaration", r"incompatible pointer",
    r"error: patch failed", r"patch does not apply", r"does not exist in index",
    r"Hunk #\d+ FAILED", r"\.rej\b", r"corrupt patch",                       # patches
    r"Config not applied", r"Config still enabled", r"Missing linked",       # our checks
    r"was dropped by olddefconfig", r"does not match", r"not found\b",
    r"No such file or directory", r"Permission denied", r"command not found",
    r"Traceback \(most recent call last\)", r"\bException:", r"unbound variable",
    r"syntax error", r"line \d+: .*(not found|No such)", r"Killed\b",
    r"No space left on device", r"out of memory", r"timed out", r"rate limit",
    r"HTTP \d{3}", r"curl: \(\d+\)",
    r"Process completed with exit code",
    r"You lost .* hook", r"incompatible hook", r"susfs_inline: WARNING",      # BakaSU hook check
    r"version code:", r"version name:", r"using SuSFS Inline hook",
    r"Kernel release", r"Build finished", r"Created flashable ZIP",
]), re.IGNORECASE)
# Not useful, even when they match above.
NOISE = re.compile("|".join([
    r"-Wno-error", r"-Werror", r"no version information available", r"warning: unused",
    r"\$CCFLAG is", r"-DCFG_", r"error_report", r"_error\.o\b", r"errors?\.c\b",
]), re.IGNORECASE)
STAMP = re.compile(r"^\ufeff?\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(\.\d+)?Z ")
ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
# GitHub prints the script of each step in cyan before running it; those
# lines are code, not output (marked with this prefix after cleaning).
CODE = "\u00a7 "
COMPILER_ERROR = re.compile(r"(\berror:|fatal error|undefined reference|Error \d+|unbound variable|##\[error\])", re.IGNORECASE)
MAX_LINES = 600
CONTEXT_BEFORE, CONTEXT_AFTER, MAX_CONTEXT = 12, 6, 8


def clean(line):
    line = STAMP.sub("", line.rstrip("\r\n"))
    code = "\x1b[36;1m" in line
    line = ANSI.sub("", line)
    return CODE + line if code else line


def is_code(line):
    return line.startswith(CODE)


def summarize(lines):
    out = []
    steps = []          # (line number, step name)
    current = None
    for i, line in enumerate(lines):
        if line.startswith("##[group]Run ") or line.startswith("##[group]Post "):
            current = line[len("##[group]"):]
            # "Run set -euo pipefail" says little: use the first real script line.
            if current.startswith("Run set -") or current == "Run |":
                for nxt in lines[i + 1:i + 15]:
                    t = nxt[len(CODE):].strip() if is_code(nxt) else ""
                    if t and not t.startswith(("set -", "#")):
                        current = f"Run ... {t}"
                        break
            steps.append((i, current))
    first_error = next((i for i, l in enumerate(lines) if not is_code(l) and ("##[error]" in l or "::error" in l)), None)
    failing = None
    if first_error is not None:
        failing = next((name for n, name in reversed(steps) if n <= first_error), None)

    out.append("=== Summary")
    out.append(f"Log lines: {len(lines)}")
    if failing:
        out.append(f"Failing step (last step started before the first error): {failing}")
    for l in lines:
        if "##[error]" in l:
            out.append("First error: " + l.replace("##[error]", "").strip())
            break
    out.append("")

    out.append("=== Steps that ran")
    for _, name in steps:
        out.append("- " + name[:160])
    out.append("")

    # Context around the first few compiler / make errors.
    out.append("=== Around the first errors")
    shown, blocks = set(), 0
    for i, l in enumerate(lines):
        if blocks >= MAX_CONTEXT:
            break
        if COMPILER_ERROR.search(l) and not is_code(l) and not NOISE.search(l) and i not in shown:
            lo, hi = max(0, i - CONTEXT_BEFORE), min(len(lines), i + CONTEXT_AFTER + 1)
            out.append(f"--- line {i + 1}")
            for j in range(lo, hi):
                if j not in shown:
                    out.append(lines[j][:400])
                    shown.add(j)
            blocks += 1
    if not blocks:
        out.append("(no compiler or make errors found)")
    out.append("")

    # Every important line once (same text = shown once, with a count).
    out.append("=== Important lines (each text once)")
    seen = OrderedDict()
    for i, l in enumerate(lines):
        if IMPORTANT.search(l) and not is_code(l) and not NOISE.search(l) and "***" not in l.replace("make", ""):
            key = l.strip()[:400]
            if key in seen:
                seen[key][1] += 1
            else:
                seen[key] = [i + 1, 1]
    for text, (num, count) in list(seen.items())[:MAX_LINES]:
        out.append(f"{num:>7}: {text}" + (f"   (x{count})" if count > 1 else ""))
    if len(seen) > MAX_LINES:
        out.append(f"... {len(seen) - MAX_LINES} more lines left out")
    out.append("")

    # Python tracebacks in full.
    tb, inside = [], False
    for l in lines:
        if "Traceback (most recent call last)" in l:
            inside = True
            tb.append("---")
        if inside:
            tb.append(l[:400])
            if l and not l.startswith(" ") and "Traceback" not in l:
                inside = False
    if tb:
        out.append("=== Python errors")
        out.extend(tb[:200])
        out.append("")

    out.append("=== Last 40 lines of the log")
    out.extend(l[:400] for l in lines[-40:])
    return out


def pick_file():
    if len(sys.argv) > 1:
        return sys.argv[1]
    try:
        import tkinter
        from tkinter import filedialog
        root = tkinter.Tk()
        root.withdraw()
        path = filedialog.askopenfilename(
            title="Choose the build log (job-logs.txt)",
            filetypes=[("Text files", "*.txt *.log"), ("All files", "*.*")])
        root.destroy()
        return path
    except Exception:
        return input("Path of the log file (job-logs.txt): ").strip().strip('"')


def main():
    path = pick_file()
    if not path:
        print("No file chosen.")
        return 1
    with open(path, encoding="utf-8", errors="replace") as handle:
        lines = [clean(l) for l in handle]
    result = summarize(lines)
    here = os.path.dirname(os.path.abspath(__file__))
    name = os.path.splitext(os.path.basename(path))[0] + "-important.txt"
    target = os.path.join(here, name)
    with open(target, "w", encoding="utf-8") as handle:
        handle.write(f"Short version of {os.path.basename(path)}\n\n")
        handle.write("\n".join(result) + "\n")
    print(f"Saved: {target} ({len(result)} lines from {len(lines)})")
    try:
        import tkinter
        from tkinter import messagebox
        if len(sys.argv) <= 1:
            root = tkinter.Tk()
            root.withdraw()
            messagebox.showinfo("Done", f"Saved:\n{target}")
            root.destroy()
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
