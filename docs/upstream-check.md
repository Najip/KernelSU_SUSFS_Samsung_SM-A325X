# Upstream check

[Back to the README](../README.md)

The **Upstream check** workflow runs three times a day (07:00, 15:00 and 23:00 Jakarta time) and looks for new commits in:

- the Aigis kernel (`bpf-5.15-legion`)
- BakaSU (`main`)
- Jack's SUSFS (`mainline`), only commits that changed the 4.14 patch the build uses
- NoMount (`master` only; the `dev` branch is not watched)

xxKSU and the mzggr kernel are no longer watched: xxKSU was archived by its developer on 22 Nov 2026 (as of 23 Nov 2026), and mzggr was xxKSU-only and is not developed anymore.

The newest commits it has seen are saved in `configs/upstream-state.json` on the default branch, with a short history of what changed. The first check only saves them, and so does the first check after a new source is added to the list. When a later check finds a new commit, it starts one **Build Kernel** run with commit mode `Latest`, NoMount branch `master` and release type **Pre-release**, so every upstream update is published as a pre-release with all files (kernel ZIP, NoMount module, BakaSU manager APK). The new commits are listed in the run summary.

What gets built:

| New commit in | Result |
|---|---|
| Aigis kernel, BakaSU or SUSFS patch | kernel and NoMount module built |
| NoMount only | kernel ZIP kept from the earlier automatic run, NoMount module built from the saved kernel kit (no kernel compile) |

The check passes this to Build Kernel in its `reuse` box. In manual runs leave it empty for a normal build, or paste a run link (or just its number) to keep that run's kernel ZIP and build only a new NoMount module; `all <run link>` keeps all its files. It needs commit mode `Latest`, NoMount `lkm`, and release type `CI` or `Pre-release`. A kept kernel comes from the last automatic run, or from the run that last built it; if that run failed or its files have expired (30 days), the kernel is built instead. Each kept kernel's `build-info.txt` names the run its ZIP was taken from. The run summary of the check has a **File / Built in run** table that marks each file as a new build or reused. The started run is checked by its title; the check fails if it is not the planned one. A full Release still comes only from **Verified** commits.

Manual **Build Kernel** runs use NoMount branch `master` by default. The build runs on the branch in the repo variable `UPSTREAM_BUILD_REF` (default: the default branch, `main`). Run the check by hand from the Actions tab to check now; untick **Build** to only check and save.

For the Aigis kernel, a new commit only counts when it changes the kernel itself. Commits that only touch the tree's own root module (BakaSU, formerly named ReSukiSU, or KSUN or any other KernelSU fork, as a submodule or folder), NoMount, `.gitmodules`, `.github/` or docs (`docs/`, README, `*.md`) are ignored: they do not start a build, since the build uses its own BakaSU and upstream NoMount anyway. They are still saved and listed under **Ignored commits** in the run summary. For NoMount, commits that only touch `.github/` or docs are ignored the same way. Any other file (sources, defconfig, build scripts, SUSFS) counts.
