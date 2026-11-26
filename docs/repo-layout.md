# Repo layout

[Back to the README](../README.md)

| Path | What it is |
|---|---|
| `.github/workflows/kernel.yml` | Kernel build and release (own PC by default) |
| `.github/workflows/upstream-check.yml` | Checks upstream for new commits and starts a build |
| `scripts/sources.conf` | Upstream repos, branches and config fragments |
| `scripts/prepare_sources.sh` | Downloads the sources and applies all patches |
| `scripts/build_kernel.sh` | Configures and compiles |
| `scripts/package_zip.sh` | Makes the AnyKernel3 ZIP and `build-info.txt` |
| `scripts/release_notes.py` | Release notes and README table |
| `tools/collect-logs.sh` | Log collector for TWRP and rooted Android (Termux) |
| `docs/xda-thread.txt` | XDA thread title and post #1 (BBCode), pasted by hand |
| `docs/xda-updates.txt` | Text of XDA post #3 (news, known issues, recommended modules), edited by hand |
| `scripts/xda_posts.py` | Makes `XDA-posts-<tag>.txt` (XDA posts #2 and #3) for every full Release |
| `scripts/telegram_post.py` | Makes `Telegram-post-<tag>.txt`, `.html`, and `.tg.html` (Telegram Markdown and HTML) for every full Release |
| `scripts/xda_changelog.py` | Turns the release notes into BBCode (used by `xda_posts.py`) |
| `tools/extract_log.py` | Makes a short version of a GitHub Actions build log (opens a file picker) |
| `patches/base/` | Turns Aigis into the BakaSU + SUSFS inline-hook layout or the xxKSU + SUSFS manual-hook layout, and the stock GPU option |
| `patches/kernelsu/` | Small changes to xxKSU itself (native wrappers, SUSFS lifecycle calls) |
| `patches/susfs/` | Small additions on top of JackA1ltman's SUSFS core files |
| `patches/bakasu/` | Takes out the kernel's own SELinux hide hooks (BakaSU does them itself) |
| `patches/kernel/` | Network fix (UDP GSO, by Juan from LumiROM) and flashlight fixes (SM5714, by aartzz) |
| `configs/a325x-bakasu-susfs.config`, `configs/a325x-xxksu-susfs.config` | Options the finished kernel config must have (BakaSU / xxKSU) |
| `configs/verified.json` | Commits pinned by the last successful `Promoted` build |
| `scripts/resolve_commits.py` | Picks the commits for Latest, Verified and Promoted |
| `scripts/promoted_source.py` | Finds and collects the `Latest` run that `Promoted` takes its files from |
| `scripts/build_nomount.sh` | Builds the NoMount module (after a kernel compile, or from a kernel kit) |
| `scripts/bakasu_manager.py` | Finds the BakaSU Build Manager run of the BakaSU commit and downloads its APK |
| `scripts/kernel_kit.py` | Kernel kit key, lookup and download |
| `scripts/kernel_id.sh` | Kernel ID that the flasher uses to check the NoMount module |
| `anykernel/nomount-check.sh`, `anykernel/valhall-install.sh`, `anykernel/jpeg-bbr-install.sh` | Flasher steps added after the kernel is written (NoMount check/install, Valhall drivers module, JPEG + BBR fix module) |
| `anykernel/jpeg-bbr/` | The JPEG + BBR fix module (by Juan, LumiROM) that every kernel ZIP installs; `rom-check.sh` skips what the ROM already fixes and removes the module when the ROM has both |
| `configs/nomount-integrate.config` | Turns on NoMount built into the kernel (`integrate`) |
| `configs/` | Config fragments merged after the tree's own fragments |
| `docs/` | These pages (the README sources table is the only part updated automatically) |

My older builds (before BakaSU) and their files are in the [`xxksu` branch](../../../tree/xxksu). xxKSU itself is built on `main` again since 2026-11-26.
