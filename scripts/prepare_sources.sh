#!/usr/bin/env bash
# Downloads every upstream source and builds a ready-to-compile kernel tree.
#
#   KERNEL_DIR   where the kernel tree goes (required). Reused if it exists.
#   INFO_DIR     where sources.json / applied-patches.txt are written (required)
#   PERF_TUNING  true = also apply the optional tuning patch (default false)
#   KERNEL_REF / KSU_REF / SUSFS_REF override scripts/sources.conf
set -euo pipefail
ROOT=$(cd -- "$(dirname -- "$0")/.." && pwd)
# shellcheck source=sources.conf
. "$ROOT/scripts/sources.conf"
: "${KERNEL_DIR:?KERNEL_DIR is required}"
: "${INFO_DIR:?INFO_DIR is required}"
PERF_TUNING=${PERF_TUNING:-false}
mkdir -p "$INFO_DIR"
INFO_DIR=$(cd -- "$INFO_DIR" && pwd)

api() {
  local auth=()
  [[ -n "${GH_TOKEN:-}" ]] && auth=(-H "Authorization: Bearer $GH_TOKEN")
  curl -fsSL --retry 3 "${auth[@]}" "https://api.github.com/$1"
}
log() { printf '\n==> %s\n' "$*"; }

# fetch <url> <ref> <dir>: shallow-fetch one ref into <dir> and check it out clean.
fetch() {
  local url=$1 ref=$2 dir=$3
  if [[ ! -d "$dir/.git" ]]; then
    rm -rf -- "$dir"
    git init -q "$dir"
    git -C "$dir" remote add origin "$url"
  else
    git -C "$dir" remote set-url origin "$url"
  fi
  git -C "$dir" fetch -q --depth=1 --no-tags origin "$ref"
  git -C "$dir" checkout -q -f --detach FETCH_HEAD
  git -C "$dir" reset -q --hard
  git -C "$dir" clean -qffdx
}

log "Kernel: $KERNEL_REPO ($KERNEL_REF)"
fetch "$KERNEL_REPO" "$KERNEL_REF" "$KERNEL_DIR"
KERNEL_DIR=$(cd -- "$KERNEL_DIR" && pwd)
cd "$KERNEL_DIR"
kernel_sha=$(git rev-parse HEAD)
kernel_date=$(git show -s --format=%cI HEAD)
kernel_subject=$(git show -s --format=%s HEAD)
# Upstream commits a stale build folder; it would break O= builds.
rm -rf -- out

log "SUSFS patch: $SUSFS_REPO ($SUSFS_REF)"
susfs_sha=$(git ls-remote "$SUSFS_REPO" "refs/heads/$SUSFS_REF" | cut -f1)
[[ -n "$susfs_sha" ]] || susfs_sha=$SUSFS_REF   # allow a commit hash as ref
susfs_patch="$INFO_DIR/susfs_patch_to_4.14.patch"
raw=${SUSFS_REPO/github.com/raw.githubusercontent.com}
curl -fsSL --retry 3 -o "$susfs_patch" "$raw/$susfs_sha/$SUSFS_PATCH"
susfs_patch_date=$(api \
  "repos/${SUSFS_REPO#https://github.com/}/commits?sha=$susfs_sha&path=$SUSFS_PATCH&per_page=1" \
  | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d[0]["commit"]["committer"]["date"] if d else "")' || true)

log "xxKSU: $KSU_REPO ($KSU_REF)"
fetch "$KSU_REPO" "$KSU_REF" KernelSU
ksu_sha=$(git -C KernelSU rev-parse HEAD)
ksu_date=$(git -C KernelSU show -s --format=%cI HEAD)
ksu_subject=$(git -C KernelSU show -s --format=%s HEAD)
ksu_version=$(grep -o 'KSU_VERSION=[0-9]*' KernelSU/kernel/Makefile | head -n1 | cut -d= -f2)
ksu_tag=$(api "repos/${KSU_REPO#https://github.com/}/releases/latest" \
  | python3 -c 'import json,sys; print(json.load(sys.stdin).get("tag_name",""))' 2>/dev/null || true)

applied=()
log "Applying build fixes for the kernel tree"
for p in "$ROOT"/patches/fixes/*.patch; do
  [[ -e "$p" ]] || continue
  echo "  $(basename "$p")"
  patch -p1 -F2 -N --no-backup-if-mismatch -s -i "$p"
  applied+=("fixes/$(basename "$p")")
done

log "Applying SUSFS (JackA1ltman)"
python3 "$ROOT/scripts/apply_susfs.py" "$KERNEL_DIR" "$susfs_patch"
applied+=("susfs_patch_to_4.14.patch@${susfs_sha:0:12}")

log "Applying xxKSU + SUSFS integration"
cp -a "$ROOT/overlay/." "$KERNEL_DIR/"
for p in "$ROOT"/patches/integration/*.patch; do
  echo "  $(basename "$p")"
  patch -p1 -F2 -N --no-backup-if-mismatch -s -i "$p"
  applied+=("$(basename "$p")")
done
if find . -name '*.rej' -print -quit | grep -q .; then
  echo "Patch rejects found:" >&2; find . -name '*.rej' >&2; exit 1
fi

log "Applying xxKSU patches"
for p in "$ROOT"/patches/kernelsu/*.patch; do
  echo "  $(basename "$p")"
  git -C KernelSU apply --whitespace=nowarn "$p"
  applied+=("kernelsu/$(basename "$p")")
done
ln -sfn ../KernelSU/kernel drivers/kernelsu

log "Applying kernel patches"
echo "  0001-network-udp-gso.patch (always)"
patch -p1 -F2 -N --no-backup-if-mismatch -s -i "$ROOT/patches/kernel/0001-network-udp-gso.patch"
applied+=("0001-network-udp-gso.patch")
if [[ "$PERF_TUNING" == true ]]; then
  echo "  0002-optional-tuning.patch (tuning ticked)"
  patch -p1 -F2 -N --no-backup-if-mismatch -s -i "$ROOT/patches/kernel/0002-optional-tuning.patch"
  applied+=("0002-optional-tuning.patch")
fi
if find . -name '*.rej' -print -quit | grep -q .; then
  echo "Patch rejects found:" >&2; find . -name '*.rej' >&2; exit 1
fi

susfs_version=$(sed -n 's/^#define SUSFS_VERSION "\([^"]*\)".*/\1/p' include/linux/susfs.h | head -n1)
kernel_version=$(make -s kernelversion 2>/dev/null || true)
printf '%s\n' "${applied[@]}" > "$INFO_DIR/applied-patches.txt"

export kernel_sha kernel_date kernel_subject kernel_version susfs_sha susfs_patch_date susfs_version
export ksu_sha ksu_date ksu_subject ksu_version ksu_tag
export KERNEL_REPO KERNEL_REF KSU_REPO KSU_REF SUSFS_REPO SUSFS_REF SUSFS_PATCH
python3 - "$INFO_DIR/sources.json" <<'EOF'
import json, os, sys
e = os.environ
data = {
    "kernel": {"repo": e["KERNEL_REPO"], "ref": e["KERNEL_REF"], "commit": e["kernel_sha"],
               "date": e["kernel_date"], "subject": e["kernel_subject"],
               "version": e["kernel_version"]},
    "xxksu": {"repo": e["KSU_REPO"], "ref": e["KSU_REF"], "commit": e["ksu_sha"],
              "date": e["ksu_date"], "subject": e["ksu_subject"],
              "ksu_version": e["ksu_version"], "tag": e["ksu_tag"]},
    "susfs": {"repo": e["SUSFS_REPO"], "ref": e["SUSFS_REF"], "commit": e["susfs_sha"],
              "path": e["SUSFS_PATCH"], "patch_date": e["susfs_patch_date"],
              "version": e["susfs_version"]},
}
json.dump(data, open(sys.argv[1], "w"), indent=2)
print(json.dumps(data, indent=2))
EOF
log "Kernel tree ready: $KERNEL_DIR"
