# Flashing and logs

[Back to the README](../README.md)

## How to flash

1. Back up your current `boot` partition.
2. Flash **one** kernel ZIP (`A325X-Aigis-BakaSU-...zip` or `A325X-Aigis-xxKSU-...zip`) with a custom recovery (TWRP / OrangeFox) or an AnyKernel3 flasher app.
3. Reboot, install the manager app of that flavor from the same release page (`BakaSU_...apk` for BakaSU, `KernelSU_...apk` for xxKSU; uninstall the other one), and install the modules below if you want them.

The ZIP only replaces the kernel inside `boot` and keeps your ramdisk.

Recommended modules:

- [BRENE](https://github.com/rrr333nnn333/BRENE): the SUSFS userspace module I recommend. It keeps up with simonpunk's SUSFS.
- [HMA-OSS](https://github.com/frknkrc44/HMA-OSS): needed for BRENE's app hiding. BRENE's "Hide third party apps" (on by default) and "Hide all apps with uid >= 10000" options give the kernel the list of apps through the SUSFS priority UID filter (`susfs set_priority_uid_filter`); HMA-OSS does the userspace side, as BRENE notes next to those options.
- BakaSU flavor: its built-in SUSFS settings work on their own, but turn them off when you use BRENE so the two do not conflict.
- Not recommended: sidex15's susfs4ksu-module. It is not updated often and does not work with the latest SUSFS (simonpunk's or JackA1ltman's 4.14 port). Installing BRENE disables it (and susfs_manager, ReSuSFS); better remove it.

After writing the kernel, the ZIP also checks your modules (when `/data` is mounted and decrypted):

- **JPEG + BBR fix** (every kernel ZIP): installs the root module `a32-jpeg-bbr` into `/data/adb/modules`. One UI 9 ports turn on a vendor JPEG path (`ro.vendor.jpeg_decode_sw_opt=1`) that takes memory from the dma-buf heap `/dev/dma_heap/mtk_mm`. The Aigis kernel has that heap and the ROM labels it for SELinux (`dmabuf_system_heap_device`), but the A32 vendor has no permission line for it, so it stays root-only (`0600`) and photos show up blank (Telegram and others). The module gives it the permissions of Android's normal heap (`0444`, owner `system`) at every boot and keeps that path on. With a kernel without `mtk_mm` it falls back to Juan's (LumiROM) workaround, `debug.jpegfull.opt.switch=0`, which turns the path off. It also sets TCP back to BBR (the kernel default) after the vendor sets it to bic (also Juan's fix). Juan's odm zip `odm-9.0.0-JPEG-BBR-PARCHE_A325F` is not needed; the module overrides it. `tools/mtk-mm-test.sh` is the one-time test (no reboot) that found the fix. At every boot it first checks the ROM's own init/ueventd files: a part the ROM already does (an `mtk_mm` permission line, or setting BBR) is skipped, and when the ROM does both (for example LumiROM after my PR #39) the module does nothing and removes itself at the next reboot. Remove the module in the manager if you do not want it.

- **NoMount check** (every kernel ZIP): every kernel has a **kernel ID** (in `build-info.txt`, line "Kernel ID (NoMount match)"), made from its kernel release, `.config` and symbol checksums. A NoMount module stores the ID of the kernel it was built for (`kernelId=` in its `module.prop`, also shown in its description). A module from any build of the same kernel has the same ID, so it does not have to come from the same run. Every `lkm` kernel ZIP also carries the NoMount module built for it (folder `nomount/`); the separate NoMount ZIP and `.ko` are still in CI and every release.
  - **Flashed in TWRP:** a NoMount module with a different ID is deleted (older modules without an ID too). When no NoMount module is installed (or it was just deleted), the one in the ZIP is installed into `/data/adb/modules/nomount` and set as the metamodule. It is skipped when another metamodule is installed (only one can be active) or when you marked NoMount for removal in the manager. `/data` must be decrypted.
  - **Flashed in Android** (BakaSU/xxKSU manager, kernel flasher apps): the running module cannot be swapped, so the ZIP stages the one it carries, the same way the manager installs modules: the files go to `/data/adb/modules_update/nomount`, and `modules/nomount` gets the new `module.prop` and an `update` marker. At the next boot the root manager (ksud) deletes the old module and moves the new one in, before any module runs. A module you disabled stays disabled. The same metamodule and marked-for-removal rules apply.
  - With NoMount `integrate`, an installed NoMount LKM module gets a warning to remove it; nothing is installed or deleted.

## Collecting logs

`tools/collect-logs.sh` gathers everything needed to debug a bootloop or a root problem. It runs both in TWRP and in booted Android (as root).

1. Download it to the phone: [collect-logs.sh](https://raw.githubusercontent.com/Najip/KernelSU_SUSFS_Samsung_SM-A325X/main/tools/collect-logs.sh) (long-press, "Download link"). It lands in `/sdcard/Download/`.
2. Run it:
   - TWRP: Advanced > Terminal, then `sh /sdcard/Download/collect-logs.sh`
   - Termux: `su -c sh /sdcard/Download/collect-logs.sh`
3. Logs are saved to `/sdcard/kernel-logs/<date-time>-twrp` (or `-android`), plus a `.tar.gz` of the same folder. Start with `summary.txt`: it shows which root (BakaSU or xxKSU) and SUSFS version the kernel reports, whether NoMount is loaded, the installed modules and manager apps, and the root/SUSFS/NoMount kernel messages. Send the `.tar.gz`, or `summary.txt` if it is too big.

After a bootloop, go straight to TWRP (Volume Down + Power, then Volume Up + Power, without powering off) so the crash log of the failed boot is still in memory. If `/sdcard` is not writable in TWRP, the script falls back to the SD card or `/data/local/tmp`.

For a failed build on GitHub (not the phone), see [Build log too long](building.md#build-log-too-long).
