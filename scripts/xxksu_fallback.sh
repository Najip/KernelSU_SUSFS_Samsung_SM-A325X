#!/usr/bin/env bash
# The newest xxKSU did not build (prepare or compile step <step>): prepare the
# sources again with the last good xxKSU (KSU_FALLBACK_REF, its Latest
# release) and record which xxKSU failed in sources.json.
#
#   xxksu_fallback.sh <step>    (exits 1 when there is nothing to fall back to)
#
# Writes KSU_REF, KSU_BRANCH and XXKSU_FALLBACK_* to $GITHUB_ENV so later steps
# (package, kernel kit) use the fallback commit.
set -euo pipefail
step=$1
ROOT=$(cd -- "$(dirname -- "$0")/.." && pwd)
if [[ "${KERNEL_SOURCE:-}" != aigis-xxksu || -z "${KSU_FALLBACK_REF:-}" || -n "${XXKSU_FALLBACK_FROM:-}" ]]; then
  exit 1
fi
failed=$KSU_REF
failed_tag=$(git ls-remote --tags "${KSU_REPO:-https://github.com/Najip/xxKSU}" 2>/dev/null \
  | awk -v c="$failed" '$1 == c { t = $2; sub("refs/tags/", "", t); sub(/\^\{\}$/, "", t); print t; exit }' || true)
echo "::warning title=xxKSU fallback::The newest xxKSU ${failed_tag:-$failed} failed in the $step step. Building with the last good xxKSU ${KSU_FALLBACK_REF:0:12} instead."
export XXKSU_FALLBACK_FROM=$failed XXKSU_FALLBACK_TAG=$failed_tag XXKSU_FALLBACK_STEP=$step
export KSU_REF=$KSU_FALLBACK_REF
# shellcheck disable=SC1091
KSU_BRANCH=$(. "$ROOT/scripts/sources.conf" >/dev/null; echo "${XXKSU_STABLE_REF:-sync-mojito}")
export KSU_BRANCH
if [[ -n "${GITHUB_ENV:-}" ]]; then
  {
    echo "KSU_REF=$KSU_REF"; echo "KSU_BRANCH=$KSU_BRANCH"
    echo "XXKSU_FALLBACK_FROM=$failed"; echo "XXKSU_FALLBACK_TAG=$failed_tag"; echo "XXKSU_FALLBACK_STEP=$step"
  } >> "$GITHUB_ENV"
fi
{
  echo
  echo "===== xxKSU ${failed_tag:-$failed} failed ($step), falling back to $KSU_FALLBACK_REF ====="
} >> "${BUILD_LOG:-/dev/null}"
bash "$ROOT/scripts/prepare_sources.sh" 2>&1 | tee -a "${BUILD_LOG:-/dev/null}"
python3 "$ROOT/scripts/sources_extra.py"
