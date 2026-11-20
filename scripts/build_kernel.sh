#!/usr/bin/env bash
# Configures and compiles the kernel tree made by prepare_sources.sh.
#
#   KERNEL_DIR   kernel tree (required)
#   OUT_DIR      build output folder (required)
#   TOOLCHAIN    AOSP Clang 14 folder (made by fetch_aosp_clang.sh if missing)
#   PERF_TUNING  true = merge configs/a325x-tuning.config too
#   KSU_HOOK     manual (default), syscall_table or branch_link
#   EXTRA_MODULE_DIR  optional out-of-tree module folder to build afterwards
#                     (used by the NoMount LKM workflow)
#   NOMOUNT_MODE      integrate = also merge configs/nomount-integrate.config
#   KERNEL_KIT        folder with .config, Module.symvers and kernel.release
#                     from an earlier full build of this exact kernel. Then the
#                     kernel is not compiled again; only modules_prepare runs,
#                     which is enough to build EXTRA_MODULE_DIR for it.
set -euo pipefail
ROOT=$(cd -- "$(dirname -- "$0")/.." && pwd)
. "$ROOT/scripts/sources.conf"
. "$ROOT/scripts/aosp_clang14.conf"
: "${KERNEL_DIR:?KERNEL_DIR is required}"
: "${OUT_DIR:?OUT_DIR is required}"
PERF_TUNING=${PERF_TUNING:-false}
KSU_HOOK=${KSU_HOOK:-manual}
KERNEL_TOOLCHAIN=${KERNEL_TOOLCHAIN:-aosp}
if [[ "$KERNEL_TOOLCHAIN" == zyc ]]; then
  TOOLCHAIN=${TOOLCHAIN:-"$ROOT/.toolchains/zyc-clang"}
else
  TOOLCHAIN=${TOOLCHAIN:-"$ROOT/.toolchains/$AOSP_CLANG_DIRECTORY"}
fi
JOBS=${JOBS:-$(nproc)}

bash "$ROOT/scripts/fetch_toolchain.sh" "$TOOLCHAIN"
TOOLCHAIN=$(cd -- "$TOOLCHAIN" && pwd)
export KBUILD_BUILD_USER=${KBUILD_BUILD_USER:-xxksu}
export KBUILD_BUILD_HOST=${KBUILD_BUILD_HOST:-builder}
export KBUILD_BUILD_VERSION=${KBUILD_BUILD_VERSION:-1}
KBUILD_BUILD_TIMESTAMP=${KBUILD_BUILD_TIMESTAMP:-$(git -C "$KERNEL_DIR" show -s --format=%cD HEAD)}
export KBUILD_BUILD_TIMESTAMP
mkdir -p "$OUT_DIR"
OUT_DIR=$(cd -- "$OUT_DIR" && pwd)

if [[ "$KERNEL_TOOLCHAIN" == zyc ]]; then
  # Exactly the Aigis CI environment ("Build kernel" step). No LLVM=1: the
  # kernel Makefile then uses $(CROSS_COMPILE)gcc, the clang wrapper made by
  # fetch_zyc_clang.sh, with ZyC's own binutils for the rest.
  export PATH="$TOOLCHAIN/bin:$PATH"
  [[ -d "$TOOLCHAIN/compat-lib" ]] && export LD_LIBRARY_PATH="$TOOLCHAIN/compat-lib:${LD_LIBRARY_PATH:-}"
  export ARCH=arm64
  export ANDROID_MAJOR_VERSION=r
  export CROSS_COMPILE="$TOOLCHAIN/bin/aarch64-linux-gnu-"
  export CROSS_COMPILE_ARM32="$TOOLCHAIN/bin/arm-linux-gnueabi-"
  export CC="$TOOLCHAIN/bin/clang"
  export LD="$TOOLCHAIN/bin/ld.lld"
  export OBJCOPY="$TOOLCHAIN/bin/llvm-objcopy"
  export AS="$TOOLCHAIN/bin/llvm-as"
  export NM="$TOOLCHAIN/bin/llvm-nm"
  export STRIP="$TOOLCHAIN/bin/llvm-strip"
  export OBJDUMP="$TOOLCHAIN/bin/llvm-objdump"
  export READELF="$TOOLCHAIN/bin/llvm-readelf"
  export KCFLAGS=' -w -pipe -O3'
  export KCPPFLAGS=' -O3'
  export CONFIG_SECTION_MISMATCH_WARN_ONLY=y
  # Same make arguments as the Aigis CI.
  # KERNEL_LINKER=lld (default) links with ZyC's ld.lld, as the published
  # Aigis kernels are ("LLD 14.0.6" in their version string). It must be a
  # make argument: the kernel Makefile overrides LD from the environment.
  # KERNEL_LINKER=gnu keeps $(CROSS_COMPILE)ld (the Aigis CI default).
  ld_args=()
  case "${KERNEL_LINKER:-lld}" in
    lld) ld_args=(LD="$TOOLCHAIN/bin/ld.lld") ;;
    gnu) ;;
    *) echo "KERNEL_LINKER must be lld or gnu" >&2; exit 1 ;;
  esac
  kmake() { make "$@" "${ld_args[@]}" KCFLAGS=' -w -pipe -O3' CONFIG_SECTION_MISMATCH_WARN_ONLY=y; }
  {
    cat "$TOOLCHAIN/zyc-source.txt"
    "$TOOLCHAIN/bin/clang" --version
    "$TOOLCHAIN/bin/ld.lld" --version
    "${CROSS_COMPILE}ld" --version | head -n1
  } > "$OUT_DIR/toolchain-source.txt"
  echo "Linker: ${KERNEL_LINKER:-lld}" >> "$OUT_DIR/toolchain-source.txt"
  echo "Toolchain: ZyC Clang (Aigis CI setup), CC=${CROSS_COMPILE}gcc, linker ${KERNEL_LINKER:-lld}"
else
kmake() { make "$@"; }
for tool in aarch64-linux-gnu-as aarch64-linux-gnu-elfedit; do
  command -v "$tool" >/dev/null || { echo "Missing $tool (install binutils-aarch64-linux-gnu)" >&2; exit 1; }
done

export ARCH=arm64
export PATH="$TOOLCHAIN/bin:$PATH"
export LD_LIBRARY_PATH="$TOOLCHAIN/lib64:$TOOLCHAIN/lib:${LD_LIBRARY_PATH:-}"
# Same toolchain setup as the booting Najip/android_kernel_a325F_bakasu xxksu
# build: Clang 14 + ld.lld, GNU as for the assembler (LLVM_IAS=0), no LTO.
export CC="$TOOLCHAIN/bin/clang" LD="$TOOLCHAIN/bin/ld.lld"
export AR="$TOOLCHAIN/bin/llvm-ar" NM="$TOOLCHAIN/bin/llvm-nm"
export STRIP="$TOOLCHAIN/bin/llvm-strip" OBJCOPY="$TOOLCHAIN/bin/llvm-objcopy"
export OBJDUMP="$TOOLCHAIN/bin/llvm-objdump" READELF="$TOOLCHAIN/bin/llvm-readelf"
export CROSS_COMPILE=aarch64-linux-gnu-
AS=$(command -v aarch64-linux-gnu-as)
export AS LLVM=1 LLVM_IAS=0
export KCFLAGS=${KCFLAGS:--Wno-error -Wno-error=incompatible-pointer-types -Wno-error=int-conversion -Wno-error=visibility -Wno-error=fortify-source -Wno-error=pointer-to-int-cast -Wno-error=typedef-redefinition -Wno-error=strict-prototypes -Wno-error=implicit-function-declaration}
{
  cat "$TOOLCHAIN/aosp-source.txt"
  "$CC" --version
  "$LD" --version
  "$AS" --version | head -n1
} > "$OUT_DIR/toolchain-source.txt"
fi

cd "$KERNEL_DIR"
base=()
for f in $KERNEL_FRAGMENTS; do base+=("arch/arm64/configs/$f"); done
fragments=("$ROOT/configs/a325x-xxksu-susfs.config" "$ROOT/configs/hooks/$KSU_HOOK.config")
[[ "$PERF_TUNING" == true ]] && fragments+=("$ROOT/configs/a325x-tuning.config")
[[ "${NOMOUNT_MODE:-lkm}" == integrate ]] && fragments+=("$ROOT/configs/nomount-integrate.config")

if [[ -n "${KERNEL_KIT:-}" ]]; then
  [[ -n "${EXTRA_MODULE_DIR:-}" ]] || { echo "KERNEL_KIT is only for building a module" >&2; exit 1; }
  for f in .config Module.symvers kernel.release; do
    [[ -s "$KERNEL_KIT/$f" ]] || { echo "Kernel kit has no $f" >&2; exit 1; }
  done
  echo "Using the kernel kit of $(cat "$KERNEL_KIT/kernel.release"): no kernel compile"
  cp -f "$KERNEL_KIT/.config" "$OUT_DIR/.config"
  kmake O="$OUT_DIR" olddefconfig
  # The kit must describe this tree exactly; olddefconfig changes nothing then.
  if ! diff -q <(grep '^CONFIG_' "$KERNEL_KIT/.config" | sort) <(grep '^CONFIG_' "$OUT_DIR/.config" | sort) >/dev/null; then
    diff <(grep '^CONFIG_' "$KERNEL_KIT/.config" | sort) <(grep '^CONFIG_' "$OUT_DIR/.config" | sort) >&2 || true
    echo "The kernel kit .config does not match this tree." >&2; exit 1
  fi
  kmake O="$OUT_DIR" -j"$JOBS" modules_prepare
  release=$(cat "$OUT_DIR/include/config/kernel.release")
  [[ "$release" == "$(cat "$KERNEL_KIT/kernel.release")" ]] || {
    echo "Kernel release $release differs from the kit" >&2; exit 1; }
  # Symbol versions (CONFIG_MODVERSIONS) of the kernel that was really built.
  cp -f "$KERNEL_KIT/Module.symvers" "$OUT_DIR/Module.symvers"
  echo "Building out-of-tree module in $EXTRA_MODULE_DIR"
  kmake O="$OUT_DIR" M="$EXTRA_MODULE_DIR" CONFIG_NOMOUNT=m -j"$JOBS" modules
  echo "Module built for: $release"
  exit 0
fi

sh scripts/kconfig/merge_config.sh -m -O "$OUT_DIR" "${base[@]}" "${fragments[@]}"
kmake O="$OUT_DIR" olddefconfig
if [[ -n "${KERNEL_GPU_PATCH:-}" ]]; then
  grep -qx 'CONFIG_MTK_GPU_VERSION="mali bifrost r25p0"' "$OUT_DIR/.config" \
    || { echo "GPU is not the stock Bifrost r25p0: $(grep MTK_GPU_VERSION "$OUT_DIR/.config")" >&2; exit 1; }
fi

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

kmake O="$OUT_DIR" headers_install INSTALL_HDR_PATH="$OUT_DIR/usr"
kmake O="$OUT_DIR" -j"$JOBS" ${KEEP_GOING:+-k}
test -s "$OUT_DIR/vmlinux"
test -s "$OUT_DIR/arch/arm64/boot/Image"
"$READELF" -h "$OUT_DIR/vmlinux" | grep -q AArch64
"$NM" --defined-only "$OUT_DIR/vmlinux" > "$OUT_DIR/kernel-symbols.txt"
case "$KSU_HOOK" in
  manual) hook_symbols="ksu_handle_sys_execve" ;;
  syscall_table) hook_symbols="hook_aarch64_execve hook_aarch64_reboot" ;;
  branch_link) hook_symbols="bl_hack_init_thread ksu_do_faccessat hook_aarch64_execve" ;;
esac
for symbol in erofs_fs_type ksu_handle_sys_reboot ksu_handle_newfstat_ret $hook_symbols \
    xxksu_parent_sucompat_enabled susfs_set_priority_uid_filter susfs_is_priority_uid_filtered; do
  grep -Eq "[[:space:]]$symbol$" "$OUT_DIR/kernel-symbols.txt" || {
    echo "Missing linked xxKSU/SUSFS symbol: $symbol" >&2; exit 1; }
done
if [[ "${NOMOUNT_MODE:-lkm}" == integrate ]]; then
  grep -q '^CONFIG_NOMOUNT=y' "$OUT_DIR/.config" || { echo "NoMount is not built in" >&2; exit 1; }
  test -s "$OUT_DIR/fs/nomount/nomount.o" || { echo "NoMount was not compiled into the kernel" >&2; exit 1; }
fi
if [[ -n "${EXTRA_MODULE_DIR:-}" ]]; then
  echo "Building out-of-tree module in $EXTRA_MODULE_DIR"
  kmake O="$OUT_DIR" M="$EXTRA_MODULE_DIR" CONFIG_NOMOUNT=m -j"$JOBS" modules
fi
echo "Build finished: $(cat "$OUT_DIR/include/config/kernel.release")"
