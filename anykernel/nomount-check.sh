
## NoMount check: warns when the installed NoMount LKM module was not built
## for this kernel. It must match the kernel (same kernel ID), not the zip:
## a module from any build of the same kernel is fine.
nomount_check() {
  local want_id=@KERNEL_ID@ want_rel="@KERNEL_RELEASE@" mode=@NOMOUNT_MODE@ d= ko= id= vm=;
  mountpoint -q /data 2>/dev/null || mount /data 2>/dev/null;
  if [ ! -d /data/adb ]; then
    ui_print " " "! /data not mounted or decrypted: NoMount check skipped.";
    return 0;
  fi;
  for d in /data/adb/modules_update/nomount /data/adb/modules/nomount; do
    [ -f $d/module.prop ] && break;
    d=;
  done;
  if [ -z "$d" ]; then
    [ "$mode" = lkm ] && ui_print " " "NoMount module not installed. To use NoMount, install the" "NoMount ZIP built for this kernel (kernel ID $want_id).";
    return 0;
  fi;
  [ -f /data/adb/modules/nomount/remove ] && [ ! -d /data/adb/modules_update/nomount ] && return 0;
  if [ "$mode" = integrate ]; then
    ui_print " " "! WARNING: this kernel has NoMount built in, but the NoMount LKM" "! module is installed too. Remove it in the KernelSU manager.";
    return 0;
  fi;
  for ko in $d/lkm/nomount.ko $d/lkm/nomount-4.14.ko; do
    [ -f $ko ] && break;
    ko=;
  done;
  id=$(sed -n 's/^kernelId=//p' $d/module.prop | head -n1 | tr -d '\r ');
  if [ "$id" = "$want_id" ]; then
    ui_print " " "NoMount module matches this kernel (kernel ID $want_id).";
    return 0;
  fi;
  if [ -z "$id" ] && [ -n "$ko" ]; then
    # Older module without a kernel ID: compare its vermagic.
    vm=$(tr -c '[:print:]' '\n' < $ko | grep -m1 '^vermagic=' | cut -d= -f2-);
    case "$vm" in "$want_rel "*) vm=ok;; esac;
    if [ "$vm" = ok ]; then
      ui_print " " "! NoMount module has no kernel ID (built before this check)." "! Its kernel release matches, but it cannot be verified." "! Install the NoMount ZIP built for this kernel (kernel ID $want_id)" "! to be sure it matches.";
      return 0;
    fi;
  fi;
  ui_print " " "! WARNING: the installed NoMount LKM module does NOT match this kernel" "!   module: kernel ID ${id:-none}${vm:+, vermagic $vm}" "!   kernel: kernel ID $want_id, kernel release $want_rel" "! It may fail to load. Remove it in the KernelSU manager and install" "! the NoMount ZIP built for this kernel (kernel ID $want_id).";
}
nomount_check;
