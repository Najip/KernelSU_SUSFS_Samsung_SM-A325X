#!/system/bin/sh
# Test for blank JPEG photos on One UI 9 ports (LumiROM 9) on the A32 4G.
#
# The kernel has /dev/dma_heap/mtk_mm, but the ROM gives it no permissions
# and no SELinux label, so apps cannot open it. Juan's fix (and our
# "A32 JPEG + BBR fix" module) only turns the new image path off.
# This test gives mtk_mm the permissions and label of Android's normal
# memory heap, turns the new image path back on and restarts Telegram.
# Nothing is saved: a reboot undoes everything.
#
# Run in Termux:   su -c sh /sdcard/Download/mtk-mm-test.sh
# Undo now:        su -c sh /sdcard/Download/mtk-mm-test.sh undo
n=/dev/dma_heap/mtk_mm
rp=resetprop
command -v resetprop >/dev/null 2>&1 || rp=/data/adb/ksu/bin/resetprop

show() {
  echo "== $1"
  ls -lZ /dev/dma_heap/ 2>&1
  echo "debug.jpegfull.opt.switch = '$(getprop debug.jpegfull.opt.switch)'"
  echo "ro.vendor.jpeg_decode_sw_opt = '$(getprop ro.vendor.jpeg_decode_sw_opt)'"
  echo "SELinux: $(getenforce)"
}

if [ "$(id -u)" != 0 ]; then echo "Run it as root: su -c sh $0"; exit 1; fi

if [ "$1" = undo ]; then
  setprop debug.jpegfull.opt.switch 0
  am force-stop org.telegram.messenger 2>/dev/null
  show "after undo (old image path again; reboot also undoes the label)"
  exit 0
fi

show before
[ -e $n ] || { echo "! $n does not exist: the kernel has no mtk_mm heap."; exit 1; }

chown system:system $n
chmod 0444 $n
label=
for t in dmabuf_system_heap_device dmabuf_heap_device; do
  if chcon u:object_r:$t:s0 $n 2>/dev/null; then label=$t; break; fi
done
echo "label set: ${label:-none (no matching SELinux type in this ROM)}"

# New image path back on (the switch only exists when something set it).
$rp --delete debug.jpegfull.opt.switch 2>/dev/null || setprop debug.jpegfull.opt.switch 1
am force-stop org.telegram.messenger 2>/dev/null
show after

echo
echo "Now open Telegram and look at a chat with JPEG photos (wait ~20 s)."
echo "Then press Enter here."
read _
echo "== SELinux denials for dma_heap / mtk_mm"
dmesg 2>/dev/null | grep -iE 'avc.*(dma_heap|mtk_mm)' | tail -n 10
logcat -d -b all 2>/dev/null | grep -iE 'avc.*(dma_heap|mtk_mm)|mtk_mm|dmabufheap' | tail -n 20
echo "== done. Photos OK? Tell me yes or no, and send all of this output."
