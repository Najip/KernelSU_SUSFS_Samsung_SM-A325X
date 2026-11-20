#!/usr/bin/env bash
# Prints the kernel ID: 16 hex chars that only depend on the kernel itself
# (kernel release, every CONFIG_ line of .config and the symbol CRCs in
# Module.symvers). A NoMount module carries the ID of the kernel it was built
# against, so any module built for the same kernel matches, whichever run
# built it (kernel compiled in the same job, saved kernel kit, or a rebuild).
#
#   kernel_id.sh <folder with .config, Module.symvers, include/config/kernel.release or kernel.release>
set -euo pipefail
dir=${1:?give the kernel output folder}
release=$dir/include/config/kernel.release
[[ -s "$release" ]] || release=$dir/kernel.release
for f in "$dir/.config" "$dir/Module.symvers" "$release"; do
  [[ -s "$f" ]] || { echo "kernel_id.sh: missing $f" >&2; exit 1; }
done
{
  echo "release $(cat "$release")"
  grep '^CONFIG_' "$dir/.config" | LC_ALL=C sort
  # CRC, symbol and export type; the module path column depends on the build folder.
  awk '{print $1, $2, $NF}' "$dir/Module.symvers" | LC_ALL=C sort
} | sha256sum | cut -c1-16
