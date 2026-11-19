#!/usr/bin/env python3
"""Apply JackA1ltman's SUSFS 4.14 patch to the Samsung A32 kernel tree.

Usage: apply_susfs.py <kernel-dir> <susfs_patch_to_4.14.patch>

The patch applies with fuzz except for one hunk: the header block that goes
at the top of fs/namespace.c (Samsung's file has different includes there).
That hunk is re-created here. Any other failure stops the build.
"""
import pathlib
import subprocess
import sys

NAMESPACE_HEADER = """
#ifdef CONFIG_KSU_SUSFS
#include <linux/susfs_def.h>
#endif // #ifdef CONFIG_KSU_SUSFS

#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT
extern bool susfs_is_current_ksu_domain(void);
extern struct static_key_true susfs_is_sdcard_android_data_not_decrypted;

#define CL_COPY_MNT_NS BIT(25) /* used by copy_mnt_ns() */

#endif // #ifdef CONFIG_KSU_SUSFS_SUS_MOUNT
"""


def main() -> int:
    kernel = pathlib.Path(sys.argv[1]).resolve()
    patch = pathlib.Path(sys.argv[2]).resolve()
    result = subprocess.run(
        ["patch", "-p1", "-F3", "-N", "--no-backup-if-mismatch", "-i", str(patch)],
        cwd=kernel, text=True, capture_output=True)
    print(result.stdout, end="")
    print(result.stderr, end="", file=sys.stderr)

    rejects = sorted(kernel.rglob("*.rej"))
    unexpected = [r for r in rejects if r.relative_to(kernel).as_posix() != "fs/namespace.c.rej"]
    if unexpected:
        print("SUSFS patch failed in: " + ", ".join(str(r.relative_to(kernel)) for r in unexpected),
              file=sys.stderr)
        return 1

    namespace = kernel / "fs/namespace.c"
    text = namespace.read_text()
    rej = kernel / "fs/namespace.c.rej"
    if rej.exists():
        rej_text = rej.read_text()
        hunks = sum(1 for line in rej_text.splitlines() if line.startswith("@@ "))
        if hunks > 1 or "susfs_def.h" not in rej_text:
            print("Unexpected reject in fs/namespace.c:\n" + rej_text, file=sys.stderr)
            return 1
        rej.unlink()
    if "linux/susfs_def.h" not in text:
        anchor = '#include "internal.h"\n'
        if anchor not in text:
            print("Cannot find #include \"internal.h\" in fs/namespace.c", file=sys.stderr)
            return 1
        text = text.replace(anchor, anchor + NAMESPACE_HEADER, 1)
        namespace.write_text(text)
        print("fs/namespace.c: added the SUSFS header block by hand (known Samsung difference).")
    elif result.returncode != 0 and not rejects:
        return result.returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())
