# Building

[Back to the README](../README.md)

## Build Kernel

1. Open the repo on GitHub and go to the **Actions** tab.
2. Pick **Build Kernel** on the left, then press **Run workflow**.
3. Choose the options and press the green **Run workflow** button:
   - **Prefer my own PC (self-hosted)**: ticked by default. If the PC is already busy with another build (any branch or workflow), the run checks the average build times and uses a free GitHub runner when that would finish sooner than waiting. Untick to always use a GitHub runner.
   - **xxKSU hook style**: `manual` by default, then `syscall_table`, then `branch_link` (currently unstable). See [Hook styles](hook-styles.md).
   - **Kernel**: `aigis` by default, or `mzggr`, or `both` (see [The two kernels](../README.md#the-two-kernels)).
   - **Root flavor**: `xxKSU` by default, `BakaSU` (Aigis only) or `All` (see [Root flavors](../README.md#root-flavors)). The xxKSU hook style is ignored for BakaSU, which always uses its SUSFS inline hooks.
   - **Performance tuning**: ticked by default (mzggr only, ignored for Aigis). Allowed with every release type.
   - **Valhall GPU** and **Compiler**: Aigis only, ignored for mzggr.
   - **uname tag**: `-forkby-gh.Najip` by default, added to the end of `uname -r` on both kernels (for example `4.14.357-openela-vigus-slmkernel-a32-forkby-gh.Najip`). Letters, digits, space and `. _ + -` only (no `/`, the release name is also a folder name). Clear it for the kernel's own name. `bpfloader`, `netbpfload` and `netd` still see the fixed fake version, so networking is not affected. A NoMount module must be built with the same tag (the **NoMount LKM** workflow has the same box).
   - **Network fix**: ticked by default. Untick to build without the UDP GSO network fix. Allowed with every release type.
   - **Commit mode**: `Latest` by default. See [Commit modes](commit-modes.md).
   - **Release**: `CI` by default, so nothing is published. `Pre-release` publishes a pre-release, `Release` publishes a full release, and `Release from last pre-release` turns the newest pre-release into the full Release without building. Both attach the NoMount module built in the same run (see [Commit modes and releases](commit-modes.md)).
   - **NoMount**: `lkm` by default, a separate module (`NoMount-...-aigis-....zip` and `nomount-4.14-aigis.ko`, or `mzggr`) built for this exact kernel. `integrate` builds NoMount into the kernel itself (the kernel ZIP name gets `-nm`), and `no` leaves it out.
   - **NoMount branch**: `dev` by default, or `master`. Used for both `lkm` and `integrate`.
   - **NoMount only**: unticked by default. Tick it to build only the NoMount module, no kernel ZIP (see [NoMount without a kernel compile](building.md#nomount-without-a-kernel-compile)).
   - **Build hook benchmark**: unticked by default. Tick it only when you want the `hook-bench` tool; the kernel does not need it.
4. When the run is green, open it and download from **Artifacts**:
   - `A325X-Aigis-xxKSU-SUSFS-....zip` (main kernel) or `A325X-mzggr-xxKSU-SUSFS-....zip` (Alt. kernel): the flashable kernel ZIP (downloaded as-is, not a ZIP inside a ZIP).
   - `build-info.txt`: what was built (also inside the ZIP).
   - `NoMount-...-<kernel>-....zip` and `nomount-4.14-<kernel>.ko` (`<kernel>` = `aigis` or `mzggr`): with NoMount `lkm`. The ZIP is flashed as a module in the KernelSU manager.
   - The xxKSU manager APK of the latest [xxKSU release](https://github.com/backslashxx/KernelSU/releases/latest) under its own name, for example `KernelSU_v3.3.1+54_32735-release.apk` (the **List manager APK** job, every run). Releases attach the same `.apk` with the same name. `xxksu-manager-info` only says where it came from (used for the release notes).
   - With BakaSU: `A325X-Aigis-BakaSU-SUSFS-....zip`, `build-info-aigis-bakasu.txt`, `NoMount-...-aigis-bakasu-....zip`, and the BakaSU manager APK under its own name (for example `BakaSU_v4.2.0-rc3_35284-arm64-v8a-release.apk`, from the BakaSU Build Manager run of the same commit; `bakasu-manager-info` says which run).
   - `hook-bench`: the benchmark tool and its script, only when **Build hook benchmark** was ticked (see [Comparing them](hook-styles.md#comparing-them)).

No Actions secret is needed. The workflows use the built-in `GITHUB_TOKEN`.

## Switch BakaSU branch

Actions -> **Switch BakaSU branch** -> pick `sync-up` (default) or `main` -> **Run workflow**. It changes the BakaSU branch in `scripts/sources.conf` and commits it, so every later build and the upstream check use that branch. Run it again to switch back.

## Build log too long

`tools/extract_log.py` makes a short version of a failed build log. In the failed job, click the gear icon -> **View raw logs**, save the page (usually `job-logs.txt`), then double-click `extract_log.py` (needs Python 3) and pick the file. It saves `job-logs-important.txt` next to the script: the failing step, the first errors with the lines around them, every warning and error once, and the end of the log. Send that file.

## NoMount LKM workflow

1. Actions -> **NoMount LKM** -> **Run workflow**.
2. Pick the NoMount branch (`dev` is the default, or `master`), the **xxKSU hook style** and the **commit mode**. Keep the **Kernel** (`aigis-bakasu` for the BakaSU kernel), hook style, **Performance tuning** (mzggr), **Valhall GPU** and **Compiler** (Aigis) the same as the kernel you flashed. **Build on my own PC** is unticked by default here, so it runs on a free GitHub runner.
3. Download the `NoMount-....zip` artifact and flash it as a module in the KernelSU manager.

The module is compiled together with a kernel from the same sources in the same run, so it matches a kernel built from the same commits. If the sources have moved on since you built your kernel, rebuild both.

## NoMount without a kernel compile

A module only needs three files from the kernel it is built for: `.config`, `Module.symvers` (this kernel has `CONFIG_MODVERSIONS=y`, so the module must carry the symbol versions of the real kernel) and the kernel release string. Every full kernel build saves these as a `kernel-kit-...` artifact (kept 30 days). Module signing is off in this kernel, so nothing else is needed.

To build a module with a kit, the run downloads and patches the same sources, copies the kit's `.config`, runs `make modules_prepare` (a minute or two instead of a full compile), adds the kit's `Module.symvers` and builds only NoMount. It checks that the `.config` and the kernel release match the kit, and that the module's `vermagic` matches.

This is used by `Promoted` and by **NoMount only**. For **NoMount only**, the kit is looked up by the exact kernel: the same kernel, xxKSU and SUSFS commits, hook style, tuning, and the same build-repo patches, configs and build scripts. If no kit matches (for example a new upstream commit since the last full build), the kernel is compiled once in that run to match the module, and no kernel ZIP is made. **NoMount only** needs NoMount `lkm` and release type `CI`, and does not work with `Promoted`.
