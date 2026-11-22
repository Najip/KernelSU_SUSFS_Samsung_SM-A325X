#!/usr/bin/env bash
# Writes the release notes of a release into <out.md>.
#
#   release_body.sh <release folder> <tag prefix> <type> <this tag> <out.md>
#
# <release folder> has sources.json, build-info.txt (the mzggr kernel, else the
# first kernel), sources-<kernel>.json / build-info-<kernel>.txt for the other
# kernels (aigis, aigis-bakasu) and files named like the release ZIPs (only the
# names are used).
# <type> Release: "what's new" since the previous full Release.
# <type> Pre-release: since the previous release of any kind.
# The previous release must use the same kernel repo, otherwise it is a first release.
set -euo pipefail
dir=$1 prefix=$2 type=$3 this=$4 out=$5
here=$(cd "$(dirname "$0")" && pwd)
if [[ "$type" == Release ]]; then only='select(.isPrerelease | not) |'; else only=; fi
prev=$(gh release list --repo "$GITHUB_REPOSITORY" --exclude-drafts --limit 100 --json tagName,isPrerelease \
  --jq "[.[] | $only .tagName | select(test(\"^$prefix-[0-9]{8}-[0-9]+\$\")) | select(. != \"$this\")][0] // \"\"")
prev_json=-
tmp=$(mktemp -d)
if [[ -n "$prev" ]] && gh release download "$prev" --repo "$GITHUB_REPOSITORY" --pattern sources.json --dir "$tmp" 2>/dev/null; then
  echo "Previous ${type/Pre-release/release}: $prev"
  prev_json=$tmp/sources.json
  if ! python3 -c 'import json,sys; k=lambda s: s.get("source") or ("aigis" if "aigis" in s["kernel"]["repo"].lower() else "mzggr"); a,b=(k(json.load(open(p))) for p in sys.argv[1:]); sys.exit(a!=b)' "$dir/sources.json" "$prev_json"; then
    echo "The previous release used another kernel; this is the first one with this kernel."
    prev_json=-
  fi
else
  echo "No previous release with sources.json; this is the first one."
fi
# info_of <kernel>: the build-info file of that kernel in this release.
info_of() {
  local f
  for f in "$dir"/sources*.json; do
    if [[ "$(python3 -c 'import json,sys; s=json.load(open(sys.argv[1])); print(s.get("source") or ("aigis" if "aigis" in s["kernel"]["repo"].lower() else "mzggr"))' "$f")" == "$1" ]]; then
      b=$(basename "$f" .json); echo "build-info${b#sources}.txt"; return
    fi
  done
  echo build-info.txt
}
python3 "$here/release_notes.py" notes "$dir/sources.json" "$prev_json" "$dir/build-info.txt" "$out"
shopt -s nullglob
others=("$dir"/sources-*.json)
if ((${#others[@]})); then
  {
    echo
    echo "## Kernels in this release"
    echo "Pick one kernel ZIP and flash it. NoMount: flash the NoMount ZIP made for that kernel."
    for z in "$dir"/*.zip; do
      n=$(basename "$z")
      case "$n" in
        NoMount-*) ;;
        *-Aigis-BakaSU-*-vgpu*.zip) echo "- \`$n\`: main kernel (Aigis) with BakaSU as root instead of xxKSU, Valhall GPU, drivers module included (needs the BakaSU manager; details: $(info_of aigis-bakasu))" ;;
        *-Aigis-BakaSU-*) echo "- \`$n\`: main kernel (Aigis) with BakaSU as root instead of xxKSU (needs the BakaSU manager; details: $(info_of aigis-bakasu))" ;;
        *-Aigis-*-valhall.zip) echo "- \`$n\`: main kernel (Aigis) with the Valhall GPU and its drivers module" ;;
        *-Aigis-*-vgpu*.zip) echo "- \`$n\`: main kernel (Aigis by SlamZDank, the one I use every day) with the Valhall GPU, drivers module included (details: $(info_of aigis))" ;;
        *-Aigis-*) echo "- \`$n\`: main kernel (Aigis by SlamZDank, the one I use every day) (details: $(info_of aigis))" ;;
        *) echo "- \`$n\`: Alt. kernel (mzggr by mzggr0914) (details: $(info_of mzggr))" ;;
      esac
    done
    for z in "$dir"/NoMount-*.zip; do
      n=$(basename "$z")
      case "$n" in *-aigis-bakasu-*) k="main kernel with BakaSU (Aigis BakaSU)" ;; *-aigis-*) k="main kernel (Aigis)" ;; *-mzggr-*) k="Alt. kernel (mzggr)" ;; *) k= ;; esac
      echo "- \`$n\`: NoMount module${k:+ for the $k}"
    done
  } >> "$out"
fi
shopt -s nullglob
apks=("$dir"/*.apk)
if ((${#apks[@]})); then
  {
    echo
    echo "## Manager apps"
    if [[ -f "$dir/manager.json" || -f "$dir/manager-bakasu.json" ]]; then
      python3 - "$dir" <<'PY2'
import json, os, sys
d = sys.argv[1]
if os.path.exists(os.path.join(d, "manager.json")):
    m = json.load(open(os.path.join(d, "manager.json")))
    print(f"- `{m['apk']}`: xxKSU manager, from the latest xxKSU release [{m['tag']}]({m['url']}). "
          "Install it to manage root on the xxKSU kernels.")
if os.path.exists(os.path.join(d, "manager-bakasu.json")):
    m = json.load(open(os.path.join(d, "manager-bakasu.json")))
    print(f"- `{m['apk']}`: BakaSU manager, from the BakaSU build [{m['tag']}]({m['url']}) of the same BakaSU "
          f"commit `{m['commit'][:12]}` as the kernel. Install it (instead of the xxKSU one) on the BakaSU kernel.")
PY2
    else
      for a in "${apks[@]}"; do echo "- \`$(basename "$a")\`: xxKSU manager. Install it to manage root."; done
    fi
  } >> "$out"
fi
# GPL-2.0: say where the complete source of the kernels in this release is.
python3 - "$dir" >> "$out" <<'PY3'
import json, os, sys
d = sys.argv[1]
print("\n## Source code (GPL-2.0)")
print("The kernels are built from these exact commits, with the patches and build scripts of this repo at the commit below:")
seen = set()
labels = {"aigis": "Main kernel: Aigis", "aigis-bakasu": "Main kernel: Aigis (BakaSU)", "mzggr": "Alt. kernel: mzggr"}
for name in sorted(n for n in os.listdir(d) if n.startswith("sources") and n.endswith(".json")):
    s = json.load(open(os.path.join(d, name)))
    kernel = s.get("source") or ("aigis" if "aigis" in s["kernel"]["repo"].lower() else "mzggr")
    label = labels.get(kernel, kernel)
    parts = [(label, s["kernel"]), (s.get("root") or "xxKSU", s["xxksu"]), ("SUSFS patch", s["susfs"]), ("This repo (patches, build scripts)", s.get("build_repo"))]
    for what, x in parts:
        if not x or (what, x["commit"]) in seen:
            continue
        seen.add((what, x["commit"]))
        repo = x["repo"].removesuffix(".git").rstrip("/")
        print(f"- {what}: [{repo.split('github.com/')[-1]} @ `{x['commit'][:12]}`]({repo}/tree/{x['commit']})")
print("- NoMount: [maxsteeel/nomount](https://github.com/maxsteeel/nomount) (commit in the NoMount ZIP name after `-n`)")
print(f"\nLicenses: see [docs/licenses.md](https://github.com/{os.environ.get('GITHUB_REPOSITORY') or 'Najip/KernelSU_SUSFS_Samsung_SM-A325X'}/blob/main/docs/licenses.md).")
PY3
rm -rf "$tmp"
