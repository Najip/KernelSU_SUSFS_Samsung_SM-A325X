# KernelSU_SUSFS_Samsung_SM-A325X

Android kernel for Samsung Galaxy A32 4G (SM-A325x, codename `a32`, MediaTek MT6768) with xxKSU (a KernelSU fork by backslashxx for non-GKI kernels), SUSFS by simonpunk ported to non-GKI by JackA1ltman, and NoMount (as a separate LKM or built into the kernel). Target: SM-A325F on LumiROM 9 (Android 17).

It builds two kernels: the main kernel **Aigis** (used every day by the repo owner) and the alternative kernel **mzggr**. Both are released.

This repo stores no kernel source. The GitHub Actions workflows download every source fresh, patch it and build a flashable ZIP.

## The two kernels

Every build can make two kernels. Both are released, so you can pick either one.

| | Main kernel: Aigis | Alternative kernel: mzggr |
|---|---|---|
| Who uses it | The repo owner, every day | Built and released too |
| Kernel tree | [Aigis by SlamZDank](https://github.com/SlamZDank/Aigis-Kernel-A32), branch `bpf-5.15-legion` | [mzggr0914](https://github.com/mzggr0914/android_kernel_a325x_bakasu), branch `common` |
| **Kernel** dropdown | `aigis` (default) | `mzggr` (`both` builds the two) |
| Kernel ZIP name | `A325X-Aigis-...zip` | `A325X-xxKSU-...zip` |
| GPU | Valhall GPU with its drivers module (ticked by default), or stock | Stock A32 GPU |
| Tuning | Aigis' own CPU/GPU tuning | Our **Performance tuning** (ticked by default) |
| Compiler | ZyC Clang 14 (as Aigis builds it), or AOSP Clang 14 | AOSP Clang 14 |
| NoMount file | `NoMount-...-aigis-...zip`, `nomount-4.14-aigis.ko` | `NoMount-...-mzggr-...zip`, `nomount-4.14-mzggr.ko` |
| Details file in a release | `build-info-aigis.txt`, `sources-aigis.json` | `build-info.txt`, `sources.json` |

Flash one kernel ZIP only, and the NoMount ZIP made for that same kernel.

## Sources used

The tables below are refreshed automatically each time a release is published: the main kernel (Aigis) first, then the alternative kernel (mzggr), then the xxKSU manager app of that release.

<!-- SOURCES:START -->
Last release: [build-20261120-79](../../releases/tag/build-20261120-79)

### Main kernel: Aigis

Used every day by the repo owner.

| Part | Source | Branch / version | Commit | Commit date |
|---|---|---|---|---|
| Kernel | [SlamZDank/Aigis-Kernel-A32](https://github.com/SlamZDank/Aigis-Kernel-A32) | `bpf-5.15-legion`, Linux 4.14.357 | [`dc0935aba4a7`](https://github.com/SlamZDank/Aigis-Kernel-A32/commit/dc0935aba4a71c0cf3d7c7fd3c38c1e5e58c86c6) | 2026-11-19 |
| xxKSU (root) | [backslashxx/KernelSU](https://github.com/backslashxx/KernelSU) | `master`, KSU_VERSION 32731, tag v3.3.1+54 | [`f27e1f0d3192`](https://github.com/backslashxx/KernelSU/commit/f27e1f0d3192820b0964881585d764ab0f0de56f) | 2026-11-20 |
| SUSFS patch | [JackA1ltman/NonGKI_Kernel_Build_2nd](https://github.com/JackA1ltman/NonGKI_Kernel_Build_2nd) | `mainline`, SUSFS v2.4.0, `Patches/Patch/susfs_patch_to_4.14.patch` | [`26f2313be61f`](https://github.com/JackA1ltman/NonGKI_Kernel_Build_2nd/commit/26f2313be61f7a8603a50b2dcd12171495a79d27) | 2026-11-18 |

### Alternative kernel: mzggr

Also built and released.

| Part | Source | Branch / version | Commit | Commit date |
|---|---|---|---|---|
| Kernel | [mzggr0914/android_kernel_a325x_bakasu](https://github.com/mzggr0914/android_kernel_a325x_bakasu) | `common`, Linux 4.14.357-openela | [`7dd52de28d1e`](https://github.com/mzggr0914/android_kernel_a325x_bakasu/commit/7dd52de28d1ee64dddc1f3e853e214fab7578c44) | 2026-11-16 |
| xxKSU (root) | [backslashxx/KernelSU](https://github.com/backslashxx/KernelSU) | `master`, KSU_VERSION 32731, tag v3.3.1+54 | [`f27e1f0d3192`](https://github.com/backslashxx/KernelSU/commit/f27e1f0d3192820b0964881585d764ab0f0de56f) | 2026-11-20 |
| SUSFS patch | [JackA1ltman/NonGKI_Kernel_Build_2nd](https://github.com/JackA1ltman/NonGKI_Kernel_Build_2nd) | `mainline`, SUSFS v2.4.0, `Patches/Patch/susfs_patch_to_4.14.patch` | [`26f2313be61f`](https://github.com/JackA1ltman/NonGKI_Kernel_Build_2nd/commit/26f2313be61f7a8603a50b2dcd12171495a79d27) | 2026-11-18 |

### Root manager app (for both kernels)

Install this app to manage root.

| Part | Source | Branch / version | Commit | Commit date |
|---|---|---|---|---|
| xxKSU manager | [backslashxx/KernelSU](https://github.com/backslashxx/KernelSU) | release [v3.3.1+54](https://github.com/backslashxx/KernelSU/releases/tag/v3.3.1%2B54), `KernelSU_v3.3.1+54_32735-release.apk` | - | 2026-11-20 |
<!-- SOURCES:END -->

Other parts (pinned in this repo):

| Part | Source | Version |
|---|---|---|
| Toolchain | AOSP Clang prebuilt | clang-r450784d (Clang 14.0.6), see `scripts/aosp_clang14.conf`. Used by mzggr, and by Aigis with **Compiler** `main` |
| Flasher | [osm0sis/AnyKernel3](https://github.com/osm0sis/AnyKernel3) | `af770f7b16cf8f8eb7c68614b2a693b3b361c90c` |
| NoMount LKM | [maxsteeel/nomount](https://github.com/maxsteeel/nomount) | `dev` (default) or `master`, chosen when you run the workflow |
| LKM loader | [maxsteeel/lkmloader](https://github.com/maxsteeel/lkmloader) | latest at build time |

Upstream repos and branches are set in `scripts/sources.conf`.

## What both kernels get

- xxKSU for root, replacing the tree's own root module (ReSukiSU in Aigis, BakaSU in mzggr) at build time.
- xxKSU hook style, chosen when you run the workflow (see [Hook styles](#hook-styles)). The default is `manual` (`branch_link` is currently unstable). No LSM hooking in any style.
- SUSFS v2.4.0: the core files (`fs/susfs.c`, `susfs.h`, `susfs_def.h`) come from JackA1ltman's patch. All features on: sus path, sus mount, sus kstat, spoof uname, spoof cmdline, open redirect, sus map, priority UID filter, hide symbols, logging.
- Upstream NoMount, replacing the tree's own NoMount: a separate LKM by default, or built in with the `integrate` option.
- Network fix (UDP-only GSO for IPv4 and IPv6). A tick, ticked by default, allowed with every release type (and with `Promoted`, which keeps the setting of the build it takes).
- No LTO.
- Built by `Najip@github`: shown in `/proc/version`, `uname -a` and About phone. The **uname tag** (default `-forkby-gh.Najip`) is added to `uname -r`.

### Main kernel: Aigis

- The [Aigis kernel by SlamZDank](https://github.com/SlamZDank/Aigis-Kernel-A32) from its default branch `bpf-5.15-legion`, with the SUSFS hooks of its `bpf-5.15-legion-susfs` branch.
- Aigis keeps its own CPU/GPU tuning. Our **Performance tuning** does not fit its tree, so for Aigis it is ignored with a warning (with `both`, only the mzggr ZIP gets the tuning).
- **Valhall GPU** (Aigis only, ticked by default, allowed with every release type): ticked = the Aigis Valhall r32p1 setup with their GPU tuning. There is one ZIP, which writes the r32p1 dtb and also installs their [Valhall drivers module](https://github.com/SlamZDank/Aigis-Kernel-A32/releases/download/GPU-Update/A32-Mali-Valhall-Drivers-KSU-Module.zip) (no kernel-only ZIP). ZIP names get `-vgpu`. Unticked = stock A32 GPU (`patches/base/0002-aigis-stock-gpu.patch`).
- **Compiler** (Aigis only): `aigis` (default) = ZyC Clang 14.0.6 the way the Aigis CI builds it; `main` = AOSP Clang 14 as for mzggr (ZIP names get `-aospclang`).

### Alternative kernel: mzggr

- mzggr0914's SLM-based Linux 4.14.357-openela tree (`4.14.357-openela-vigus-slmkernel-a32`). It carries the BPF backports and the fake `5.10` version for `netbpfload`, so newer ROMs such as LumiROM 9 (Android 17) boot.
- The tree's BakaSU and in-tree NoMount are swapped the same way as the booting [Najip/android_kernel_a325F_bakasu `xxksu`](https://github.com/Najip/android_kernel_a325F_bakasu/tree/xxksu) branch, stored here as `patches/base/0001-mzggr-common-to-xxksu-susfs.patch`. The SUSFS hooks in the rest of the kernel are the 4.14 ones already in mzggr0914's tree.
- Config as the tree ships it: `mt6768_slm_defconfig` + `a32.config` + `battery.config` (CPU undervolt, conservative governor, 100 Hz) + `ksu-a325n-common.config` + `a325n-release.config`.
- Performance tuning (ticked by default, mzggr only), taken from [Najip/android_kernel_a325F_bakasu](https://github.com/Najip/android_kernel_a325F_bakasu): GPU 1100 MHz @ 1.035 V, CCI overclock, CPU/CCI undervolt, DDR DVFS tweaks, BORE scheduler, 250 Hz, schedutil governor, fast charging with the screen on, zram default `zstd`, GPU frequency meter at `/sys/kernel/gpu/gpu_fmeter`, USB autosuspend off, BBR TCP and fq_codel. The undervolt was tuned on one phone; if yours freezes or reboots under load, build without tuning.
- Toolchain: AOSP Clang 14 with ld.lld and GNU as.

## How to build

1. Open the repo on GitHub and go to the **Actions** tab.
2. Pick **Build Kernel** on the left, then press **Run workflow**.
3. Choose the options and press the green **Run workflow** button:
   - **Prefer my own PC (self-hosted)**: ticked by default. If the PC is already busy with another build (any branch or workflow), the run checks the average build times and uses a free GitHub runner when that would finish sooner than waiting. Untick to always use a GitHub runner.
   - **xxKSU hook style**: `manual` by default, then `syscall_table`, then `branch_link` (currently unstable). See [Hook styles](#hook-styles).
   - **Kernel**: `aigis` by default, or `mzggr`, or `both` (see [The two kernels](#the-two-kernels)).
   - **Performance tuning**: ticked by default (mzggr only, ignored for Aigis). Allowed with every release type.
   - **Valhall GPU** and **Compiler**: Aigis only, ignored for mzggr.
   - **uname tag**: `-forkby-gh.Najip` by default, added to the end of `uname -r` on both kernels (for example `4.14.357-openela-vigus-slmkernel-a32-forkby-gh.Najip`). Letters, digits, space and `. _ + -` only (no `/`, the release name is also a folder name). Clear it for the kernel's own name. `bpfloader`, `netbpfload` and `netd` still see the fixed fake version, so networking is not affected. A NoMount module must be built with the same tag (the **NoMount LKM** workflow has the same box).
   - **Network fix**: ticked by default. Untick to build without the UDP GSO network fix. Allowed with every release type.
   - **Commit mode**: `Latest` by default. See [Commit modes](#commit-modes).
   - **Release**: `CI` by default, so nothing is published. `Pre-release` publishes a pre-release, `Release` publishes a full release, and `Release from last pre-release` turns the newest pre-release into the full Release without building. Both attach the NoMount module built in the same run (see below).
   - **NoMount**: `lkm` by default, a separate module (`NoMount-...-aigis-....zip` and `nomount-4.14-aigis.ko`, or `mzggr`) built for this exact kernel. `integrate` builds NoMount into the kernel itself (the kernel ZIP name gets `-nm`), and `no` leaves it out.
   - **NoMount branch**: `dev` by default, or `master`. Used for both `lkm` and `integrate`.
   - **NoMount only**: unticked by default. Tick it to build only the NoMount module, no kernel ZIP (see [NoMount without a kernel compile](#nomount-without-a-kernel-compile)).
   - **Build hook benchmark**: unticked by default. Tick it only when you want the `hook-bench` tool; the kernel does not need it.
4. When the run is green, open it and download from **Artifacts**:
   - `A325X-xxKSU-SUSFS-....zip`: the flashable kernel ZIP (downloaded as-is, not a ZIP inside a ZIP).
   - `build-info.txt`: what was built (also inside the ZIP).
   - `NoMount-...-<kernel>-....zip` and `nomount-4.14-<kernel>.ko` (`<kernel>` = `aigis` or `mzggr`): with NoMount `lkm`. The ZIP is flashed as a module in the KernelSU manager.
   - `xxksu-manager`: the xxKSU manager APK of the latest [xxKSU release](https://github.com/backslashxx/KernelSU/releases/latest) (the **List manager APK** job, every run). The artifact downloads as a ZIP with the `.apk` inside; releases attach the `.apk` itself.
   - `hook-bench`: the benchmark tool and its script, only when **Build hook benchmark** was ticked (see below).

No Actions secret is needed. The workflows use the built-in `GITHUB_TOKEN`.

## Hook styles

xxKSU needs to see a few syscalls: `execve`/`execveat` (for `su` and `ksud`), `faccessat` and `newfstatat` (so apps can find `su`), `reboot` (manager and SUSFS commands), and `newfstat`/`read` during boot (to add its lines to `init.rc`). There are three ways to catch them on this non-GKI 4.14 kernel:

| Style | ZIP name ends in | How it works |
|---|---|---|
| `manual` (default) | nothing | The kernel source calls xxKSU directly inside `fs/exec.c`, `fs/open.c`, `fs/stat.c` and `kernel/reboot.c`. Fixed at compile time. |
| `syscall_table` | `-sct` | xxKSU replaces those entries in `sys_call_table` with small wrappers at boot. The `newfstat`/`read` ones are put back once `init.rc` is done. |
| `branch_link` (currently unstable) | `-bl` | Starts like `syscall_table`, then shortly after `init.rc` is handled rewrites the `bl` (call) instructions inside `sys_faccessat`, `sys_newfstatat` and `sys_execve` to jump straight to xxKSU, and removes each table hook that worked. If one cannot be patched, its table hook stays. HMA-oss and BRENE's priority UID filter fail with it; use `manual`. |

For `syscall_table` and `branch_link`, `patches/hooks/0001-hookless-skip-parent-hooks.patch` switches off the kernel's own calls for those syscalls, so nothing runs twice. The security hooks (setuid, rename, setxattr, setprocattr, file permission) stay manual in all three styles, and SUSFS is the same in all three.

The same NoMount module works with all three styles. NoMount does not hook syscalls, and the kernel version string is the same.

### Comparing them

1. Build the kernel once per style (same tuning setting each time), and tick **Build hook benchmark** in one of the runs and download its `hook-bench` artifact.
2. Copy `hook-bench` and `hook-bench.sh` to the same folder on the phone, for example `/sdcard/Download`.
3. Flash one kernel, reboot, wait 2-3 minutes, then in Termux run `sh /sdcard/Download/hook-bench.sh`. With root it also runs the test as root and shows from `dmesg` which style is active (for `branch_link` it shows which patches worked).
4. Repeat for the other styles. Results are saved in `/sdcard/hook-bench/`.

The script times `faccessat` and `newfstatat` on `/system/bin/su` and `/system/bin/sh`, `fstat`, `read`, and `fork + execve`, and prints nanoseconds per call (median and best of 7 rounds). Lower is faster. `fstat` and `read` only act as a baseline, since they are no longer hooked after boot in any style. The differences are expected to be small, so run each test 2-3 times with the phone cool and idle, and compare medians.

## Commit modes

Every build picks the commits of the kernel, xxKSU and the SUSFS patch in one of three ways. The pins are saved in `configs/verified.json`.

| Mode | What it builds | When to use it |
|---|---|---|
| `Latest` (default) | The newest commit of each source. | Trying out new upstream changes. |
| `Verified` | The pinned commits saved by the last successful `Promoted` build. | Rebuilding something you already tested. A full `Release` only works in this mode. |
| `Promoted` | Nothing new is compiled for the kernel. It takes the files of the most recent successful `Latest` run with the default kernel options (on the same branch) and saves that run's commits as the new `Verified` pins. | After you have flashed and tested the newest default `Latest` build and want to mark it as good. |

Tuning is allowed in every release type, and `Promoted` takes builds with or without tuning.

`Verified` keeps separate pins for each kernel. The Aigis pins come from a `Promoted` run with Kernel `aigis` or `both`; before that, `Verified` with Aigis stops with "No verified Aigis commits yet".

Which `Latest` runs `Promoted` accepts: hook style `manual`, NoMount `lkm` or `no` (not `integrate`), not a **NoMount only** run and **Compiler** `aigis`, and it must have built every kernel you picked (Kernel `both` needs a `Latest` run with `both`; `mzggr` or `aigis` also accept a `both` run). The runner (your PC or GitHub), tuning, **Valhall GPU** (Promoted keeps the GPU of that run), the release type and the benchmark tick do not matter. Runs with other options are skipped. If no run fits, `Promoted` ends with the warning "Nothing promoted" and changes nothing.

How `Promoted` gets the NoMount module:

- If that `Latest` run already has the NoMount module from the chosen **NoMount branch**, it is reused. Nothing is built.
- If it has none (NoMount `no`) or one from the other branch, `Promoted` builds the module from that run's saved kernel kit, without compiling the kernel. Older runs from before the kit existed fall back to compiling the kernel once, only to match the module.
- With NoMount `no`, the promoted build has no module. `integrate` is not allowed with `Promoted`.

With **Release** set to `CI`, the files are kept as artifacts of the `Promoted` run. With `Pre-release`, they are published as a pre-release. The hook style and tuning options are ignored in `Promoted`; they come from the `Latest` run.

A full `Release` with `Latest` or `Promoted` stops with the message "Release must use Verified". Use `Pre-release` for those, or switch to `Verified`.

**Release from last pre-release** (no build): test first, then publish exactly what you flashed.

1. Run Build Kernel with commit mode `Verified` and release type `Pre-release`, and flash that pre-release.
2. When it works, run Build Kernel again with commit mode `Verified` and release type `Release from last pre-release`. The newest pre-release of this branch becomes the full Release (same ZIPs, notes rewritten as "what's new since the last Release") and the README sources table is updated. Kernel options are ignored here.

It stops with "Release must use Verified" when that pre-release was not built from the commits in `configs/verified.json` (for example a `Latest` pre-release, or one made before a newer `Promoted`).

"What's new" in a full Release always compares with the previous full Release; a pre-release compares with the previous release of any kind. A previous release of another kernel repo makes it a "First release".

With NoMount `lkm`, a `Pre-release` or `Release` attaches the module ZIP and `nomount-4.14-<kernel>.ko` built in the same run to the release page, plus the xxKSU manager `.apk`. The README sources table is updated only by a full `Release`.

## Upstream check

The **Upstream check** workflow runs three times a day (07:00, 15:00 and 23:00 Jakarta time) and looks for new commits in:

- the mzggr kernel (`common`) and the Aigis kernel (`bpf-5.15-legion`)
- xxKSU (`master`)
- Jack's SUSFS (`mainline`), only commits that changed the 4.14 patch the build uses

NoMount is not watched. The newest commits it has seen are saved in `configs/upstream-state.json` on the default branch, with a short history of what changed. The first check only saves them. When a later check finds a new commit, it starts **Build Kernel** with Kernel `both`, commit mode `Latest` and release type `CI` (never a release), and lists the new commits in the run summary. The build runs on the branch in the repo variable `UPSTREAM_BUILD_REF` (default: the default branch, `main`). Run it by hand from the Actions tab to check now; untick **Build** to only check and save.

For the mzggr and Aigis kernels, a new commit only counts when it changes the kernel itself. Commits that only touch the tree's own root module (BakaSU, KSUN, ReSukiSU or any other KernelSU fork, as a submodule or folder), NoMount, `.gitmodules`, `.github/` or docs (`docs/`, README, `*.md`) are ignored: they do not start a build, since the build replaces those with xxKSU and upstream NoMount anyway. They are still saved and listed under **Ignored kernel commits** in the run summary. Any other file (sources, defconfig, build scripts, SUSFS) counts.

## NoMount without a kernel compile

A module only needs three files from the kernel it is built for: `.config`, `Module.symvers` (this kernel has `CONFIG_MODVERSIONS=y`, so the module must carry the symbol versions of the real kernel) and the kernel release string. Every full kernel build saves these as a `kernel-kit-...` artifact (kept 30 days). Module signing is off in this kernel, so nothing else is needed.

To build a module with a kit, the run downloads and patches the same sources, copies the kit's `.config`, runs `make modules_prepare` (a minute or two instead of a full compile), adds the kit's `Module.symvers` and builds only NoMount. It checks that the `.config` and the kernel release match the kit, and that the module's `vermagic` matches.

This is used by `Promoted` and by **NoMount only**. For **NoMount only**, the kit is looked up by the exact kernel: the same kernel, xxKSU and SUSFS commits, hook style, tuning, and the same build-repo patches, configs and build scripts. If no kit matches (for example a new upstream commit since the last full build), the kernel is compiled once in that run to match the module, and no kernel ZIP is made. **NoMount only** needs NoMount `lkm` and release type `CI`, and does not work with `Promoted`.

## NoMount LKM

1. Actions -> **NoMount LKM** -> **Run workflow**.
2. Pick the NoMount branch (`dev` is the default, or `master`), the **xxKSU hook style** and the **commit mode**. Keep the **Kernel**, hook style, **Performance tuning** (mzggr), **Valhall GPU** and **Compiler** (Aigis) the same as the kernel you flashed. **Build on my own PC** is unticked by default here, so it runs on a free GitHub runner.
3. Download the `NoMount-....zip` artifact and flash it as a module in the KernelSU manager.

The module is compiled together with a kernel from the same sources in the same run, so it matches a kernel built from the same commits. If the sources have moved on since you built your kernel, rebuild both.

## How to flash

1. Back up your current `boot` partition.
2. Flash the kernel ZIP with a custom recovery (TWRP / OrangeFox) or an AnyKernel3 flasher app.
3. Reboot, install the xxKSU manager from [backslashxx/KernelSU releases](https://github.com/backslashxx/KernelSU/releases), and install a SUSFS userspace module if you want to configure SUSFS.

The ZIP only replaces the kernel inside `boot` and keeps your ramdisk.

After writing the kernel, the ZIP also checks your modules (when `/data` is mounted and decrypted):

- **NoMount check** (every kernel ZIP): every kernel has a **kernel ID** (in `build-info.txt`, line "Kernel ID (NoMount match)"), made from its kernel release, `.config` and symbol checksums. A NoMount module stores the ID of the kernel it was built for (`kernelId=` in its `module.prop`, also shown in its description). A module from any build of the same kernel has the same ID, so it does not have to come from the same run. If the installed NoMount module has a different ID, the flasher shows a warning to remove it in the KernelSU manager and install the NoMount ZIP built for this kernel. It is only a warning; nothing is deleted. Older modules without an ID are compared by kernel release, and the flasher says they cannot be fully verified. With NoMount `integrate`, an installed NoMount LKM module gets a warning to remove it.
- **GPU module cleanup** (mzggr ZIP only): the mzggr kernel uses the stock A32 GPU, so the Aigis Valhall GPU drivers module (`a32-gpu-upgrade`) is deleted if it is installed.

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
| `configs/verified.json` | Commits pinned by the last successful `Promoted` build |
| `scripts/resolve_commits.py` | Picks the commits for Latest, Verified and Promoted |
| `scripts/promoted_source.py` | Finds and collects the `Latest` run that `Promoted` takes its files from |
| `scripts/build_nomount.sh` | Builds the NoMount module (after a kernel compile, or from a kernel kit) |
| `scripts/kernel_kit.py` | Kernel kit key, lookup and download |
| `scripts/kernel_id.sh` | Kernel ID that the flasher uses to check the NoMount module |
| `anykernel/nomount-check.sh`, `anykernel/gpu-cleanup.sh` | Flasher checks added after the kernel is written |
| `configs/nomount-integrate.config` | Turns on NoMount built into the kernel (`integrate`) |
| `tools/hook-bench.c`, `tools/hook-bench.sh` | Benchmark for comparing hook styles |
| `configs/` | Config fragments merged after the tree's own fragments |
| `anykernel/anykernel.sh` | AnyKernel3 settings (device `a32`, `boot` partition) |
