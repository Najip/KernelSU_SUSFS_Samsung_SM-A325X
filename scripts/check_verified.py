#!/usr/bin/env python3
"""Compare the kernels of a release with the Verified commits.

  check_verified.py [--report] <configs/verified.json> <sources.json>...

--report: only tell (log and run summary), never fail. Used by
"Release from pre-release", which may publish any pre-release.

Each sources.json is matched to its pins by its "source" field (older builds:
kernel repo): the "aigis" entry for Aigis, "aigis-bakasu" for Aigis BakaSU,
the top-level entries for mzggr. Fails when a commit
differs (without --report).
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from resolve_commits import NESTED, kernel_of, load_sources  # noqa: E402


def main(verified_path, *paths, report=False):
    verified = json.load(open(verified_path))
    bad = []
    for path in paths:
        src = load_sources(path)
        source = kernel_of(src)
        pins = verified.get(source) or {} if source in NESTED else verified
        name = NESTED.get(source, "mzggr")
        for key in ("kernel", "ksu", "susfs"):
            want = (pins.get(key) or {}).get("commit", "")
            have = (src.get(key) or {}).get("commit", "")
            if not want or want != have:
                bad.append(f"{name} {key}: built {have[:12] or 'none'}, Verified {want[:12] or 'none'}")
            else:
                print(f"{name} {key}: {have[:12]} = Verified")
    if report:
        line = ("Built from the Verified commits." if not bad
                else "Not built from the Verified commits (fine for Release from pre-release): " + "; ".join(bad))
        print(line)
        summary = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary:
            with open(summary, "a") as f:
                f.write(f"Verified check: {line}\n\n")
        return
    if bad:
        print("::error::Release must use Verified. This build was not made from the Verified commits: "
              + "; ".join(bad), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    args = sys.argv[1:]
    report = bool(args) and args[0] == "--report"
    if report:
        args = args[1:]
    if len(args) < 2:
        sys.exit(__doc__)
    main(*args, report=report)
