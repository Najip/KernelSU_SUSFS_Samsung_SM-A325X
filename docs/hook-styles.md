# Hook styles

[Back to the README](../README.md)

xxKSU needs to see a few syscalls: `execve`/`execveat` (for `su` and `ksud`), `faccessat` and `newfstatat` (so apps can find `su`), `reboot` (manager and SUSFS commands), and `newfstat`/`read` during boot (to add its lines to `init.rc`). There are three ways to catch them on this non-GKI 4.14 kernel:

| Style | ZIP name ends in | How it works |
|---|---|---|
| `manual` (default) | nothing | The kernel source calls xxKSU directly inside `fs/exec.c`, `fs/open.c`, `fs/stat.c` and `kernel/reboot.c`. Fixed at compile time. |
| `syscall_table` | `-sct` | xxKSU replaces those entries in `sys_call_table` with small wrappers at boot. The `newfstat`/`read` ones are put back once `init.rc` is done. |
| `branch_link` (currently unstable) | `-bl` | Starts like `syscall_table`, then shortly after `init.rc` is handled rewrites the `bl` (call) instructions inside `sys_faccessat`, `sys_newfstatat` and `sys_execve` to jump straight to xxKSU, and removes each table hook that worked. If one cannot be patched, its table hook stays. HMA-oss, SUSFS and BRENE's priority UID filter fail with it; use `manual`. |

For `syscall_table` and `branch_link`, `patches/hooks/0001-hookless-skip-parent-hooks.patch` switches off the kernel's own calls for those syscalls, so nothing runs twice. The security hooks (setuid, rename, setxattr, setprocattr, file permission) stay manual in all three styles, and the SUSFS code is the same in all three (it still fails with `branch_link`, see the table).

The same NoMount module works with all three styles. NoMount does not hook syscalls, and the kernel version string is the same.

## Comparing them

1. Build the kernel once per style (same tuning setting each time), and tick **Build hook benchmark** in one of the runs and download its `hook-bench` artifact.
2. Copy `hook-bench` and `hook-bench.sh` to the same folder on the phone, for example `/sdcard/Download`.
3. Flash one kernel, reboot, wait 2-3 minutes, then in Termux run `sh /sdcard/Download/hook-bench.sh`. With root it also runs the test as root and shows from `dmesg` which style is active (for `branch_link` it shows which patches worked).
4. Repeat for the other styles. Results are saved in `/sdcard/hook-bench/`.

The script times `faccessat` and `newfstatat` on `/system/bin/su` and `/system/bin/sh`, `fstat`, `read`, and `fork + execve`, and prints nanoseconds per call (median and best of 7 rounds). Lower is faster. `fstat` and `read` only act as a baseline, since they are no longer hooked after boot in any style. The differences are expected to be small, so run each test 2-3 times with the phone cool and idle, and compare medians.
