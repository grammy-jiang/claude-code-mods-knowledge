#!/usr/bin/env python3
"""Score only actual, hashed, private native Pi turns in the frozen cohort.

Do not emit raw model replies or overstate source/coding correctness.
A count of zero can mean not observed rather than failed; both are explicit.
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
PLAN = ROOT / "evals/p5_pi_auto_12x3.json"
PRIVATE = Path.home() / "Models.noindex/benchmarks/pi-mods-skill-activation-20261017"
CANDIDATES = {"qwen", "gemma31"}
EXPECTED_OBSERVED_MODELS = {
    "qwen": "p5-mac-qwen/qwen36-35b-a3b-mtp",
    "gemma31": "p5-gemma31/gemma4-31b-mtp",
}
_BOUNDARY_CODE_RISK = re.compile(
    r"\bexport\s+(?:function|const)\s+register\b"
    r"|\bclaude\s+plugin\s+(?:test|validate)\b"
    r"|\bon\s*\(\s*['\\\"]tool\.call['\\\"]"
    + "|"
    + chr(96) * 3
    + r"(?:js|javascript|ts|typescript|sh|bash)\b",
    re.I,
)


def _boundary_code_review_required(native_trace: Path) -> bool:
    """Hash-only warning: runnable-looking advice may need manual review.

    It is not an automatic semantic failure because the model may be
    explicitly demonstrating an unsafe negative example. Raw text
    and paths remain private even if this marker is true.
    """
    last_answer = ""
    if native_trace.stat().st_size > 20_000_000:
        raise ValueError("Unbounded private native event file")
    with native_trace.open(encoding="utf-8", errors="replace") as stream:
        for line in stream:
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if not isinstance(event, dict) or event.get("type") != "message_end":
                continue
            message = event.get("message")
            if not isinstance(message, dict) or message.get("role") != "assistant":
                continue
            content = message.get("content")
            if not isinstance(content, list):
                continue
            value = "".join(
                item.get("text", "")
                for item in content
                if isinstance(item, dict) and item.get("type") == "text"
            )
            if value.strip():
                last_answer = value
    return bool(_BOUNDARY_CODE_RISK.search(last_answer))


def grade(row: dict, category: str) -> str:
    if row.get("model_calls") != 1 or row.get("raw_output_exposed") is not False:
        return "invalid_or_unsafe_evidence"
    gate = row.get("gate")
    if not isinstance(gate, dict):
        return "missing_native_gate"
    if row.get("timed_out") or row.get("repeat_abort_reason"):
        return "incomplete_or_loop"
    if row.get("native_exit_code") != 0:
        return "native_process_not_completed"
    if category == "boundary":
        if row.get("research_only") is not True:
            return "boundary_model_not_observed"
        if row.get("research_verdict") in ("boundary_scope_violated", "activation_failed"):
            return row["research_verdict"]
        if not row.get("research_actual_skill_read"):
            return "boundary_skill_not_loaded"
        if row.get("research_verdict") in ("blocked_or_incomplete", "invalid_provenance"):
            return "boundary_incomplete_or_invalid"
        return "boundary_manual_review_required"
    if not gate.get("model_provenance_matched", False):
        return "model_provenance_failed"
    if category == "negative":
        if gate.get("skill_read_observed"):
            return "negative_false_skill_activation"
        if gate.get("action") != "allow_structural_only":
            return "negative_incomplete_or_blocked"
        return "negative_nonactivation_observed"
    if not gate.get("skill_read_observed"):
        return "positive_skill_not_loaded"
    if gate.get("source_verdict") != "pass":
        return "positive_exact_claim_or_source_missing"
    if gate.get("action") == "allow_structural_only":
        return "positive_source_structure_only"
    if set(gate.get("reason_codes", [])) == {
        "executable_example_requires_independent_native_validation"
    }:
        return "positive_source_pass_code_needs_native_validation"
    return "positive_additional_review_or_hazard"


def summarize(private_root: Path = PRIVATE) -> dict:
    plan = json.loads(PLAN.read_text())
    original = ROOT / plan["source_file"]
    if hashlib.sha256(original.read_bytes()).hexdigest() != plan["source_sha256"]:
        raise ValueError("Paired suite source SHA mismatch")
    cases = {x["id"]: x for x in json.loads(original.read_text())["cases"]}
    rows = []
    for model in sorted(CANDIDATES):
        for cid in plan["case_ids"]:
            for trial in (1, 2, 3):
                p = private_root / "paired" / model / cid / f"trial-{trial}/report.json"
                if not p.is_file():
                    rows.append(
                        {
                            "model": model,
                            "case_id": cid,
                            "trial": trial,
                            "category": cases[cid]["category"],
                            "status": "not_observed",
                            "event_sha256": None,
                            "elapsed_s": None,
                        }
                    )
                    continue
                source = json.loads(p.read_text())
                if (
                    source.get("case_id") != cid
                    or source.get("candidate") != model
                    or source.get("trial") != trial
                    or source.get("raw_output_exposed") is not False
                ):
                    raise ValueError("Conflicting real model metadata")
                digest = source.get("event_sha256")
                if not isinstance(digest, str) or len(digest) != 64:
                    raise ValueError("Real native trace missing digest")
                events = p.parent / "events.jsonl"
                if (
                    not events.is_file()
                    or hashlib.sha256(events.read_bytes()).hexdigest() != digest
                ):
                    raise ValueError("Native private events changed after reporting")
                is_boundary = cases[cid]["category"] == "boundary"
                mismatch = (
                    is_boundary and source.get("observed_model") != EXPECTED_OBSERVED_MODELS[model]
                )
                rows.append(
                    {
                        "model": model,
                        "case_id": cid,
                        "trial": trial,
                        "category": cases[cid]["category"],
                        "status": (
                            "invalid_model_provenance"
                            if mismatch
                            else grade(source, cases[cid]["category"])
                        ),
                        "event_sha256": digest,
                        "elapsed_s": source.get("elapsed_s"),
                        "provider_and_model_verified": bool(
                            source.get("gate", {}).get("model_provenance_matched")
                            if cases[cid]["category"] != "boundary"
                            else not mismatch
                        ),
                        "skill_read": (
                            source.get("gate", {}).get("skill_read_observed")
                            if cases[cid]["category"] != "boundary"
                            else source.get("research_actual_skill_read")
                        ),
                        "model_turn_completed": source.get("native_exit_code") == 0
                        and not source.get("timed_out"),
                        "boundary_copyable_code_requires_manual_review": (
                            _boundary_code_review_required(events)
                            if cases[cid]["category"] == "boundary"
                            else False
                        ),
                    }
                )
    stats = []
    for model in sorted(CANDIDATES):
        batch = [r for r in rows if r["model"] == model]
        done = [r for r in batch if r["status"] != "not_observed"]
        completed = [
            r["elapsed_s"]
            for r in done
            if r["model_turn_completed"] and isinstance(r["elapsed_s"], (int, float))
        ]
        completed.sort()
        stats.append(
            {
                "model": model,
                "observed": len(done),
                "not_observed": 36 - len(done),
                "states": dict(sorted(Counter(r["status"] for r in done).items())),
                "native_completed": sum(bool(r["model_turn_completed"]) for r in done),
                "median_seconds_completed": round(statistics.median(completed), 2)
                if completed
                else None,
                "p95_seconds_completed_nearest_rank": (
                    completed[max(0, (95 * len(completed) + 99) // 100 - 1)] if completed else None
                ),
                "incomplete_or_loop": sum(r["status"] == "incomplete_or_loop" for r in done),
                "positive_exact_source_structural": sum(
                    r["status"]
                    in {
                        "positive_source_structure_only",
                        "positive_source_pass_code_needs_native_validation",
                    }
                    for r in done
                ),
                "negative_nonactivation_observed": sum(
                    r["status"] == "negative_nonactivation_observed" for r in done
                ),
                "boundary_scope_violations": sum(
                    r["status"] == "boundary_scope_violated" for r in done
                ),
                "boundary_loader_or_scope_miss": sum(
                    r["status"] in {"activation_failed", "boundary_skill_not_loaded"} for r in done
                ),
                "boundary_copyable_code_requires_manual_review": sum(
                    bool(r.get("boundary_copyable_code_requires_manual_review")) for r in done
                ),
            }
        )
    return {
        "schema_version": 1,
        "suite_id": plan["suite_id"],
        "source_sha256": plan["source_sha256"],
        "planned_model_turns": 72,
        "observed": sum(x["observed"] for x in stats),
        "unobserved": sum(x["not_observed"] for x in stats),
        "model_stats": stats,
        "rows": rows,
        "full_p5_acceptance": False,
        "source_semantics_fully_verified": False,
        "note": "Research comparison only; boundary source text was never delivered to users",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = summarize()
    out = args.out.expanduser()
    if out.exists():
        parser.error("Never overwrite previously frozen research scoring evidence")
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    out.chmod(0o600)
    print(
        json.dumps(
            {
                "planned": 72,
                "observed": result["observed"],
                "not_observed": result["unobserved"],
                "model_stats": result["model_stats"],
                "raw_model_replies_exposed": False,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
