# Commit modes and releases

[Back to the README](../README.md)

Every build picks the commits of the kernel, BakaSU and the SUSFS patch in one of three ways. The pins are saved in `configs/verified.json`.

| Mode | What it builds | When to use it |
|---|---|---|
| `Latest` (default) | The newest commit of each source. | Trying out new upstream changes. |
| `Verified` | The pinned commits saved by the last successful `Promoted` build. | Rebuilding something you already tested. A full `Release` only works in this mode. |
| `Promoted` | Nothing new is compiled for the kernel. It takes the files of the most recent successful `Latest` run with the default kernel options (on the same branch) and saves that run's commits as the new `Verified` pins. | After you have flashed and tested the newest default `Latest` build and want to mark it as good. |

The pins were reset when I switched to BakaSU (23 Nov 2026), because the old ones were for xxKSU. Until the first `Promoted` run after that, `Verified` stops with "No verified commits yet": run `Latest`, test it, then `Promoted`.

Which `Latest` runs `Promoted` accepts: a BakaSU build with NoMount `lkm` (not `integrate`), not a **NoMount only** run, and **Compiler** `aigis`. The runner (my PC or GitHub), **Valhall GPU** (Promoted keeps the GPU of that run) and the release type do not matter. Older xxKSU runs are never taken. Runs with other options are skipped. If no run fits, `Promoted` ends with the warning "Nothing promoted" and changes nothing.

How `Promoted` gets the NoMount module:

- If that `Latest` run already has the NoMount module from the chosen **NoMount branch**, it is reused. Nothing is built.
- If it has none (older runs with NoMount `no`) or one from the other branch, `Promoted` builds the module from that run's saved kernel kit, without compiling the kernel. Older runs from before the kit existed fall back to compiling the kernel once, only to match the module.
- The release step puts the NoMount module into every kernel ZIP that does not carry it yet (it must have the same kernel ID). Kernel ZIPs from before this TWRP install cannot take it: build the kernel again. `integrate` is not allowed with `Promoted`.

With **Release** set to `CI`, the files are kept as artifacts of the `Promoted` run. With `Pre-release`, they are published as a pre-release. The kernel options are ignored in `Promoted`; they come from the `Latest` run.

A full `Release` with `Latest` or `Promoted` stops with the message "Release must use Verified". Use `Pre-release` for those, or switch to `Verified`.

**Release from last pre-release** (no build): test first, then publish exactly what you flashed.

1. Run Build Kernel with commit mode `Verified` and release type `Pre-release`, and flash that pre-release.
2. When it works, run Build Kernel again with commit mode `Verified` and release type `Release from last pre-release`. The newest pre-release of this branch becomes the full Release (same ZIPs, notes rewritten as "what's new since the last Release") and the README sources table is updated. Kernel options are ignored here.

It stops with "Release must use Verified" when that pre-release was not built from the commits in `configs/verified.json` (for example a `Latest` pre-release, or one made before a newer `Promoted`).

"What's new" in a full Release always compares with the previous full Release; a pre-release compares with the previous release of any kind. A previous release of another kernel repo makes it a "First release".

With NoMount `lkm`, a `Pre-release` or `Release` attaches the module ZIP and `nomount-4.14-aigis-bakasu.ko` built in the same run to the release page, plus the BakaSU manager `.apk`. The README sources table is updated only by a full `Release`.

## XDA posts

Every full Release (`Release`, or `Release from last pre-release`) also gets `XDA-posts-<tag>.txt` (BBCode, made by `scripts/xda_posts.py`):

- **Post #2, changelog**: this release in full (the long build info folded into a spoiler), then a list of the older full Releases with links.
- **Post #3, updates**: the text of [`docs/xda-updates.txt`](xda-updates.txt) (news, known issues, recommended modules) plus a line with the newest stable release. I edit that file by hand when there is news.

Download it from the release page, then on XDA edit post #2 and replace all of it, and the same for post #3. Pre-releases do not get it. For any release by hand: `python3 scripts/xda_posts.py --release <tag>`.

The thread title and post #1 are in [`docs/xda-thread.txt`](xda-thread.txt) and are pasted once by hand.
