#!/usr/bin/env python3
"""Complete native Codex Sol/medium 12x3 with web disabled and enabled.

Runs one hosted Codex model turn at a time. Original model wires and
candidate Skill identity are privately audited, never overwritten.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time

from run_p5_p123_codex_case import PRIVATE, ROOT

STATE = PRIVATE / "codex-72-campaign.json"
RUNNER = ROOT / "scripts/run_p5_p123_codex_batch.py"


def update(report: dict) -> None:
    temp = STATE.with_suffix(".tmp")
    temp.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    temp.chmod(0o600)
    temp.replace(STATE)


def main() -> int:
    if STATE.exists():
        raise RuntimeError("Codex 72 campaign already started; original evidence cannot replay")
    status = {
        "status": "running",
        "started_epoch": time.time(),
        "expected_native_turns": 72,
        "completed_cohorts": [],
        "active_cohort": None,
        "all_original_wire_text_private": True,
    }
    update(status)
    for cohort in ("no_web", "web"):
        status["active_cohort"] = cohort
        update(status)
        flags = ["--no-web"] if cohort == "no_web" else []
        log = PRIVATE / f"codex-corrected-{cohort}.log"
        with log.open("xb") as output:
            proc = subprocess.run(  # noqa: S603 - fixed, owned local model-test runner
                [sys.executable, str(RUNNER), "--timeout", "115", *flags],
                cwd=ROOT,
                stdin=subprocess.DEVNULL,
                stdout=output,
                stderr=output,
                timeout=5500,
            )
        report_file = PRIVATE / (
            "codex-v2-no-web-progress.json" if cohort == "no_web" else "codex-v2-web-progress.json"
        )
        if not report_file.exists() or proc.returncode != 0:
            status["status"] = "paused_incomplete_native_codex"
            status["active_cohort"] = cohort
            update(status)
            return 2
        details = json.loads(report_file.read_text())
        if details.get("state") != "complete" or len(details.get("attempts", [])) != 36:
            status["status"] = "paused_incomplete_native_codex"
            update(status)
            return 2
        status["completed_cohorts"].append(
            {
                "configuration": cohort,
                "actual_native_turns": 36,
                "raw_messages_released": False,
            }
        )
        status["active_cohort"] = None
        update(status)
    status["status"] = "all_72_native_turns_observed"
    status["finished_epoch"] = time.time()
    update(status)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
