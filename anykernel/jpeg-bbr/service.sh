#!/system/bin/sh
# A32 JPEG + BBR fix, see post-fs-data.sh. Runs again after boot, because
# the vendor (BBR) and Juan's odm patch (JPEG switch) change them at boot.
set_fix() {
  if [ -c /dev/dma_heap/mtk_mm ]; then
    chmod 0444 /dev/dma_heap/mtk_mm
    setprop debug.jpegfull.opt.switch 1
  else
    setprop debug.jpegfull.opt.switch 0
  fi
  grep -qw bbr /proc/sys/net/ipv4/tcp_available_congestion_control 2>/dev/null \
    && echo bbr > /proc/sys/net/ipv4/tcp_congestion_control
}
set_fix
until [ "$(getprop sys.boot_completed)" = 1 ]; do sleep 2; done
set_fix
