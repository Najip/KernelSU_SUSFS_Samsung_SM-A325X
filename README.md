# KernelSU_SUSFS_Samsung_SM-A325X

Android kernel for Samsung Galaxy A32 4G (SM-A325x, codename `a32`, MediaTek MT6768) with xxKSU (a KernelSU fork by backslashxx for non-GKI kernels), SUSFS by simonpunk ported to non-GKI by JackA1ltman, and the NoMount LKM. Target: SM-A325F on LumiROM 9 (Android 16).

This repo stores no kernel source. The GitHub Actions workflows download every source fresh, patch it and build a flashable ZIP.

## Sources used

The table below is refreshed automatically each time a release is published.

<!-- SOURCES:START -->
Last release: [build-20261119-21](../../releases/tag/build-20261119-21)

| Part | Source | Branch / version | Commit | Commit date |
|---|---|---|---|---|
| Kernel | [mzggr0914/android_kernel_a325x_bakasu](https://github.com/mzggr0914/android_kernel_a325x_bakasu) | `common`, Linux 4.14.357-openela | [`7dd52de28d1e`](https://github.com/mzggr0914/android_kernel_a325x_bakasu/commit/7dd52de28d1ee64dddc1f3e853e214fab7578c44) | 2026-11-16 |
| xxKSU | [backslashxx/KernelSU](https://github.com/backslashxx/KernelSU) | `master`, KSU_VERSION 32731, tag v3.3.1-54 | [`22b67efa772e`](https://github.com/backslashxx/KernelSU/commit/22b67efa772e961f913c4a9e674b43fa6eadf6b1) | 2026-11-19 |
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

- Kernel: mzggr0914's SLM-based Linux 4.14.357-openela tree (`4.14.357-openela-vigus-slmkernel-a32`). It carries the BPF backports and the fake `5.10` version for `netbpfload`, so Android 15 and 16 ROMs such as LumiROM 9 boot.
- The tree's own BakaSU and in-tree NoMount are removed at build time and replaced by xxKSU and the NoMount LKM. The conversion is the same as the booting [Najip/android_kernel_a325F_bakasu `xxksu`](https://github.com/Najip/android_kernel_a325F_bakasu/tree/xxksu) branch, stored here as `patches/base/0001-mzggr-common-to-xxksu-susfs.patch`.
- xxKSU hook style, chosen when you run the workflow (see [Hook styles](#hook-styles)). The default `manual` is the one that has been tested on the phone. No LSM hooking in any style.
- SUSFS v2.4.0: the core files (`fs/susfs.c`, `susfs.h`, `susfs_def.h`) come from JackA1ltman's patch; the hooks in the rest of the kernel are the 4.14 ones already in mzggr0914's tree. All features on: sus path, sus mount, sus kstat, spoof uname, spoof cmdline, open redirect, sus map, priority UID filter, hide symbols, logging.
- Config as the tree ships it: `mt6768_slm_defconfig` + `a32.config` + `battery.config` (CPU undervolt, conservative governor, 100 Hz) + `ksu-a325n-common.config` + `a325n-release.config`.
- Network fix (UDP-only GSO for IPv4 and IPv6). Always applied.
- Optional performance tuning (only when ticked), taken from [Najip/android_kernel_a325F_bakasu](https://github.com/Najip/android_kernel_a325F_bakasu): GPU 1100 MHz @ 1.035 V, CCI overclock, CPU/CCI undervolt, DDR DVFS tweaks, BORE scheduler, 250 Hz, schedutil governor, fast charging with the screen on, zram default `zstd`, GPU frequency meter at `/sys/kernel/gpu/gpu_fmeter`, USB autosuspend off, BBR TCP and fq_codel. The undervolt was tuned on one phone; if yours freezes or reboots under load, build without tuning.
- Toolchain: AOSP Clang 14 with ld.lld and GNU as. No LTO.

## How to build

1. Open the repo on GitHub and go to the **Actions** tab.
2. Pick **Build Kernel** on the left, then press **Run workflow**.
3. Choose the options and press the green **Run workflow** button:
   - **Prefer my own PC (self-hosted)**: ticked by default. If the PC is already busy with another build (any branch or workflow), the run checks the average build times and uses a free GitHub runner when that would finish sooner than waiting. Untick to always use a GitHub runner.
   - **xxKSU hook style**: `manual` by default. `syscall_table` and `branch_link` are for comparing speed, see [Hook styles](#hook-styles).
   - **Performance tuning**: unticked by default.
   - **Publish a GitHub Release**: unticked by default. When ticked, the run also creates a release (ZIP, `build-info.txt`, `sources.json`, `SHA256SUMS.txt`), lists what is new in each source since the previous release, and updates the "Sources used" table above.
4. When the run is green, open it and download from **Artifacts**:
   - `A325X-xxKSU-SUSFS-....zip`: the flashable kernel ZIP (downloaded as-is, not a ZIP inside a ZIP).
   - `build-info.txt`: what was built (also inside the ZIP).
   - `hook-bench`: the benchmark tool and its script (see below).

No Actions secret is needed. The workflows use the built-in `GITHUB_TOKEN`.

## Hook styles

xxKSU needs to see a few syscalls: `execve`/`execveat` (for `su` and `ksud`), `faccessat` and `newfstatat` (so apps can find `su`), `reboot` (manager and SUSFS commands), and `newfstat`/`read` during boot (to add its lines to `init.rc`). There are three ways to catch them on this non-GKI 4.14 kernel:

| Style | ZIP name ends in | How it works |
|---|---|---|
| `manual` (default) | nothing | The kernel source calls xxKSU directly inside `fs/exec.c`, `fs/open.c`, `fs/stat.c` and `kernel/reboot.c`. Fixed at compile time. This is the style that has been tested on the phone. |
| `syscall_table` | `-sct` | xxKSU replaces those entries in `sys_call_table` with small wrappers at boot. The `newfstat`/`read` ones are put back once `init.rc` is done. |
| `branch_link` | `-bl` | Starts like `syscall_table`, then shortly after `init.rc` is handled rewrites the `bl` (call) instructions inside `sys_faccessat`, `sys_newfstatat` and `sys_execve` to jump straight to xxKSU, and removes each table hook that worked. If one cannot be patched, its table hook stays. |

For `syscall_table` and `branch_link`, `patches/hooks/0001-hookless-skip-parent-hooks.patch` switches off the kernel's own calls for those syscalls, so nothing runs twice. The security hooks (setuid, rename, setxattr, setprocattr, file permission) stay manual in all three styles, and SUSFS is the same in all three.

The same NoMount module works with all three styles. NoMount does not hook syscalls, and the kernel version string is the same.

### Comparing them

1. Build the kernel once per style (same tuning setting each time), and download the `hook-bench` artifact from any of the runs.
2. Copy `hook-bench` and `hook-bench.sh` to the same folder on the phone, for example `/sdcard/Download`.
3. Flash one kernel, reboot, wait 2-3 minutes, then in Termux run `sh /sdcard/Download/hook-bench.sh`. With root it also runs the test as root and shows from `dmesg` which style is active (for `branch_link` it shows which patches worked).
4. Repeat for the other styles. Results are saved in `/sdcard/hook-bench/`.

The script times `faccessat` and `newfstatat` on `/system/bin/su` and `/system/bin/sh`, `fstat`, `read`, and `fork + execve`, and prints nanoseconds per call (median and best of 7 rounds). Lower is faster. `fstat` and `read` only act as a baseline, since they are no longer hooked after boot in any style. The differences are expected to be small, so run each test 2-3 times with the phone cool and idle, and compare medians.

## NoMount LKM

1. Actions -> **NoMount LKM** -> **Run workflow**.
2. Pick the NoMount branch (`dev` is the default, or `master`). **Build on my own PC** is unticked by default here, so it runs on a free GitHub runner. Keep **Performance tuning** the same as the kernel you flashed.
3. Download the `NoMount-....zip` artifact and flash it as a module in the KernelSU manager.

The module is compiled together with a kernel from the same sources in the same run, so it matches a kernel built from the same commits. If the sources have moved on since you built your kernel, rebuild both.

## How to flash

1. Back up your current `boot` partition.
2. Flash the kernel ZIP with a custom recovery (TWRP / OrangeFox) or an AnyKernel3 flasher app.
3. Reboot, install the xxKSU manager from [backslashxx/KernelSU releases](https://github.com/backslashxx/KernelSU/releases), and install a SUSFS userspace module if you want to configure SUSFS.

The ZIP only replaces the kernel inside `boot` and keeps your ramdisk.

## Collecting logs

`tools/collect-logs.sh` gathers everything needed to debug a bootloop or a root problem. It runs both in TWRP and in booted Android (as root).

1. Download it to the phone: [collect-logs.sh](https://raw.githubusercontent.com/Najip/KernelSU_SUSFS_Samsung_SM-A325X/main/tools/collect-logs.sh) (long-press, "Download link"). It lands in `/sdcard/Download/`.
2. Run it:
   - TWRP: Advanced > Terminal, then `sh /sdcard/Download/collect-logs.sh`
   - Termux: `su -c sh /sdcard/Download/collect-logs.sh`
3. Logs are saved to `/sdcard/kernel-logs/<date-time>-twrp` (or `-android`), plus a `.tar.gz` of the same folder. Start with `summary.txt`.

After a bootloop, go straight to TWRP (Volume Down + Power, then Volume Up + Power, without powering off) so the crash log of the failed boot is still in memory. If `/sdcard` is not writable in TWRP, the script falls back to the SD card or `/data/local/tmp`.

## Credits

- [mzggr0914/android_kernel_a325x_bakasu](https://github.com/mzggr0914/android_kernel_a325x_bakasu): the kernel tree used here (A32 4G BakaSU kernel with 4.14 SUSFS hooks).
- [Samsung-MT6769-Devs/android_kernel_samsung_mt6768](https://github.com/Samsung-MT6769-Devs/android_kernel_samsung_mt6768): the SLM MT6768 kernel source that tree is based on.
- [backslashxx/KernelSU](https://github.com/backslashxx/KernelSU): xxKSU.
- [simonpunk/susfs4ksu](https://gitlab.com/simonpunk/susfs4ksu): SUSFS, and [JackA1ltman/NonGKI_Kernel_Build_2nd](https://github.com/JackA1ltman/NonGKI_Kernel_Build_2nd) for the non-GKI 4.14 port.
- [maxsteeel/nomount](https://github.com/maxsteeel/nomount) and [maxsteeel/lkmloader](https://github.com/maxsteeel/lkmloader): NoMount LKM.
- [osm0sis/AnyKernel3](https://github.com/osm0sis/AnyKernel3): flashable ZIP.
- [Najip/android_kernel_a325F_bakasu](https://github.com/Najip/android_kernel_a325F_bakasu/tree/xxksu): the xxKSU + SUSFS conversion this repo reproduces.

## Repo layout

| Path | What it is |
|---|---|
| `.github/workflows/kernel.yml` | Kernel build and release (own PC by default) |
| `.github/workflows/nomount-lkm.yml` | NoMount module build (GitHub runner by default) |
| `scripts/sources.conf` | Upstream repos, branches and config fragments |
| `scripts/prepare_sources.sh` | Downloads the sources and applies all patches |
| `scripts/build_kernel.sh` | Configures and compiles |
| `scripts/package_zip.sh` | Makes the AnyKernel3 ZIP and `build-info.txt` |
| `scripts/release_notes.py` | Release notes and README table |
| `tools/collect-logs.sh` | Log collector for TWRP and rooted Android |
| `patches/base/` | Turns mzggr0914's BakaSU tree into the xxKSU + SUSFS layout |
| `patches/susfs/` | Small additions on top of JackA1ltman's SUSFS core files |
| `patches/kernelsu/` | Small xxKSU changes for SUSFS |
| `patches/kernel/` | Network fix and optional tuning |
| `patches/hooks/` | Turns off the kernel's own xxKSU calls for the `syscall_table` and `branch_link` styles |
| `configs/hooks/` | One config fragment per hook style |
| `tools/hook-bench.c`, `tools/hook-bench.sh` | Benchmark for comparing hook styles |
| `configs/` | Config fragments merged after the tree's own fragments |
| `anykernel/anykernel.sh` | AnyKernel3 settings (device `a32`, `boot` partition) |
