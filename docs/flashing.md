# Flashing and logs

[Back to the README](../README.md)

## How to flash

1. Back up your current `boot` partition.
2. Flash the kernel ZIP with a custom recovery (TWRP / OrangeFox) or an AnyKernel3 flasher app.
3. Reboot, install the xxKSU manager from [backslashxx/KernelSU releases](https://github.com/backslashxx/KernelSU/releases), and install a SUSFS userspace module if you want to configure SUSFS.

The ZIP only replaces the kernel inside `boot` and keeps your ramdisk.

After writing the kernel, the ZIP also checks your modules (when `/data` is mounted and decrypted):

- **NoMount check** (every kernel ZIP): every kernel has a **kernel ID** (in `build-info.txt`, line "Kernel ID (NoMount match)"), made from its kernel release, `.config` and symbol checksums. A NoMount module stores the ID of the kernel it was built for (`kernelId=` in its `module.prop`, also shown in its description). A module from any build of the same kernel has the same ID, so it does not have to come from the same run. Every `lkm` kernel ZIP also carries the NoMount module built for it (folder `nomount/`); the separate NoMount ZIP and `.ko` are still in CI and every release.
  - **Flashed in TWRP:** a NoMount module with a different ID is deleted (older modules without an ID too). When no NoMount module is installed (or it was just deleted), the one in the ZIP is installed into `/data/adb/modules/nomount` and set as the metamodule. It is skipped when another metamodule is installed (only one can be active) or when you marked NoMount for removal in the manager. `/data` must be decrypted.
  - **Flashed in Android** (BakaSU/KernelSU manager, kernel flasher apps): the running module cannot be swapped, so the ZIP stages the one it carries, the same way the manager installs modules: the files go to `/data/adb/modules_update/nomount`, and `modules/nomount` gets the new `module.prop` and an `update` marker. At the next boot the root manager (ksud) deletes the old module and moves the new one in, before any module runs. A module you disabled stays disabled. The same metamodule and marked-for-removal rules apply.
  - With NoMount `integrate`, an installed NoMount LKM module gets a warning to remove it; nothing is installed or deleted.
- **GPU module cleanup** (mzggr ZIP only): the mzggr kernel uses the stock A32 GPU, so the Aigis Valhall GPU drivers module (`a32-gpu-upgrade`) is deleted if it is installed.

## Collecting logs

`tools/collect-logs.sh` gathers everything needed to debug a bootloop or a root problem. It runs both in TWRP and in booted Android (as root).

1. Download it to the phone: [collect-logs.sh](https://raw.githubusercontent.com/Najip/KernelSU_SUSFS_Samsung_SM-A325X/main/tools/collect-logs.sh) (long-press, "Download link"). It lands in `/sdcard/Download/`.
2. Run it:
   - TWRP: Advanced > Terminal, then `sh /sdcard/Download/collect-logs.sh`
   - Termux: `su -c sh /sdcard/Download/collect-logs.sh`
3. Logs are saved to `/sdcard/kernel-logs/<date-time>-twrp` (or `-android`), plus a `.tar.gz` of the same folder. Start with `summary.txt`: it shows which root (xxKSU or BakaSU) and SUSFS version the kernel reports, whether NoMount is loaded, the installed modules and manager apps, and the root/SUSFS/NoMount kernel messages. Send the `.tar.gz`, or `summary.txt` if it is too big.

After a bootloop, go straight to TWRP (Volume Down + Power, then Volume Up + Power, without powering off) so the crash log of the failed boot is still in memory. If `/sdcard` is not writable in TWRP, the script falls back to the SD card or `/data/local/tmp`.

For a failed build on GitHub (not the phone), see [Build log too long](building.md#build-log-too-long).
