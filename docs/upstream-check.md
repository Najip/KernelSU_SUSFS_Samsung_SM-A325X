# Upstream check

[Back to the README](../README.md)

The **Upstream check** workflow runs three times a day (07:00, 15:00 and 23:00 Jakarta time) and looks for new commits in:

- the Aigis kernel (`bpf-5.15-legion`)
- BakaSU (`main`)
- xxKSU ([Najip/xxKSU](https://github.com/Najip/xxKSU) `sync-mojito`, which follows backslashxx's mojito updates). New xxKSU releases also start a pre-release build right away from Najip/xxKSU itself (secret `KERNEL_DISPATCH_TOKEN`), so this check is the backup.
- Jack's SUSFS (`mainline`), only commits that changed the 4.14 patch the build uses
- NoMount (`master` only; the `dev` branch is not watched)


The newest commits it has seen are saved in `configs/upstream-state.json` on the default branch, with a short history of what changed. The first check only saves them, and so does the first check after a new source is added to the list. When a later check finds a new commit, it starts one **Build Kernel** run with commit mode `Latest`, NoMount branch `master` and release type **Pre-release**, so every upstream update is published as a pre-release with all files (kernel ZIPs, NoMount modules, BakaSU and xxKSU manager APKs). The new commits are listed in the run summary.

What gets built:

| New commit in | Result |
|---|---|
| Aigis kernel, BakaSU, xxKSU or SUSFS patch | kernel and NoMount module built (for the flavor that changed, both for the kernel and SUSFS) |
| NoMount only | kernel ZIP kept from the earlier automatic run, NoMount module built from the saved kernel kit (no kernel compile) |

The check passes this to Build Kernel in its `reuse` box. In manual runs leave it empty for a normal build, or paste a run link (or just its number) to keep that run's kernel ZIP. Its NoMount module is kept too when it has one from the chosen **NoMount branch**; otherwise a new one is built from its kernel kit. `nomount <run link>` always builds a new NoMount module. It needs commit mode `Latest` and NoMount `lkm`; release type `CI`, `Pre-release` or `Release` (a full Release of that tested run, Verified not needed). A kept kernel comes from the last automatic run, or from the run that last built it; if that run failed or its files have expired (30 days), the kernel is built instead. Each kept kernel's `build-info.txt` names the run its ZIP was taken from. The run summary of the check has a **File / Built in run** table that marks each file as a new build or reused. The started run is checked by its title; the check fails if it is not the planned one.

Manual **Build Kernel** runs use NoMount branch `master` by default. The build runs on the branch in the repo variable `UPSTREAM_BUILD_REF` (default: the default branch, `main`). Run the check by hand from the Actions tab to check now; untick **Build** to only check and save.

For the Aigis kernel, a new commit only counts when it changes the kernel itself. Commits that only touch the tree's own root module (BakaSU, formerly named ReSukiSU, or KSUN or any other KernelSU fork, as a submodule or folder), NoMount, `.gitmodules`, `.github/` or docs (`docs/`, README, `*.md`) are ignored: they do not start a build, since the build uses its own BakaSU and upstream NoMount anyway. They are still saved and listed under **Ignored commits** in the run summary. For NoMount, commits that only touch `.github/` or docs are ignored the same way. Any other file (sources, defconfig, build scripts, SUSFS) counts.
