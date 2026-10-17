#!/usr/bin/env python3
"""Sequential exact three-condition Codex Skill evidence benchmark.

All 108 cells preserve their original wire SHA-256 and case identity.
No retries, no overrides of installed Skills, no concurrent Codex calls.
The conditions rotate to reduce time-order confounding.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import subprocess
import sys
import time

from run_p5_codex_evidence_ab_case import CONDITIONS, MANIFEST, PRIVATE, ROOT, TARGET_SKILL_SHA

RUNNER = ROOT / "scripts/run_p5_codex_evidence_ab_case.py"
PROGRESS = PRIVATE / "ab-campaign-progress.json"


class EvidenceRunError(RuntimeError):
    """Refuse to silently repeat or replace a missing native Codex observation."""


def expected_cells() -> list[tuple[str, int, str]]:
    plan = json.loads(MANIFEST.read_text())
    items = list(plan["case_ids"])
    result = []
    for trial in (1, 2, 3):
        seq = (
            items
            if trial == 1
            else list(reversed(items))
            if trial == 2
            else items[4:8] + items[8:12] + items[:4]
        )
        for cid in seq:
            order = (
                CONDITIONS
                if trial == 1
                else (
                    CONDITIONS[1:] + CONDITIONS[:1]
                    if trial == 2
                    else CONDITIONS[2:] + CONDITIONS[:2]
                )
            )
            for condition in order:
                result.append((condition, trial, cid))
    if len(result) != 108 or len(set(result)) != 108:
        raise EvidenceRunError("Incomplete or duplicated 12x3x3 frozen case matrix")
    return result


def observed_native(cell: tuple[str, int, str]) -> dict | None:
    condition, trial, cid = cell
    home = PRIVATE / "cases" / condition / cid / f"trial-{trial}"
    report, wire = home / "ab-report.json", home / "native-wire.jsonl"
    if not report.is_file():
        if home.exists():
            raise EvidenceRunError(
                "Partial original native turn exists; manual reconciliation needed"
            )
        return None
    result = json.loads(report.read_text())
    plan = json.loads(MANIFEST.read_text())
    if (
        result.get("condition") != condition
        or result.get("trial") != trial
        or result.get("case_id") != cid
        or result.get("frozen_suite_sha256") != plan["source_sha256"]
        or result.get("frozen_v3_skill_sha256") != TARGET_SKILL_SHA
        or result.get("native_model") != "gpt-6.1-sol"
        or result.get("native_effort") != "medium"
        or result.get("no_web") is not True
        or result.get("raw_user_or_model_text_exported") is not False
        or not wire.is_file()
        or hashlib.sha256(wire.read_bytes()).hexdigest()
        != result.get("original_native_wire_sha256")
    ):
        raise EvidenceRunError("Conflicting original V3/condition/model/wire identity")
    return result


def save(obj: dict) -> None:
    temp = PROGRESS.with_suffix(".tmp")
    temp.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")
    temp.chmod(0o600)
    temp.replace(PROGRESS)


def run(max_new_trials: int, resume: bool) -> dict:
    expected = expected_cells()
    plan = json.loads(MANIFEST.read_text())
    if PROGRESS.exists():
        if not resume:
            raise EvidenceRunError("Original A/B/C campaign exists; --resume is required")
        progress = json.loads(PROGRESS.read_text())
        if progress.get("state") not in ("intentionally_partial", "paused"):
            raise EvidenceRunError("Previous campaign not in an explicitly safe resume state")
        if progress.get("plan_sha256") != hashlib.sha256(MANIFEST.read_bytes()).hexdigest():
            raise EvidenceRunError("Original immutable campaign plan changed")
    else:
        if resume:
            raise EvidenceRunError("Cannot resume an unobserved campaign")
        progress = {
            "campaign": plan["suite_id"],
            "state": "running",
            "started_epoch": time.time(),
            "expected_original_turns": 108,
            "plan_sha256": hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
            "finished_original_turns": [],
            "active": None,
            "final_report_generated": False,
        }
    PRIVATE.mkdir(parents=True, mode=0o700, exist_ok=True)
    PRIVATE.chmod(0o700)
    progress["state"] = "running"
    save(progress)
    new_count = 0
    try:
        for condition, trial, case_id in expected:
            key = f"{condition}|{trial}|{case_id}"
            prior = observed_native((condition, trial, case_id))
            seen = {x["key"] for x in progress["finished_original_turns"]}
            if prior is not None:
                if key not in seen:
                    progress["finished_original_turns"].append(
                        {
                            "key": key,
                            "original_wire_sha256": prior["original_native_wire_sha256"],
                            "completed": prior["native_turn_completed"],
                            "source": prior["native_source_verdict"],
                            "context_sent": prior["task_evidence_submitted"],
                            "raw_model_text_exported": False,
                        }
                    )
                    save(progress)
                continue
            if new_count >= max_new_trials:
                break
            if key in seen:
                raise EvidenceRunError(
                    "Previous journal says observed but original wire is missing"
                )
            progress["active"] = {"condition": condition, "trial": trial, "case_id": case_id}
            save(progress)
            log = PRIVATE / f"run-{condition}-{trial}-{case_id}.log"
            with log.open("xb") as output:
                child = subprocess.Popen(  # noqa: S603 - fixed trusted Python experiment runner
                    [
                        sys.executable,
                        str(RUNNER),
                        "--condition",
                        condition,
                        "--trial",
                        str(trial),
                        "--case",
                        case_id,
                    ],
                    cwd=ROOT,
                    stdin=subprocess.DEVNULL,
                    stdout=output,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
                try:
                    child.wait(timeout=165)
                except subprocess.TimeoutExpired as exc:
                    # The model runner's own native 120-s loop is expected
                    # to exit well before this emergency timeout.
                    os.killpg(child.pid, signal.SIGTERM)
                    child.wait(timeout=7)
                    raise EvidenceRunError("Native case exceeded 165-s run guard") from exc
            trial_result = observed_native((condition, trial, case_id))
            if trial_result is None:
                raise EvidenceRunError("Original model result not produced; no automatic replay")
            progress["finished_original_turns"].append(
                {
                    "key": key,
                    "original_wire_sha256": trial_result["original_native_wire_sha256"],
                    "completed": trial_result["native_turn_completed"],
                    "source": trial_result["native_source_verdict"],
                    "context_sent": trial_result["task_evidence_submitted"],
                    "raw_model_text_exported": False,
                }
            )
            progress["active"] = None
            new_count += 1
            save(progress)
            # Sequential pacing; no parallel hosted requests or artificial
            # retry storms after rate limits.
            time.sleep(0.6)
        count = len({x["key"] for x in progress["finished_original_turns"]})
        progress["state"] = (
            "all_108_original_turns_observed" if count == 108 else "intentionally_partial"
        )
    except Exception as exc:
        progress["state"] = "paused"
        progress["blocker_category"] = type(exc).__name__
    finally:
        progress["ended_epoch"] = time.time()
        save(progress)
    return progress


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--max-new-trials", type=int, default=108)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.max_new_trials <= 108:
        parser.error("Only 1..108 explicitly approved native Codex trials")
    if not args.execute:
        print(
            json.dumps(
                {
                    "ready": True,
                    "model": "gpt-6.1-sol",
                    "effort": "medium",
                    "web_search": "disabled",
                    "original_frozen_cases": 12,
                    "repeats": 3,
                    "conditions": list(CONDITIONS),
                    "native_model_trials": 108,
                    "one_native_turn_at_a_time": True,
                    "changes_model_weights_or_global_skill": False,
                    "makes_native_model_calls": False,
                }
            )
        )
        return 0
    status = run(args.max_new_trials, args.resume)
    print(
        json.dumps(
            {
                "status": status["state"],
                "original_turns": len(status["finished_original_turns"]),
                "last_blocker": status.get("blocker_category"),
                "private_raw_model_answers_exported": False,
            }
        )
    )
    return (
        0 if status["state"] in ("intentionally_partial", "all_108_original_turns_observed") else 2
    )


if __name__ == "__main__":
    raise SystemExit(main())
