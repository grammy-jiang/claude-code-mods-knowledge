#!/usr/bin/env python3
"""Run same twelve frozen P5 prompts three times on native Codex Sol/medium.

One live model turn at a time to avoid artificial concurrency/429 effects.
Private per-trial evidence is immutable. A failed turn is never silently
replaced by a successful retry.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from run_p5_p123_codex_case import PLAN, PRIVATE, ROOT

MODEL = "gpt-6.1-sol"


def frozen() -> dict:
    plan = json.loads(PLAN.read_text())
    if len(plan["case_ids"]) != 12 or plan["repetitions"] != 3:
        raise ValueError("Original Codex cohort manifest invalid")
    return plan


def case_root(case_id: str, trial: int, *, web_disabled: bool) -> Path:
    cohort = "codex_no_web" if web_disabled else "codex"
    return PRIVATE / "codex-v2" / cohort / case_id / f"trial-{trial}"


RUNNER = ROOT / "scripts/run_p5_p123_codex_case.py"


def round_cases(items: list[str], round_no: int) -> list[str]:
    if round_no == 1:
        return items
    if round_no == 2:
        return list(reversed(items))
    if round_no == 3:
        return items[4:8] + items[8:12] + items[:4]
    raise ValueError("Invalid round number")


def execute(*, max_seconds: int, rounds: list[int], no_web: bool = False) -> dict:
    plan = frozen()
    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    PRIVATE.chmod(0o700)
    status_path = PRIVATE / (
        "codex-v2-no-web-progress.json" if no_web else "codex-v2-web-progress.json"
    )
    progress = {
        "model": MODEL,
        "effort": "medium",
        "expected_case_count": 36,
        "web_search_disabled_requested": no_web,
        "state": "running",
        "active_case": None,
        "active_round": None,
        "attempts": [],
    }

    def save() -> None:
        temporary = status_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(progress, ensure_ascii=False, indent=2) + "\n")
        temporary.chmod(0o600)
        temporary.replace(status_path)

    save()
    for round_no in rounds:
        for cid in round_cases(plan["case_ids"], round_no):
            private = case_root(cid, round_no, web_disabled=no_web)
            old_report = private / "report.json"
            if old_report.is_file():
                previous = json.loads(old_report.read_text())
                if (
                    previous.get("case_id") != cid
                    or previous.get("trial") != round_no
                    or previous.get("candidate") != ("codex_no_web" if no_web else "codex")
                    or previous.get("raw_reply_exposed") is not False
                    or previous.get("web_search_disabled") is not no_web
                ):
                    raise RuntimeError("Conflicting prior native model evidence")
                progress["attempts"].append(
                    {
                        "round": round_no,
                        "case_id": cid,
                        "status": "already_observed_no_replay",
                        "verdict": previous.get("native_scorer_verdict"),
                        "source_verdict": previous.get("source_verdict"),
                    }
                )
                save()
                continue
            progress["active_case"] = cid
            progress["active_round"] = round_no
            save()
            command = [
                sys.executable,
                str(RUNNER),
                "--case",
                cid,
                "--trial",
                str(round_no),
            ]
            if no_web:
                command.append("--no-web")
            started = time.monotonic()
            try:
                result = subprocess.run(  # noqa: S603 - owned, scoped local runner with enumerated IDs
                    command,
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    stdin=subprocess.DEVNULL,
                    timeout=max_seconds + 18,
                )
                if result.stdout.strip():
                    json.loads(result.stdout.strip())
            except (subprocess.TimeoutExpired, ValueError, json.JSONDecodeError):
                result = None
            report = private / "report.json"
            if report.exists():
                detail = json.loads(report.read_text())
                audit = detail
                outcome = {
                    "round": round_no,
                    "case_id": cid,
                    "status": "model_trial_observed",
                    "duration_s": detail.get("elapsed_s"),
                    "model_identity": audit.get("model_server_resolved"),
                    "verdict": audit.get("native_scorer_verdict"),
                    "source_verdict": audit.get("source_verdict"),
                    "skill_loaded": audit.get("actual_candidate_skill_read"),
                    "native_web_search_count": detail.get("native_web_search_count"),
                    "raw_user_content_exposed": False,
                }
            else:
                outcome = {
                    "round": round_no,
                    "case_id": cid,
                    "status": "runner_missing_or_unattributed",
                    "duration_s": round(time.monotonic() - started, 2),
                    "raw_user_content_exposed": False,
                }
                # Stop on unexpected orchestration failures, preserve prior evidence.
                progress["attempts"].append(outcome)
                progress["state"] = "stopped_on_runner_failure"
                progress["active_case"] = None
                progress["active_round"] = None
                save()
                return progress
            progress["attempts"].append(outcome)
            progress["active_case"] = None
            progress["active_round"] = None
            save()
            # Gentle sequential pacing; preserve model-config identity.
            time.sleep(0.5)
    progress["state"] = "complete"
    progress["active_case"] = None
    progress["active_round"] = None
    save()
    return progress


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=int, default=100)
    parser.add_argument("--rounds", type=int, nargs="+", choices=(1, 2, 3), default=[1, 2, 3])
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-web", action="store_true")
    opts = parser.parse_args()
    if opts.timeout < 45 or opts.timeout > 160:
        parser.error("Unsafe/unsupported bounded model timeout")
    if len(opts.rounds) != len(set(opts.rounds)):
        parser.error("Round numbers must not repeat")
    plan = frozen()
    if opts.dry_run:
        print(
            json.dumps(
                {
                    "approved_model": MODEL,
                    "effort": "medium",
                    "cases": plan["case_ids"],
                    "rounds": opts.rounds,
                    "max_attempts": 12 * len(opts.rounds),
                    "web_search_disabled_requested": opts.no_web,
                    "will_send_model_requests": False,
                }
            )
        )
        return 0
    result = execute(max_seconds=opts.timeout, rounds=opts.rounds, no_web=opts.no_web)
    print(
        json.dumps(
            {
                "state": result["state"],
                "observations": len(result["attempts"]),
                "raw_model_responses_exposed": False,
            }
        )
    )
    return 0 if result["state"] == "complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())
