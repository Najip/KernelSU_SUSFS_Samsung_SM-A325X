
## Valhall GPU drivers: installs the KernelSU module a32-gpu-upgrade
## (A32-Mali-Valhall-Drivers-KSU-Module.zip) straight into /data/adb/modules.
valhall_install() {
  local mod=/data/adb/modules/a32-gpu-upgrade;
  ui_print " " "Installing the Valhall GPU drivers module...";
  mountpoint -q /data 2>/dev/null || mount /data 2>/dev/null;
  if [ ! -d /data/adb ]; then
    ui_print "! /data/adb not found (data not mounted or decrypted)." "! Kernel is installed. Install A32-Mali-Valhall-Drivers-KSU-Module.zip from the KernelSU manager.";
    return 0;
  fi;
  if [ -f /data/adb/modules/gpu_driver_mali/module.prop ]; then
    ui_print "! Conflicting module gpu_driver_mali found, drivers module skipped." "! Remove it, then flash this zip again.";
    return 0;
  fi;
  rm -rf $mod /data/adb/modules_update/a32-gpu-upgrade;
  mkdir -p $mod;
  cp -rf $AKHOME/valhall/. $mod/;
  rm -f $mod/customize.sh;
  chown -R 0:0 $mod;
  find $mod -type d -exec chmod 755 {} +;
  find $mod -type f -exec chmod 644 {} +;
  chcon -R u:object_r:system_file:s0 $mod 2>/dev/null;
  chcon -R u:object_r:same_process_hal_file:s0 $mod/system/vendor 2>/dev/null;
  # The module's own GPU shader cache cleanup (limited to app code caches).
  find /data/user_de /data/data -path '*code_cache*' -name '*shader*' -type f -exec rm -f {} + 2>/dev/null;
  ui_print "Valhall GPU drivers module installed ($mod).";
}
valhall_install;
