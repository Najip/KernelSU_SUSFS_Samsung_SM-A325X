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
| `docs/xda-thread.txt` | XDA thread template (BBCode): first post, changelog post, reserved posts |
| `scripts/xda_changelog.py` | Turns the release notes into `XDA-changelog-<tag>.txt` for the XDA changelog post |
| `tools/extract_log.py` | Makes a short version of a GitHub Actions build log (opens a file picker) |
| `patches/base/` | Turns Aigis into the BakaSU + SUSFS inline-hook layout, and the stock GPU option |
| `patches/susfs/` | Small additions on top of JackA1ltman's SUSFS core files |
| `patches/bakasu/` | Takes out the kernel's own SELinux hide hooks (BakaSU does them itself) |
| `patches/kernel/` | Network fix |
| `configs/a325x-bakasu-susfs.config` | Options the finished kernel config must have |
| `configs/verified.json` | Commits pinned by the last successful `Promoted` build |
| `scripts/resolve_commits.py` | Picks the commits for Latest, Verified and Promoted |
| `scripts/promoted_source.py` | Finds and collects the `Latest` run that `Promoted` takes its files from |
| `scripts/build_nomount.sh` | Builds the NoMount module (after a kernel compile, or from a kernel kit) |
| `scripts/bakasu_manager.py` | Finds the BakaSU Build Manager run of the BakaSU commit and downloads its APK |
| `scripts/kernel_kit.py` | Kernel kit key, lookup and download |
| `scripts/kernel_id.sh` | Kernel ID that the flasher uses to check the NoMount module |
| `anykernel/nomount-check.sh`, `anykernel/valhall-install.sh` | Flasher steps added after the kernel is written (NoMount check/install, Valhall drivers module) |
| `configs/nomount-integrate.config` | Turns on NoMount built into the kernel (`integrate`) |
| `configs/` | Config fragments merged after the tree's own fragments |
| `docs/` | These pages (the README sources table is the only part updated automatically) |

The old xxKSU and mzggr files (hook styles, tuning, benchmark, xxKSU patches, the separate NoMount LKM workflow) are only in the [`xxksu` branch](../../../tree/xxksu).
