# Upstream check

[Back to the README](../README.md)

The **Upstream check** workflow runs three times a day (07:00, 15:00 and 23:00 Jakarta time) and looks for new commits in:

- the Aigis kernel (`bpf-5.15-legion`) and the mzggr kernel (`common`)
- xxKSU (`master`)
- BakaSU (`sync-up`, or the branch set by **Switch BakaSU branch**). When everything in `sync-up` is already in BakaSU's `main`, the summary says so, so you can decide whether to switch
- Jack's SUSFS (`mainline`), only commits that changed the 4.14 patch the build uses
- NoMount (`master` only; the `dev` branch is not watched)

The newest commits it has seen are saved in `configs/upstream-state.json` on the default branch, with a short history of what changed. The first check only saves them, and so does the first check after a new source is added to the list. When a later check finds a new commit, it starts one **Build Kernel** run with Kernel `both`, Root flavor `All`, commit mode `Latest`, NoMount branch `master` and release type **Pre-release**, so every upstream update is published as a pre-release with all files (all three kernel ZIPs, their NoMount modules, both manager APKs). The new commits are listed in the run summary.

Only what changed is rebuilt. The rest is taken from an earlier automatic run and put in the same pre-release:

| New commit in | Aigis xxKSU | Aigis BakaSU | mzggr |
|---|---|---|---|
| SUSFS patch | built | built | built |
| xxKSU | built | kept | built |
| BakaSU | kept | built | kept |
| Aigis kernel | built | built | kept from the earlier run |
| mzggr kernel | kept from the earlier run | kept | built |
| NoMount only | kernel kept, NoMount module built (from the saved kernel kit, no kernel compile) | same | same |

If more than one source changed, the rules are joined (for example mzggr and NoMount: mzggr is built, and Aigis keeps its kernel ZIP and gets a new NoMount module). The check passes this to Build Kernel in its `reuse` box (leave it empty in manual runs). A kept kernel comes from the last automatic run, or from the run that last built it; if that run failed or its files have expired (30 days), the kernel is built instead. Each kept kernel's `build-info.txt` names the run its ZIP was taken from. The run summary of the check has a **File / Built in run** table that marks each file as a new build or reused. The started run is checked by its title; the check fails if it is not the planned one. A full Release still comes only from **Verified** commits.

Manual **Build Kernel** runs keep NoMount branch `dev` as the default. The build runs on the branch in the repo variable `UPSTREAM_BUILD_REF` (default: the default branch, `main`). Run the check by hand from the Actions tab to check now; untick **Build** to only check and save.

For the mzggr and Aigis kernels, a new commit only counts when it changes the kernel itself. Commits that only touch the tree's own root module (BakaSU by default, formerly named ReSukiSU, or KSUN or any other KernelSU fork, as a submodule or folder), NoMount, `.gitmodules`, `.github/` or docs (`docs/`, README, `*.md`) are ignored: they do not start a build, since the build replaces those with xxKSU and upstream NoMount anyway. They are still saved and listed under **Ignored commits** in the run summary. For NoMount, commits that only touch `.github/` or docs are ignored the same way. Any other file (sources, defconfig, build scripts, SUSFS) counts.
