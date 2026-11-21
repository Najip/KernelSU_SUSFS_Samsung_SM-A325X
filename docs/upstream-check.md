# Upstream check

[Back to the README](../README.md)

The **Upstream check** workflow runs three times a day (07:00, 15:00 and 23:00 Jakarta time) and looks for new commits in:

- the Aigis kernel (`bpf-5.15-legion`) and the mzggr kernel (`common`)
- xxKSU (`master`)
- Jack's SUSFS (`mainline`), only commits that changed the 4.14 patch the build uses
- NoMount (`master` only; the `dev` branch is not watched)

The newest commits it has seen are saved in `configs/upstream-state.json` on the default branch, with a short history of what changed. The first check only saves them, and so does the first check after a new source is added to the list. When a later check finds a new commit, it starts **Build Kernel** with commit mode `Latest`, release type `CI` (never a release) and NoMount branch `master`, and lists the new commits in the run summary.

Only what changed is rebuilt:

| New commit in | What is built | Files rebuilt |
|---|---|---|
| xxKSU or SUSFS patch | Kernel `both` (Aigis first, then mzggr) | all kernel ZIPs and both NoMount modules |
| Aigis kernel | Kernel `aigis` | Aigis ZIPs and the Aigis NoMount module |
| mzggr kernel | Kernel `mzggr` | mzggr ZIP and the mzggr NoMount module |
| NoMount only | **NoMount only**, for the kernels not already rebuilt | the NoMount module(s) |

If more than one source changed, the plans are joined (for example mzggr and NoMount: a full mzggr build plus a NoMount-only build for Aigis). Each started run is checked against its plan by its title; the check fails if it does not match. Files with no update are not rebuilt: the state file keeps, for each file, the run that last built it, and the run summary has a **File / From run** table that links the new runs and marks the others as reused from their older run. These are CI builds (no release); a Release still comes only from **Verified** commits.

Manual **Build Kernel** runs keep NoMount branch `dev` as the default. The build runs on the branch in the repo variable `UPSTREAM_BUILD_REF` (default: the default branch, `main`). Run the check by hand from the Actions tab to check now; untick **Build** to only check and save.

For the mzggr and Aigis kernels, a new commit only counts when it changes the kernel itself. Commits that only touch the tree's own root module (BakaSU by default, formerly named ReSukiSU, or KSUN or any other KernelSU fork, as a submodule or folder), NoMount, `.gitmodules`, `.github/` or docs (`docs/`, README, `*.md`) are ignored: they do not start a build, since the build replaces those with xxKSU and upstream NoMount anyway. They are still saved and listed under **Ignored commits** in the run summary. For NoMount, commits that only touch `.github/` or docs are ignored the same way. Any other file (sources, defconfig, build scripts, SUSFS) counts.
