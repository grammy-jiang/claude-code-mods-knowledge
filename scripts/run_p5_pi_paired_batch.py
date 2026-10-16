#!/usr/bin/env python3
"""Resumable, bounded research-only Mac Pi Agent model comparison.

The model's raw output never leaves private files. This is NOT a
production Agent turn or a stable release certification. Candidate
models are limited to the frozen two-model manifest.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "evals/p5_pi_auto_12x3.json"
PRIVATE = Path.home() / "Models.noindex/benchmarks/pi-mods-skill-activation-20261017"
RUNNER = ROOT / "scripts/run_p5_pi_gated.py"
CANDIDATES = {"qwen", "gemma31"}


def _preflight(candidate: str, manifest: dict) -> None:
    if candidate not in CANDIDATES:
        raise ValueError("Unapproved model candidate")
    original = ROOT / manifest["source_file"]
    if hashlib.sha256(original.read_bytes()).hexdigest() != manifest["source_sha256"]:
        raise RuntimeError("Frozen P4 evaluation prompts changed")
    if manifest["repetitions"] != 3 or len(set(manifest["case_ids"])) != 12:
        raise RuntimeError("Unexpected paired suite size")
    if (
        sum(cid.startswith("POS-") for cid in manifest["case_ids"]) != 4
        or sum(cid.startswith("NEG-") for cid in manifest["case_ids"]) != 4
    ):
        raise RuntimeError("Frozen paired case category mix changed")


def _pressure() -> tuple[int, float]:
    sysctl = shutil.which("sysctl") or "/usr/sbin/sysctl"
    mem = subprocess.run(  # noqa: S603 - fixed local system metadata only
        [sysctl, "-n", "kern.memorystatus_level"],
        capture_output=True,
        text=True,
        check=True,
        timeout=5,
    ).stdout
    sw = subprocess.run(  # noqa: S603 - fixed local system metadata only
        [sysctl, "-n", "vm.swapusage"],
        capture_output=True,
        text=True,
        check=True,
        timeout=5,
    ).stdout
    match = re.search(r"used\s*=\s*([\d.]+)([MGT]?)", sw)
    if not match:
        raise RuntimeError("Could not parse current swap usage")
    mib = float(match.group(1)) * {"M": 1, "G": 1024, "T": 1048576, "": 1}[match.group(2)]
    return int(mem.strip()), mib


def _cases_for_round(ids: list[str], round_number: int) -> list[str]:
    if round_number == 1:
        return ids
    if round_number == 2:
        return list(reversed(ids))
    if round_number == 3:
        return ids[4:8] + ids[8:12] + ids[:4]
    raise ValueError("Only three independent rounds are approved")


def _report(case_id: str, candidate: str, trial: int) -> dict | None:
    p = PRIVATE / "paired" / candidate / case_id / f"trial-{trial}" / "report.json"
    if not p.exists():
        return None
    row = json.loads(p.read_text())
    if (
        row.get("case_id") != case_id
        or row.get("candidate") != candidate
        or row.get("trial") != trial
        or row.get("model_calls") != 1
        or row.get("raw_output_exposed") is not False
    ):
        raise RuntimeError("Conflicting private trial evidence: refusing overwrite")
    return row


def _run_one(case_id: str, candidate: str, round_number: int, timeout: int) -> dict:
    before = time.monotonic()
    args = [
        sys.executable,
        str(RUNNER),
        "--case",
        case_id,
        "--mode",
        "auto",
        "--candidate",
        candidate,
        "--trial",
        str(round_number),
        "--timeout",
        str(timeout),
    ]
    if case_id.startswith("BOUND-"):
        args.append("--research-boundary")
    try:
        proc = subprocess.run(  # noqa: S603 - fixed trusted native QA script and case IDs
            args,
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=timeout + 18,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Outer bounded model process exceeded deadline") from exc
    if proc.returncode:
        raise RuntimeError("Native research runner rejected its bounded case")
    stored = _report(case_id, candidate, round_number)
    if not stored:
        raise RuntimeError("Native research runner failed to persist private evidence")
    return {
        "case_id": case_id,
        "candidate": candidate,
        "round": round_number,
        "duration_seconds": round(time.monotonic() - before, 2),
        "native_model_call_count": 1,
        "candidate_answer_exposed": False,
        "gate_action": stored.get("gate", {}).get("action"),
        "native_model_provenance": stored.get("gate", {}).get("model_provenance_matched"),
        "skill_read": stored.get("gate", {}).get("skill_read_observed")
        if not stored.get("research_only")
        else stored.get("research_actual_skill_read"),
        "research_verdict": stored.get("research_verdict"),
        "reason_codes": stored.get("gate", {}).get("reason_codes", []),
        "tool_repeat_abort": stored.get("repeat_abort_reason"),
        "trace_sha256": stored.get("event_sha256"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", choices=sorted(CANDIDATES), required=True)
    parser.add_argument("--round", type=int, choices=[1, 2, 3], required=True)
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument("--max-cases", type=int, default=12)
    parser.add_argument("--wall-seconds", type=int, default=780)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not 40 <= args.timeout <= 150 or not 1 <= args.max_cases <= 12:
        parser.error("Invalid bounded per-case or batch limits")
    if not 90 <= args.wall_seconds <= 1800:
        parser.error("Invalid batch wall-clock safety limit")
    plan = json.loads(MANIFEST.read_text())
    _preflight(args.candidate, plan)
    cases = _cases_for_round(plan["case_ids"], args.round)
    pending = [cid for cid in cases if _report(cid, args.candidate, args.round) is None]
    if args.dry_run:
        print(
            json.dumps(
                {
                    "candidate": args.candidate,
                    "round": args.round,
                    "planned_cases": len(cases),
                    "remaining_cases": pending,
                    "will_make_model_requests": False,
                    "raw_user_data_logged": False,
                }
            )
        )
        return 0
    PRIVATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    journal = PRIVATE / f"batch-{args.candidate}-round-{args.round}.json"
    output = {
        "candidate": args.candidate,
        "round": args.round,
        "original_case_ids": cases,
        "results": [],
        "state": "running",
    }
    started = time.monotonic()

    def save() -> None:
        tmp = journal.with_suffix(".tmp")
        tmp.write_text(json.dumps(output, indent=2) + "\n")
        tmp.replace(journal)
        journal.chmod(0o600)

    save()
    for case_id in pending[: args.max_cases]:
        pressure, swap_mib = _pressure()
        if pressure < 55 or swap_mib > 512:
            output["state"] = "stopped_by_resource_guard"
            break
        if time.monotonic() - started > args.wall_seconds:
            output["state"] = "stopped_by_bounded_window"
            break
        output["active_case"] = case_id
        save()
        try:
            entry = _run_one(case_id, args.candidate, args.round, args.timeout)
        except Exception as exc:
            output["state"] = "runner_error"
            output["error_category"] = type(exc).__name__
            break
        output["results"].append(entry)
        output["active_case"] = None
        save()
    else:
        if output["state"] == "running":
            output["state"] = "batch_completed"
    output["elapsed_seconds"] = round(time.monotonic() - started, 2)
    output["new_cases_completed"] = len(output["results"])
    output.pop("active_case", None)
    save()
    print(
        json.dumps(
            {
                "candidate": args.candidate,
                "round": args.round,
                "state": output["state"],
                "new_cases_completed": len(output["results"]),
                "remaining_unobserved": sum(
                    _report(cid, args.candidate, args.round) is None for cid in cases
                ),
                "elapsed_seconds": output["elapsed_seconds"],
            }
        )
    )
    return 0 if output["state"] == "batch_completed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
