#!/system/bin/sh
# Compare xxKSU hook styles (manual / syscall_table / branch_link) on the phone.
#
# 1. Put hook-bench and hook-bench.sh in the same folder (for example
#    /sdcard/Download), from the "hook-bench" artifact of any kernel build.
# 2. In Termux:   sh /sdcard/Download/hook-bench.sh
#    (no su needed; with root it also runs the test as root and reads dmesg)
# 3. The result is printed and saved in /sdcard/hook-bench/.
# Flash another hook style, reboot, let the phone settle for 2-3 minutes,
# and run it again. Compare the "median" numbers: lower is faster.
LOOPS=${1:-200000}
here=$(cd "$(dirname "$0")" 2>/dev/null && pwd)
src="$here/hook-bench"
[ -f "$src" ] || { echo "hook-bench binary not found next to this script ($src)"; exit 1; }

# /sdcard does not allow running programs, so copy it somewhere that does.
for dir in "$HOME" /data/local/tmp "${TMPDIR:-/tmp}"; do
  [ -n "$dir" ] && [ -d "$dir" ] && [ -w "$dir" ] || continue
  if cp "$src" "$dir/hook-bench" 2>/dev/null && chmod 755 "$dir/hook-bench" && "$dir/hook-bench" 1000 >/dev/null 2>&1; then
    bin="$dir/hook-bench"; break
  fi
done
[ -n "$bin" ] || { echo "Could not find a folder where hook-bench can run"; exit 1; }

outdir=/sdcard/hook-bench
mkdir -p "$outdir" 2>/dev/null || outdir=$here
kernel=$(uname -r)
out="$outdir/$(date +%y%m%d%H%M%S)-hook-bench.txt"

has_root=no
if command -v su >/dev/null 2>&1 && su -c true >/dev/null 2>&1; then has_root=yes; fi

{
  echo "Kernel: $kernel"
  echo "Built:  $(uname -v)"
  echo "Date:   $(date)"
  if [ "$has_root" = yes ]; then
    mode=$(su -c 'dmesg' 2>/dev/null | grep -m1 'Initialized on:' | sed 's/.*Initialized on: //')
    echo "xxKSU:  ${mode:-unknown (dmesg already rotated)}"
    case "$mode" in
      *arm64_branch_link*) echo "Hook style: branch_link" ;;
      *syscall_table_hook*) echo "Hook style: syscall_table" ;;
      ?*) echo "Hook style: manual" ;;
    esac
    su -c 'dmesg' 2>/dev/null | grep -E 'branch_link: done|hook_site:|patch_hook:' | sed 's/^/  /'
  fi
  echo "Uptime: $(cut -d' ' -f1 /proc/uptime) s"
  echo
  echo "== As this app (normal app path, what every app pays)"
  "$bin" "$LOOPS"
  if [ "$has_root" = yes ]; then
    echo
    echo "== As root (su)"
    su -c "$bin $LOOPS" 2>&1
  fi
} 2>&1 | tee "$out"
echo
echo "Saved: $out"
