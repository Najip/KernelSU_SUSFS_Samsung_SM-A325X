# KernelSU_SUSFS_Samsung_SM-A325X

Android kernel for Samsung Galaxy A32 4G (SM-A325x, codename `a32`) with xxKSU (a KernelSU fork by backslashxx for non-GKI kernels), SUSFS by simonpunk ported to non-GKI by JackA1ltman, and the NoMount LKM. Tested using SM-A325F.

This repo stores no kernel source. The GitHub Actions workflows download every source fresh, patch it and build a flashable ZIP.

## Sources used

The table below is refreshed automatically each time a release is published.

<!-- SOURCES:START -->
Last release: [build-20261119-8](../../releases/tag/build-20261119-8)

| Part | Source | Branch / version | Commit | Commit date |
|---|---|---|---|---|
| Kernel | [mertsan2007/android_kernel_samsung_mt6768-k414](https://github.com/mertsan2007/android_kernel_samsung_mt6768-k414) | `upstream`, Linux 4.14.200 | [`10f1f45423f7`](https://github.com/mertsan2007/android_kernel_samsung_mt6768-k414/commit/10f1f45423f771a1105fd795533d638edcf58354) | 2026-11-17 |
| xxKSU | [backslashxx/KernelSU](https://github.com/backslashxx/KernelSU) | `master`, KSU_VERSION 32731, tag v3.3.1-52 | [`ae59aa5509c3`](https://github.com/backslashxx/KernelSU/commit/ae59aa5509c39276117e15f8fedc0740e5bda7f8) | 2026-11-19 |
| SUSFS patch | [JackA1ltman/NonGKI_Kernel_Build_2nd](https://github.com/JackA1ltman/NonGKI_Kernel_Build_2nd) | `mainline`, SUSFS v2.4.0, `Patches/Patch/susfs_patch_to_4.14.patch` | [`26f2313be61f`](https://github.com/JackA1ltman/NonGKI_Kernel_Build_2nd/commit/26f2313be61f7a8603a50b2dcd12171495a79d27) | 2026-11-18 |
<!-- SOURCES:END -->

Other parts (pinned in this repo):

| Part | Source | Version |
|---|---|---|
| Toolchain | AOSP Clang prebuilt | clang-r450784d (Clang 14.0.6), see `scripts/aosp_clang14.conf` |
| Flasher | [osm0sis/AnyKernel3](https://github.com/osm0sis/AnyKernel3) | `af770f7b16cf8f8eb7c68614b2a693b3b361c90c` |
| NoMount LKM | [maxsteeel/nomount](https://github.com/maxsteeel/nomount) | `dev` (default) or `master`, chosen when you run the workflow |
| LKM loader | [maxsteeel/lkmloader](https://github.com/maxsteeel/lkmloader) | latest at build time |

Upstream repos and branches are set in `scripts/sources.conf`.

## What the kernel contains

- xxKSU in manual-hook mode (no LSM, syscall-table or branch-link hooking).
- SUSFS (all features on: sus path, sus mount, sus kstat, spoof uname, spoof cmdline, open redirect, sus map, priority UID filter, hide symbols, logging).
- Samsung protections that block root are turned off: UH/RKP, KDP, DEFEX, PROCA, DSMS, Integrity. Knox NCM stays on because Samsung's network code needs it.
- EROFS support, needed by custom ROMs such as LumiROM whose `/system` is EROFS (stock a32_defconfig leaves it off, which bootloops on those ROMs). Also blkio, pids and devices cgroups, matching the older working kernel.
- Network fix (UDP GSO fix for IPv4 and IPv6). Always applied.
- Optional performance tuning (only when ticked): fast-charge thermal limit fix, zram default `zstd`, GPU frequency meter, USB autosuspend off, BBR TCP and fq_codel by default. Stock already uses 250 Hz and schedutil.
- No LTO.

## How to build

1. Open the repo on GitHub and go to the **Actions** tab.
2. Pick **Build Kernel** on the left, then press **Run workflow**.
3. Choose the options and press the green **Run workflow** button:
   - **Build on my own PC (self-hosted runner)**: ticked by default. Untick to use a free GitHub runner instead.
   - **Performance tuning**: unticked by default.
   - **Publish a GitHub Release**: unticked by default. When ticked, the run also creates a release (ZIP, `build-info.txt`, `sources.json`, `SHA256SUMS.txt`), lists what is new in each source since the previous release, and updates the "Sources used" table above.
4. When the run is green, open it and download from **Artifacts**:
   - `A325X-xxKSU-SUSFS-....zip`: the flashable kernel ZIP (downloaded as-is, not a ZIP inside a ZIP).
   - `build-info.txt`: what was built (also inside the ZIP).

No Actions secret is needed. The workflows use the built-in `GITHUB_TOKEN`.

## NoMount LKM

1. Actions -> **NoMount LKM** -> **Run workflow**.
2. Pick the NoMount branch (`dev` is the default, or `master`). Keep **Performance tuning** the same as the kernel you flashed.
3. Download the `NoMount-....zip` artifact and flash it as a module in the KernelSU manager.

The module is compiled together with a kernel from the same sources in the same run, so it matches a kernel built from the same commits. If the sources have moved on since you built your kernel, rebuild both.

## How to flash

1. Back up your current `boot` partition.
2. Flash the kernel ZIP with a custom recovery (TWRP / OrangeFox) or an AnyKernel3 flasher app.
3. Reboot, install the xxKSU manager from [backslashxx/KernelSU releases](https://github.com/backslashxx/KernelSU/releases), and install a SUSFS userspace module if you want to configure SUSFS.

The ZIP only replaces the kernel inside `boot` and keeps your ramdisk.

## Repo layout

| Path | What it is |
|---|---|
| `.github/workflows/kernel.yml` | Kernel build and release |
| `.github/workflows/nomount-lkm.yml` | NoMount module build |
| `scripts/prepare_sources.sh` | Downloads the sources and applies all patches |
| `scripts/apply_susfs.py` | Applies JackA1ltman's SUSFS patch (with the one Samsung fix-up) |
| `scripts/build_kernel.sh` | Configures and compiles |
| `scripts/package_zip.sh` | Makes the AnyKernel3 ZIP and `build-info.txt` |
| `scripts/release_notes.py` | Release notes and README table |
| `patches/fixes/` | Build fixes for the kernel tree (left over from its 4.14.200 merge) |
| `patches/integration/` | Connects xxKSU and SUSFS to the kernel (manual hooks) |
| `patches/kernelsu/` | Small xxKSU changes for SUSFS |
| `patches/kernel/` | Network fix and optional tuning |
| `overlay/` | Extra source files copied into the kernel tree |
| `configs/` | Config fragments merged on top of `a32_defconfig` |
| `anykernel/anykernel.sh` | AnyKernel3 settings (device `a32`, `boot` partition) |
