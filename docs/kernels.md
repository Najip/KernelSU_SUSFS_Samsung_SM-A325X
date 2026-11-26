# Kernel details

[Back to the README](../README.md)

One kernel, Aigis, is built in two root flavors: **BakaSU** and **xxKSU**. The **Root flavor** option of Build Kernel picks one or both (default: both); a full Release always has both. Each flavor gets its own kernel ZIP, NoMount module and manager app.

## Aigis kernel

- The [Aigis kernel by SlamZDank](https://github.com/SlamZDank/Aigis-Kernel-A32) from its default branch `bpf-5.15-legion` (BPF backports and the Android 15+ `netbpfload` workaround), with the SUSFS hooks of its `bpf-5.15-legion-susfs` branch.
- Aigis keeps its own CPU/GPU tuning.
- **Valhall GPU** (ticked by default, allowed with every release type): ticked = the Aigis Valhall r32p1 setup with their GPU tuning. There is one ZIP, which writes the r32p1 dtb and also installs their [Valhall drivers module](https://github.com/SlamZDank/Aigis-Kernel-A32/releases/download/GPU-Update/A32-Mali-Valhall-Drivers-KSU-Module.zip) (no kernel-only ZIP). ZIP names get `-vgpu`. Unticked = stock A32 GPU (`patches/base/0002-aigis-stock-gpu.patch`).
- **Compiler**: `aigis` (default) = ZyC Clang 14.0.6 the way the Aigis CI builds it; `main` = AOSP Clang 14 (ZIP names get `-aospclang`).
- Config: `a32_slamzdank_defconfig` + `bakasu-aigis.config` (the Aigis BakaSU setup) + the GPU fragment, then checked against `configs/a325x-bakasu-susfs.config` (BakaSU) or `configs/a325x-xxksu-susfs.config` (xxKSU).

## BakaSU

- BakaSU branch: `main` by default, set in the **BakaSU branch** box of Build Kernel (any branch of Baka-SU/BakaSU; the run stops if it does not exist). The upstream check always watches `main`.
- Hook style: SUSFS inline hooks, always. BakaSU has three styles: tracepoint (GKI 2 kernels only, not this phone), manual, and SUSFS inline. With SUSFS, BakaSU only allows the inline style: the hooks are calls compiled into the kernel, no run-time patching, and it is the fastest one. The build fails if BakaSU's own check reports a missing or wrong hook.
- The base patch `patches/base/0001-aigis-legion-to-bakasu-susfs.patch` puts the 4.14 SUSFS inline hooks into the Aigis tree in the places BakaSU expects. `patches/bakasu/0001-bakasu-auto-selinux-hide.patch` takes out the kernel's own SELinux hide hooks, since BakaSU (from 16 Nov 2026) hooks those places itself on 4.14. BakaSU itself is not patched (its build refuses a changed copy).
- Version: BakaSU counts it from its git history (for example version code 35284, `v4.2.0-rc3-a049dee8`), so the manager shows the kernel as matching.
- Manager app: taken from the BakaSU **Build Manager** run made from the same BakaSU commit (the `arm64-v8a` APK, under its original name). If that commit has no manager build (BakaSU only builds the manager when the app or kernel code changes), the newest earlier one is used and the run shows a warning.
- NoMount: the module `NoMount-...-aigis-bakasu-...zip` is built for this kernel and also travels inside the kernel ZIP. Modules built for other kernels do not fit; the flasher replaces them.

## xxKSU

- Source: [Najip/xxKSU](https://github.com/Najip/xxKSU), branch `sync-mojito` (set in `scripts/sources.conf`, kernel `aigis-xxksu`). That branch follows backslashxx's kernel-side xxKSU updates from the [ximi-mojito kernel tree (`personal` branch)](https://github.com/ximi-mojito/android_kernel_xiaomi_mojito/tree/personal) every day, and switches back to `backslashxx/KernelSU` if that repo comes back. backslashxx's last commit from his own repo is kept untouched on the `final` branch.
- Hook style: manual hooks, next to the SUSFS hooks. The base patch `patches/base/0001-aigis-legion-to-xxksu-susfs.patch` puts them into the Aigis tree; `patches/kernelsu/0001-native-wrappers.patch` and `0002-susfs-lifecycle-calls.patch` are applied to xxKSU itself.
- Manager app: the `KernelSU_...apk` of the newest [Najip/xxKSU release](https://github.com/Najip/xxKSU/releases), built from the same `sync-mojito` code.
- Updates: each new Najip/xxKSU release starts a pre-release build of this kernel (both flavors) through the `KERNEL_DISPATCH_TOKEN` secret; the upstream check also watches `sync-mojito`.
- NoMount: the module `NoMount-...-aigis-xxksu-...zip` is built for the xxKSU kernel and travels inside its ZIP.
- Why it is here again: the kernel started with xxKSU, moved to BakaSU only on 2026-11-23 and dropped xxKSU when `backslashxx/KernelSU` was taken down. Since backslashxx kept working on it in the mojito tree, it was added back on 2026-11-26. See the README.
