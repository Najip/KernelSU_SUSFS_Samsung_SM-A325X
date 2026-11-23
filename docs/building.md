# Building

[Back to the README](../README.md)

## Build Kernel

1. Open the repo on GitHub and go to the **Actions** tab.
2. Pick **Build Kernel** on the left, then press **Run workflow**.
3. Choose the options and press the green **Run workflow** button:
   - **Prefer my own PC (self-hosted)**: ticked by default. If the PC is already busy with another build (any branch or workflow), the run checks the average build times and uses a free GitHub runner when that would finish sooner than waiting. Untick to always use a GitHub runner.
   - **BakaSU branch**: `main` by default. The run stops if Baka-SU/BakaSU has no such branch.
   - **Valhall GPU** and **Compiler**: see [Kernel details](kernels.md).
   - **uname tag**: `-forkby-gh.Najip` by default, added to the end of `uname -r`. Letters, digits, space and `. _ + -` only (no `/`, the release name is also a folder name). Clear it for the kernel's own name. `bpfloader`, `netbpfload` and `netd` still see the fixed fake version, so networking is not affected. A NoMount module must be built with the same tag.
   - **Network fix**: ticked by default. Untick to build without the UDP GSO network fix. Allowed with every release type.
   - **Commit mode**: `Latest` by default. See [Commit modes](commit-modes.md).
   - **Release**: `CI` by default, so nothing is published. `Pre-release` publishes a pre-release, `Release` publishes a full release, and `Release from last pre-release` turns the newest pre-release into the full Release without building. Both attach the NoMount module built in the same run (see [Commit modes and releases](commit-modes.md)).
   - **NoMount**: `lkm` by default: the module built for this exact kernel goes inside the kernel ZIP (folder `nomount/`, installed by TWRP) and is also kept as a separate module (`NoMount-...-aigis-bakasu-....zip` and `nomount-4.14-aigis-bakasu.ko`). `integrate` builds NoMount into the kernel itself (the kernel ZIP name gets `-nm`). There is no kernel-only choice.
   - **NoMount branch**: `master` by default, or `dev`. Used for both `lkm` and `integrate`.
   - **NoMount only**: unticked by default. Tick it to build only the NoMount module, no kernel ZIP (see [NoMount without a kernel compile](building.md#nomount-without-a-kernel-compile)).
4. When the run is green, open it and download from **Artifacts**:
   - `A325X-Aigis-BakaSU-SUSFS-....zip`: the flashable kernel ZIP (downloaded as-is, not a ZIP inside a ZIP). It carries the NoMount module.
   - `build-info-aigis-bakasu.txt`: what was built (also inside the ZIP).
   - `NoMount-...-aigis-bakasu-....zip` and `nomount-4.14-aigis-bakasu.ko`: the same NoMount module as separate files, with NoMount `lkm`. The ZIP can be flashed as a module in the BakaSU manager.
   - The BakaSU manager APK under its own name, for example `BakaSU_v4.2.0-rc3_35284-arm64-v8a-release.apk`, from the BakaSU Build Manager run of the same commit (the **List manager APK** job). `bakasu-manager-info` says which run. Releases attach the same `.apk`.

No Actions secret is needed. The workflows use the built-in `GITHUB_TOKEN`.

## Build log too long

`tools/extract_log.py` makes a short version of a failed build log. In the failed job, click the gear icon -> **View raw logs**, save the page (usually `job-logs.txt`), then double-click `extract_log.py` (needs Python 3) and pick the file. It saves `job-logs-important.txt` next to the script: the failing step, the first errors with the lines around them, every warning and error once, and the end of the log. Send that file.

## NoMount without a kernel compile

A module only needs three files from the kernel it is built for: `.config`, `Module.symvers` (this kernel has `CONFIG_MODVERSIONS=y`, so the module must carry the symbol versions of the real kernel) and the kernel release string. Every full kernel build saves these as a `kernel-kit-...` artifact (kept 30 days). Module signing is off in this kernel, so nothing else is needed.

To build a module with a kit, the run downloads and patches the same sources, copies the kit's `.config`, runs `make modules_prepare` (a minute or two instead of a full compile), adds the kit's `Module.symvers` and builds only NoMount. It checks that the `.config` and the kernel release match the kit, and that the module's `vermagic` matches.

This is used by `Promoted`, by the upstream check (NoMount changed) and by **NoMount only** (it replaced the old separate NoMount LKM workflow). For **NoMount only**, the kit is looked up by the exact kernel: the same kernel, BakaSU and SUSFS commits, and the same build-repo patches, configs and build scripts. If no kit matches (for example a new upstream commit since the last full build), the kernel is compiled once in that run to match the module, and no kernel ZIP is made. **NoMount only** needs NoMount `lkm` and release type `CI`, and does not work with `Promoted`.
