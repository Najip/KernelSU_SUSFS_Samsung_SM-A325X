#!/usr/bin/env bash
# Downloads every upstream source and builds a ready-to-compile kernel tree.
#
#   KERNEL_DIR   where the kernel tree goes (required). Reused if it exists.
#   INFO_DIR     where sources.json / applied-patches.txt are written (required)
#   NETWORK_FIX  true = apply the UDP GSO network fix (default true)
#   KERNEL_REF / KSU_REF / SUSFS_REF override scripts/sources.conf
#   KERNEL_BRANCH / KSU_BRANCH / SUSFS_BRANCH  branch name recorded in sources.json
#                when the ref above is a pinned commit (Verified mode)
#   NOMOUNT_MODE lkm (default, separate module), no, or integrate (built into
#                the kernel from NOMOUNT_REPO at NOMOUNT_REF, default master)
set -euo pipefail
ROOT=$(cd -- "$(dirname -- "$0")/.." && pwd)
# shellcheck source=sources.conf
. "$ROOT/scripts/sources.conf"
: "${KERNEL_DIR:?KERNEL_DIR is required}"
: "${INFO_DIR:?INFO_DIR is required}"
NOMOUNT_MODE=${NOMOUNT_MODE:-lkm}
NOMOUNT_REF=${NOMOUNT_REF:-master}
case "$NOMOUNT_MODE" in
  no|lkm|integrate) ;;
  *) echo "Unknown NOMOUNT_MODE '$NOMOUNT_MODE' (use no, lkm or integrate)" >&2; exit 1 ;;
esac
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
  if ! git -C "$dir" fetch -q --depth=1 --no-tags origin "$ref"; then
    # A reused copy can refuse the fetch (for example "not our ref" after the
    # upstream branch changed): start again with a fresh copy.
    echo "Fetch failed in the reused copy of $url, starting with a fresh copy."
    rm -rf -- "$dir"
    git init -q "$dir"
    git -C "$dir" remote add origin "$url"
    git -C "$dir" fetch -q --depth=1 --no-tags origin "$ref"
  fi
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
# The tree ships its own KernelSU submodule and an in-tree NoMount; this build
# uses BakaSU (fetched below) and the separate NoMount LKM instead.
rm -rf -- out KernelSU NoMount fs/nomount .gitmodules drivers/kernelsu

applied=()
log "Converting the tree to the BakaSU + SUSFS layout"
git apply --whitespace=nowarn "$ROOT/patches/$KERNEL_BASE_PATCH"
applied+=("$KERNEL_BASE_PATCH")
if [[ -n "${KERNEL_GPU_PATCH:-}" ]]; then
  log "GPU: stock A32 stack (Bifrost r25p0, taken from the mzggr kernel)"
  git apply --whitespace=nowarn "$ROOT/patches/$KERNEL_GPU_PATCH"
  applied+=("$KERNEL_GPU_PATCH")
fi

log "SUSFS core: $SUSFS_REPO ($SUSFS_REF)"
susfs_sha=$(git ls-remote "$SUSFS_REPO" "refs/heads/$SUSFS_REF" | cut -f1)
[[ -n "$susfs_sha" ]] || susfs_sha=$SUSFS_REF   # allow a commit hash as ref
susfs_patch="$INFO_DIR/susfs_patch_to_4.14.patch"
raw=${SUSFS_REPO/github.com/raw.githubusercontent.com}
curl -fsSL --retry 3 -o "$susfs_patch" "$raw/$susfs_sha/$SUSFS_PATCH"
susfs_patch_date=$(api \
  "repos/${SUSFS_REPO#https://github.com/}/commits?sha=$susfs_sha&path=$SUSFS_PATCH&per_page=1" \
  | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d[0]["commit"]["committer"]["date"] if d else "")' || true)
# Only the three SUSFS core files are taken from Jack's patch. The hooks in
# the rest of the kernel stay as the bakasu tree already has them for 4.14.
core_files=(fs/susfs.c include/linux/susfs.h include/linux/susfs_def.h)
rm -f -- "${core_files[@]}"
awk -v want="fs/susfs.c include/linux/susfs.h include/linux/susfs_def.h" '
  BEGIN { n = split(want, w, " "); for (i = 1; i <= n; i++) keep["a/" w[i]] = 1 }
  /^diff --git / { on = ($3 in keep) }
  on' "$susfs_patch" > "$INFO_DIR/susfs-core.patch"
git apply --whitespace=nowarn "$INFO_DIR/susfs-core.patch"
sed -i 's/[ \t]*$//' "${core_files[@]}"
git apply --whitespace=nowarn "$ROOT/patches/susfs/0001-jack-core-local-additions.patch"
applied+=("susfs_patch_to_4.14.patch@${susfs_sha:0:12} (core files)" "susfs/0001-jack-core-local-additions.patch")
# A32 storage: /sdcard/Android/data and obb go through sdcardfs, which the
# SUSFS core does not know. Small addition on top of Jack's core (sus_path only).
git apply --whitespace=nowarn "$ROOT/patches/susfs/0002-sdcardfs-sus-path.patch"
applied+=("susfs/0002-sdcardfs-sus-path.patch")

log "$ROOT_NAME: $KSU_REPO ($KSU_REF)"
if [[ "$ROOT_FLAVOR" == bakasu ]]; then
  # BakaSU's version code is its commit count (30000 + count + 700), the same
  # number its manager shows, so it needs the full history and tags. Always a
  # fresh copy: a reused one may hold the history of another BakaSU branch.
  bakasu_branch=${KSU_BRANCH:-main}
  [[ "$bakasu_branch" =~ ^[0-9a-f]{40}$ ]] && bakasu_branch=main
  # Show any git setting on this PC that sends GitHub downloads somewhere else
  # (for example to a fork with an older main), then ignore those settings.
  redirects=$(git config --show-origin --get-regexp '^url\..*' 2>/dev/null \
    | sed -E 's#(https?://)[^/@]+@#\1***@#g' || true)
  if [[ -n "$redirects" ]]; then
    echo "Note: this PC's git redirects some URLs (ignored for BakaSU):"
    echo "$redirects"
  fi
  bakasu_clone() {
    rm -rf -- KernelSU
    GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1 \
      git "$@" clone -q --no-checkout --branch "$bakasu_branch" "$KSU_REPO" KernelSU
    git -C KernelSU config --local core.hooksPath /dev/null
  }
  if ! bakasu_clone; then
    echo "BakaSU download failed, trying again with the older git protocol."
    if ! bakasu_clone -c protocol.version=0; then
      echo "BakaSU download failed twice. Git settings that can change downloads:"
      git --version
      git config --show-origin --get-regexp '^(url\.|protocol|fetch\.|transfer\.|remote\.|http\.).*' \
        | sed -E 's#(https?://)[^/@]+@#\1***@#g' || true
      exit 1
    fi
  fi
  if [[ "$KSU_REF" =~ ^[0-9a-f]{40}$ ]]; then
    if ! git -C KernelSU cat-file -e "$KSU_REF^{commit}" 2>/dev/null; then
      echo "Commit $KSU_REF is not in the downloaded BakaSU $bakasu_branch (its newest is $(git -C KernelSU rev-parse "origin/$bakasu_branch"))."
      GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1 git -C KernelSU fetch -q --tags origin "$KSU_REF"
    fi
    git -C KernelSU checkout -q -f --detach "$KSU_REF"
  else
    git -C KernelSU checkout -q -f --detach "origin/$bakasu_branch"
  fi
else
  fetch "$KSU_REPO" "$KSU_REF" KernelSU
fi
ksu_sha=$(git -C KernelSU rev-parse HEAD)
ksu_date=$(git -C KernelSU show -s --format=%cI HEAD)
ksu_subject=$(git -C KernelSU show -s --format=%s HEAD)
if [[ "$ROOT_FLAVOR" == bakasu ]]; then
  ksu_version=$((30000 + $(git -C KernelSU rev-list --count HEAD) + 700))
  ksu_tag=$(git -C KernelSU describe --abbrev=0 --tags 2>/dev/null || true)
else
  ksu_version=$(grep -o 'KSU_VERSION=[0-9]*' KernelSU/kernel/Makefile | head -n1 | cut -d= -f2)
  # The xxKSU release of exactly this commit (its manager APK is shipped with
  # the kernel); empty when the commit has no release.
  ksu_tag=$(git ls-remote --tags "$KSU_REPO" 2>/dev/null \
    | awk -v c="$ksu_sha" '$1 == c { t = $2; sub("refs/tags/", "", t); sub(/\^\{\}$/, "", t); print t; exit }' || true)
  log "Applying xxKSU patches"
  for p in "$ROOT"/patches/kernelsu/*.patch; do
    echo "  $(basename "$p")"
    git -C KernelSU apply --whitespace=nowarn "$p"
    applied+=("kernelsu/$(basename "$p")")
  done
fi
ln -sfn ../KernelSU/kernel drivers/kernelsu

if [[ "$ROOT_FLAVOR" == bakasu ]]; then
  log "Hook style: BakaSU SUSFS inline hooks"
  applied+=("hook style: BakaSU SUSFS inline (kernel calls BakaSU directly, next to the SUSFS hooks)")
  # BakaSU (since 2b558ca5, 16 Nov 2026) no longer has the my_* SELinux hide
  # functions the kernel's own hooks called. On 4.14 BakaSU hooks those
  # places itself ("auto" mode), so take the kernel's hooks out.
  for p in "$ROOT"/patches/bakasu/*.patch; do
    echo "  bakasu/$(basename "$p")"
    git apply --whitespace=nowarn "$p"
    applied+=("bakasu/$(basename "$p")")
  done
else
  log "Hook style: xxKSU manual hooks"
  applied+=("hook style: xxKSU manual (kernel calls xxKSU directly, next to the SUSFS hooks)")
fi

log "Applying kernel patches"
netfix="$ROOT/patches/kernel/0001-network-udp-gso.patch"
# Some trees (Aigis) already carry the same fix; then the tick decides
# whether it stays (ticked) or is reverted (unticked).
netfix_files=(net/ipv4/ip_output.c net/ipv6/ip6_output.c)
netfix_fixed='(sk->sk_type == SOCK_DGRAM && sk->sk_protocol == IPPROTO_UDP) ? ipc'
netfix_in_tree=false
[[ $(grep -lF "$netfix_fixed" "${netfix_files[@]}" | wc -l) == 2 ]] && netfix_in_tree=true
if [[ "${NETWORK_FIX:-true}" == true ]]; then
  if [[ "$netfix_in_tree" == true ]]; then
    echo "  0001-network-udp-gso.patch: already in the kernel tree (kept)"
    applied+=("0001-network-udp-gso.patch (already in the tree)")
  else
    echo "  0001-network-udp-gso.patch (network fix ticked)"
    git apply "$netfix"
    applied+=("0001-network-udp-gso.patch")
  fi
elif [[ "$netfix_in_tree" == true ]]; then
  echo "  network fix unticked: reverting the tree's own copy of the fix"
  sed -i 's/(sk->sk_type == SOCK_DGRAM \&\& sk->sk_protocol == IPPROTO_UDP) ? ipc/sk->sk_type == SOCK_DGRAM ? ipc/' "${netfix_files[@]}"
  if grep -q 'sk->sk_protocol == IPPROTO_UDP) ? ipc' "${netfix_files[@]}"; then
    echo "Could not revert the network fix" >&2; exit 1
  fi
  applied+=("0001-network-udp-gso.patch reverted (unticked)")
else
  echo "  network fix unticked: 0001-network-udp-gso.patch not applied"
fi
flashfix="$ROOT/patches/kernel/0002-flashlight-sm5714.patch"
# Flashlight fixes by aartzz. Skipped if the tree already has them.
if git apply --reverse --check "$flashfix" 2>/dev/null; then
  echo "  0002-flashlight-sm5714.patch: already in the kernel tree"
  applied+=("0002-flashlight-sm5714.patch (already in the tree)")
else
  echo "  0002-flashlight-sm5714.patch"
  git apply --whitespace=nowarn "$flashfix"
  applied+=("0002-flashlight-sm5714.patch")
fi
nomount_sha=
if [[ "$NOMOUNT_MODE" == integrate ]]; then
  log "NoMount built into the kernel: $NOMOUNT_REPO ($NOMOUNT_REF)"
  nm_up=$(mktemp -d)
  git clone -q --branch "$NOMOUNT_REF" "$NOMOUNT_REPO" "$nm_up"
  nomount_sha=$(git -C "$nm_up" rev-parse HEAD)
  nm_count=$(git -C "$nm_up" rev-list --count HEAD)
  nm_src=$nm_up/kernel/src
  for f in Kconfig Makefile nomount.c nomount.h; do
    [[ -f "$nm_src/$f" ]] || { echo "NoMount $NOMOUNT_REF has no kernel/src/$f" >&2; exit 1; }
  done
  mkdir -p fs/nomount
  cp -f "$nm_src"/Kconfig "$nm_src"/nomount.c "$nm_src"/nomount.h fs/nomount/
  # Same Makefile, with the commit count fixed (the tree is not a NoMount git checkout).
  {
    echo "# NoMount $nomount_sha ($nm_count commits), copied by CI."
    printf 'ccflags-y += -DNOMOUNT_COMMIT_COUNT=\\"%s\\"\n' "$nm_count"
    echo
    sed -n '/^obj-\$(CONFIG_NOMOUNT)/,$p' "$nm_src/Makefile"
  } > fs/nomount/Makefile
  grep -q 'obj-\$(CONFIG_NOMOUNT)' fs/nomount/Makefile
  grep -q 'fs/nomount/Kconfig' fs/Kconfig || sed -i 's|^source "fs/Kconfig.susfs"$|&\nsource "fs/nomount/Kconfig"|' fs/Kconfig
  grep -q 'fs/nomount/Kconfig' fs/Kconfig || sed -i 's|^source "fs/unicode/Kconfig"$|&\nsource "fs/nomount/Kconfig"|' fs/Kconfig
  grep -q 'fs/nomount/Kconfig' fs/Kconfig || { echo "Could not add NoMount to fs/Kconfig" >&2; exit 1; }
  grep -q 'nomount/' fs/Makefile || echo 'obj-$(CONFIG_NOMOUNT) += nomount/' >> fs/Makefile
  rm -rf -- "$nm_up"
  applied+=("NoMount built in: $NOMOUNT_REF @ ${nomount_sha:0:12} ($nm_count commits)")
fi

if find . -name '*.rej' -print -quit | grep -q .; then
  echo "Patch rejects found:" >&2; find . -name '*.rej' >&2; exit 1
fi

susfs_version=$(sed -n 's/^#define SUSFS_VERSION "\([^"]*\)".*/\1/p' include/linux/susfs.h | head -n1)
kernel_version=$(make -s kernelversion 2>/dev/null || true)
# When a ref is a pinned commit, record the branch it came from instead.
branch_of() { [[ -n "${2:-}" ]] && printf '%s' "$2" || printf '%s' "$1"; }
kernel_branch=$(branch_of "$KERNEL_REF" "${KERNEL_BRANCH:-}")
ksu_branch=$(branch_of "$KSU_REF" "${KSU_BRANCH:-}")
susfs_branch=$(branch_of "$SUSFS_REF" "${SUSFS_BRANCH:-}")
printf '%s\n' "${applied[@]}" > "$INFO_DIR/applied-patches.txt"

export kernel_sha kernel_date kernel_subject kernel_version kernel_branch ksu_branch susfs_branch susfs_sha susfs_patch_date susfs_version
export ksu_sha ksu_date ksu_subject ksu_version ksu_tag nomount_sha NOMOUNT_MODE NOMOUNT_REF NOMOUNT_REPO
export KERNEL_SOURCE ROOT_NAME KERNEL_REPO KERNEL_REF KSU_REPO KSU_REF SUSFS_REPO SUSFS_REF SUSFS_PATCH
python3 - "$INFO_DIR/sources.json" <<'EOF'
import json, os, sys
e = os.environ
data = {
    "kernel": {"repo": e["KERNEL_REPO"], "ref": e["KERNEL_REF"], "commit": e["kernel_sha"],
               "date": e["kernel_date"], "subject": e["kernel_subject"],
               "version": e["kernel_version"], "branch": e["kernel_branch"]},
    "source": e["KERNEL_SOURCE"],
    "root": e["ROOT_NAME"],
    # "ksu" = the root module of this kernel (BakaSU, see "root").
    "ksu": {"name": e["ROOT_NAME"], "repo": e["KSU_REPO"], "ref": e["KSU_REF"], "commit": e["ksu_sha"],
            "date": e["ksu_date"], "subject": e["ksu_subject"],
            "ksu_version": e["ksu_version"], "tag": e["ksu_tag"], "branch": e["ksu_branch"]},
    "susfs": {"repo": e["SUSFS_REPO"], "ref": e["SUSFS_REF"], "commit": e["susfs_sha"],
              "path": e["SUSFS_PATCH"], "patch_date": e["susfs_patch_date"], "branch": e["susfs_branch"],
              "version": e["susfs_version"]},
}
if e.get("nomount_sha"):
    # Only when NoMount is built into the kernel (it is then part of the kernel itself).
    data["nomount"] = {"repo": e["NOMOUNT_REPO"], "ref": e["NOMOUNT_REF"], "commit": e["nomount_sha"],
                       "branch": e["NOMOUNT_REF"], "mode": "integrate"}
json.dump(data, open(sys.argv[1], "w"), indent=2)
print(json.dumps(data, indent=2))
EOF
log "Kernel tree ready: $KERNEL_DIR"
