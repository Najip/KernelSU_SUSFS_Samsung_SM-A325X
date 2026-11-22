# Commit modes and releases

[Back to the README](../README.md)

Every build picks the commits of the kernel, xxKSU and the SUSFS patch in one of three ways. The pins are saved in `configs/verified.json`.

| Mode | What it builds | When to use it |
|---|---|---|
| `Latest` (default) | The newest commit of each source. | Trying out new upstream changes. |
| `Verified` | The pinned commits saved by the last successful `Promoted` build. | Rebuilding something you already tested. A full `Release` only works in this mode. |
| `Promoted` | Nothing new is compiled for the kernel. It takes the files of the most recent successful `Latest` run with the default kernel options (on the same branch) and saves that run's commits as the new `Verified` pins. | After you have flashed and tested the newest default `Latest` build and want to mark it as good. |

Tuning is allowed in every release type, and `Promoted` takes builds with or without tuning.

`Verified` keeps separate pins for each kernel. The Aigis pins come from a `Promoted` run with Kernel `aigis` or `both`; before that, `Verified` with Aigis stops with "No verified Aigis commits yet".

Which `Latest` runs `Promoted` accepts: hook style `manual`, NoMount `lkm` or `no` (not `integrate`), not a **NoMount only** run and **Compiler** `aigis`, and it must have built every kernel you picked (Kernel `both` needs a `Latest` run with `both`; `mzggr` or `aigis` also accept a `both` run). The runner (your PC or GitHub), tuning, **Valhall GPU** (Promoted keeps the GPU of that run), the release type and the benchmark tick do not matter. Runs with other options are skipped. If no run fits, `Promoted` ends with the warning "Nothing promoted" and changes nothing.

How `Promoted` gets the NoMount module:

- If that `Latest` run already has the NoMount module from the chosen **NoMount branch**, it is reused. Nothing is built.
- If it has none (NoMount `no`) or one from the other branch, `Promoted` builds the module from that run's saved kernel kit, without compiling the kernel. Older runs from before the kit existed fall back to compiling the kernel once, only to match the module.
- With NoMount `no`, the promoted build has no module. `integrate` is not allowed with `Promoted`.

With **Release** set to `CI`, the files are kept as artifacts of the `Promoted` run. With `Pre-release`, they are published as a pre-release. The hook style and tuning options are ignored in `Promoted`; they come from the `Latest` run.

A full `Release` with `Latest` or `Promoted` stops with the message "Release must use Verified". Use `Pre-release` for those, or switch to `Verified`.

**Release from last pre-release** (no build): test first, then publish exactly what you flashed.

1. Run Build Kernel with commit mode `Verified` and release type `Pre-release`, and flash that pre-release.
2. When it works, run Build Kernel again with commit mode `Verified` and release type `Release from last pre-release`. The newest pre-release of this branch becomes the full Release (same ZIPs, notes rewritten as "what's new since the last Release") and the README sources table is updated. Kernel options are ignored here.

It stops with "Release must use Verified" when that pre-release was not built from the commits in `configs/verified.json` (for example a `Latest` pre-release, or one made before a newer `Promoted`).

"What's new" in a full Release always compares with the previous full Release; a pre-release compares with the previous release of any kind. A previous release of another kernel repo makes it a "First release".

With NoMount `lkm`, a `Pre-release` or `Release` attaches the module ZIP and `nomount-4.14-<kernel>.ko` built in the same run to the release page, plus the xxKSU manager `.apk`. The README sources table is updated only by a full `Release`.

## XDA changelog

Every full Release (`Release`, or `Release from last pre-release`) also gets `XDA-changelog-<tag>.txt`: the release notes as an XDA post (BBCode), with the download link and the long build info folded into a spoiler. Download it from the release page, copy everything, and paste it at the top of the changelog post of the XDA thread. Pre-releases do not get it. The thread template is in [`docs/xda-thread.txt`](xda-thread.txt).
