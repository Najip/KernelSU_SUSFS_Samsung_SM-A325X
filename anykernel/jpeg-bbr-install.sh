
## A32 JPEG + BBR fix (BBR and first JPEG fix by Juan, LumiROM): installs the small root module
## a32-jpeg-bbr (folder jpeg-bbr/ of this zip) straight into /data/adb/modules.
## Fixes blank JPEG photos on One UI 9 ports (apps get access to mtk_mm) and keeps TCP on BBR.
jpeg_bbr_install() {
  local mod=/data/adb/modules/a32-jpeg-bbr;
  ui_print " " "Installing the JPEG + BBR fix module...";
  mountpoint -q /data 2>/dev/null || mount /data 2>/dev/null;
  if [ ! -d /data/adb ]; then
    ui_print "! /data/adb not found (data not mounted or decrypted)." "! Kernel is installed, the JPEG + BBR fix module is not.";
    return 0;
  fi;
  rm -rf $mod /data/adb/modules_update/a32-jpeg-bbr;
  mkdir -p $mod;
  cp -rf $AKHOME/jpeg-bbr/. $mod/;
  chown -R 0:0 $mod;
  chmod 755 $mod;
  chmod 644 $mod/module.prop;
  chmod 755 $mod/post-fs-data.sh $mod/service.sh $mod/rom-check.sh;
  chcon -R u:object_r:system_file:s0 $mod 2>/dev/null;
  ui_print "JPEG + BBR fix module installed ($mod).";
}
jpeg_bbr_install;
