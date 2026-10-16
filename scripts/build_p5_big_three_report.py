#!/usr/bin/env python3
"""Sanitize complete native Pi Agent 120B-model trials from private Mac evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOME = Path.home()
LAB = HOME / "Projects/strata-mac-lab/model-campaign"
BENCH = HOME / "Models.noindex/benchmarks"
RUN = BENCH / "pi-big-three-context16k-20261017"
RETRY = BENCH / "pi-big-three-heretic-neg-20261017"
OUTPUT = ROOT / "docs/reports/2026-10-17-p5-big-three-completion"
MODEL_NAMES = {
    "gpt-oss-120b": "GPT-OSS 120B",
    "mistral-small-4-119b": "Mistral Small 4 119B",
    "qwen35-122b-heretic": "Qwen3.5 122B Heretic v2",
}
FROZEN = ("POS-E-01", "POS-Q-01", "NEG-TYPESCRIPT", "BOUND-VERSION-NEW")
SOURCE = "6cbdc9ad6ed9f958072f9cbf4a34c4bbc2d5ef3e"


def _sha(path: Path) -> str:
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 50_000_000:
        raise ValueError("Original native event evidence unavailable")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _state(name: str) -> dict:
    path = LAB / name / "live_state.json"
    record = json.loads(path.read_text())
    if not (
        record.get("phase") == "complete"
        and record.get("restore_confirmed") is True
        and not record.get("fatal_error")
        and record.get("restore", {}).get("all_five_running") is True
        and record.get("restore", {}).get("qwen_api_healthy") is True
    ):
        raise ValueError("Original five AI services were not fully restored")
    return record


def summarize() -> dict:
    original = _state("big-model-20261017-context16k")
    follow_state = _state("big-model-20261017-heretic-repeats")
    audit = json.loads((RUN / "evaluated-models.json").read_text())
    if (
        audit.get("source_revision") != SOURCE
        or audit.get("expected_native_turns") != 12
        or audit.get("qualified_response_tally") != 11
        or audit.get("production_mods_approved") is not False
    ):
        raise ValueError("Source-pinned Mods Skill cohort not verified")
    source_models = {x["model"]: x for x in audit["models"]}
    own_models = {x["model"]: x for x in original["models"]}
    models = []
    for mid, title in MODEL_NAMES.items():
        if mid not in source_models or mid not in own_models:
            raise ValueError("Unobserved candidate")
        m, owner = source_models[mid], own_models[mid]
        if not m["available"] or owner.get("stop_success") is not True:
            raise ValueError("Candidate not started and stopped safely")
        cases = []
        for cid in FROZEN:
            a = [x for x in m["cases"] if x["case_id"] == cid]
            b = [x for x in owner["cases"] if x["case_id"] == cid]
            if len(a) != 1 or len(b) != 1:
                raise ValueError("Original frozen prompt not observed exactly once")
            case, native = a[0], b[0]
            sha = _sha(RUN / "runs" / mid / cid / "events.jsonl")
            if sha != case["raw_sha256"]:
                raise ValueError("Original native JSONL SHA changed")
            cases.append(
                {
                    "id": cid,
                    "complete_answer": case["valid_substantive_answer"] is True,
                    "model_identity_verified": case["model_identity_verified"] is True,
                    "prompt_matched": case["frozen_prompt_matched"] is True,
                    "final_stop_reason": case["model_finish_reason"],
                    "final_characters": case["final_visible_chars"],
                    "skill_actually_read": case["skill_actually_loaded"] is True,
                    "exact_claim_source_verdict": case["claim_official_source_verdict"],
                    "risk_flags": case["risk_flags"],
                    "manual_flags": case["manual_flags"],
                    "native_tools": case["tool_calls"],
                    "native_tool_errors": case["tool_errors"],
                    "elapsed_seconds": case["elapsed_s"],
                    "native_events_sha256": sha,
                    "answer_sha256": native.get("answer_sha256"),
                    "code_semantic_approval": False,
                }
            )
        models.append(
            {
                "id": mid,
                "name": title,
                "runtime": "llama.cpp" if mid == "gpt-oss-120b" else "oMLX",
                "context_window": 16384,
                "max_output_tokens": 6144,
                "load_seconds": m["load_seconds"],
                "peak_process_rss_gib": round(m["max_process_rss_mib"] / 1024, 2),
                "min_macos_memorystatus_percent": m["min_memory_free_pct"],
                "peak_swap_mib": m["peak_swap_mib"],
                "primary_complete": sum(x["complete_answer"] for x in cases),
                "cases": cases,
            }
        )
    follow = follow_state.get("models", [])
    if len(follow) != 1 or follow[0]["model"] != "qwen35-122b-heretic":
        raise ValueError("Heretic-only retest mixed with other candidates")
    attempts = follow[0].get("cases", [])
    if len(attempts) != 3 or {x.get("trial") for x in attempts} != {1, 2, 3}:
        raise ValueError("Three independent Heretic retests required")
    retry = []
    for attempt in sorted(attempts, key=lambda x: x["trial"]):
        if attempt.get("case_id") != "NEG-TYPESCRIPT":
            raise ValueError("Heretic frozen control changed")
        sha = _sha(
            RETRY
            / "runs/qwen35-122b-heretic/NEG-TYPESCRIPT"
            / ("trial-" + str(attempt["trial"]))
            / "events.jsonl"
        )
        if attempt.get("event_sha256") != sha:
            raise ValueError("Private Heretic retest transcript mutated")
        retry.append(
            {
                "trial": attempt["trial"],
                "case_id": "NEG-TYPESCRIPT",
                "context_window": 8192,
                "max_output_tokens": 2400,
                "complete_answer": attempt["substantive_completed_answer"] is True,
                "repeat_tool_abort": attempt["repeat_abort"] is True,
                "elapsed_seconds": attempt["elapsed_s"],
                "native_tool_calls": attempt["tool_calls"],
                "native_events_sha256": sha,
            }
        )
    counts = [m["primary_complete"] for m in models]
    if (
        counts != [4, 4, 3]
        or sum(x["complete_answer"] for x in retry) != 1
        or sum(x["repeat_tool_abort"] for x in retry) != 2
    ):
        raise ValueError("Primary and follow-up completion counts disagree")
    source_passes = sum(
        c["exact_claim_source_verdict"] == "pass"
        for m in models
        for c in m["cases"]
        if c["id"].startswith("POS-")
    )
    scope_flags = sum(
        "unreviewed-version-implementation-present" in c["manual_flags"]
        for m in models
        for c in m["cases"]
        if c["id"] == "BOUND-VERSION-NEW"
    )
    if source_passes != 0 or scope_flags != 3:
        raise ValueError("Source or version-risk metrics changed unexpectedly")
    return {
        "schema_version": 1,
        "date": "2026-10-17",
        "computer": "MacBook Pro M5 Max / 128 GiB",
        "frozen_cases": list(FROZEN),
        "reviewed_knowledge_source": SOURCE,
        "reviewed_target": "Claude Code CLI 2.1.296 only",
        "native_primary_attempts": 12,
        "complete_primary_answers": 11,
        "separate_heretic_attempts": 3,
        "separate_heretic_complete": 1,
        "every_model_completed_each_case_at_least_once": True,
        "not_a_single_configuration_12_of_12_pass": True,
        "models": models,
        "heretic_retest": retry,
        "positive_exact_source_passes": source_passes,
        "version_boundary_implementation_flags": scope_flags,
        "custom_50_percent_abort_disabled": True,
        "isolated_omlx_guard_disabled": True,
        "macos_memory_management_unchanged": True,
        "observed_max_swap_mib": max(original["max_swap_mib"], follow_state["max_swap_mib"]),
        "original_five_ai_services_restored": True,
        "global_pi_defaults_unchanged": True,
        "production_mods_approved": False,
        "full_semantic_code_validation": False,
        "raw_native_transcripts_private": True,
    }


def markdown(data: dict) -> str:
    lines = [
        "# Mac 120B models: Native Pi Agent completion and quality",
        "",
        "Date: 2026-10-17. This is actual Mac-local model inference and",
        "reviewed Claude Code Mods Skill evidence, not a simulated benchmark.",
        "",
        "## 16K context, 6144 maximum output-token primary experiment",
        "",
        "| Model | Engine | Load | Complete | Peak process RSS | Min macOS memorystatus level | Peak swap |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for m in data["models"]:
        lines.append(
            f"| {m['name']} | {m['runtime']} | {m['load_seconds']:.2f}s"
            f" | {m['primary_complete']}/4 | {m['peak_process_rss_gib']} GiB"
            f" | {m['min_macos_memorystatus_percent']}%"
            f" | {m['peak_swap_mib']} MiB |"
        )
    lines += [
        "",
        "Process RSS is not full unified-memory usage. Memorystatus level is a",
        "macOS resource indicator, not a direct free-RAM measurement. The",
        "custom 50-percent termination rule and isolated oMLX memory guard",
        "were disabled; native macOS memory management stayed enabled.",
        "A separate emergency Swap cap and independent restoration watchdog remained.",
        "",
        "## Exact frozen-case final-answer completion",
        "",
        "| Model | POS-E-01 | POS-Q-01 | NEG-TYPESCRIPT | BOUND-VERSION-NEW |",
        "| --- | --- | --- | --- | --- |",
    ]
    for m in data["models"]:
        line = "| " + m["name"] + " | "
        line += (
            " | ".join("completed" if x["complete_answer"] else "incomplete" for x in m["cases"])
            + " |"
        )
        lines.append(line)
    lines += [
        "",
        "Completion means the native model identity matched, the Agent turn",
        "finished with stop rather than length, and nontrivial final text",
        "was returned. Completion is not correct API or code semantics.",
        "",
        "## Heretic TypeScript reliability: separate 8K retest",
        "",
        "The 16K NEG-TYPESCRIPT run timed out after repeated successful reads.",
        "With the unchanged frozen prompt but 8K context, three new attempts were:",
        "",
        "| Trial | Complete | Repeated tool-call abort | Seconds |",
        "| --- | --- | --- | ---: |",
    ]
    for x in data["heretic_retest"]:
        lines.append(
            f"| {x['trial']} | {'yes' if x['complete_answer'] else 'no'}"
            f" | {'yes' if x['repeat_tool_abort'] else 'no'}"
            f" | {x['elapsed_seconds']:.2f} |"
        )
    lines += [
        "",
        "**All three models demonstrated all four case types at least once,",
        "but not 12/12 passes in one uniform configuration.** Qwen Heretic",
        "has inconsistent tool-call termination and remains unreliable.",
        "",
        "## Mods Skill production acceptance: FAIL",
        "",
        "- Six positive answers, exact approved Claim and official links:",
        f"  **{data['positive_exact_source_passes']}/6** structural passes.",
        "- Three unreviewed 2.1.310 version-boundary answers:",
        f"  **{data['version_boundary_implementation_flags']}/3** implementation",
        "  scope violations flagged, including cases with disclaimers.",
        "- Mistral negative TypeScript task completed despite 12 tool errors;",
        "  blocked tool actions must not be treated as approved execution.",
        "- No model's generated Mods code received complete native event",
        "  semantic verification, including preservation of downstream errors.",
        "",
        "## Environment, provenance and decision",
        "",
        "- Two separate bounded maintenance windows stopped and later restored",
        "  Qwen, Whisper, MLX-Audio, Ollama and ComfyUI. All five and the default",
        "  Qwen API were independently verified healthy after each window.",
        "- GPT-OSS ran with llama.cpp and the other two with oMLX; these were",
        "  not Strata-native or MTPLX inference runs.",
        "- Pi global defaults, installed Skill and macOS global Metal/OS limits",
        "  were not changed. Original private event JSONL, answers and local paths",
        "  remain on Mac; only case IDs, metrics and hashes are published.",
        "",
        "**Conclusion:** Three models can complete the four test categories,",
        "but none qualifies for unrestricted production Mods Skill use.",
        "Leave P5 Issue #3 and stable release gates open.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    result = summarize()
    if args.dry_run:
        print(
            json.dumps(
                {
                    "primary_completed": result["complete_primary_answers"],
                    "heretic_retest_completed": result["separate_heretic_complete"],
                    "source_passes": result["positive_exact_source_passes"],
                    "scope_violations": result["version_boundary_implementation_flags"],
                }
            )
        )
        return 0
    path_json = OUTPUT.with_suffix(".json")
    path_md = OUTPUT.with_suffix(".md")
    if path_json.exists() or path_md.exists():
        parser.error("Never overwrite an immutable published report")
    path_json.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    path_md.write_text(markdown(result))
    print(
        json.dumps(
            {
                "saved": True,
                "original_attempts": 12,
                "original_completed": 11,
                "separate_followup": 3,
                "all_original_services_restored": True,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
