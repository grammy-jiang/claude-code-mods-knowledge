#!/usr/bin/env python3
"""Score immutable genuine Codex Sol/medium no-web A/B/C Skill evidence turns.

Separation:
  - raw model source behavior / Skill activation (not semantic correctness)
  - factually reviewed evidence submitted by client vs proven consumed
  - postflight P3 buffer gate (cannot retroactively alter model replies)

Private original model text, user inputs, thread/account IDs and paths are
never added to the public score. Missing original turns are NEVER scored PASS.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from collections import Counter
from pathlib import Path

from run_p5_codex_ab_holdout_case import (
    CONDITIONS,
    MANIFEST,
    PRIVATE,
    ROOT,
    TARGET_SKILL_SHA,
)

from mods_knowledge.claims import load_claims
from mods_knowledge.evidence_delivery import evidence_fingerprint, make_verified_task_context
from mods_knowledge.registry import load_registry
from mods_knowledge.task_evidence import select_task_evidence


class CodexABEvidentiaryError(ValueError):
    """No reported numeric model results without pinned native provenance."""


def frozen() -> tuple[dict, dict[str, dict], dict]:
    plan = json.loads(MANIFEST.read_text())
    source = ROOT / plan["source_file"]
    if (
        hashlib.sha256(source.read_bytes()).hexdigest() != plan["source_sha256"]
        or plan["repetitions"] != 3
        or len(plan["case_ids"]) != 4
        or len(set(plan["case_ids"])) != 4
        or plan["conditions"] != list(CONDITIONS)
        or plan["native_turns_planned"] != 36
        or plan["frozen_skill_sha256"] != TARGET_SKILL_SHA
        or plan["model"] != "gpt-6.1-sol"
        or plan["effort"] != "medium"
        or plan["web_search"] != "disabled"
    ):
        raise CodexABEvidentiaryError("Original model/effort/Skill/cases changed")
    all_cases = {row["id"]: row for row in json.loads(source.read_text())["cases"]}
    claims = load_claims(
        ROOT / "claims",
        load_registry(ROOT / "sources/registry.json"),
        ROOT / "sources/snapshots",
        ROOT / "decisions",
    )
    return plan, all_cases, claims


def row(condition: str, trial: int, case: dict, claims: dict) -> dict:
    cid = case["id"]
    home = PRIVATE / "holdout-cases" / condition / cid / f"trial-{trial}"
    report = home / "ab-report.json"
    wire = home / "native-wire.jsonl"
    base = {
        "condition": condition,
        "case_id": cid,
        "trial": trial,
        "category": case["category"],
    }
    if not report.exists():
        return {**base, "status": "not_observed", "original_event_sha256": None}
    if not wire.is_file() or wire.is_symlink() or wire.stat().st_size >= 30_000_000:
        raise CodexABEvidentiaryError("Missing or unbounded original native Codex event evidence")
    score = json.loads(report.read_text())
    plan = json.loads(MANIFEST.read_text())
    selected = select_task_evidence(case["prompt"], claims, version="2.1.296")
    expected_ids = [x["claim_id"] for x in selected["claims"]]
    should_have_context = condition != "A_v3" and case["category"] == "positive"
    context = make_verified_task_context(selected) if should_have_context else None
    expected_digest = evidence_fingerprint(context) if context else None
    if (
        score.get("condition") != condition
        or score.get("case_id") != cid
        or score.get("trial") != trial
        or score.get("category") != case["category"]
        or score.get("frozen_suite_sha256") != plan["source_sha256"]
        or score.get("frozen_v3_skill_sha256") != TARGET_SKILL_SHA
        or score.get("native_model") != "gpt-6.1-sol"
        or score.get("native_effort") != "medium"
        or score.get("no_web") is not True
        or score.get("native_web_search_count") != 0
        or score.get("frozen_original_prompt_sha256")
        != hashlib.sha256(case["prompt"].encode()).hexdigest()
        or score.get("selected_claim_ids") != expected_ids
        or score.get("task_evidence_submitted") is not should_have_context
        or score.get("task_evidence_sha256") != expected_digest
        or score.get("task_evidence_confirmed_consumed_by_model") is not False
        or score.get("raw_user_or_model_text_exported") is not False
        or score.get("semantic_mod_runtime_verified") is not False
        or score.get("original_native_wire_sha256") != hashlib.sha256(wire.read_bytes()).hexdigest()
    ):
        raise CodexABEvidentiaryError("Original model/Skill/context/wire/prompt attribution failed")
    if (
        not isinstance(score.get("duration_seconds"), (int, float))
        or score["duration_seconds"] < 0
        or score["duration_seconds"] > 180
    ):
        raise CodexABEvidentiaryError("Missing bounded native model duration")
    completed = (
        score.get("native_turn_completed") is True and score.get("native_model_resolved") is True
    )
    skill_read = score.get("actual_v3_skill_read") is True
    raw_pass = completed and score.get("native_source_verdict") == "pass"
    successful_source_skill = raw_pass and skill_read
    negative_pass = case["category"] == "negative" and completed and not skill_read
    gate = score.get("buffered_gate")
    if condition == "C_context_gate":
        if (
            not isinstance(gate, dict)
            or gate.get("buffered") is not True
            or gate.get("original_model_text_delivered_to_user") is not False
            or gate.get("native_mod_semantics_approved") is not False
            or type(gate.get("allowed_structural_candidate_only")) is not bool
        ):
            raise CodexABEvidentiaryError("Missing or fabricated native C postflight gate")
        if case["category"] == "boundary" and gate.get("allowed_structural_candidate_only"):
            raise CodexABEvidentiaryError("Unreviewed CLI code was incorrectly allowed")
    elif gate is not None:
        raise CodexABEvidentiaryError("A/B did not have P3; cannot attribute non-native gate")
    return {
        **base,
        "status": "observed",
        "native_completed": completed,
        "actual_v3_skill_read": skill_read,
        "raw_exact_source_pass": raw_pass if case["category"] == "positive" else False,
        "raw_exact_source_and_skill_pass": (
            successful_source_skill if case["category"] == "positive" else False
        ),
        "negative_no_mods_skill_completed": negative_pass,
        "boundary_rule_detected_risk": (
            case["category"] == "boundary"
            and score.get("native_source_scorer_verdict") == "boundary_scope_violated"
        ),
        "native_source_verdict": score.get("native_source_verdict"),
        "native_scorer_verdict": score.get("native_source_scorer_verdict"),
        "SSOT_task_context_submitted": should_have_context,
        "native_developer_context_sha256": expected_digest,
        "SSOT_evidence_consumed_confirmed": False,
        "P3_structural_candidate_allowed": (
            gate.get("allowed_structural_candidate_only") if gate else None
        ),
        "P3_gate_reasons": gate.get("reasons") if gate else None,
        "native_duration_seconds": score["duration_seconds"],
        "original_event_sha256": score["original_native_wire_sha256"],
        "original_answer_sha256": score["original_answer_sha256"],
        "model_weights_or_effort_changed": False,
        "raw_model_text_exported": False,
        "semantic_mod_runtime_verified": False,
    }


def score(*, complete: bool = False) -> dict:
    plan, cases, claims = frozen()
    rows = []
    for condition in CONDITIONS:
        for cid in plan["case_ids"]:
            for trial in (1, 2, 3):
                rows.append(row(condition, trial, cases[cid], claims))
    observed = [x for x in rows if x["status"] == "observed"]
    if complete and len(observed) != 36:
        raise CodexABEvidentiaryError("Not all 36 original heldout Codex turns verified")
    cells = {(x["condition"], x["case_id"], x["trial"]) for x in rows}
    if len(cells) != 36:
        raise CodexABEvidentiaryError("Duplicate original research trials")
    by_condition = {}
    for condition in CONDITIONS:
        group = [x for x in observed if x["condition"] == condition]
        positives = [x for x in group if x["category"] == "positive"]
        negatives = [x for x in group if x["category"] == "negative"]
        boundaries = [x for x in group if x["category"] == "boundary"]
        times = sorted(x["native_duration_seconds"] for x in group if x["native_completed"])
        by_condition[condition] = {
            "observed": len(group),
            "missing": 12 - len(group),
            "completed": sum(x["native_completed"] for x in group),
            "positive_raw_exact_source": sum(x["raw_exact_source_pass"] for x in positives),
            "positive_source_with_verified_skill_read": sum(
                x["raw_exact_source_and_skill_pass"] for x in positives
            ),
            "positive_skill_loaded": sum(x["actual_v3_skill_read"] for x in positives),
            "negative_correct_nonactivation": sum(
                x["negative_no_mods_skill_completed"] for x in negatives
            ),
            "boundary_rule_risks": sum(x["boundary_rule_detected_risk"] for x in boundaries),
            "context_submitted": sum(x["SSOT_task_context_submitted"] for x in group),
            "P3_buffered_structural_candidates_permitted": sum(
                x["P3_structural_candidate_allowed"] is True for x in group
            )
            if condition == "C_context_gate"
            else None,
            "median_seconds_completed": round(statistics.median(times), 2) if times else None,
            "p95_seconds_completed": times[max(0, (95 * len(times) + 99) // 100 - 1)]
            if times
            else None,
            "native_scorer_statuses": dict(
                sorted(
                    Counter(x["native_scorer_verdict"] for x in group).items(),
                    key=lambda x: str(x[0]),
                )
            ),
        }
    return {
        "schema_version": 1,
        "study_id": plan["suite_id"],
        "source_sha256": plan["source_sha256"],
        "frozen_v3_skill_sha256": TARGET_SKILL_SHA,
        "reviewed_cli_target": "Claude Code CLI 2.1.296 only",
        "model": "gpt-6.1-sol",
        "effort": "medium",
        "web_search": "disabled",
        "planned_original_native_turns": 36,
        "verified_original_native_turns": len(observed),
        "unobserved_original_native_turns": 36 - len(observed),
        "holdout_not_used_to_tune_skill": True,
        "no_historical_holdout_baseline": True,
        "conditions": by_condition,
        "rows": rows,
        "native_developer_instructions_field_changed_only_in_B_and_C": True,
        "original_frozen_user_question_unchanged": True,
        "model_weights_effort_tools_and_web_setting_unchanged": True,
        "P3_changes_postflight_delivery_not_raw_model_capability": True,
        "source_citations_are_not_code_semantic_pass": True,
        "chatgpt_chat_mode_plugin_acceptance": False,
        "stable_production_skill_approved": False,
        "private_model_text_kept_on_mac": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    result = score(complete=args.require_complete)
    if args.out:
        if args.out.exists():
            parser.error("Immutable sanitized report already exists")
        args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        args.out.chmod(0o600)
    print(
        json.dumps(
            {
                "observed": result["verified_original_native_turns"],
                "missing": result["unobserved_original_native_turns"],
                "conditions": result["conditions"],
                "raw_model_replies_exposed": False,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
