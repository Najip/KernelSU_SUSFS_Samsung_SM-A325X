#!/usr/bin/env bash
# Configures and compiles the kernel tree made by prepare_sources.sh.
#
#   KERNEL_DIR   kernel tree (required)
#   OUT_DIR      build output folder (required)
#   TOOLCHAIN    AOSP Clang 14 folder (made by fetch_aosp_clang.sh if missing)
#   PERF_TUNING  true = merge configs/a325x-tuning.config too
#   EXTRA_MODULE_DIR  optional out-of-tree module folder to build afterwards
#                     (used by the NoMount LKM workflow)
set -euo pipefail
ROOT=$(cd -- "$(dirname -- "$0")/.." && pwd)
. "$ROOT/scripts/sources.conf"
. "$ROOT/scripts/aosp_clang14.conf"
: "${KERNEL_DIR:?KERNEL_DIR is required}"
: "${OUT_DIR:?OUT_DIR is required}"
PERF_TUNING=${PERF_TUNING:-false}
TOOLCHAIN=${TOOLCHAIN:-"$ROOT/.toolchains/$AOSP_CLANG_DIRECTORY"}
JOBS=${JOBS:-$(nproc)}

sh "$ROOT/scripts/fetch_aosp_clang.sh" "$TOOLCHAIN"
TOOLCHAIN=$(cd -- "$TOOLCHAIN" && pwd)
for tool in aarch64-linux-gnu-as aarch64-linux-gnu-elfedit; do
  command -v "$tool" >/dev/null || { echo "Missing $tool (install binutils-aarch64-linux-gnu)" >&2; exit 1; }
done

export ARCH=arm64
export PATH="$TOOLCHAIN/bin:$PATH"
export LD_LIBRARY_PATH="$TOOLCHAIN/lib64:$TOOLCHAIN/lib:${LD_LIBRARY_PATH:-}"
export CROSS_COMPILE=aarch64-linux-gnu-
NM="$TOOLCHAIN/bin/llvm-nm" READELF="$TOOLCHAIN/bin/llvm-readelf"
# This Samsung Makefile hard-codes CC to a bundled clang, so the tools must be
# given on the make command line. Clang 14 compiles; GNU binutils assemble and
# link, like the stock Samsung build (no LTO).
MAKE_ARGS=(
  ARCH=arm64
  CC="$TOOLCHAIN/bin/clang"
  CLANG_TRIPLE=aarch64-linux-gnu-
  CROSS_COMPILE=aarch64-linux-gnu-
  HOSTCC=gcc HOSTCXX=g++ PYTHON=python3
)
CC="$TOOLCHAIN/bin/clang" LD=$(command -v aarch64-linux-gnu-ld)
AS=$(command -v aarch64-linux-gnu-as)
# Empty LOCALVERSION stops the kernel adding "+" / git hashes to the version.
export LOCALVERSION=
export KBUILD_BUILD_USER=${KBUILD_BUILD_USER:-xxksu}
export KBUILD_BUILD_HOST=${KBUILD_BUILD_HOST:-builder}
export KBUILD_BUILD_VERSION=${KBUILD_BUILD_VERSION:-1}
KBUILD_BUILD_TIMESTAMP=${KBUILD_BUILD_TIMESTAMP:-$(git -C "$KERNEL_DIR" show -s --format=%cD HEAD)}
export KBUILD_BUILD_TIMESTAMP
export KCFLAGS=${KCFLAGS:--Wno-error -Wno-error=incompatible-pointer-types -Wno-error=int-conversion -Wno-error=visibility -Wno-error=fortify-source -Wno-error=pointer-to-int-cast -Wno-error=typedef-redefinition -Wno-error=strict-prototypes -Wno-error=implicit-function-declaration}

mkdir -p "$OUT_DIR"
OUT_DIR=$(cd -- "$OUT_DIR" && pwd)
{
  cat "$TOOLCHAIN/aosp-source.txt"
  "$CC" --version
  "$LD" --version
  "$AS" --version | head -n1
} > "$OUT_DIR/toolchain-source.txt"

fragments=("$ROOT/configs/a325x-xxksu-susfs.config")
[[ "$PERF_TUNING" == true ]] && fragments+=("$ROOT/configs/a325x-tuning.config")
cd "$KERNEL_DIR"
CC="$CC" sh scripts/kconfig/merge_config.sh -m -O "$OUT_DIR" "arch/arm64/configs/$DEFCONFIG" "${fragments[@]}"
make "${MAKE_ARGS[@]}" O="$OUT_DIR" olddefconfig

# Make sure every requested option really ended up in .config.
missing=0
for frag in "${fragments[@]}"; do
  while IFS= read -r line; do
    case "$line" in
      CONFIG_*=*) grep -qxF "$line" "$OUT_DIR/.config" || { echo "Config not applied: $line" >&2; missing=1; } ;;
      "# CONFIG_"*" is not set")
        opt=${line#\# }; opt=${opt%% *}
        grep -q "^$opt=" "$OUT_DIR/.config" && { echo "Config still enabled: $opt" >&2; missing=1; } ;;
    esac
  done < "$frag"
done
((missing == 0)) || { echo "Some config options were dropped by olddefconfig." >&2; exit 1; }

make "${MAKE_ARGS[@]}" O="$OUT_DIR" -j"$JOBS"
test -s "$OUT_DIR/vmlinux"
test -s "$OUT_DIR/arch/arm64/boot/Image"
"$READELF" -h "$OUT_DIR/vmlinux" | grep -q AArch64
"$NM" --defined-only "$OUT_DIR/vmlinux" > "$OUT_DIR/kernel-symbols.txt"
for symbol in ksu_handle_sys_reboot ksu_handle_sys_execve ksu_handle_newfstat_ret \
    xxksu_parent_sucompat_enabled susfs_set_priority_uid_filter susfs_is_priority_uid_filtered; do
  grep -Eq "[[:space:]]$symbol$" "$OUT_DIR/kernel-symbols.txt" || {
    echo "Missing linked xxKSU/SUSFS symbol: $symbol" >&2; exit 1; }
done
if [[ -n "${EXTRA_MODULE_DIR:-}" ]]; then
  echo "Building out-of-tree module in $EXTRA_MODULE_DIR"
  make "${MAKE_ARGS[@]}" O="$OUT_DIR" M="$EXTRA_MODULE_DIR" CONFIG_NOMOUNT=m -j"$JOBS" modules
fi
echo "Build finished: $(cat "$OUT_DIR/include/config/kernel.release")"
