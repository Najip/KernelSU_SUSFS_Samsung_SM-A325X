
## The mzggr kernel uses the stock A32 GPU (Mali Bifrost r25p0). The Aigis
## Valhall GPU drivers module (a32-gpu-upgrade) does not work with it, so it
## is deleted here.
gpu_cleanup() {
  local m=a32-gpu-upgrade d= found=;
  mountpoint -q /data 2>/dev/null || mount /data 2>/dev/null;
  [ -d /data/adb ] || return 0;
  for d in /data/adb/modules/$m /data/adb/modules_update/$m; do
    if [ -d $d ]; then
      rm -rf $d;
      found=1;
    fi;
  done;
  [ "$found" ] || return 0;
  # Drop GPU shader caches built with the Valhall drivers (app code caches only).
  find /data/user_de /data/data -path '*code_cache*' -name '*shader*' -type f -exec rm -f {} + 2>/dev/null;
  ui_print " " "Removed the Valhall GPU drivers module ($m):" "this kernel uses the stock A32 GPU.";
}
gpu_cleanup;
