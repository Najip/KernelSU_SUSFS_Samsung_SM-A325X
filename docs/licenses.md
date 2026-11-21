# Licenses

[Back to the README](../README.md)

## This repo

This repo is licensed under the [GNU General Public License v2.0 only](../LICENSE) (GPL-2.0-only), the same license as the Linux kernel.

You may fork it, build from it, change it and share it, as long as you keep it under GPL-2.0 and share the source of what you release.

### Why not an "ask me first" license

A license that lets people build but makes them ask before reusing the `.patch` files is not possible here:

- The patches change the Linux kernel (GPL-2.0-only), and many of them carry code from xxKSU, SUSFS and NoMount (all GPL-2.0 on the kernel side). A change to GPL-2.0 code must stay GPL-2.0 when it is shared, and GPL-2.0 does not allow extra conditions such as "ask first" (section 6).
- The releases publish kernels built from these patches, so their source (the patches and the build scripts) must be offered under GPL-2.0 to everyone who gets the kernel (section 3).
- No copyright license can stop someone from writing their own version of the same idea. Copyright covers the code itself, not the idea.

The repo was under GPL-3.0 before. GPL-3.0 does not fit kernel patches, because the Linux kernel is GPL-2.0 **only**, so it was changed to GPL-2.0-only.

What you can still ask for (a request, not a license condition): credit this repo when you reuse its work, and let the owner know.

## Upstream parts

| Part | Where it comes from | License | How this repo uses it | OK? |
|---|---|---|---|---|
| Main kernel: Aigis | [SlamZDank/Aigis-Kernel-A32](https://github.com/SlamZDank/Aigis-Kernel-A32) | GPL-2.0 (its `COPYING`) | Downloaded at build time, patched and built; the kernel is released | Yes, its source commit is linked in every release |
| Alt. kernel: mzggr | [mzggr0914/android_kernel_a325x_bakasu](https://github.com/mzggr0914/android_kernel_a325x_bakasu) | GPL-2.0 (its `COPYING`) | Same as above | Yes, its source commit is linked in every release |
| xxKSU (kernel part) | [backslashxx/KernelSU](https://github.com/backslashxx/KernelSU) `kernel/` | GPL-2.0 (`kernel/LICENSE`) | Built into the kernel | Yes |
| xxKSU manager app | [backslashxx/KernelSU releases](https://github.com/backslashxx/KernelSU/releases) | GPL-3.0 | The `.apk` is attached to releases unchanged | Yes, linked to its release and source |
| SUSFS | [simonpunk/susfs4ksu](https://gitlab.com/simonpunk/susfs4ksu), 4.14 port by [JackA1ltman/NonGKI_Kernel_Build_2nd](https://github.com/JackA1ltman/NonGKI_Kernel_Build_2nd) | The repos are GPL-3.0; the kernel files are kernel code under GPL-2.0 | The patch is downloaded at build time and built into the kernel | Yes |
| NoMount (kernel module) | [maxsteeel/nomount](https://github.com/maxsteeel/nomount) `kernel/` | GPL-2.0 (`kernel/LICENSE`) | Built as an LKM or into the kernel | Yes |
| NoMount (userspace) and LKM loader | [maxsteeel/nomount](https://github.com/maxsteeel/nomount), [maxsteeel/lkmloader](https://github.com/maxsteeel/lkmloader) | GPL-3.0 | Put in the NoMount module ZIP | Yes, separate programs in the same ZIP |
| AnyKernel3 | [osm0sis/AnyKernel3](https://github.com/osm0sis/AnyKernel3) | Its own BSD-style license; its tools keep their own licenses | The flasher in every kernel ZIP | Yes, its `LICENSE` file stays in the ZIP |
| BakaSU | [Baka-SU/BakaSU](https://github.com/Baka-SU/BakaSU) | GPL-3.0 | Removed at build time, not shipped | Not used |
| Valhall GPU drivers module | [Aigis release `GPU-Update`](https://github.com/SlamZDank/Aigis-Kernel-A32/releases/tag/GPU-Update) | No license given. It holds closed Mali GPU driver files from Samsung A14 vendor firmware | Bundled into the Aigis Valhall kernel ZIP | **Risk**: nobody gave a license to share these files (the Aigis release shares them the same way) |

## Source for each release

Every release lists the exact commits of each kernel, xxKSU, the SUSFS patch and this repo under **Source code (GPL-2.0)**, so anyone can rebuild the same kernel.
