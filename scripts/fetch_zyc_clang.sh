#!/usr/bin/env bash
# Downloads ZyC Clang (scripts/zyc_clang14.conf) into <dest> and sets it up the
# way the Aigis CI does: aarch64-linux-gnu-gcc / arm-linux-gnueabi-gcc wrappers
# that run clang for that target (the kernel Makefile then uses them as CC).
set -euo pipefail
ROOT=$(cd -- "$(dirname -- "$0")/.." && pwd)
# shellcheck source=zyc_clang14.conf
. "$ROOT/scripts/zyc_clang14.conf"
dest=${1:?give the toolchain folder}
stamp="ZyC Clang: $ZYC_CLANG_REPO $ZYC_CLANG_RELEASE ($ZYC_CLANG_ASSET)"

if [[ -x "$dest/bin/clang" ]] && grep -qxF "$stamp" "$dest/zyc-source.txt" 2>/dev/null; then
  cat "$dest/zyc-source.txt"
  exit 0
fi
if [[ -e "$dest" && ! -f "$dest/zyc-source.txt" ]]; then
  echo "$dest exists and is not a ZyC Clang folder; not touching it" >&2; exit 1
fi
cache=${ZYC_CLANG_CACHE:-"${XDG_CACHE_HOME:-$HOME/.cache}/zyc-clang"}
mkdir -p "$cache"
archive="$cache/$ZYC_CLANG_ASSET"
if [[ ! -s "$archive" ]]; then
  url="https://github.com/$ZYC_CLANG_REPO/releases/download/$ZYC_CLANG_RELEASE/$ZYC_CLANG_ASSET"
  echo "Downloading $url"
  curl -fL --retry 5 --retry-delay 2 --retry-all-errors -o "$archive.part" "$url"
  mv -f "$archive.part" "$archive"
fi
rm -rf -- "$dest.tmp"
mkdir -p "$dest.tmp"
tar --no-same-owner -xzf "$archive" -C "$dest.tmp"
bin=$(dirname "$(find "$dest.tmp" -path '*/bin/clang' -print -quit)")
[[ -x "$bin/clang" ]] || { echo "No bin/clang in $ZYC_CLANG_ASSET" >&2; exit 1; }
top=$(dirname "$bin")
if [[ "$top" != "$dest.tmp" ]]; then mv "$top" "$dest.tmp.top"; rm -rf -- "$dest.tmp"; mv "$dest.tmp.top" "$dest.tmp"; fi

# Same wrappers as the Aigis CI ("ZyC clang provides clang/ld.lld but some
# scripts expect CROSS_COMPILE gcc wrapper with target").
for p in aarch64-linux-gnu arm-linux-gnueabi; do
  if [[ ! -x "$dest.tmp/bin/$p-gcc" ]]; then
    printf '#!/bin/sh\nexec "%s/bin/clang" --target=%s "$@"\n' "$dest" "$p" > "$dest.tmp/bin/$p-gcc"
    printf '#!/bin/sh\nexec "%s/bin/clang++" --target=%s "$@"\n' "$dest" "$p" > "$dest.tmp/bin/$p-g++"
    chmod +x "$dest.tmp/bin/$p-gcc" "$dest.tmp/bin/$p-g++"
  fi
done
echo "$stamp" > "$dest.tmp/zyc-source.txt"
rm -rf -- "$dest"
mv "$dest.tmp" "$dest"

# ZyC ld.lld links against libxml2.so.2; newer distros only ship .so.16.
# The Aigis CI symlinks it system-wide; here a private folder is enough.
if ldd "$dest/bin/ld.lld" 2>/dev/null | grep -q 'libxml2.so.2 => not found'; then
  newer=$(ls /lib/x86_64-linux-gnu/libxml2.so.* /usr/lib/x86_64-linux-gnu/libxml2.so.* 2>/dev/null | head -n1 || true)
  [[ -n "$newer" ]] || { echo "ld.lld needs libxml2 (install libxml2)" >&2; exit 1; }
  mkdir -p "$dest/compat-lib"
  ln -sfn "$newer" "$dest/compat-lib/libxml2.so.2"
  echo "libxml2.so.2 -> $newer (compat-lib)" >> "$dest/zyc-source.txt"
fi
cat "$dest/zyc-source.txt"
