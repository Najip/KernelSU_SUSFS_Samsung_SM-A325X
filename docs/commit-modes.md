# Commit modes and releases

[Back to the README](../README.md)

Every build picks the commits of the kernel, BakaSU and the SUSFS patch in one of three ways. The pins are saved in `configs/verified.json`.

| Mode | What it builds | When to use it |
|---|---|---|
| `Latest` (default) | The newest commit of each source. | Trying out new upstream changes. |
| `Verified` | The pinned commits saved by the last successful `Promoted` build. | Rebuilding something you already tested. No release type needs it. |
| `Promoted` | Nothing new is compiled for the kernel. It takes the files of the most recent successful `Latest` run with the default kernel options (on the same branch) and saves that run's commits as the new `Verified` pins. | After you have flashed and tested the newest default `Latest` build and want to mark it as good. |

The pins were reset on 23 Nov 2026. Until the first `Promoted` run after that, `Verified` stops with "No verified commits yet": run `Latest`, test it, then `Promoted`.

Which `Latest` runs `Promoted` accepts: a BakaSU build with NoMount `lkm` (not `integrate`), not a **NoMount only** run, and **Compiler** `aigis`. The runner (my PC or GitHub), **Valhall GPU** (Promoted keeps the GPU of that run) and the release type do not matter. Runs older than 23 Nov 2026 are never taken. Runs with other options are skipped. If no run fits, `Promoted` ends with the warning "Nothing promoted" and changes nothing.

How `Promoted` gets the NoMount module:

- If that `Latest` run already has the NoMount module from the chosen **NoMount branch**, it is reused. Nothing is built.
- If it has none (older runs with NoMount `no`) or one from the other branch, `Promoted` builds the module from that run's saved kernel kit, without compiling the kernel. Older runs from before the kit existed fall back to compiling the kernel once, only to match the module.
- The release step puts the NoMount module into every kernel ZIP that does not carry it yet (it must have the same kernel ID). Kernel ZIPs from before this TWRP install cannot take it: build the kernel again. `integrate` is not allowed with `Promoted`.

With **Release** set to `CI`, the files are kept as artifacts of the `Promoted` run. With `Pre-release`, they are published as a pre-release. The kernel options are ignored in `Promoted`; they come from the `Latest` run.

A full `Release` (release type `Release`) can be built and published in one run with any commit mode (`Latest`, `Verified` or `Promoted`); Verified is not required. To publish exactly what you already tested, use `Latest` + `Release` with the tested run's link in the **reuse** box (no new kernel build), or turn a pre-release into the Release as below.

**Release from pre-release** (no build): test first, then publish exactly what you flashed. Any pre-release works, also one built with `Latest` (for example an automatic upstream pre-release) that was never Verified.

1. Flash a pre-release and test it.
2. When it works, run Build Kernel with release type `Release from pre-release`. Put its tag in **Pre-release tag** (for example `build-20261124-120`), or leave it empty for the newest pre-release of this branch. Commit mode and kernel options are ignored. That pre-release becomes the full Release (same ZIPs, notes rewritten as "what's new since the last Release", XDA posts attached) and the README sources table is updated.

The run summary says whether it was built from the Verified commits (information only, it never stops the run). It stops only when the tag does not exist, is already a full Release, or has no BakaSU kernel ZIP (pre-releases from before the switch to BakaSU on 23 Nov 2026). Publishing does not change `configs/verified.json`; run `Promoted` if you also want new Verified pins.

"What's new" in a full Release always compares with the previous full Release; a pre-release compares with the previous release of any kind. A previous release of another kernel repo makes it a "First release".

With NoMount `lkm`, a `Pre-release` or `Release` attaches the module ZIP and `nomount-4.14-aigis-bakasu.ko` built in the same run to the release page, plus the BakaSU manager `.apk`. The README sources table is updated only by a full `Release`.

## XDA posts

Every full Release (`Release`, or `Release from pre-release`) also gets `XDA-posts-<tag>.txt` (BBCode, made by `scripts/xda_posts.py`):

- **Post #2, changelog**: this release in full (the long build info folded into a spoiler), then a list of the older full Releases with links.
- **Post #3, updates**: the text of [`docs/xda-updates.txt`](xda-updates.txt) (news, known issues, recommended modules) plus a line with the newest stable release. I edit that file by hand when there is news.

Download it from the release page, then on XDA edit post #2 and replace all of it, and the same for post #3. Pre-releases do not get it. For any release by hand: `python3 scripts/xda_posts.py --release <tag>`.

The thread title and post #1 are in [`docs/xda-thread.txt`](xda-thread.txt) and are pasted once by hand.

## Telegram post

Every full Release also gets `Telegram-post-<tag>.txt` (plain text, one message, made by `scripts/telegram_post.py`): one line about the kernel, my news from [`docs/xda-updates.txt`](xda-updates.txt) dated since the previous full Release, the notable Aigis / BakaSU / SUSFS changes (version bumps and translations left out), and the download link. I copy it and post it by hand in the Telegram groups. For any release by hand: `python3 scripts/telegram_post.py --release <tag>`.

Automatic posting (optional, only to a channel or group of my own): the release also sends that text with a Telegram bot when two settings exist. Until then the step is skipped and nothing fails.

1. In Telegram, open @BotFather, send `/newbot` and copy the bot token.
2. Add the bot to my channel as an admin (allowed to post messages).
3. Save the token as a repo secret and the channel as a repo variable:
   `gh secret set TELEGRAM_BOT_TOKEN -R Najip/KernelSU_SUSFS_Samsung_SM-A325X` (paste the token), then
   `gh variable set TELEGRAM_CHAT_ID -R Najip/KernelSU_SUSFS_Samsung_SM-A325X -b @mychannel` (a private channel uses its number, like `-100...`).

Other people's groups (for example BakaSU's) only accept a bot if their admins add it, so I post there by hand.
