#!/usr/bin/env bash
# Builds the NoMount module for the kernel sources already chosen.
#
# Expects the same environment as a kernel build (KERNEL_DIR is created here),
# plus NOMOUNT_REF (dev or master) and KSU_HOOK / PERF_TUNING.
# The last argument is the folder the ZIP and nomount-4.14.ko are copied to.
set -euo pipefail
ROOT=$(cd -- "$(dirname -- "$0")/.." && pwd)
# shellcheck source=sources.conf
. "$ROOT/scripts/sources.conf"
dest=${1:?give the output folder}
: "${NOMOUNT_REF:?NOMOUNT_REF is required}"
KVER=4.14

work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT
export BUILD_WORK=$work
export KERNEL_DIR=$work/kernel
export OUT_DIR=$work/out
export INFO_DIR=$work/info
export TOOLCHAIN=${TOOLCHAIN:-$work/toolchain}

bash "$ROOT/scripts/prepare_sources.sh"
bash "$ROOT/scripts/fetch_aosp_clang.sh" "$TOOLCHAIN"

log=$work/build.log
up=$work/nomount
git clone -q --branch "$NOMOUNT_REF" "$NOMOUNT_REPO" "$up"
src=$up/kernel/src
for f in Makefile nomount.c nomount.h; do
  [[ -f "$src/$f" ]] || { echo "NoMount $NOMOUNT_REF has no kernel/src/$f" >&2; exit 1; }
done
[[ -f "$up/module/module.prop" ]]
sha=$(git -C "$up" rev-parse HEAD)
count=$(git -C "$up" rev-list --count HEAD)
mod_src=$work/nomount-kmod
mkdir -p "$mod_src"
cp -f "$src"/nomount.c "$src"/nomount.h "$mod_src/"
[[ -f "$src/Kconfig" ]] && cp -f "$src/Kconfig" "$mod_src/"
{
  echo "# NoMount $sha ($count commits), copied by CI."
  printf 'ccflags-y += -DNOMOUNT_COMMIT_COUNT=\\"%s\\"\n' "$count"
  echo
  sed -n '/^obj-\$(CONFIG_NOMOUNT)/,$p' "$src/Makefile"
} > "$mod_src/Makefile"
grep -q 'obj-\$(CONFIG_NOMOUNT)' "$mod_src/Makefile"
echo "Using NoMount $NOMOUNT_REF at $sha ($count commits)"

EXTRA_MODULE_DIR=$mod_src bash "$ROOT/scripts/build_kernel.sh" 2>&1 | tee "$log"
[[ -s "$mod_src/nomount.ko" ]]
release=$(cat "$OUT_DIR/include/config/kernel.release")
vermagic=$(strings "$mod_src/nomount.ko" | grep -m1 '^vermagic=' || true)
echo "kernel.release: $release"
echo "$vermagic"
case "$vermagic" in
  "vermagic=$release "*) ;;
  *) echo "vermagic does not match kernel.release" >&2; exit 1 ;;
esac
artifacts=$work/artifacts
mkdir -p "$artifacts"
install -m644 "$mod_src/nomount.ko" "$artifacts/nomount-$KVER.ko"
"$TOOLCHAIN/bin/llvm-strip" --strip-debug "$artifacts/nomount-$KVER.ko"

command -v zig >/dev/null || { echo "zig is not installed" >&2; exit 1; }
bin=$work/bin
mkdir -p "$bin"
cd "$up/userspace/src"
if grep -q '#include <unistd.h>' nm.h; then
  zig cc -target aarch64-linux -Oz -mcmodel=tiny -static -ffreestanding -fno-unwind-tables -fno-ident \
    -Wno-invalid-noreturn -mllvm -enable-machine-outliner=always nm.c -o "$bin/nm-arm64"
  zig cc -target arm-linux -Oz -static -ffreestanding -fno-unwind-tables -fno-ident -Wno-invalid-noreturn \
    -ffunction-sections -fdata-sections -Wl,--gc-sections nm.c -o "$bin/nm-arm"
else
  zig cc -target aarch64-linux -Oz -mcmodel=tiny -static -nostdlib -ffreestanding -fno-unwind-tables \
    -fno-ident -Wno-invalid-noreturn -mllvm -enable-machine-outliner=always -Wl,--entry=_start nm.c -o "$bin/nm-arm64"
  zig cc -target arm-linux -Oz -static -nostdlib -ffreestanding -fno-unwind-tables -fno-ident -Wno-invalid-noreturn \
    -ffunction-sections -fdata-sections -Wl,--gc-sections -Wl,--entry=_start nm.c -o "$bin/nm-arm"
fi
git clone -q --depth=1 "$LKMLOADER_REPO" "$work/lkmloader"
lkm_sha=$(git -C "$work/lkmloader" rev-parse HEAD)
cd "$work/lkmloader"
zig cc -target aarch64-linux -Oz -mcmodel=tiny -static -Wl,--gc-sections,-z,norelro -fno-unwind-tables \
  -fno-ident -flto -fmerge-all-constants -fomit-frame-pointer -mllvm -enable-machine-outliner=always \
  src/lkmloader.c -o "$bin/lkmloader-arm64"
zig cc -target arm-linux -Oz -static -Wl,--gc-sections,-z,norelro -fno-unwind-tables \
  -fno-ident -flto -fmerge-all-constants -fomit-frame-pointer src/lkmloader.c -o "$bin/lkmloader-arm"

mod=$work/module
rm -rf "$mod"
cp -a "$up/module" "$mod"
mkdir -p "$mod/bin" "$mod/lkm"
cp "$bin"/* "$mod/bin/"
cp "$artifacts/nomount-$KVER.ko" "$mod/lkm/nomount-$KVER.ko"
kshort=$(python3 -c "import json;print(json.load(open('$INFO_DIR/sources.json'))['kernel']['commit'][:8])")
nshort=${sha:0:8}
base_ver=$(sed -n 's/^version=//p' "$mod/module.prop" | tr -d '\r ' | head -n1)
sed -i "s/^versionCode=.*/versionCode=${count}/" "$mod/module.prop"
sed -i "s/^version=.*/version=${base_ver} (${count}-${nshort}, LKM ${KVER})/" "$mod/module.prop"
suffix=
[[ "${PERF_TUNING:-false}" == true ]] && suffix=-tuning
name="NoMount-${base_ver}-${NOMOUNT_REF}-lkm-${KVER}-k${kshort}-n${nshort}${suffix}"
{
  echo "NoMount LKM for A325X xxKSU + SUSFS kernel"
  echo "NoMount: $NOMOUNT_REPO branch $NOMOUNT_REF @ $sha ($count commits)"
  echo "lkmloader: $LKMLOADER_REPO @ $lkm_sha"
  echo "Built for kernel release: $release"
  echo "xxKSU hook style: ${KSU_HOOK:-}"
  echo "Performance tuning kernel: ${PERF_TUNING:-false}"
  echo "Kernel sources used:"
  python3 -c "import json;d=json.load(open('$INFO_DIR/sources.json'));[print(f'  {k}: {v[\"repo\"]} @ {v[\"commit\"]}') for k,v in d.items()]"
  [[ -n "${GITHUB_RUN_ID:-}" ]] && echo "Workflow run: $GITHUB_SERVER_URL/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID"
} > "$artifacts/build-info.txt"
cp "$artifacts/build-info.txt" "$mod/build-info.txt"
(cd "$mod" && zip -qr9 "$artifacts/$name.zip" .)
unzip -tq "$artifacts/$name.zip"
unzip -l "$artifacts/$name.zip" | grep -q "lkm/nomount-$KVER.ko"
unzip -l "$artifacts/$name.zip" | grep -q 'bin/lkmloader-arm64'
unzip -l "$artifacts/$name.zip" | grep -q 'module.prop'

mkdir -p "$dest"
cp -v "$artifacts/$name.zip" "$artifacts/nomount-$KVER.ko" "$dest/"
[[ -s "$dest/$name.zip" && -s "$dest/nomount-$KVER.ko" ]] || { echo "Copy into $dest failed" >&2; ls -l "$dest"; exit 1; }
echo "NoMount module: $dest/$name.zip"
