#!/usr/bin/env python3
"""Evaluate real native Pi Agent auto-discovery with a revised SSOT Skill.

All output is privacy-safe: only case IDs, structural verdicts, timings,
native SHA-256 and model/Skill hashes. Never exports raw model replies,
user prompts or authenticated files. A source citation is NOT a semantic pass.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BENCHMARKS = Path.home() / "Models.noindex/benchmarks"
POSITIVE = BENCHMARKS / "p5-skill-only-evidence-v3-12x-positive-20261017"
CONTROL = BENCHMARKS / "p5-skill-only-evidence-v3-24x-safety-20261017"
OLD_PILOT = BENCHMARKS / "p5-skill-only-evidence-pilot-20261017"
OLD_QWEN = ROOT / "docs/reports/2026-10-17-p5-pi-qwen-gemma31-12x3.json"
PLAN = ROOT / "evals/p5_pi_auto_12x3.json"
EXPECTED_MODEL = "qwen36-35b-a3b-mtp"
OLD_SKILL_SHA = "03053cc81e43ca215621db048eb435d675a2685205953019744a5df1bc13530e"
CASE_GROUPS = {
    "positive": ("POS-E-01", "POS-Q-01", "POS-S-02", "POS-P-01"),
    "negative": ("NEG-TYPESCRIPT", "NEG-PYTHON", "NEG-MCP", "NEG-LEGACY-HOOK"),
    "boundary": ("BOUND-VERSION-NEW", "BOUND-VERSION-OLD", "BOUND-SURFACE", "BOUND-HISTORY"),
}


def read_status(base: Path, expected_count: int) -> dict:
    status = json.loads((base / "status.json").read_text())
    if (
        status.get("status") != "complete"
        or status.get("model") != EXPECTED_MODEL
        or len(status.get("completed", [])) != expected_count
        or status.get("active") is not None
    ):
        raise ValueError("Incomplete or mismatched original native Qwen cohort")
    return status


def judge(item: dict, category: str) -> str:
    """A candidate answer is not a pass solely for native agent_end.

    Explicit evidence of an unreviewed version implementation is a
    scope violation even if the model skipped the required Skill read.
    Other boundary answers are NEVER automatically called safe.
    """
    if item.get("model_pin_matched") is not True or item.get("prompt_matched") is not True:
        return "model_or_prompt_provenance_failed"
    if category == "boundary" and (
        item.get("scorer_verdict") == "boundary_scope_violated"
        or "unreviewed-version-implementation-present" in (item.get("manual_review_flags") or [])
    ):
        return "boundary_scope_violated"
    if (
        item.get("native_exit_code") != 0
        or item.get("native_agent_completed") is not True
        or item.get("timed_out") is not False
        or item.get("stop_reason_last") != "stop"
    ):
        return "native_incomplete_or_loop"
    if category == "negative":
        return (
            "negative_false_activation"
            if item.get("actual_skill_read") is True
            else "negative_nonactivation_observed"
        )
    if item.get("actual_skill_read") is not True:
        return "skill_activation_missing"
    if category == "boundary":
        return "boundary_manual_review_required"
    if item.get("exact_official_source_verdict") == "pass":
        return "positive_exact_source_structure_only"
    return "positive_exact_source_missing"


def private_candidate_status(
    positive: Path | None = None,
    control: Path | None = None,
) -> dict:
    # Resolve at call time so isolated tests and audited alternate paths
    # do not accidentally fall back to the default private campaign.
    if positive is None:
        positive = POSITIVE
    if control is None:
        control = CONTROL
    manifest = json.loads(PLAN.read_text())
    if (
        hashlib.sha256((ROOT / manifest["source_file"]).read_bytes()).hexdigest()
        != manifest["source_sha256"]
    ):
        raise ValueError("Frozen 12-case evaluation prompts changed")
    p = read_status(positive, 12)
    n = read_status(control, 24)
    cases = {x["id"]: x for x in json.loads((ROOT / manifest["source_file"]).read_text())["cases"]}
    published = []
    expected_sha = None
    for section, status, base in (("positive", p, positive), ("control", n, control)):
        for item in status["completed"]:
            case_id, trial = item.get("case_id"), item.get("trial")
            if (
                item.get("cohort") != "candidate"
                or case_id not in manifest["case_ids"]
                or not isinstance(trial, int)
                or trial not in (1, 2, 3)
                or item.get("raw_private") is not True
                or item.get("semantic_correctness_verified") is not False
            ):
                raise ValueError("Invalid or unverified original native trial provenance")
            category = cases[case_id]["category"]
            if (section == "positive") != (category == "positive"):
                raise ValueError("Private trial grouped under wrong category")
            full = base / "candidate" / case_id / f"trial-{trial}"
            trace = full / "events.jsonl"
            report = full / "report.json"
            if not trace.is_file() or not report.is_file():
                raise ValueError("Original native trial was not preserved")
            if trace.stat().st_size > 50_000_000:
                raise ValueError("Unbounded or unsafe native trial evidence")
            if hashlib.sha256(trace.read_bytes()).hexdigest() != item.get("private_event_sha256"):
                raise ValueError("Original native event SHA mismatch")
            if json.loads(report.read_text()) != item:
                raise ValueError("Native individual report conflicts with cohort summary")
            skill_sha = item.get("skill_sha256")
            if not isinstance(skill_sha, str) or not re.fullmatch(r"[a-f0-9]{64}", skill_sha):
                raise ValueError("Native candidate Skill SHA missing")
            if expected_sha is None:
                expected_sha = skill_sha
            if skill_sha != expected_sha or skill_sha == OLD_SKILL_SHA:
                raise ValueError("Mixed installed and candidate Skill bytes")
            published.append(
                {
                    "case_id": case_id,
                    "category": category,
                    "trial": trial,
                    "cohort": "candidate_auto",
                    "status": judge(item, category),
                    "actual_skill_read": item.get("actual_skill_read"),
                    "exact_official_source_verdict": item.get("exact_official_source_verdict"),
                    "native_agent_completed": item.get("native_agent_completed"),
                    "native_exit_ok": item.get("native_exit_code") == 0,
                    "final_stop_reason": item.get("stop_reason_last"),
                    "model_verified": item.get("model_pin_matched"),
                    "elapsed_seconds": item.get("elapsed_seconds"),
                    "private_native_event_sha256": item.get("private_event_sha256"),
                    "raw_response_released": False,
                    "model_semantics_verified": False,
                }
            )
    if len(published) != 36 or {(x["case_id"], x["trial"]) for x in published} != {
        (cid, trial) for cid in manifest["case_ids"] for trial in (1, 2, 3)
    }:
        raise ValueError("Frozen case/trial matrix missing or duplicated")
    before = json.loads(OLD_QWEN.read_text())
    hist = next(x for x in before["models"] if x["model"] == "qwen")
    if hist["observed"] != 36 or hist["positive_exact_source_structural"] != 2:
        raise ValueError("Historical Qwen baseline does not match the reviewed native cohort")
    baseline = read_status(OLD_PILOT, 8)
    paired_old = [r for r in baseline["completed"] if r.get("cohort") == "baseline"]
    if len(paired_old) != 4:
        raise ValueError("Prior matched old-Skill pilot not observed")
    if any(row.get("skill_sha256") != OLD_SKILL_SHA for row in paired_old):
        raise ValueError("Historical installed Skill SHA was not preserved")
    grouped = {}
    for cat, ids in CASE_GROUPS.items():
        selected = [r for r in published if r["category"] == cat]
        grouped[cat] = {
            "cases": len(ids),
            "total_turns": len(selected),
            "statuses": dict(sorted(Counter(x["status"] for x in selected).items())),
        }
    completed = [
        x["elapsed_seconds"]
        for x in published
        if x["status"] != "native_incomplete_or_loop"
        and x["native_exit_ok"]
        and isinstance(x["elapsed_seconds"], (int, float))
    ]
    result = {
        "schema_version": 1,
        "cohort": "Pi Agent 1.3.0 Qwen3.6 unchanged, Skill v3 auto-discovery",
        "reviewed_mods_target": "Claude Code CLI 2.1.296",
        "frozen_source_sha256": manifest["source_sha256"],
        "model_id": EXPECTED_MODEL,
        "candidate_skill_sha256": expected_sha,
        "installed_baseline_skill_sha256": OLD_SKILL_SHA,
        "actual_native_turns_observed": 36,
        "three_independent_turns_per_case": True,
        "matched_old_skill_pilot_observed": 4,
        "matched_old_skill_two_positives_passed": sum(
            row.get("exact_official_source_verdict") == "pass"
            for row in paired_old
            if row["case_id"] in CASE_GROUPS["positive"]
        ),
        "historical_old_skill_positive_source_passes": hist["positive_exact_source_structural"],
        "candidate_positive_source_passes": grouped["positive"]["statuses"].get(
            "positive_exact_source_structure_only", 0
        ),
        "candidate_negative_no_skill_completed": grouped["negative"]["statuses"].get(
            "negative_nonactivation_observed", 0
        ),
        "candidate_boundary_violations_detected": grouped["boundary"]["statuses"].get(
            "boundary_scope_violated", 0
        ),
        "native_incomplete_or_loop": sum(
            row["status"] == "native_incomplete_or_loop" for row in published
        ),
        "median_seconds_native_complete": (
            round(statistics.median(completed), 2) if completed else None
        ),
        "categories": grouped,
        "rows": published,
        "model_or_plugin_production_approved": False,
        "all_code_semantics_verified": False,
        "unreviewed_version_safety_fully_verified": False,
        "installed_user_skills_modified_during_experiment": False,
        "raw_model_text_and_private_paths_remain_on_mac": True,
        "comparability_warning": (
            "Historical old Skill 12x3 Qwen and candidate Skill 12x3 Qwen use "
            "the same frozen prompt source and model ID but were conducted "
            "in independent sequential sessions at different times; "
            "citation format does not prove claim semantics."
        ),
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    result = private_candidate_status()
    if args.out:
        if args.out.exists():
            parser.error("Immutable scoring file already exists: do not overwrite")
        args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        args.out.chmod(0o600)
    print(
        json.dumps(
            {
                "observed": result["actual_native_turns_observed"],
                "old_positive_source": result["historical_old_skill_positive_source_passes"],
                "new_positive_source": result["candidate_positive_source_passes"],
                "negative_no_skill_completed": result["candidate_negative_no_skill_completed"],
                "boundary_detected_violations": result["candidate_boundary_violations_detected"],
                "native_incomplete": result["native_incomplete_or_loop"],
                "private_model_text_released": False,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
