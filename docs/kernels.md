# Kernel details

[Back to the README](../README.md)

One kernel is built: Aigis with BakaSU. xxKSU was archived by its developer on 22 Nov 2026 (as of 23 Nov 2026), so the xxKSU kernels and the Alt. kernel (mzggr, xxKSU only, no longer developed) stopped. They are kept, frozen, in the [`xxksu` branch](../../../tree/xxksu).

## Aigis kernel

- The [Aigis kernel by SlamZDank](https://github.com/SlamZDank/Aigis-Kernel-A32) from its default branch `bpf-5.15-legion` (BPF backports and the Android 15+ `netbpfload` workaround), with the SUSFS hooks of its `bpf-5.15-legion-susfs` branch.
- Aigis keeps its own CPU/GPU tuning.
- **Valhall GPU** (ticked by default, allowed with every release type): ticked = the Aigis Valhall r32p1 setup with their GPU tuning. There is one ZIP, which writes the r32p1 dtb and also installs their [Valhall drivers module](https://github.com/SlamZDank/Aigis-Kernel-A32/releases/download/GPU-Update/A32-Mali-Valhall-Drivers-KSU-Module.zip) (no kernel-only ZIP). ZIP names get `-vgpu`. Unticked = stock A32 GPU (`patches/base/0002-aigis-stock-gpu.patch`).
- **Compiler**: `aigis` (default) = ZyC Clang 14.0.6 the way the Aigis CI builds it; `main` = AOSP Clang 14 (ZIP names get `-aospclang`).
- Config: `a32_slamzdank_defconfig` + `bakasu-aigis.config` (the Aigis BakaSU setup) + the GPU fragment, then checked against `configs/a325x-bakasu-susfs.config`.

## BakaSU

- BakaSU branch: `main` by default, set in the **BakaSU branch** box of Build Kernel (any branch of Baka-SU/BakaSU; the run stops if it does not exist). The upstream check always watches `main`.
- Hook style: SUSFS inline hooks, always. BakaSU has three styles: tracepoint (GKI 2 kernels only, not this phone), manual, and SUSFS inline. With SUSFS, BakaSU only allows the inline style: the hooks are calls compiled into the kernel, no run-time patching, and it is the fastest one. The build fails if BakaSU's own check reports a missing or wrong hook.
- The base patch `patches/base/0001-aigis-legion-to-bakasu-susfs.patch` puts the 4.14 SUSFS inline hooks into the Aigis tree in the places BakaSU expects. `patches/bakasu/0001-bakasu-auto-selinux-hide.patch` takes out the kernel's own SELinux hide hooks, since BakaSU (from 16 Nov 2026) hooks those places itself on 4.14. BakaSU itself is not patched (its build refuses a changed copy).
- Version: BakaSU counts it from its git history (for example version code 35284, `v4.2.0-rc3-a049dee8`), so the manager shows the kernel as matching.
- Manager app: taken from the BakaSU **Build Manager** run made from the same BakaSU commit (the `arm64-v8a` APK, under its original name). If that commit has no manager build (BakaSU only builds the manager when the app or kernel code changes), the newest earlier one is used and the run shows a warning.
- NoMount: the module `NoMount-...-aigis-bakasu-...zip` is built for this kernel and also travels inside the kernel ZIP. Modules built for the old xxKSU kernels do not fit; the flasher replaces them.
