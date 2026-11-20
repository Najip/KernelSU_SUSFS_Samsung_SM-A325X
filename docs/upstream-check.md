# Upstream check

[Back to the README](../README.md)

The **Upstream check** workflow runs three times a day (07:00, 15:00 and 23:00 Jakarta time) and looks for new commits in:

- the mzggr kernel (`common`) and the Aigis kernel (`bpf-5.15-legion`)
- xxKSU (`master`)
- Jack's SUSFS (`mainline`), only commits that changed the 4.14 patch the build uses

NoMount is not watched. The newest commits it has seen are saved in `configs/upstream-state.json` on the default branch, with a short history of what changed. The first check only saves them. When a later check finds a new commit, it starts **Build Kernel** with Kernel `both` (always both kernels, main Aigis and Alt. kernel mzggr, whatever the Kernel dropdown default is; the check fails if the started build is not `both`), commit mode `Latest` and release type `CI` (never a release), and lists the new commits in the run summary. The build runs on the branch in the repo variable `UPSTREAM_BUILD_REF` (default: the default branch, `main`). Run it by hand from the Actions tab to check now; untick **Build** to only check and save.

For the mzggr and Aigis kernels, a new commit only counts when it changes the kernel itself. Commits that only touch the tree's own root module (BakaSU by default, formerly named ReSukiSU, or KSUN or any other KernelSU fork, as a submodule or folder), NoMount, `.gitmodules`, `.github/` or docs (`docs/`, README, `*.md`) are ignored: they do not start a build, since the build replaces those with xxKSU and upstream NoMount anyway. They are still saved and listed under **Ignored kernel commits** in the run summary. Any other file (sources, defconfig, build scripts, SUSFS) counts.
