#!/usr/bin/env python3
"""Copy the dtb section out of an Android boot image (header v2).

    bootimg_dtb.py <boot.img> <out-dtb>
"""
import struct
import sys

src, dst = sys.argv[1:3]
data = open(src, "rb").read()
if data[:8] != b"ANDROID!":
    sys.exit(f"{src}: not an Android boot image")
ksz, _, rsz, _, ssz, _, _, page, hver = struct.unpack_from("<9I", data, 8)
if hver != 2:
    sys.exit(f"{src}: boot header v{hver}, only v2 has a dtb section here")
rec_dtbo_size, _, _ = struct.unpack_from("<IQI", data, 1632)
dtb_size, _ = struct.unpack_from("<IQ", data, 1648)
pad = lambda n: (n + page - 1) // page * page
off = page + pad(ksz) + pad(rsz) + pad(ssz) + pad(rec_dtbo_size)
dtb = data[off:off + dtb_size]
if not dtb_size or dtb[:4] not in (bytes.fromhex("d7b7ab1e"), bytes.fromhex("d00dfeed")):
    sys.exit(f"{src}: no dtb table / FDT found in the dtb section")
open(dst, "wb").write(dtb)
print(f"dtb: {dtb_size} bytes (magic {dtb[:4].hex()})")
