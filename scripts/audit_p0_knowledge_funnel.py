#!/usr/bin/env python3
"""Offline P0 knowledge-use funnel from PUBLIC, sanitized native QA reports.

No raw model responses, private traces, user prompts, connections, or model
calls are needed. Counts measure observable events/structural citations only;
they do NOT establish source truth or executable Mod correctness.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NATIVE = ROOT / "docs/reports/2026-10-17-p5-p123-seven-stack-12x3.json"
CHAT = ROOT / "docs/reports/2026-10-15-six-arm-automatic-routing-observations.json"


def _validate_rows(data: dict) -> list[dict]:
    rows = data.get("rows")
    if not isinstance(rows, list) or not rows:
        raise ValueError("Missing nonempty native rows")
    if data.get("actual_native_attempts") != len(rows):
        raise ValueError("Native attempt count does not match saved rows")
    keys = set()
    required = {
        "model", "case_id", "trial", "category", "native_completed",
        "actual_skill_read", "raw_exact_source_verdict",
        "selected_evidence_actually_read", "raw_events_sha256",
    }
    for row in rows:
        if (
            not isinstance(row, dict)
            or not required <= row.keys()
            or row.get("category") not in {"positive", "negative", "boundary"}
        ):
            raise ValueError("Invalid native row")
        key = (row.get("model"), row.get("case_id"), row.get("trial"))
        if None in key or key in keys:
            raise ValueError("Missing or duplicate native model/case/trial")
        keys.add(key)
    return rows


def _count(rows: list[dict], field: str, value: object = True) -> int:
    return sum(row.get(field) is value if type(value) is bool else row.get(field) == value for row in rows)


def summarize(native: dict, chat: dict) -> dict:
    """Compute stage-separated measurements without making a quality claim."""
    rows = _validate_rows(native)
    cases = chat.get("case_results")
    if not isinstance(cases, list) or not cases:
        raise ValueError("Missing Chat-mode case results")
    if any(
        not isinstance(row, dict)
        or not {"arm", "case_id", "case_key", "category", "invocation_mode", "skill_loaded"} <= row.keys()
        for row in cases
    ):
        raise ValueError("Invalid Chat-mode case record")

    def stages(selected: list[dict]) -> dict:
        positive = [r for r in selected if r["category"] == "positive"]
        negatives = [r for r in selected if r["category"] == "negative"]
        boundary = [r for r in selected if r["category"] == "boundary"]
        return {
            "total_native_turns": len(selected),
            "positive": {
                "attempts": len(positive),
                "main_skill_read_observed": _count(positive, "actual_skill_read"),
                "exact_claim_source_structural_pass": _count(
                    positive, "raw_exact_source_verdict", "pass"
                ),
                "selected_evidence_file_read_observed": _count(
                    positive, "selected_evidence_actually_read"
                ),
                "native_completed": _count(positive, "native_completed"),
            },
            "negative": {
                "attempts": len(negatives),
                "completed_without_mod_skill": sum(
                    r.get("native_completed") is True
                    and r.get("actual_skill_read") is False
                    for r in negatives
                ),
            },
            "boundary": {
                "attempts": len(boundary),
                "detected_version_or_surface_flags": sum(
                    bool(r.get("boundary_rule_flag")) for r in boundary
                ),
                "verified_safe_answers": None,
            },
        }

    by_model = defaultdict(list)
    for row in rows:
        by_model[row["model"]].append(row)

    auto = [
        r for r in cases
        if r.get("invocation_mode") == "automatic" and r.get("category") == "positive"
    ]
    explicit = [r for r in cases if r.get("invocation_mode") == "explicit"]
    if not auto or not explicit:
        raise ValueError("Missing Chat-mode automatic or explicit controls")
    return {
        "schema": "p0-skill-knowledge-funnel-v1",
        "source": {
            "native_report": NATIVE.name,
            "chat_report": CHAT.name,
        },
        "native": stages(rows),
        "by_model": {m: stages(group) for m, group in sorted(by_model.items())},
        "chat_mode": {
            "automatic_positive_attempts": len(auto),
            "automatic_positive_plugin_skill_reads": _count(auto, "skill_loaded"),
            "explicit_control_attempts": len(explicit),
            "explicit_control_plugin_skill_reads": _count(explicit, "skill_loaded"),
            "causal_routing_difference_established": chat.get("causal_routing_difference_established"),
            "protocol_all_arms_admitted": chat.get("protocol_all_arms_admitted"),
        },
        "not_measured": [
            "retrieval_recall_at_k",
            "whether the selected evidence was understood",
            "factual_answer_accuracy",
            "semantic_correctness_of_generated_code",
            "ChatGPT internal automatic routing decision or cache state",
        ],
        "raw_private_data_read": False,
        "new_model_turns_run": 0,
    }


def main() -> int:
    report = summarize(
        json.loads(NATIVE.read_text(encoding="utf-8")),
        json.loads(CHAT.read_text(encoding="utf-8")),
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
