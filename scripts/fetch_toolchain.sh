#!/usr/bin/env bash
# Fetches the toolchain picked by KERNEL_TOOLCHAIN in scripts/sources.conf
# (aosp = pinned AOSP Clang 14, zyc = ZyC Clang as used by the Aigis CI).
set -euo pipefail
ROOT=$(cd -- "$(dirname -- "$0")/.." && pwd)
# shellcheck source=sources.conf
. "$ROOT/scripts/sources.conf"
case "${KERNEL_TOOLCHAIN:-aosp}" in
  aosp) exec sh "$ROOT/scripts/fetch_aosp_clang.sh" "$@" ;;
  zyc) exec bash "$ROOT/scripts/fetch_zyc_clang.sh" "$@" ;;
  *) echo "Unknown KERNEL_TOOLCHAIN '$KERNEL_TOOLCHAIN'" >&2; exit 1 ;;
esac
