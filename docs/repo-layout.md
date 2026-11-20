# Repo layout

[Back to the README](../README.md)

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
| `docs/` | These pages (the README sources table is the only part updated automatically) |
