#!/system/bin/sh
# Kernel log collector for the A32 (SM-A325F/M/N/X).
#
# Works from:
#   - TWRP:   Advanced > Terminal, then:  sh /sdcard/Download/collect-logs.sh
#   - Termux: su -c sh /sdcard/Download/collect-logs.sh
#
# Output: /sdcard/kernel-logs/<date-time>-<twrp|android>/ plus a .tar.gz of it.
# Best moment to run it in TWRP: right after a bootloop, entered with
# Volume Down + Power, then Volume Up + Power (no full power-off), so the
# crash log of the failed boot is still in memory.

export PATH="/system/bin:/system/xbin:/sbin:/vendor/bin:/bin:$PATH"

if [ "$(id -u 2>/dev/null)" != "0" ]; then
  echo "Run this as root (TWRP terminal, or 'su -c sh $0' in Termux)."
  exit 1
fi

# Where are we?
MODE=android
if [ -f /tmp/recovery.log ] || [ -n "$(getprop ro.twrp.version 2>/dev/null)" ] || [ -d /twres ]; then
  MODE=twrp
fi

STAMP=$(date +%y%m%d%H%M%S 2>/dev/null || echo now)

# Pick a writable place: internal storage first, then the SD card, then /data.
OUT=
for base in /sdcard /storage/emulated/0 /data/media/0 /external_sd /sdcard1 /data/local/tmp; do
  [ -d "$base" ] || continue
  dir="$base/kernel-logs/$STAMP-$MODE"
  if mkdir -p "$dir" 2>/dev/null && touch "$dir/.test" 2>/dev/null; then
    rm -f "$dir/.test"
    OUT=$dir
    break
  fi
done
if [ -z "$OUT" ]; then
  echo "No writable storage found. In TWRP, decrypt data or insert an SD card."
  exit 1
fi

echo "Mode: $MODE"
echo "Saving logs to: $OUT"

# save <file name> <command...>: run a command, keep its output if not empty.
save() {
  name=$1
  shift
  command -v "$1" >/dev/null 2>&1 || [ -x "$1" ] || return 0
  "$@" > "$OUT/$name" 2>&1
  if [ ! -s "$OUT/$name" ]; then
    rm -f "$OUT/$name"
  else
    echo "  saved $name"
  fi
}

# copy <source> <file name>: copy a file if it exists and is not empty.
copy() {
  [ -r "$1" ] || return 0
  cat "$1" > "$OUT/$2" 2>/dev/null
  if [ -s "$OUT/$2" ]; then echo "  saved $2"; else rm -f "$OUT/$2"; fi
}

# Crash logs from the previous boot (the important part).
mkdir -p "$OUT/pstore"
for f in /sys/fs/pstore/*; do
  [ -f "$f" ] && cat "$f" > "$OUT/pstore/$(basename "$f")" 2>/dev/null && echo "  saved pstore/$(basename "$f")"
done
rmdir "$OUT/pstore" 2>/dev/null
save pstore-list.txt ls -la /sys/fs/pstore
copy /proc/last_kmsg last_kmsg.txt

# Current kernel log and basic info.
save dmesg.txt dmesg
save kernel-version.txt cat /proc/version
save uname.txt uname -a
save cmdline.txt cat /proc/cmdline
save filesystems.txt cat /proc/filesystems
save mounts.txt cat /proc/mounts
save partitions.txt ls -la /dev/block/by-name /dev/block/platform/bootdevice/by-name
if [ -r /proc/config.gz ]; then
  cat /proc/config.gz > "$OUT/kernel-config.gz" 2>/dev/null && echo "  saved kernel-config.gz"
fi
save getprop.txt getprop

if [ "$MODE" = twrp ]; then
  copy /tmp/recovery.log recovery.log
else
  # Booted Android: logcat, root and SUSFS state.
  save logcat.txt logcat -d -b all
  save logcat-crash.txt logcat -d -b crash
  save selinux.txt getenforce
  save ksu-files.txt ls -la /data/adb /data/adb/ksu /data/adb/modules
  for ksud in /data/adb/ksud /data/adb/ksu/bin/ksud; do
    if [ -x "$ksud" ]; then
      save ksud-version.txt "$ksud" -V
      save ksud-debug.txt "$ksud" debug version
      break
    fi
  done
  save susfs-dmesg.txt sh -c 'dmesg | grep -iE "susfs|kernelsu|ksu"'
  copy /data/adb/ksu/log ksu-log.txt
fi

# Summary of what usually matters most.
{
  echo "Collected: $STAMP ($MODE)"
  echo "Kernel now running: $(cat /proc/version 2>/dev/null)"
  echo "ROM: $(getprop ro.build.display.id 2>/dev/null)"
  echo "Model: $(getprop ro.product.model 2>/dev/null) / bootloader $(getprop ro.boot.bootloader 2>/dev/null)"
  echo
  echo "== Previous boot: kernel version"
  cat "$OUT"/pstore/console-ramoops* "$OUT/last_kmsg.txt" 2>/dev/null | grep -a -m 2 "Linux version"
  echo
  echo "== Previous boot: errors (first 60)"
  cat "$OUT"/pstore/console-ramoops* "$OUT/last_kmsg.txt" 2>/dev/null \
    | grep -a -iE "Kernel panic|Unable to handle|Internal error|BUG:|Oops|Failed to mount|InitFatalReboot|init: .*(fatal|failed)|No such device|reboot" \
    | grep -a -v "libfs_mgr\]0x" | head -n 60
} > "$OUT/summary.txt" 2>/dev/null
echo "  saved summary.txt"

# One archive that is easy to send.
cd "$(dirname "$OUT")" && tar -czf "$OUT.tar.gz" "$(basename "$OUT")" 2>/dev/null \
  && echo "Archive: $OUT.tar.gz"

echo "Done. Send me the folder or the .tar.gz file."
