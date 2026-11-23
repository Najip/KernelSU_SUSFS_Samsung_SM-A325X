# KernelSU_SUSFS_Samsung_SM-A325X

Android kernel for Samsung Galaxy A32 4G (SM-A325x series, codename `a32`, MediaTek MT6768): the **Aigis** kernel by SlamZDank with [BakaSU](https://github.com/Baka-SU/BakaSU) for root (a KernelSU fork for non-GKI kernels), SUSFS by simonpunk ported to non-GKI by JackA1ltman, and NoMount. Tested only on: SM-A325F on LumiROM 9 (Android 17).

This repo stores no kernel source. The GitHub Actions workflows download every source fresh, patch it and build a flashable ZIP.

## Why BakaSU, not xxKSU

Until 22 Nov 2026 I built with xxKSU (backslashxx/KernelSU). Its developer archived that repo on 22 Nov 2026 (as of 23 Nov 2026 its future is unknown), so it gets no more fixes. Since then I build only Aigis with BakaSU, which is actively developed and supports SUSFS on 4.14. The Alt. kernel (mzggr) was xxKSU-only and is not developed anymore, so it is dropped too.

The old xxKSU pipeline (Aigis and mzggr, hook styles, benchmark) is kept, frozen, in the [`xxksu` branch](../../tree/xxksu). Older releases with xxKSU stay on the [Releases](../../releases) page.

## What the kernel gets

- BakaSU for root, from its `main` branch, with its SUSFS inline hooks (calls compiled into the kernel, the fastest style that works with SUSFS). The BakaSU manager app of the same BakaSU commit is in every release.
- SUSFS v2.4.0: the core files (`fs/susfs.c`, `susfs.h`, `susfs_def.h`) come from JackA1ltman's patch. All features on: sus path, sus mount, sus kstat, spoof uname, spoof cmdline, open redirect, sus map, priority UID filter, hide symbols, logging.
- Upstream NoMount, built for this exact kernel. The kernel ZIP carries it and installs or replaces it when you flash; it is also released as a separate ZIP. Or built into the kernel with the `integrate` option.
- Valhall GPU with Aigis' drivers module (default), or the stock A32 GPU. Aigis' own CPU/GPU tuning.
- Network fix by Juan (LumiROM): UDP-only GSO for IPv4 and IPv6, ticked by default. No LTO.
- JPEG + BBR fix: every kernel ZIP installs the small root module `a32-jpeg-bbr`. It fixes blank JPEG photos in Telegram and other apps on One UI 9 ports by letting apps use the kernel's `mtk_mm` memory heap, and keeps TCP on BBR (the vendor switches it to bic). Based on Juan's (LumiROM) fix.
- Built by `Najip@github`: shown in `/proc/version`, `uname -a` and About phone. The **uname tag** (default `-forkby-gh.Najip`) is added to `uname -r`.

Details: [Kernel details](docs/kernels.md).

## Sources used

This table is refreshed automatically each time a full Release is published (the one below is from the last xxKSU release until the first BakaSU Release).

<!-- SOURCES:START -->
Last release: [build-20261123-122](../../releases/tag/build-20261123-122)

| Part | Used by | Source | Branch / version | Commit | Commit date |
|---|---|---|---|---|---|
| Kernel | Main kernel: Aigis (BakaSU) | [SlamZDank/Aigis-Kernel-A32](https://github.com/SlamZDank/Aigis-Kernel-A32) | `bpf-5.15-legion`, Linux 4.14.357 | [`a4a77c638ab8`](https://github.com/SlamZDank/Aigis-Kernel-A32/commit/a4a77c638ab809bbe299a18858706afff8c3cadd) | 2026-11-23 |
| BakaSU (root) | Main kernel: Aigis (BakaSU) | [Baka-SU/BakaSU](https://github.com/Baka-SU/BakaSU) | `main`, KSU_VERSION 35285, tag v4.2.0-rc3 | [`57b2db6076f4`](https://github.com/Baka-SU/BakaSU/commit/57b2db6076f439cfd489f14576444e8f0f2f0a25) | 2026-11-24 |
| SUSFS patch | Main kernel: Aigis (BakaSU) | [JackA1ltman/NonGKI_Kernel_Build_2nd](https://github.com/JackA1ltman/NonGKI_Kernel_Build_2nd) | `mainline`, SUSFS v2.4.0, `Patches/Patch/susfs_patch_to_4.14.patch` | [`ec069a4e34f9`](https://github.com/JackA1ltman/NonGKI_Kernel_Build_2nd/commit/ec069a4e34f992d602a6b40d2e211df2516e2865) | 2026-11-18 |
| BakaSU manager app | Main kernel: Aigis (BakaSU) | [Baka-SU/BakaSU](https://github.com/Baka-SU/BakaSU) | Actions build [Build Manager #3786](https://github.com/Baka-SU/BakaSU/actions/runs/45221593387), `BakaSU_v4.2.0-rc3_35285-arm64-v8a-release.apk` | [`57b2db6076f4`](https://github.com/Baka-SU/BakaSU/commit/57b2db6076f439cfd489f14576444e8f0f2f0a25) | 2026-11-23 |
<!-- SOURCES:END -->

Other parts (pinned in this repo):

| Part | Source | Version |
|---|---|---|
| Toolchain | ZyC Clang 14.0.6 (as the Aigis CI builds it), or AOSP Clang prebuilt clang-r450784d with **Compiler** `main` | see `scripts/zyc_clang14.conf`, `scripts/aosp_clang14.conf` |
| Flasher | The Aigis tree's own `AnyKernel` folder (AnyKernel3) | from the kernel commit |
| NoMount LKM | [maxsteeel/nomount](https://github.com/maxsteeel/nomount) | `master` (default) or `dev`, chosen when you run the workflow |
| LKM loader | [maxsteeel/lkmloader](https://github.com/maxsteeel/lkmloader) | latest at build time |

Upstream repos and branches are set in `scripts/sources.conf`.

## Quick start

1. **Build**: on GitHub, open **Actions** > **Build Kernel** > **Run workflow**, keep the defaults and press **Run workflow**. Download the kernel ZIP from **Artifacts** when it is green. Or take a ready ZIP from [Releases](../../releases).
2. **Flash**: back up `boot`, flash the kernel ZIP in TWRP / OrangeFox (it also installs the matching NoMount module), reboot, and install the BakaSU manager app (`BakaSU_...apk`, on the release page). Recommended modules: BRENE for SUSFS (turn off BakaSU's built-in SUSFS settings when you use it) and HMA-OSS, which BRENE needs for hiding apps (SUSFS priority UID filter), see [Flashing](docs/flashing.md). Coming from xxKSU: see [Moving from xxKSU](docs/flashing.md#moving-from-xxksu).

## More docs

| Page | What it covers |
|---|---|
| [Kernel details](docs/kernels.md) | The Aigis kernel with BakaSU: GPU, compiler, hooks, version, manager |
| [Building](docs/building.md) | Every Build Kernel option, the artifacts, and building only the NoMount module |
| [Commit modes and releases](docs/commit-modes.md) | `Latest`, `Verified`, `Promoted`, pre-releases and full Releases |
| [Upstream check](docs/upstream-check.md) | The automatic check for new upstream commits, and which commits it ignores |
| [Flashing and logs](docs/flashing.md) | Flashing, moving from xxKSU, the NoMount check in the flasher, collecting phone logs and shortening build logs |
| [Repo layout](docs/repo-layout.md) | What each file and folder in this repo is |
| [Licenses](docs/licenses.md) | This repo's license and the license of every upstream part |

## Credits

- [SlamZDank/Aigis-Kernel-A32](https://github.com/SlamZDank/Aigis-Kernel-A32): the kernel tree (Aigis).
- [Baka-SU/BakaSU](https://github.com/Baka-SU/BakaSU): root (kernel part and manager app).
- [simonpunk/susfs4ksu](https://gitlab.com/simonpunk/susfs4ksu): SUSFS, and [JackA1ltman/NonGKI_Kernel_Build_2nd](https://github.com/JackA1ltman/NonGKI_Kernel_Build_2nd) for the non-GKI 4.14 port.
- [maxsteeel/nomount](https://github.com/maxsteeel/nomount) and [maxsteeel/lkmloader](https://github.com/maxsteeel/lkmloader): NoMount LKM.
- [osm0sis/AnyKernel3](https://github.com/osm0sis/AnyKernel3): flashable ZIP.
- Juan (LumiROM): the network fix (UDP GSO), the mzggr tuning (earlier builds), the BBR fix and the first JPEG fix.
- SlamZDank also for the `mtk_mm` memory heap in Aigis and for finding the real cause of the blank JPEGs.
- Earlier builds: [backslashxx/KernelSU](https://github.com/backslashxx/KernelSU) (xxKSU, archived 22 Nov 2026) and [mzggr0914/android_kernel_a325x_bakasu](https://github.com/mzggr0914/android_kernel_a325x_bakasu) (the Alt. kernel), see the `xxksu` branch.

## License

[GPL-2.0-only](LICENSE), the same license as the Linux kernel. You may fork, build, change and share this repo under the same license. Upstream parts keep their own licenses, see [Licenses](docs/licenses.md).
