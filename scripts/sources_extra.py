#!/usr/bin/env python3
"""Adds what prepare_sources.sh does not know to $INFO_DIR/sources.json:

  build_repo           this repo, branch and commit (in GitHub Actions)
  ksu.fallback_from    XXKSU_FALLBACK_FROM is set: the newest xxKSU commit
                       that did not build (and its release tag); the kernel
                       was built with the last good xxKSU instead. xxKSU reads
                       this to decide whether it can promote its pre-release.
"""
import json
import os
import subprocess

e = os.environ
p = os.path.join(e["INFO_DIR"], "sources.json")
d = json.load(open(p))
if e.get("GITHUB_REPOSITORY"):
    git = lambda *a: subprocess.check_output(["git", *a], text=True).strip()
    d["build_repo"] = {
        "repo": f"{e['GITHUB_SERVER_URL']}/{e['GITHUB_REPOSITORY']}",
        "ref": e["GITHUB_REF_NAME"], "commit": git("rev-parse", "HEAD"),
        "subject": git("show", "-s", "--format=%s", "HEAD"),
    }
if e.get("XXKSU_FALLBACK_FROM"):
    d["ksu"]["fallback_from"] = {"commit": e["XXKSU_FALLBACK_FROM"], "tag": e.get("XXKSU_FALLBACK_TAG", ""),
                                 "step": e.get("XXKSU_FALLBACK_STEP", "")}
json.dump(d, open(p, "w"), indent=2)
