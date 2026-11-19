#!/usr/bin/env python3
"""Choose the runner for a build job: the self-hosted PC or a GitHub runner.

Used by the "Pick runner" job of both workflows. Prints `runner=<label>` to
$GITHUB_OUTPUT.

  WANT_SELF_HOSTED  "true" if the "Build on my own PC" box was ticked
  GH_TOKEN          token with actions:read
  GITHUB_REPOSITORY, GITHUB_RUN_ID  set by GitHub Actions

Rules:
- Box unticked: GitHub runner.
- Box ticked and the PC is idle: the PC.
- Box ticked and the PC is busy (a job is running or queued on it, from any
  branch or workflow of this repo): wait for the PC only if that is expected to
  finish sooner than a GitHub runner, otherwise use a GitHub runner.
  Expected times are the average durations of recent successful build jobs on
  each runner type.
"""
import datetime as dt
import json
import os
import sys
import time
import urllib.request

API = "https://api.github.com/"
REPO = os.environ["GITHUB_REPOSITORY"]
RUN_ID = int(os.environ["GITHUB_RUN_ID"])
SELF, GH = "self-hosted", "ubuntu-latest"
DEFAULT_MIN = {SELF: 10.0, GH: 12.0}   # used until there is build history


def api(path):
    req = urllib.request.Request(API + path, headers={"Accept": "application/vnd.github+json"})
    req.add_header("Authorization", "Bearer " + os.environ["GH_TOKEN"])
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def ts(value):
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None


def kind(job):
    return SELF if "self-hosted" in (job.get("labels") or []) else GH


def is_build(job):
    return not job["name"].startswith("Pick runner") and not job["name"].startswith("Publish")


def jobs_of(run_id):
    return api(f"repos/{REPO}/actions/runs/{run_id}/jobs?per_page=50").get("jobs", [])


def averages():
    """Average minutes of recent successful build jobs per runner type."""
    samples = {SELF: [], GH: []}
    runs = api(f"repos/{REPO}/actions/runs?status=success&per_page=30").get("workflow_runs", [])
    for run in runs:
        for job in jobs_of(run["id"]):
            if is_build(job) and job["conclusion"] == "success" and job["started_at"] and job["completed_at"]:
                minutes = (ts(job["completed_at"]) - ts(job["started_at"])).total_seconds() / 60
                samples[kind(job)].append(minutes)
    return {k: (sum(v[:10]) / len(v[:10]) if v else DEFAULT_MIN[k]) for k, v in samples.items()}


def busy_self_hosted_jobs():
    """Jobs of other runs that are running or queued on the PC.

    Runs created before this one that have not created their build job yet
    (still picking) are waited for briefly so two runs started together do not
    both choose the idle PC.
    """
    me = api(f"repos/{REPO}/actions/runs/{RUN_ID}")
    my_created = ts(me["created_at"])
    for _ in range(12):
        busy, undecided = [], False
        for status in ("in_progress", "queued"):
            for run in api(f"repos/{REPO}/actions/runs?status={status}&per_page=50").get("workflow_runs", []):
                if run["id"] == RUN_ID:
                    continue
                jobs = jobs_of(run["id"])
                builds = [j for j in jobs if is_build(j)]
                if not builds and ts(run["created_at"]) <= my_created:
                    undecided = True
                busy += [j for j in builds if j["status"] in ("queued", "in_progress", "waiting")
                         and kind(j) == SELF]
        if not undecided:
            return busy
        time.sleep(5)
    return busy


def main():
    want = os.environ.get("WANT_SELF_HOSTED", "false") == "true"
    choice, why = GH, "the 'Build on my own PC' box is unticked"
    if want:
        busy = busy_self_hosted_jobs()
        if not busy:
            choice, why = SELF, "the PC is idle"
        else:
            avg = averages()
            now = dt.datetime.now(dt.timezone.utc)
            wait = 0.0
            for job in busy:
                started = ts(job.get("started_at")) if job["status"] == "in_progress" else None
                done = (now - started).total_seconds() / 60 if started else 0.0
                wait += max(avg[SELF] - done, 1.0)
            pc_total, gh_total = wait + avg[SELF], avg[GH]
            names = ", ".join(f"{j['name']} ({j['status']})" for j in busy)
            print(f"PC busy with: {names}")
            print(f"Expected: PC {pc_total:.1f} min (wait {wait:.1f} + build {avg[SELF]:.1f}), "
                  f"GitHub runner {gh_total:.1f} min")
            if pc_total < gh_total:
                choice, why = SELF, "the PC is busy but should still finish sooner"
            else:
                choice, why = GH, "the PC is busy and a GitHub runner should finish sooner"
    print(f"Runner: {choice} ({why})")
    with open(os.environ["GITHUB_OUTPUT"], "a") as out:
        out.write(f"runner={choice}\n")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as out:
            out.write(f"Runner: **{choice}** ({why})\n")


if __name__ == "__main__":
    sys.exit(main())
