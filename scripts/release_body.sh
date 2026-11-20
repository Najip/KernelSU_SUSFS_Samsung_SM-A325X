#!/usr/bin/env bash
# Writes the release notes of a release into <out.md>.
#
#   release_body.sh <release folder> <tag prefix> <type> <this tag> <out.md>
#
# <release folder> has sources.json, build-info.txt (and the -aigis copies for
# the Aigis kernel) and files named like the release ZIPs (only the names are used).
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
  if ! python3 -c 'import json,sys; a,b=(json.load(open(p))["kernel"]["repo"] for p in sys.argv[1:]); sys.exit(a!=b)' "$dir/sources.json" "$prev_json"; then
    echo "The previous release used another kernel; this is the first one with this kernel."
    prev_json=-
  fi
else
  echo "No previous release with sources.json; this is the first one."
fi
python3 "$here/release_notes.py" notes "$dir/sources.json" "$prev_json" "$dir/build-info.txt" "$out"
if [[ -f "$dir/sources-aigis.json" ]]; then
  shopt -s nullglob
  {
    echo
    echo "## Kernels in this release"
    echo "Pick one kernel ZIP and flash it. NoMount: flash the NoMount ZIP made for that kernel."
    for z in "$dir"/*.zip; do
      n=$(basename "$z")
      case "$n" in
        NoMount-*) ;;
        *-Aigis-*-valhall.zip) echo "- \`$n\`: Aigis kernel with the Valhall GPU and its drivers module" ;;
        *-Aigis-*-vgpu*.zip) echo "- \`$n\`: Aigis kernel by SlamZDank with the Valhall GPU, drivers module included (details: build-info-aigis.txt)" ;;
        *-Aigis-*) echo "- \`$n\`: Aigis kernel by SlamZDank (details: build-info-aigis.txt)" ;;
        *) echo "- \`$n\`: mzggr0914 kernel (details: build-info.txt)" ;;
      esac
    done
    for z in "$dir"/NoMount-*.zip; do
      n=$(basename "$z")
      case "$n" in *-aigis-*) k=Aigis ;; *-mzggr-*) k=mzggr ;; *) k= ;; esac
      echo "- \`$n\`: NoMount module${k:+ for the $k kernel}"
    done
    echo
    echo "Aigis sources: $(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(d["kernel"]["repo"] + " @ " + d["kernel"]["commit"][:12])' "$dir/sources-aigis.json")"
  } >> "$out"
fi
shopt -s nullglob
apks=("$dir"/*.apk)
if ((${#apks[@]})); then
  {
    echo
    echo "## xxKSU manager"
    if [[ -f "$dir/manager.json" ]]; then
      python3 - "$dir/manager.json" <<'PY2'
import json, sys
m = json.load(open(sys.argv[1]))
print(f"- `{m['apk']}`: from the latest xxKSU release [{m['tag']}]({m['url']}). Install it to manage root.")
PY2
    else
      for a in "${apks[@]}"; do echo "- \`$(basename "$a")\`: xxKSU manager. Install it to manage root."; done
    fi
  } >> "$out"
fi
rm -rf "$tmp"
