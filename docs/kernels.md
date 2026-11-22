# Kernel details

[Back to the README](../README.md)

What is special about each kernel. What they share is listed in the README under [What both kernels get](../README.md#what-both-kernels-get).

## Main kernel: Aigis

- The [Aigis kernel by SlamZDank](https://github.com/SlamZDank/Aigis-Kernel-A32) from its default branch `bpf-5.15-legion`, with the SUSFS hooks of its `bpf-5.15-legion-susfs` branch.
- Aigis keeps its own CPU/GPU tuning. Our **Performance tuning** does not fit its tree, so for Aigis it is ignored with a warning (with `both`, only the mzggr ZIP gets the tuning).
- **Valhall GPU** (Aigis only, ticked by default, allowed with every release type): ticked = the Aigis Valhall r32p1 setup with their GPU tuning. There is one ZIP, which writes the r32p1 dtb and also installs their [Valhall drivers module](https://github.com/SlamZDank/Aigis-Kernel-A32/releases/download/GPU-Update/A32-Mali-Valhall-Drivers-KSU-Module.zip) (no kernel-only ZIP). ZIP names get `-vgpu`. Unticked = stock A32 GPU (`patches/base/0002-aigis-stock-gpu.patch`).
- **Compiler** (Aigis only): `aigis` (default) = ZyC Clang 14.0.6 the way the Aigis CI builds it; `main` = AOSP Clang 14 as for mzggr (ZIP names get `-aospclang`).

## Alt. kernel: mzggr

- mzggr0914's SLM-based Linux 4.14.357-openela tree (`4.14.357-openela-vigus-slmkernel-a32`). It carries the BPF backports and the fake `5.10` version for `netbpfload`, so newer ROMs such as LumiROM 9 (Android 17) boot.
- The tree's BakaSU and in-tree NoMount are swapped the same way as the booting [Najip/android_kernel_a325F_bakasu `xxksu`](https://github.com/Najip/android_kernel_a325F_bakasu/tree/xxksu) branch, stored here as `patches/base/0001-mzggr-common-to-xxksu-susfs.patch`. The SUSFS hooks in the rest of the kernel are the 4.14 ones already in mzggr0914's tree.
- Config as the tree ships it: `mt6768_slm_defconfig` + `a32.config` + `battery.config` (CPU undervolt, conservative governor, 100 Hz) + `ksu-a325n-common.config` + `a325n-release.config`.
- Performance tuning (ticked by default, mzggr only), taken from [Najip/android_kernel_a325F_bakasu](https://github.com/Najip/android_kernel_a325F_bakasu): GPU 1100 MHz @ 1.035 V, CCI overclock, CPU/CCI undervolt, DDR DVFS tweaks, BORE scheduler, 250 Hz, schedutil governor, fast charging with the screen on, zram default `zstd`, GPU frequency meter at `/sys/kernel/gpu/gpu_fmeter`, USB autosuspend off, BBR TCP and fq_codel. The undervolt was tuned on one phone; if yours freezes or reboots under load, build without tuning.
- Toolchain: AOSP Clang 14 with ld.lld and GNU as.

## Aigis with BakaSU

Built with **Root flavor** `BakaSU` or `All`. It is the same Aigis kernel (same tree, Valhall GPU and Compiler options, same SUSFS v2.4.0 from Jack's 4.14 patch), with [BakaSU](https://github.com/Baka-SU/BakaSU) for root instead of xxKSU.

- BakaSU branch: `main` by default, set in the **BakaSU branch** box of Build Kernel (any branch of Baka-SU/BakaSU; the run stops if it does not exist). The upstream check always watches `main`.
- Hook style: SUSFS inline hooks, always. BakaSU has three styles: tracepoint (GKI 2 kernels only, not this phone), manual, and SUSFS inline. With SUSFS, BakaSU only allows the inline style, which is the same idea as xxKSU's `manual` (the hooks are calls compiled into the kernel, no run-time patching) and the fastest one. The **xxKSU hook style** box is ignored for this kernel; `syscall_table` and `branch_link` exist only in xxKSU. The build fails if BakaSU's own check reports a missing or wrong hook.
- The base patch `patches/base/0001-aigis-legion-to-bakasu-susfs.patch` puts the 4.14 SUSFS inline hooks into the Aigis tree in the places BakaSU expects. BakaSU itself is not patched (its build refuses a changed copy).
- Version: BakaSU counts it from its git history (for example version code 35284, `v4.2.0-rc3-a049dee8`), so the manager shows the kernel as matching.
- Manager app: taken from the BakaSU **Build Manager** run made from the same BakaSU commit (the `arm64-v8a` APK, under its original name). If that commit has no manager build (BakaSU only builds the manager when the app or kernel code changes), the newest earlier one is used and the run shows a warning.
- NoMount: its own module, `NoMount-...-aigis-bakasu-...zip`, built for this kernel. The xxKSU Aigis NoMount module does not fit it, and the flasher warns if the wrong one is installed.
- Config: `a32_slamzdank_defconfig` + `bakasu-aigis.config` (the Aigis BakaSU setup) + the Valhall fragment, then checked against `configs/a325x-bakasu-susfs.config`.
