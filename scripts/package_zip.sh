#!/usr/bin/env bash
# Makes the flashable AnyKernel3 ZIP and build-info.txt.
#
#   KERNEL_DIR, OUT_DIR, INFO_DIR  same as the other scripts (required)
#   PACKAGE_DIR  where the ZIP and txt files go (required)
#   PERF_TUNING, KSU_HOOK  only used for the file name / build info
# Prints nothing special; writes $PACKAGE_DIR/zip-name.txt with the ZIP name.
set -euo pipefail
ROOT=$(cd -- "$(dirname -- "$0")/.." && pwd)
. "$ROOT/scripts/sources.conf"
: "${KERNEL_DIR:?}" "${OUT_DIR:?}" "${INFO_DIR:?}" "${PACKAGE_DIR:?}"
PERF_TUNING=${PERF_TUNING:-false}
KSU_HOOK=${KSU_HOOK:-manual}
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
  git init -q "$ak3"
  git -C "$ak3" fetch -q --depth=1 "$AK3_REPO" "$AK3_COMMIT"
  git -C "$ak3" checkout -q --detach FETCH_HEAD
  rm -rf -- "$ak3/.git" "$ak3/.github" "$ak3"/Image* "$ak3"/zImage* "$ak3/README.md"
  cp "$ROOT/anykernel/anykernel.sh" "$ak3/anykernel.sh"
  ak3_line="$AK3_REPO @ $AK3_COMMIT"
fi

read_json() { python3 -c "import json,sys; d=json.load(open('$INFO_DIR/sources.json')); print(d$1)"; }
susfs=$(read_json '["susfs"]["version"]')
kshort=$(read_json '["kernel"]["commit"][:8]')
xshort=$(read_json '["xxksu"]["commit"][:8]')
repo_sha=$(git -C "$ROOT" rev-parse HEAD 2>/dev/null || echo unknown)
release=$(cat "$OUT_DIR/include/config/kernel.release")
date=$(date -u +%Y%m%d)
suffix=
case "$KSU_HOOK" in
  syscall_table) suffix=-sct ;;
  branch_link) suffix=-bl ;;
esac
[[ "$PERF_TUNING" == true ]] && suffix=$suffix-tuning
NOMOUNT_MODE=${NOMOUNT_MODE:-lkm}
[[ "$NOMOUNT_MODE" == integrate ]] && suffix=$suffix-nm
case "$NOMOUNT_MODE" in
  integrate) nomount_line="built into the kernel ($(read_json '["nomount"]["branch"]') @ $(read_json '["nomount"]["commit"]'))" ;;
  lkm) nomount_line="separate LKM (${NOMOUNT_REF:-dev})" ;;
  *) nomount_line="not included" ;;
esac
name="${KERNEL_LABEL}-xxKSU-SUSFS-${susfs}-${date}-k${kshort}-x${xshort}${suffix}"

sed -i "s|^kernel\.string=.*|kernel.string=${KERNEL_LABEL} ${release} xxKSU SUSFS ${susfs}${suffix}|" "$ak3/anykernel.sh"
cp "$IMAGE" "$ak3/Image"
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
  echo "${KERNEL_LABEL} xxKSU + SUSFS kernel"
  echo "Built: $(date -u '+%Y-%m-%d %H:%M UTC')"
  echo "Kernel release: $release"
  echo "Kernel source: $(read_json '["kernel"]["repo"]') @ $(read_json '["kernel"]["commit"]') ($(read_json '["kernel"]["ref"]'))"
  echo "xxKSU: $(read_json '["xxksu"]["repo"]') @ $(read_json '["xxksu"]["commit"]') (KSU_VERSION $(read_json '["xxksu"]["ksu_version"]'), latest tag $(read_json '["xxksu"]["tag"]'))"
  echo "SUSFS: $susfs from $(read_json '["susfs"]["repo"]') @ $(read_json '["susfs"]["commit"]') ($(read_json '["susfs"]["path"]'))"
  echo "Build repo commit: $repo_sha"
  if [[ "${KERNEL_TOOLCHAIN:-aosp}" == zyc ]]; then
    echo "Toolchain: $(grep -m1 "clang version" "$OUT_DIR/toolchain-source.txt") (ZyC, Aigis CI setup: gcc wrappers, no LLVM=1, -w -pipe -O3)"
  else
    echo "Toolchain: $(grep -m1 "clang version" "$OUT_DIR/toolchain-source.txt") + ld.lld + GNU as (no LTO)"
  fi
  echo "AnyKernel3: $ak3_line"
  echo "dtb: $dtb_line"
  [[ -n "${VALHALL_DRIVERS_URL:-}" ]] && echo "Valhall GPU drivers module (only if your vendor lacks them): $VALHALL_DRIVERS_URL"
  echo "Network fix (UDP GSO): $([[ "${NETWORK_FIX:-true}" == true ]] && echo applied || echo 'not applied')"
  echo "xxKSU hook style: $KSU_HOOK"
  echo "Performance tuning: $PERF_TUNING"
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

# Second ZIP: the same kernel + the Valhall GPU drivers module, installed
# into /data/adb/modules by the zip itself (one flash instead of two).
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
  sed -i "s|^kernel\.string=.*|&-valhall|" "$vak3/anykernel.sh"
  sed -i "s|^Valhall GPU drivers module.*|Valhall GPU drivers module: included in ${name}-valhall.zip (installed to /data/adb/modules/a32-gpu-upgrade); the plain zip leaves it out: $VALHALL_DRIVERS_URL|" "$work/build-info.txt" "$vak3/build-info.txt" "$ak3/build-info.txt"
  vzip_path="$PACKAGE_DIR/$name-valhall.zip"
  (cd "$vak3" && zip -qr9 "$vzip_path" . -x '*~')
  unzip -tq "$vzip_path"
  unzip -p "$vzip_path" Image | cmp - "$IMAGE"
  unzip -p "$vzip_path" valhall/system/vendor/lib64/egl/libGLES_mali.so | cmp - "$vak3/valhall/system/vendor/lib64/egl/libGLES_mali.so"
  unzip -p "$vzip_path" anykernel.sh | grep -q '^valhall_install;'
  echo "$name-valhall" > "$PACKAGE_DIR/zip-name-valhall.txt"
  # Refresh the plain zip's build-info.txt with the updated Valhall line.
  (cd "$ak3" && zip -q9 "$zip_path" build-info.txt)
fi

cp "$work/build-info.txt" "$PACKAGE_DIR/build-info.txt"
cp "$INFO_DIR/sources.json" "$PACKAGE_DIR/sources.json"
(cd "$PACKAGE_DIR" && sha256sum "$name".zip "$name"-valhall.zip 2>/dev/null > SHA256SUMS.txt || true)
grep -q " $name.zip$" "$PACKAGE_DIR/SHA256SUMS.txt"
echo "$name" > "$PACKAGE_DIR/zip-name.txt"
cat "$PACKAGE_DIR/build-info.txt"
echo "Created flashable ZIP: $zip_path"
[[ -f "$PACKAGE_DIR/zip-name-valhall.txt" ]] && echo "Created flashable ZIP with the Valhall drivers: $PACKAGE_DIR/$name-valhall.zip"
exit 0
