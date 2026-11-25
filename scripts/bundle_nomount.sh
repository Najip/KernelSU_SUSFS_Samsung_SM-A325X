#!/usr/bin/env bash
# Puts a NoMount LKM module into a flashable kernel ZIP (folder nomount/).
# Every kernel ZIP with NoMount "lkm" carries the module built for it; the
# separate NoMount ZIP and .ko stay in CI and releases too. Flashed in TWRP,
# the kernel zip installs it when no NoMount module is installed (see
# anykernel/nomount-check.sh).
#
#   bundle_nomount.sh <kernel.zip> <NoMount.zip> [build-info.txt ...]
# The module must be for the same kernel ID as the kernel zip. A module
# already in the zip is replaced. The build-info.txt files given get a line
# naming the module.
set -euo pipefail
zip_path=$(realpath "${1:?kernel zip}")
nm_zip=$(realpath "${2:?NoMount zip}")
shift 2
[[ -s "$zip_path" && -s "$nm_zip" ]]

work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT
want=$(unzip -p "$zip_path" build-info.txt | sed -n 's/^Kernel ID (NoMount match): //p' | head -n1)
mkdir -p "$work/nomount"
unzip -q "$nm_zip" -d "$work/nomount"
got=$(sed -n 's/^kernelId=//p' "$work/nomount/module.prop" | head -n1)
echo "$(basename "$zip_path"): kernel ID $want, NoMount module $got"
[[ -n "$want" && "$want" == "$got" ]] || { echo "NoMount module $(basename "$nm_zip") is not for this kernel" >&2; exit 1; }
for f in module.prop bin/nm-arm64 bin/lkmloader-arm64 lkm/nomount-4.14.ko; do
  [[ -s "$work/nomount/$f" ]] || { echo "NoMount module has no $f" >&2; exit 1; }
done
unzip -p "$zip_path" anykernel.sh | grep -q '^nm_install()' \
  || { echo "$(basename "$zip_path") is from before the TWRP NoMount install; build the kernel again" >&2; exit 1; }

tag="NoMount module in this ZIP (TWRP installs it when none is installed):"
line="$tag $(basename "$nm_zip")"
unzip -p "$zip_path" build-info.txt | grep -vF "$tag" > "$work/build-info.txt" || true
echo "$line" >> "$work/build-info.txt"
if unzip -l "$zip_path" | grep -q ' nomount/'; then
  zip -qd "$zip_path" 'nomount/*'
fi
extra_files=()
if unzip -l "$zip_path" | grep -q ' banner$'; then
  nm_ver=$(sed -n 's/^version=//p' "$work/nomount/module.prop" | tr -d '\r' | head -n1 | sed 's/, LKM [^)]*//')
  [[ -n "$nm_ver" ]] || nm_ver=$(basename "$nm_zip" .zip)
  unzip -p "$zip_path" banner | sed "s|^ NoMount:.*| NoMount: $nm_ver|" > "$work/banner"
  extra_files+=(banner)
fi
(cd "$work" && zip -qr9 "$zip_path" nomount build-info.txt "${extra_files[@]}")
unzip -tq "$zip_path"
unzip -l "$zip_path" | grep -q 'nomount/lkm/nomount-4.14.ko'
for info in "$@"; do
  [[ -f "$info" ]] || continue
  grep -vF "$tag" "$info" > "$work/info" || true
  echo "$line" >> "$work/info"
  cat "$work/info" > "$info"
done
echo "Added $(basename "$nm_zip") to $(basename "$zip_path")"
