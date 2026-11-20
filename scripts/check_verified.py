#!/usr/bin/env python3
"""Check that the kernels of a release were built from the Verified commits.

  check_verified.py <configs/verified.json> <sources.json>...

Each sources.json is matched to its pins by its kernel repo: the "aigis" entry
for the Aigis kernel, the top-level entries for mzggr. Fails when a commit
differs, so only a build of the Verified commits can become a full Release.
"""
import json
import sys


def main(verified_path, *paths):
    verified = json.load(open(verified_path))
    aigis = verified.get("aigis") or {}
    bad = []
    for path in paths:
        src = json.load(open(path))
        repo = (src.get("kernel") or {}).get("repo", "").rstrip("/")
        pins = aigis if aigis and repo == aigis["kernel"]["repo"].rstrip("/") else verified
        name = "Aigis" if pins is aigis else "mzggr"
        for key in ("kernel", "xxksu", "susfs"):
            want = (pins.get(key) or {}).get("commit", "")
            have = (src.get(key) or {}).get("commit", "")
            if not want or want != have:
                bad.append(f"{name} {key}: built {have[:12] or 'none'}, Verified {want[:12] or 'none'}")
            else:
                print(f"{name} {key}: {have[:12]} = Verified")
    if bad:
        print("::error::Release must use Verified. This pre-release was not built from the Verified commits: "
              + "; ".join(bad), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    main(*sys.argv[1:])
