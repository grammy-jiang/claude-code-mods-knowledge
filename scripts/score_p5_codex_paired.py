#!/usr/bin/env python3
"""Score same frozen P5 12x3 native Codex Sol/medium case observations.

Every observed turn needs the original SHA-256-pinned native App Server
wire transcript, a matching frozen prompt, confirmed server model and
medium effort. Does not emit raw model/user text or claim Mod runtime pass.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
from collections import Counter
from pathlib import Path

from run_p5_codex_paired import CASES, MODEL, PRIVATE, SOURCE, frozen

_CODE = re.compile(
    r"\bexport\s+(?:function|const)\s+register\b"
    r"|\bclaude\s+plugin\s+(?:test|validate)\b"
    r"|\bon\s*\(\s*['\"]tool\.call['\"]"
    + "|"
    + chr(96) * 3
    + r"(?:js|javascript|ts|typescript|sh|bash)\b",
    re.I,
)


def _manual_boundary_code(path: Path) -> bool:
    """Code-shaped text in last answer needs review, not automatic condemnation."""
    if path.stat().st_size > 30_000_000:
        raise ValueError("Unbounded private native Codex transcript")
    last = ""
    for line in path.read_text(errors="replace").splitlines():
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if e.get("method") != "item/completed":
            continue
        item = e.get("params", {}).get("item")
        if isinstance(item, dict) and item.get("type") == "agentMessage":
            s = item.get("text")
            if isinstance(s, str) and s.strip():
                last = s
    return bool(_CODE.search(last))


def grade(report: dict, category: str) -> str:
    evidence = report.get("evidence", {})
    if (
        report.get("raw_output_exposed") is not False
        or report.get("raw_transcript_private") is not True
    ):
        return "invalid_or_exposed_evidence"
    if not isinstance(evidence, dict) or evidence.get("state") != "native_turn_recorded":
        return "incomplete_or_tool_failure"
    if (
        evidence.get("model_server_resolved") != MODEL
        or evidence.get("effort_server_resolved") != "medium"
        or evidence.get("model_provenance") != "same-thread-app-server-response+thread-read"
        or evidence.get("prompt_matched") is not True
    ):
        return "model_or_prompt_provenance_failed"
    if evidence.get("agent_completed") is not True or evidence.get("answer_present") is not True:
        return "incomplete_or_tool_failure"
    if category == "boundary":
        if "unreviewed-version-implementation-present" in evidence.get("manual_review_flags", []):
            return "boundary_scope_violated"
        if evidence.get("skill_loaded") is not True:
            return "boundary_skill_not_loaded"
        return "boundary_manual_review_required"
    if category == "negative":
        if evidence.get("skill_loaded") is True:
            return "negative_false_skill_activation"
        return "negative_nonactivation_observed"
    if evidence.get("skill_loaded") is not True:
        return "positive_skill_not_loaded"
    if evidence.get("source_verdict") != "pass":
        return "positive_exact_claim_or_source_missing"
    if evidence.get("risk_flags") or evidence.get("manual_review_flags"):
        return "positive_additional_review_or_hazard"
    return "positive_source_structure_only"


def summarize() -> dict:
    manifest = frozen()
    cases = {x["id"]: x for x in json.loads(CASES.read_text())["cases"]}
    observations = []
    for case_id in manifest["case_ids"]:
        for trial in (1, 2, 3):
            folder = PRIVATE / "paired" / MODEL / case_id / f"trial-{trial}"
            path = folder / "report.json"
            if not path.is_file():
                observations.append(
                    {
                        "model": "codex",
                        "case_id": case_id,
                        "trial": trial,
                        "category": cases[case_id]["category"],
                        "status": "not_observed",
                        "wire_sha256": None,
                        "elapsed_s": None,
                    }
                )
                continue
            report = json.loads(path.read_text())
            wire = folder / "native-wire.jsonl"
            if (
                not wire.is_file()
                or report.get("case_id") != case_id
                or report.get("trial") != trial
                or report.get("candidate") != "codex"
                or report.get("model_requested") != MODEL
                or report.get("effort_requested") != "medium"
                or report.get("source_revision") != SOURCE
                or report.get("original_case_file_sha256") != manifest["source_sha256"]
                or report.get("raw_output_exposed") is not False
                or report.get("semantic_review_complete") is not False
                or report.get("native_mod_runtime_verified") is not False
            ):
                raise ValueError("Unverifiable Codex frozen case metadata")
            sha = hashlib.sha256(wire.read_bytes()).hexdigest()
            if report.get("native_wire_sha256") != sha:
                raise ValueError("Original private native Codex transcript mutated")
            audit = report["evidence"]
            category = cases[case_id]["category"]
            observations.append(
                {
                    "model": "codex",
                    "case_id": case_id,
                    "trial": trial,
                    "category": category,
                    "status": grade(report, category),
                    "wire_sha256": sha,
                    "elapsed_s": report.get("elapsed_s"),
                    "provider_and_model_verified": (
                        audit.get("model_server_resolved") == MODEL
                        and audit.get("effort_server_resolved") == "medium"
                        and audit.get("model_provider_server_resolved") == "openai"
                        and audit.get("model_provenance")
                        == "same-thread-app-server-response+thread-read"
                    ),
                    "skill_read": audit.get("skill_loaded"),
                    "reference_read": audit.get("reference_read"),
                    "source_verdict": audit.get("source_verdict"),
                    "model_turn_completed": (
                        audit.get("state") == "native_turn_recorded"
                        and audit.get("agent_completed") is True
                        and audit.get("answer_present") is True
                    ),
                    "boundary_copyable_code_requires_manual_review": (
                        _manual_boundary_code(wire) if category == "boundary" else False
                    ),
                    "full_mod_semantic_acceptance": False,
                }
            )
    done = [x for x in observations if x["status"] != "not_observed"]
    times = sorted(
        x["elapsed_s"]
        for x in done
        if x["model_turn_completed"] and isinstance(x.get("elapsed_s"), (int, float))
    )
    stat = {
        "model": "codex",
        "observed": len(done),
        "not_observed": 36 - len(done),
        "states": dict(sorted(Counter(x["status"] for x in done).items())),
        "native_completed": sum(bool(x["model_turn_completed"]) for x in done),
        "median_seconds_completed": round(statistics.median(times), 2) if times else None,
        "p95_seconds_completed_nearest_rank": (
            times[max(0, (95 * len(times) + 99) // 100 - 1)] if times else None
        ),
        "positive_exact_source_structural": sum(
            x["category"] == "positive"
            and x["status"]
            in ("positive_source_structure_only", "positive_additional_review_or_hazard")
            for x in done
        ),
        "negative_nonactivation_observed": sum(
            x["status"] == "negative_nonactivation_observed" for x in done
        ),
        "boundary_scope_violations": sum(x["status"] == "boundary_scope_violated" for x in done),
        "boundary_skill_not_loaded": sum(x["status"] == "boundary_skill_not_loaded" for x in done),
        "boundary_copyable_code_requires_manual_review": sum(
            bool(x.get("boundary_copyable_code_requires_manual_review")) for x in done
        ),
        "incomplete_or_tool_failure": sum(
            x["status"] == "incomplete_or_tool_failure" for x in done
        ),
    }
    return {
        "schema_version": 1,
        "suite_id": manifest["suite_id"],
        "source_sha256": manifest["source_sha256"],
        "model_id": MODEL,
        "effort": "medium",
        "native_codex_version": "0.163.0",
        "source_revision": SOURCE,
        "target_claim_scope": "Claude Code CLI 2.1.296",
        "planned_codex_calls": 36,
        "codex_observed": len(done),
        "codex_unobserved": 36 - len(done),
        "stat": stat,
        "rows": observations,
        "native_mod_runtime_verified": False,
        "full_p5_acceptance": False,
        "qualifier": "Same-thread native App Server response/readback plus original prompt; structural Claim evidence is not executable Mod correctness.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    report = summarize()
    if args.dry_run:
        print(
            json.dumps(
                {
                    "observed": report["codex_observed"],
                    "unobserved": report["codex_unobserved"],
                    "stat": report["stat"],
                }
            )
        )
        return 0
    if args.out.exists():
        parser.error("Never silently replace immutable native cohort evidence")
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    args.out.chmod(0o600)
    print(
        json.dumps(
            {
                "observed": report["codex_observed"],
                "unobserved": report["codex_unobserved"],
                "stat": report["stat"],
                "raw_private": True,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
