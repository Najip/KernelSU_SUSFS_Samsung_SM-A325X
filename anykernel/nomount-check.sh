
## NoMount check. The installed NoMount LKM module must match the kernel
## (same kernel ID), not the zip: a module from any build of the same kernel
## is fine.
##  - Flashed in TWRP (recovery): a NoMount module that does not match this
##    kernel is deleted, and when no NoMount module is installed, the one in
##    this zip (folder nomount/, built for this kernel) is installed.
##  - Flashed in Android (KernelSU/BakaSU manager, kernel flasher apps): only
##    warnings, nothing is changed (Android is running and using the module).
##  - Kernels with NoMount built in (integrate): only warnings.
nm_in_recovery() {
  [ "$BOOTMODE" = true ] && return 1;
  ps 2>/dev/null | grep zygote | grep -v grep >/dev/null && return 1;
  ps -A 2>/dev/null | grep zygote | grep -v grep >/dev/null && return 1;
  return 0;
}

nm_delete() {
  local t;
  rm -rf /data/adb/modules/nomount /data/adb/modules_update/nomount;
  t=$(readlink /data/adb/metamodule 2>/dev/null);
  case "$t" in */nomount|*/nomount/) rm -f /data/adb/metamodule;; esac;
  for t in /data/adb/ksu/bin/nm /data/adb/ap/bin/nm; do
    [ -L $t ] && rm -f $t;
  done;
}

nm_install() {
  local want_id=$1 src=$AKHOME/nomount mod=/data/adb/modules/nomount p= t= id= f=;
  [ -f $src/module.prop ] || return 1;
  id=$(sed -n 's/^kernelId=//p' $src/module.prop | head -n1 | tr -d '\r ');
  if [ "$id" != "$want_id" ]; then
    ui_print "! NoMount module in this zip is for kernel ID ${id:-none}, not $want_id: not installed.";
    return 1;
  fi;
  # Only one metamodule can be active.
  for p in /data/adb/modules/*/module.prop /data/adb/modules_update/*/module.prop; do
    [ -f "$p" ] || continue;
    case "$p" in */nomount/module.prop) continue;; esac;
    [ -f "${p%/module.prop}/remove" ] && continue;
    if grep -qiE '^metamodule=(1|true)' "$p"; then
      t=${p%/module.prop};
      ui_print "! Another metamodule is installed (${t##*/}): NoMount not installed." "! Remove it in the manager, then flash this zip again in TWRP.";
      return 1;
    fi;
  done;
  ui_print "Installing the NoMount module built for this kernel...";
  rm -rf $mod /data/adb/modules_update/nomount;
  mkdir -p $mod;
  cp -rf $src/. $mod/;
  # What the module's own installer does (it needs a running Android).
  mv -f $mod/bin/nm-arm64 $mod/bin/nm;
  mv -f $mod/bin/lkmloader-arm64 $mod/lkm/lkmloader;
  rm -f $mod/bin/nm-* $mod/bin/lkmloader-*;
  for f in $mod/lkm/nomount-*.ko; do
    [ -f "$f" ] && mv -f "$f" $mod/lkm/nomount.ko && break;
  done;
  rm -f $mod/customize.sh;
  if [ ! -f $mod/bin/nm ] || [ ! -f $mod/lkm/lkmloader ] || [ ! -f $mod/lkm/nomount.ko ]; then
    ui_print "! NoMount module files missing in this zip: not installed.";
    rm -rf $mod;
    return 1;
  fi;
  chown -R 0:0 $mod;
  find $mod -type d -exec chmod 755 {} +;
  find $mod -type f -exec chmod 644 {} +;
  chmod 755 $mod/bin/nm $mod/lkm/lkmloader $mod/*.sh;
  chcon -R u:object_r:system_file:s0 $mod 2>/dev/null;
  rm -f /data/adb/metamodule;
  ln -s /data/adb/modules/nomount /data/adb/metamodule;
  mkdir -p /data/adb/nomount;
  rm -f /data/adb/nomount/.booting;
  mkdir -p /data/adb/ksu/bin;
  ln -sf /data/adb/modules/nomount/bin/nm /data/adb/ksu/bin/nm;
  ui_print "NoMount module installed ($mod, kernel ID $want_id).";
  return 0;
}

nomount_check() {
  local want_id=@KERNEL_ID@ want_rel="@KERNEL_RELEASE@" mode=@NOMOUNT_MODE@ d= ko= id= vm= ok= rec=false;
  nm_in_recovery && rec=true;
  mountpoint -q /data 2>/dev/null || mount /data 2>/dev/null;
  if [ ! -d /data/adb ]; then
    ui_print " " "! /data not mounted or decrypted: NoMount check skipped.";
    return 0;
  fi;
  ui_print " ";
  for d in /data/adb/modules_update/nomount /data/adb/modules/nomount; do
    [ -f $d/module.prop ] && break;
    d=;
  done;
  if [ "$mode" = integrate ]; then
    [ -n "$d" ] && [ ! -f /data/adb/modules/nomount/remove -o -d /data/adb/modules_update/nomount ] && \
      ui_print "! WARNING: this kernel has NoMount built in, but the NoMount LKM" "! module is installed too. Remove it in the KernelSU manager.";
    return 0;
  fi;
  [ "$mode" = lkm ] || return 0;
  # Marked for removal in the manager: leave it, and do not install one.
  if [ -n "$d" ] && [ -f /data/adb/modules/nomount/remove ] && [ ! -d /data/adb/modules_update/nomount ]; then
    ui_print "NoMount module is marked for removal: left as it is.";
    return 0;
  fi;
  if [ -n "$d" ]; then
    for ko in $d/lkm/nomount.ko $d/lkm/nomount-4.14.ko; do
      [ -f $ko ] && break;
      ko=;
    done;
    id=$(sed -n 's/^kernelId=//p' $d/module.prop | head -n1 | tr -d '\r ');
    if [ "$id" = "$want_id" ]; then
      ui_print "NoMount module matches this kernel (kernel ID $want_id).";
      return 0;
    fi;
    if [ -z "$id" ] && [ -n "$ko" ]; then
      # Older module without a kernel ID: compare its vermagic.
      vm=$(tr -c '[:print:]' '\n' < $ko | grep -m1 '^vermagic=' | cut -d= -f2-);
      case "$vm" in "$want_rel "*) ok=1;; esac;
    fi;
    if $rec; then
      # TWRP: replace it with the module built for this kernel, if this zip has one.
      if [ -n "$ok" ] && [ ! -f $AKHOME/nomount/module.prop ]; then
        ui_print "! NoMount module has no kernel ID, but its kernel release matches: kept.";
        return 0;
      fi;
      ui_print "! NoMount module does not match this kernel (kernel ID ${id:-none}${vm:+, vermagic $vm}): deleted.";
      nm_delete;
      d=;
    else
      if [ -n "$ok" ]; then
        ui_print "! NoMount module has no kernel ID (built before this check)." "! Its kernel release matches, but it cannot be verified." "! Flash this zip in TWRP to replace it with the module built for this kernel.";
      else
        ui_print "! WARNING: the installed NoMount LKM module does NOT match this kernel" "!   module: kernel ID ${id:-none}${vm:+, vermagic $vm}" "!   kernel: kernel ID $want_id, kernel release $want_rel" "! It may fail to load. Flash this zip in TWRP to replace it, or remove" "! it in the manager and install the NoMount ZIP built for this kernel.";
      fi;
      return 0;
    fi;
  fi;
  # No NoMount module installed (or just deleted).
  if $rec && [ -f $AKHOME/nomount/module.prop ]; then
    nm_install "$want_id" && return 0;
  fi;
  if [ -f $AKHOME/nomount/module.prop ]; then
    ui_print "NoMount module not installed. Flash this zip in TWRP to install the" "NoMount module it carries, or install the NoMount ZIP built for this" "kernel (kernel ID $want_id) in the manager.";
  else
    ui_print "NoMount module not installed. To use NoMount, install the" "NoMount ZIP built for this kernel (kernel ID $want_id).";
  fi;
}
nomount_check;
