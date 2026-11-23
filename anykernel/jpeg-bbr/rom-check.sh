#!/system/bin/sh
# A32 JPEG + BBR fix: checks whether the ROM already has each fix itself
# (for example LumiROM after PR #39). Comment lines do not count.
# Sets ROM_JPEG=1 and/or ROM_BBR=1. When the ROM has both, the module is
# not needed: it does nothing and removes itself at the next reboot.
MODDIR=${0%/*}
rom_rc() {
  for f in /odm/etc/init/*.rc /vendor/etc/init/*.rc /odm/ueventd.rc \
           /vendor/ueventd.rc /vendor/etc/ueventd.rc; do
    [ -f "$f" ] && grep -v '^[[:space:]]*#' "$f"
  done 2>/dev/null
}
ROM_JPEG=0; ROM_BBR=0
rc="$(rom_rc)"
echo "$rc" | grep -q 'mtk_mm' && ROM_JPEG=1
echo "$rc" | grep 'tcp_congestion_control' | grep -qw bbr && ROM_BBR=1
if [ $ROM_JPEG = 1 ] && [ $ROM_BBR = 1 ]; then
  touch "$MODDIR/remove"
  sed -i 's/^description=.*/description=Not needed: the ROM already has the JPEG and BBR fixes. This module removes itself at the next reboot./' "$MODDIR/module.prop"
  ROM_DONE=1
else
  ROM_DONE=0
fi
