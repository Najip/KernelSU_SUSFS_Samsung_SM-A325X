#!/system/bin/sh
# A32 JPEG + BBR fix (by Juan, LumiROM), see post-fs-data.sh.
set_fix() {
  setprop debug.jpegfull.opt.switch 0
  grep -qw bbr /proc/sys/net/ipv4/tcp_available_congestion_control 2>/dev/null \
    && echo bbr > /proc/sys/net/ipv4/tcp_congestion_control
}
set_fix
until [ "$(getprop sys.boot_completed)" = 1 ]; do sleep 2; done
set_fix
