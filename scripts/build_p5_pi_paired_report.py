#!/usr/bin/env python3
"""Emit sanitized, 72-turn-only Pi Qwen/Gemma research conclusions.

Cannot publish a complete comparison when any trial or safe Qwen restoration
is missing. No raw Pi prompt, assistant answer or local paths leave private
benchmark storage.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from score_p5_pi_paired import PRIVATE, summarize

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "docs/reports"
JSON_NAME = "2026-10-17-p5-pi-qwen-gemma31-12x3.json"
MD_NAME = "2026-10-17-p5-pi-qwen-gemma31-12x3.md"


def checked_window_rollbacks() -> dict:
    folder = PRIVATE / "gemma-windows"
    all_files = sorted(folder.glob("round-*/window-*.json"))
    safe = []
    bad = []
    for path in all_files:
        obj = json.loads(path.read_text())
        details = {
            "round": obj.get("round"),
            "phase": obj.get("phase"),
            "restored": obj.get("qwen_restored"),
            "batch_exit_code": obj.get("batch_exit_code"),
            "clean": not any(
                obj.get(k)
                for k in (
                    "error_category",
                    "cleanup_error",
                    "restore_error",
                    "fatal_error",
                )
            ),
            "all_five_services_up": all(obj.get("after", {}).get("service_states", {}).values())
            if obj.get("after", {}).get("service_states")
            else False,
            "qwen_endpoint_up": obj.get("after", {}).get("qwen_healthy") is True,
        }
        if (
            details["phase"] == "complete"
            and details["restored"] is True
            and details["batch_exit_code"] == 0
            and details["clean"]
            and details["all_five_services_up"]
            and details["qwen_endpoint_up"]
        ):
            safe.append(details)
        else:
            bad.append(details)
    return {
        "observed_windows": len(all_files),
        "fully_restored_windows": len(safe),
        "unverified_windows": len(bad),
        "all_restorations_verified": len(all_files) >= 6 and not bad,
        "per_round_window_count": dict(sorted(Counter(str(x["round"]) for x in safe).items())),
    }


def report() -> tuple[dict, str]:
    model_data = summarize()
    rollback = checked_window_rollbacks()
    if (
        model_data["observed"] != 72
        or model_data["unobserved"] != 0
        or not rollback["all_restorations_verified"]
    ):
        raise ValueError("Not a complete 72-case model comparison with verified restorations")
    summary = {
        "schema_version": 1,
        "suite": model_data["suite_id"],
        "source_sha256": model_data["source_sha256"],
        "model_count": 2,
        "cases_per_model": 12,
        "repetitions_per_case": 3,
        "observed_calls": 72,
        "no_gpt_oss_120b_inference": True,
        "reference_version": "Claude Code CLI 2.1.296 only",
        "pi_version": "1.3.0",
        "original_services": rollback,
        "models": model_data["model_stats"],
        "rows": model_data["rows"],
        "model_level_full_semantic_acceptance": False,
        "version_and_code_manual_validation_still_required": True,
        "note": "All real model output and private native events remain on Mac; category distinctions never imply production Mod runtime approval",
    }
    bt = chr(96)
    lines = [
        "# P5 local Pi Agent — Qwen3.6 vs Gemma 4 31B paired 12×3",
        "",
        "Date: 2026-10-17 (Sydney). Exact frozen original 12-case cohort, "
        "three independent sessions per model per case. GPT-OSS 120B deferred.",
        "",
        "## Models and scope",
        "",
        "- Mac M5 Max, 128 GiB. Native Pi Agent 1.3.0 with isolation and "
        "read-only scoped tools. Normal automatic Skill discovery in all trials.",
        "- Original reviewed Mods Skill SHA: "
        + bt
        + "03053cc81e43ca215621db048eb435d675a2685205953019744a5df1bc13530e"
        + bt
        + "; knowledge approved only for Claude Code CLI 2.1.296.",
        "- Qwen3.6 35B-A3B was served by existing local Qwen oMLX endpoint; "
        "Gemma 4 31B by the independent oMLX MTP endpoint while Qwen was "
        "temporarily paused. Different weights/quantization make task-time "
        "comparison descriptive, not a strict identical-hardware latency A/B.",
        "- Each model attempted 36 frozen tasks: 12 positives, 12 unrelated "
        "negatives, 12 boundary tasks. Research-only boundary model text "
        "was buffered privately and **never delivered as a verified answer**.",
        "- Any model-generated runnable code remains blocked pending exact "
        "target CLI strict/mock and downstream-error identity testing.",
        "",
        "## Observed native summary",
        "",
        "| Measure | Qwen3.6 | Gemma 4 31B |",
        "| --- | ---: | ---: |",
    ]
    keyed = {x["model"]: x for x in model_data["model_stats"]}
    left, right = keyed["qwen"], keyed["gemma31"]
    fields = [
        ("Model calls observed", "observed", "36"),
        ("Native completed turns", "native_completed", "36"),
        (
            "Positive exact-Claim/source structural results",
            "positive_exact_source_structural",
            "12",
        ),
        ("Negative nonactivation with completed answer", "negative_nonactivation_observed", "12"),
        ("Explicit unreviewed-version scope violations", "boundary_scope_violations", "12"),
        (
            "Boundary containing copyable code, manual review needed",
            "boundary_copyable_code_requires_manual_review",
            "12",
        ),
        ("Native incomplete or detected identical read loop", "incomplete_or_loop", "36"),
    ]
    for label, field, denominator in fields:
        lines.append(f"| {label} | {left[field]}/{denominator} | {right[field]}/{denominator} |")
    for label, key in [
        ("Median native completed-task elapsed seconds", "median_seconds_completed"),
        ("P95 completed-task seconds (nearest-rank)", "p95_seconds_completed_nearest_rank"),
    ]:
        lines.append(f"| {label} | {left[key]} | {right[key]} |")
    lines += [
        "",
        "The positive count means **exact official source structure**, not full "
        "code semantic correctness. Only the narrow "
        + bt
        + "boundary_scope_violated"
        + bt
        + " rubric is counted as an explicit high-severity scope failure; "
        "other boundaries require human review and are NOT counted safe.",
        "",
        "## Full verdict distributions",
        "",
    ]
    for name, stat in (("Qwen3.6", left), ("Gemma 4 31B", right)):
        lines += [f"### {name}", "", "| Native scoring outcome | Count |", "| --- | ---: |"]
        for status, number in stat["states"].items():
            lines.append(f"| {bt}{status}{bt} | {number} |")
        lines.append("")
    lines += [
        "## Safety, inference and restoration",
        "",
        "- Resource guard retained. Gemma model was serially tested in six "
        "bounded Qwen maintenance windows; the Qwen launchd service was "
        "restored and its local models endpoint confirmed healthy after "
        "each window. Other four AI services remained running.",
        f"- Verified rollback windows: {rollback['fully_restored_windows']}/"
        f"{rollback['observed_windows']}; per-round windows: "
        + ", ".join(f"{k}={v}" for k, v in rollback["per_round_window_count"].items())
        + ".",
        "- Original Pi global provider/model settings and installed Skill were not modified. "
        "No Claude model tokens, ChatGPT ordinary Chat-mode requests, or GPT-OSS 120B model calls.",
        "- All original native JSONL, prompts, responses, local paths and private "
        "model-service logs stay in the protected Mac benchmark directory. "
        "This report stores only bounded case IDs, response metadata, "
        "SHA256 and fail-closed verdicts.",
        "",
        "## Decision boundary",
        "",
        "**Neither model is approved for unrestricted Mods Skill code delivery** "
        "unless it meets the complete source, runtime, version and output "
        "safety gates. Do not silently switch the existing Pi default based "
        "on this benchmark. The results guide a future model/guardrail "
        "choice rather than certifying full P5 host acceptance.",
        "",
    ]
    return summary, "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        data, markdown = report()
    except ValueError:
        print(json.dumps({"ready": False, "reason": "incomplete_cases_or_unverified_rollback"}))
        return 2
    if args.dry_run:
        print(
            json.dumps(
                {
                    "ready": True,
                    "observed": data["observed_calls"],
                    "verified_rollback": data["original_services"]["all_restorations_verified"],
                }
            )
        )
        return 0
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    js, md = REPORT_DIR / JSON_NAME, REPORT_DIR / MD_NAME
    if js.exists() or md.exists():
        raise ValueError("Public evaluation already exists; never silently overwrite evidence")
    js.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    md.write_text(markdown.rstrip("\n") + "\n")
    print(
        json.dumps(
            {"ready": True, "observed": 72, "verified_rollback": True, "reports_generated": 2}
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
