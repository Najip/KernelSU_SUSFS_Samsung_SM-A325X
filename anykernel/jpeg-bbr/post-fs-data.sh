#!/system/bin/sh
# A32 JPEG + BBR fix.
#
# 1) Blank JPEG photos (Telegram and others) on One UI 9 ports: the vendor
#    turns on ro.vendor.jpeg_decode_sw_opt=1, and One UI 9's libhwui then
#    takes memory from the dma-buf heap /dev/dma_heap/mtk_mm. The Aigis
#    kernel has that heap, and the ROM labels it dmabuf_system_heap_device,
#    but the A32 vendor has no ueventd line for it, so it is root-only
#    (0600) and apps cannot open it. Give it the permissions Android uses for
#    its normal heap (0444 system:system). Tested with tools/mtk-mm-test.sh.
#    Without mtk_mm (other kernels): fall back to Juan's (LumiROM) workaround,
#    debug.jpegfull.opt.switch=0, which turns that path off.
n=/dev/dma_heap/mtk_mm
if [ -c $n ]; then
  chown system:system $n
  chmod 0444 $n
  case "$(ls -Z $n 2>/dev/null)" in
    *dmabuf_system_heap_device*) ;;
    *) chcon u:object_r:dmabuf_system_heap_device:s0 $n 2>/dev/null ;;
  esac
  # Path on (Juan's odm patch, if still flashed, turns it off at boot).
  setprop debug.jpegfull.opt.switch 1
else
  setprop debug.jpegfull.opt.switch 0
fi
# 2) BBR (by Juan, LumiROM): the kernel default. The vendor's
#    networksetting.rc sets bic later, so service.sh sets BBR again.
grep -qw bbr /proc/sys/net/ipv4/tcp_available_congestion_control 2>/dev/null \
  && echo bbr > /proc/sys/net/ipv4/tcp_congestion_control
