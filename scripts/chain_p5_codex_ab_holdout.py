#!/usr/bin/env python3
"""Run approved holdout only after ALL 108 original Codex trials finish.

Detached, owner-only supervisor; never launches two overlapping model
cohorts. Missing/blocked native evidence halts instead of retrying calls.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time

from run_p5_codex_evidence_ab_case import PRIVATE, ROOT

BASE_PROGRESS = PRIVATE / "ab-campaign-progress.json"
HOLDOUT_PROGRESS = PRIVATE / "holdout-campaign-progress.json"
AUDIT = PRIVATE / "holdout-chain-state.json"


def write_state(status: str, *, reason: str | None = None) -> None:
    data = {
        "status": status,
        "reason_class": reason,
        "updated_epoch": time.time(),
        "raw_model_text_exported": False,
        "original_user_skill_modified": False,
    }
    temp = AUDIT.with_suffix(".tmp")
    temp.write_text(json.dumps(data, indent=2) + "\n")
    temp.chmod(0o600)
    temp.replace(AUDIT)


def main() -> int:
    if AUDIT.exists() or HOLDOUT_PROGRESS.exists():
        raise RuntimeError("A holdout chain has already started")
    write_state("waiting_for_108_original_turns")
    deadline = time.monotonic() + 10000
    while time.monotonic() < deadline:
        try:
            progress = json.loads(BASE_PROGRESS.read_text())
        except (OSError, ValueError):
            time.sleep(15)
            continue
        if progress.get("state") == "all_108_original_turns_observed":
            if len(progress.get("finished_original_turns", [])) != 108:
                write_state("blocked", reason="incomplete_original_study")
                return 2
            break
        if progress.get("state") == "paused":
            write_state("blocked", reason="original_campaign_paused")
            return 2
        time.sleep(15)
    else:
        write_state("blocked", reason="original_campaign_wait_deadline")
        return 2
    write_state("running_36_holdout_turns")
    with (PRIVATE / "holdout-campaign.log").open("xb") as log:
        try:
            proc = subprocess.run(  # noqa: S603 - fixed audited, local-only native runner
                [
                    sys.executable,
                    str(ROOT / "scripts/run_p5_codex_ab_holdout_batch.py"),
                    "--execute",
                    "--max-new-trials",
                    "36",
                ],
                cwd=ROOT,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=7200,
            )
        except subprocess.TimeoutExpired:
            write_state("blocked", reason="native_holdout_deadline")
            return 2
    if proc.returncode:
        write_state("blocked", reason="holdout_runner_nonzero")
        return 2
    if not HOLDOUT_PROGRESS.is_file():
        write_state("blocked", reason="holdout_progress_missing")
        return 2
    detail = json.loads(HOLDOUT_PROGRESS.read_text())
    if (
        detail.get("state") != "all_36_holdout_turns_observed"
        or len(detail.get("finished_original_turns", [])) != 36
    ):
        write_state("blocked", reason="holdout_incomplete_original_evidence")
        return 2
    write_state("all_holdout_native_evidence_collected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
