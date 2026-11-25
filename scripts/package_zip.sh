#!/usr/bin/env bash
# Makes the flashable AnyKernel3 ZIP and build-info.txt.
#
#   KERNEL_DIR, OUT_DIR, INFO_DIR  same as the other scripts (required)
#   PACKAGE_DIR  where the ZIP and txt files go (required)
# Prints nothing special; writes $PACKAGE_DIR/zip-name.txt with the ZIP name.
set -euo pipefail
ROOT=$(cd -- "$(dirname -- "$0")/.." && pwd)
. "$ROOT/scripts/sources.conf"
: "${KERNEL_DIR:?}" "${OUT_DIR:?}" "${INFO_DIR:?}" "${PACKAGE_DIR:?}"
IMAGE="$OUT_DIR/arch/arm64/boot/Image"
test -s "$IMAGE"

work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT
ak3="$work/AnyKernel3"
if [[ -n "${AK3_FROM_TREE:-}" ]]; then
  # The kernel tree's own AnyKernel folder (its anykernel.sh, tools and
  # device names), as the Aigis CI packages it: only Image is added.
  [[ -f "$KERNEL_DIR/$AK3_FROM_TREE/anykernel.sh" ]] || { echo "No $AK3_FROM_TREE/anykernel.sh in the kernel tree" >&2; exit 1; }
  cp -a "$KERNEL_DIR/$AK3_FROM_TREE" "$ak3"
  rm -rf -- "$ak3/.git" "$ak3/.github" "$ak3"/Image* "$ak3"/zImage* "$ak3/dtbo.img" "$ak3/README.md"
  ak3_line="$AK3_FROM_TREE folder of the kernel tree (Image only)"
else
  echo "AK3_FROM_TREE is not set (the Aigis kernel packs with its own AnyKernel folder)" >&2; exit 1
fi

read_json() { python3 -c "import json,sys; d=json.load(open('$INFO_DIR/sources.json')); print(d$1)"; }
susfs=$(read_json '["susfs"]["version"]')
kshort=$(read_json '["kernel"]["commit"][:8]')
# Root module (BakaSU): its short commit, b<sha> in the name. (The sources.json
# key "ksu" means the root module of the kernel, BakaSU.)
xshort=$(read_json '["ksu"]["commit"][:8]')
rletter=b
repo_sha=$(git -C "$ROOT" rev-parse HEAD 2>/dev/null || echo unknown)
release=$(cat "$OUT_DIR/include/config/kernel.release")
# Kernel ID: the same for every build of this exact kernel; the NoMount module
# built for it carries the same ID (see scripts/kernel_id.sh).
kernel_id=$(bash "$ROOT/scripts/kernel_id.sh" "$OUT_DIR")
date=$(date -u +%Y%m%d)
suffix=
[[ "${VALHALL_GPU:-false}" == true ]] && suffix=$suffix-vgpu
[[ "${KERNEL_SOURCE%-bakasu}" == aigis && "$KERNEL_TOOLCHAIN" == aosp ]] && suffix=$suffix-aospclang
NOMOUNT_MODE=${NOMOUNT_MODE:-lkm}
[[ "$NOMOUNT_MODE" == integrate ]] && suffix=$suffix-nm
case "$NOMOUNT_MODE" in
  integrate)
    nomount_line="built into the kernel ($(read_json '["nomount"]["branch"]') @ $(read_json '["nomount"]["commit"]'))"
    nomount_short="built-in ($(read_json '["nomount"]["branch"]') @ $(read_json '["nomount"]["commit"][:8]'))"
    ;;
  lkm)
    nomount_line="separate LKM (${NOMOUNT_REF:-master})"
    nomount_short="LKM (${NOMOUNT_REF:-master})"
    ;;
  *)
    nomount_line="not included"
    nomount_short="not included"
    ;;
esac
name="${KERNEL_LABEL}-${ROOT_NAME}-SUSFS-${susfs}-${date}-k${kshort}-${rletter}${xshort}${suffix}"

sed -i "s|^kernel\.string=.*|kernel.string=${KERNEL_LABEL} ${release} ${ROOT_NAME} SUSFS ${susfs}${suffix}|" "$ak3/anykernel.sh"
if [[ -f "$ROOT/anykernel/banner" ]]; then
  sed -e "s|@KVER@|${release%%-*}|g" -e "s|@ROOT@|${ROOT_NAME}|g" -e "s|@SUSFS@|${susfs}|g" \
    -e "s|@NOMOUNT@|${nomount_short}|g" \
    "$ROOT/anykernel/banner" > "$ak3/banner"
fi
cp "$IMAGE" "$ak3/Image"

# Flasher additions, run after the kernel is written:
#  - every zip: NoMount check (warns when the installed NoMount LKM was not
#    built for this kernel, by kernel ID)
add_after_boot() {
  python3 - "$ak3/anykernel.sh" "$1" <<'PY'
import sys
p, add = sys.argv[1], open(sys.argv[2]).read()
s = open(p).read()
for marker in ("## end boot install", "## end install"):
    if s.count(marker) == 1:
        open(p, "w").write(s.replace(marker, marker + "\n" + add, 1))
        break
else:
    sys.exit("anykernel.sh: no single '## end boot install' or '## end install' line")
PY
}
sed -e "s|@KERNEL_ID@|$kernel_id|" -e "s|@KERNEL_RELEASE@|$release|" -e "s|@NOMOUNT_MODE@|${NOMOUNT_MODE:-lkm}|" \
  "$ROOT/anykernel/nomount-check.sh" > "$work/nomount-check.sh"
add_after_boot "$work/nomount-check.sh"
grep -q '^nomount_check;' "$ak3/anykernel.sh"
# Every zip: the JPEG + BBR fix module (mtk_mm access for apps; BBR by Juan, LumiROM).
cp -r "$ROOT/anykernel/jpeg-bbr" "$ak3/jpeg-bbr"
add_after_boot "$ROOT/anykernel/jpeg-bbr-install.sh"
grep -q '^jpeg_bbr_install;' "$ak3/anykernel.sh"
dtb_line="not included (the phone's current dtb is kept)"
if [[ -n "${AK3_DTB_BOOTIMG:-}" ]]; then
  bootimg="$work/dtb-source-boot.img"
  curl -fsSL --retry 3 -o "$bootimg" "$AK3_DTB_BOOTIMG"
  echo "$AK3_DTB_BOOTIMG_SHA256  $bootimg" | sha256sum -c --quiet - \
    || { echo "dtb source boot image checksum changed: $AK3_DTB_BOOTIMG" >&2; exit 1; }
  python3 "$ROOT/scripts/bootimg_dtb.py" "$bootimg" "$ak3/dtb"
  echo "$AK3_DTB_SHA256  $ak3/dtb" | sha256sum -c --quiet -
  dtb_line="$(basename "$AK3_DTB_BOOTIMG") (sha256 ${AK3_DTB_SHA256:0:16}...), written to the boot partition with the kernel"
fi
[[ -z "${AK3_FROM_TREE:-}" ]] && gzip -n -9 -c "$IMAGE" > "$ak3/Image.gz"

{
  echo "${KERNEL_LABEL} ${ROOT_NAME} + SUSFS kernel"
  echo "Built: $(date -u '+%Y-%m-%d %H:%M UTC')"
  echo "Kernel release: $release"
  echo "Kernel ID (NoMount match): $kernel_id"
  echo "uname tag: ${KERNEL_TAG:-none}"
  echo "Kernel source: $(read_json '["kernel"]["repo"]') @ $(read_json '["kernel"]["commit"]') ($(read_json '["kernel"]["ref"]'))"
  echo "$ROOT_NAME: $(read_json '["ksu"]["repo"]') @ $(read_json '["ksu"]["commit"]') (KSU_VERSION $(read_json '["ksu"]["ksu_version"]'), latest tag $(read_json '["ksu"]["tag"]'))"
  echo "SUSFS: $susfs from $(read_json '["susfs"]["repo"]') @ $(read_json '["susfs"]["commit"]') ($(read_json '["susfs"]["path"]'))"
  echo "Build repo commit: $repo_sha"
  if [[ "${KERNEL_TOOLCHAIN:-aosp}" == zyc ]]; then
    echo "Toolchain: $(grep -m1 "clang version" "$OUT_DIR/toolchain-source.txt") (ZyC, Aigis CI setup: gcc wrappers, no LLVM=1, -w -pipe -O3, linker: ${KERNEL_LINKER:-lld})"
  else
    echo "Toolchain: $(grep -m1 "clang version" "$OUT_DIR/toolchain-source.txt") + ld.lld + GNU as (no LTO)"
  fi
  echo "AnyKernel3: $ak3_line"
  echo "GPU: $([[ "${VALHALL_GPU:-false}" == true ]] && echo 'Aigis Valhall r32p1 with Aigis GPU tuning' || echo 'stock A32 Bifrost r25p0')"
  echo "dtb: $dtb_line"
  [[ -n "${VALHALL_DRIVERS_URL:-}" ]] && echo "Valhall GPU drivers module (only if your vendor lacks them): $VALHALL_DRIVERS_URL"
  echo "JPEG + BBR fix module $(sed -n 's/^version=//p' "$ROOT/anykernel/jpeg-bbr/module.prop") (apps get access to /dev/dma_heap/mtk_mm; BBR by Juan, LumiROM): installed to /data/adb/modules/a32-jpeg-bbr"
  echo "Network fix (UDP GSO): $([[ "${NETWORK_FIX:-true}" == true ]] && echo applied || echo 'not applied')"
  echo "BakaSU hook style: SUSFS inline hooks (compile-time calls inside the kernel functions)"
  echo "NoMount: $nomount_line"
  echo "Patches applied:"
  sed 's/^/  - /' "$INFO_DIR/applied-patches.txt"
  [[ -n "${GITHUB_RUN_ID:-}" ]] && echo "Workflow run: $GITHUB_SERVER_URL/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID"
  echo "Image SHA256: $(sha256sum "$IMAGE" | cut -d' ' -f1)"
} > "$work/build-info.txt"
cp "$work/build-info.txt" "$ak3/build-info.txt"

mkdir -p "$PACKAGE_DIR"
zip_path="$PACKAGE_DIR/$name.zip"
rm -f "$zip_path"
(cd "$ak3" && zip -qr9 "$zip_path" . -x '*.zip' '*~')
unzip -tq "$zip_path"
unzip -p "$zip_path" Image | cmp - "$IMAGE"
[[ -z "${AK3_DTB_BOOTIMG:-}" ]] || unzip -p "$zip_path" dtb | sha256sum | grep -q "^$AK3_DTB_SHA256 "
[[ -n "${AK3_FROM_TREE:-}" ]] || unzip -p "$zip_path" Image.gz | gzip -dc | cmp - "$IMAGE"
unzip -l "$zip_path" | grep -q 'META-INF/com/google/android/update-binary'
unzip -l "$zip_path" | grep -q 'tools/ak3-core.sh'
unzip -l "$zip_path" | grep -q ' banner$'
unzip -l "$zip_path" | grep -q 'jpeg-bbr/service.sh'

# Valhall GPU: the ZIP is replaced by the bundle, the same kernel + the Valhall
# GPU drivers module installed into /data/adb/modules by the zip itself (one
# flash). There is no kernel-only ZIP for Valhall builds.
rm -f "$PACKAGE_DIR"/*-valhall.zip "$PACKAGE_DIR/zip-name-valhall.txt"
if [[ -n "${VALHALL_DRIVERS_URL:-}" ]]; then
  vzip="$work/valhall-module.zip"
  curl -fsSL --retry 3 -o "$vzip" "$VALHALL_DRIVERS_URL"
  echo "$VALHALL_DRIVERS_SHA256  $vzip" | sha256sum -c --quiet - \
    || { echo "Valhall drivers module checksum changed: $VALHALL_DRIVERS_URL" >&2; exit 1; }
  vak3="$work/AnyKernel3-valhall"
  cp -a "$ak3" "$vak3"
  mkdir "$vak3/valhall"
  unzip -q "$vzip" -d "$vak3/valhall"
  grep -q '^id=a32-gpu-upgrade$' "$vak3/valhall/module.prop"
  # Run after write_boot, so the kernel is flashed first.
  python3 - "$vak3/anykernel.sh" "$ROOT/anykernel/valhall-install.sh" <<'PY'
import sys
p, add = sys.argv[1], open(sys.argv[2]).read()
s = open(p).read()
marker = "## end boot install"
assert s.count(marker) == 1, "anykernel.sh: no single '## end boot install' line"
open(p, "w").write(s.replace(marker, marker + "\n" + add, 1))
PY
  sed -i "s|^kernel\.string=.*|& + Valhall drivers|" "$vak3/anykernel.sh"
  sed -i "s|^Valhall GPU drivers module.*|Valhall GPU drivers module: included in this zip (installed to /data/adb/modules/a32-gpu-upgrade): $VALHALL_DRIVERS_URL|" "$work/build-info.txt" "$vak3/build-info.txt"
  vzip_path=$zip_path
  rm -f "$vzip_path"
  (cd "$vak3" && zip -qr9 "$vzip_path" . -x '*~')
  unzip -tq "$vzip_path"
  unzip -p "$vzip_path" Image | cmp - "$IMAGE"
  unzip -p "$vzip_path" valhall/system/vendor/lib64/egl/libGLES_mali.so | cmp - "$vak3/valhall/system/vendor/lib64/egl/libGLES_mali.so"
  unzip -p "$vzip_path" anykernel.sh | grep -q '^valhall_install;'
  unzip -p "$vzip_path" anykernel.sh | grep -q '^jpeg_bbr_install;'
  unzip -l "$vzip_path" | grep -q 'META-INF/com/google/android/update-binary'
fi

cp "$work/build-info.txt" "$PACKAGE_DIR/build-info.txt"
cp "$INFO_DIR/sources.json" "$PACKAGE_DIR/sources.json"
(cd "$PACKAGE_DIR" && sha256sum "$name".zip > SHA256SUMS.txt)
grep -q " $name.zip$" "$PACKAGE_DIR/SHA256SUMS.txt"
echo "$name" > "$PACKAGE_DIR/zip-name.txt"
cat "$PACKAGE_DIR/build-info.txt"
echo "Created flashable ZIP: $zip_path$([[ -n "${VALHALL_DRIVERS_URL:-}" ]] && echo ' (kernel + Valhall GPU drivers module)')"
exit 0
