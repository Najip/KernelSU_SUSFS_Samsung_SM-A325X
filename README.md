# KernelSU_SUSFS_Samsung_SM-A325X

Android kernel for Samsung Galaxy A32 4G (SM-A325x, codename `a32`, MediaTek MT6768) with xxKSU (a KernelSU fork by backslashxx for non-GKI kernels), SUSFS by simonpunk ported to non-GKI by JackA1ltman, and NoMount (as a separate LKM or built into the kernel). Target: SM-A325F on LumiROM 9 (Android 17).

It builds two kernels: the main kernel **Aigis** (used every day by the repo owner) and the Alt. kernel **mzggr**. Both are released.

This repo stores no kernel source. The GitHub Actions workflows download every source fresh, patch it and build a flashable ZIP.

## The two kernels

Every build can make two kernels. Both are released, so you can pick either one.

| | Main kernel: Aigis | Alt. kernel: mzggr |
|---|---|---|
| Who uses it | The repo owner, every day | Built and released too |
| Root in the upstream tree | [BakaSU](https://github.com/Baka-SU/BakaSU), replaced by xxKSU | [BakaSU](https://github.com/Baka-SU/BakaSU), replaced by xxKSU |
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

This table is refreshed automatically each time a full Release is published. xxKSU, the SUSFS patch and the manager app are the same for both kernels, so each has one row.

<!-- SOURCES:START -->
Last release: [build-20261120-79](../../releases/tag/build-20261120-79)

| Part | Used by | Source | Branch / version | Commit | Commit date |
|---|---|---|---|---|---|
| Kernel | Main kernel: Aigis | [SlamZDank/Aigis-Kernel-A32](https://github.com/SlamZDank/Aigis-Kernel-A32) | `bpf-5.15-legion`, Linux 4.14.357 | [`dc0935aba4a7`](https://github.com/SlamZDank/Aigis-Kernel-A32/commit/dc0935aba4a71c0cf3d7c7fd3c38c1e5e58c86c6) | 2026-11-19 |
| Kernel | Alt. kernel: mzggr | [mzggr0914/android_kernel_a325x_bakasu](https://github.com/mzggr0914/android_kernel_a325x_bakasu) | `common`, Linux 4.14.357-openela | [`7dd52de28d1e`](https://github.com/mzggr0914/android_kernel_a325x_bakasu/commit/7dd52de28d1ee64dddc1f3e853e214fab7578c44) | 2026-11-16 |
| xxKSU (root) | Both kernels | [backslashxx/KernelSU](https://github.com/backslashxx/KernelSU) | `master`, KSU_VERSION 32731, tag v3.3.1+54 | [`f27e1f0d3192`](https://github.com/backslashxx/KernelSU/commit/f27e1f0d3192820b0964881585d764ab0f0de56f) | 2026-11-20 |
| SUSFS patch | Both kernels | [JackA1ltman/NonGKI_Kernel_Build_2nd](https://github.com/JackA1ltman/NonGKI_Kernel_Build_2nd) | `mainline`, SUSFS v2.4.0, `Patches/Patch/susfs_patch_to_4.14.patch` | [`26f2313be61f`](https://github.com/JackA1ltman/NonGKI_Kernel_Build_2nd/commit/26f2313be61f7a8603a50b2dcd12171495a79d27) | 2026-11-18 |
| xxKSU manager app | Both kernels | [backslashxx/KernelSU](https://github.com/backslashxx/KernelSU) | release [v3.3.1+54](https://github.com/backslashxx/KernelSU/releases/tag/v3.3.1%2B54), `KernelSU_v3.3.1+54_32735-release.apk` | - | 2026-11-20 |
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

- xxKSU for root, replacing the tree's own root module at build time. Both upstream kernels ship [BakaSU](https://github.com/Baka-SU/BakaSU) by default, as the `KernelSU` submodule (Aigis' `.gitmodules` still uses BakaSU's old name, ReSukiSU, which now leads to the same repo).
- xxKSU hook style, chosen when you run the workflow (see [Hook styles](docs/hook-styles.md)). The default is `manual` (`branch_link` is currently unstable). No LSM hooking in any style.
- SUSFS v2.4.0: the core files (`fs/susfs.c`, `susfs.h`, `susfs_def.h`) come from JackA1ltman's patch. All features on: sus path, sus mount, sus kstat, spoof uname, spoof cmdline, open redirect, sus map, priority UID filter, hide symbols, logging.
- Upstream NoMount, replacing the tree's own NoMount: a separate LKM by default, or built in with the `integrate` option.
- Network fix (UDP-only GSO for IPv4 and IPv6). A tick, ticked by default, allowed with every release type (and with `Promoted`, which keeps the setting of the build it takes).
- No LTO.
- Built by `Najip@github`: shown in `/proc/version`, `uname -a` and About phone. The **uname tag** (default `-forkby-gh.Najip`) is added to `uname -r`.

Kernel-specific details: [Kernel details](docs/kernels.md).

## Quick start

1. **Build**: on GitHub, open **Actions** > **Build Kernel** > **Run workflow**, keep the defaults and press **Run workflow**. Download the kernel ZIP from **Artifacts** when it is green. Or take a ready ZIP from [Releases](../../releases).
2. **Flash**: back up `boot`, flash the kernel ZIP in TWRP / OrangeFox, reboot, and install the xxKSU manager app (the `.apk` on the release page). With NoMount `lkm`, flash the NoMount ZIP made for the same kernel as a module in the manager.

## More docs

| Page | What it covers |
|---|---|
| [Kernel details](docs/kernels.md) | What is special about the main kernel (Aigis) and the Alt. kernel (mzggr) |
| [Building](docs/building.md) | Every Build Kernel option, the artifacts, and building only the NoMount module |
| [Hook styles](docs/hook-styles.md) | `manual`, `syscall_table`, `branch_link`, what fails with which, and the benchmark |
| [Commit modes and releases](docs/commit-modes.md) | `Latest`, `Verified`, `Promoted`, pre-releases and full Releases |
| [Upstream check](docs/upstream-check.md) | The automatic check for new upstream commits, and which commits it ignores |
| [Flashing and logs](docs/flashing.md) | Flashing, the NoMount and GPU checks in the flasher, and collecting logs |
| [Repo layout](docs/repo-layout.md) | What each file and folder in this repo is |
| [Licenses](docs/licenses.md) | This repo's license and the license of every upstream part |

## Credits

- [SlamZDank/Aigis-Kernel-A32](https://github.com/SlamZDank/Aigis-Kernel-A32): the main kernel tree (Aigis).
- [mzggr0914/android_kernel_a325x_bakasu](https://github.com/mzggr0914/android_kernel_a325x_bakasu): the Alt. kernel tree (A32 4G BakaSU kernel with 4.14 SUSFS hooks).
- [Samsung-MT6769-Devs/android_kernel_samsung_mt6768](https://github.com/Samsung-MT6769-Devs/android_kernel_samsung_mt6768): the SLM MT6768 kernel source the mzggr tree is based on.
- [backslashxx/KernelSU](https://github.com/backslashxx/KernelSU): xxKSU.
- [Baka-SU/BakaSU](https://github.com/Baka-SU/BakaSU): the root module both upstream trees ship (replaced by xxKSU here).
- [simonpunk/susfs4ksu](https://gitlab.com/simonpunk/susfs4ksu): SUSFS, and [JackA1ltman/NonGKI_Kernel_Build_2nd](https://github.com/JackA1ltman/NonGKI_Kernel_Build_2nd) for the non-GKI 4.14 port.
- [maxsteeel/nomount](https://github.com/maxsteeel/nomount) and [maxsteeel/lkmloader](https://github.com/maxsteeel/lkmloader): NoMount LKM.
- [osm0sis/AnyKernel3](https://github.com/osm0sis/AnyKernel3): flashable ZIP.
- [Najip/android_kernel_a325F_bakasu](https://github.com/Najip/android_kernel_a325F_bakasu/tree/xxksu): the xxKSU + SUSFS conversion this repo reproduces.

## License

[GPL-2.0-only](LICENSE), the same license as the Linux kernel. You may fork, build, change and share this repo under the same license. Upstream parts keep their own licenses, see [Licenses](docs/licenses.md).
