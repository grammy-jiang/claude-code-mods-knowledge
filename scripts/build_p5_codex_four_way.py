#!/usr/bin/env python3
"""Publish the authentic four Agent/model-stack comparison, no raw content.

The Codex no-web cohort is a separate 36-run experiment and must have
zero actual native webSearch items. No missing cases can become passes.
"""

from __future__ import annotations

import argparse
import hashlib
import json

from run_p5_codex_paired import PRIVATE, ROOT
from score_p5_codex_no_web import summarize as no_web
from score_p5_codex_paired import summarize as with_web

PI_REPORT = ROOT / "docs/reports/2026-10-17-p5-pi-qwen-gemma31-12x3.json"
OUT_MD = ROOT / "docs/reports/2026-10-17-p5-four-way-codex-vs-local-12x3.md"
OUT_JSON = ROOT / "docs/reports/2026-10-17-p5-four-way-codex-vs-local-12x3.json"

LABELS = [
    ("qwen", "Qwen3.6 + Pi"),
    ("gemma31", "Gemma 4 31B + Pi"),
    ("codex_no_web", "Codex Sol medium, no web"),
    ("codex", "Codex Sol medium, web available"),
]


def _total_web_calls() -> tuple[int, int]:
    observed = 0
    total = 0
    for file in (PRIVATE / "paired/gpt-6.1-sol").glob("*/trial-*/native-wire.jsonl"):
        observed += 1
        for line in file.read_text(errors="replace").splitlines():
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if event.get("method") == "item/completed":
                item = event.get("params", {}).get("item")
                if isinstance(item, dict) and item.get("type") == "webSearch":
                    total += 1
    return observed, total


def report() -> tuple[dict, str]:
    online, offline = with_web(), no_web()
    pi_raw = PI_REPORT.read_bytes()
    pi = json.loads(pi_raw)
    if (
        pi["observed_calls"] != 72
        or len(pi["rows"]) != 72
        or online["codex_observed"] != 36
        or offline["codex_observed"] != 36
        or online["codex_unobserved"] != 0
        or offline["codex_unobserved"] != 0
    ):
        raise ValueError("Incomplete or mismatched model-cohort source baseline")
    if not (online["source_sha256"] == offline["source_sha256"] == pi["source_sha256"]):
        raise ValueError("Frozen model-cohort source mismatch")
    if any(
        x.get("full_mod_semantic_acceptance") is not False for x in online["rows"] + offline["rows"]
    ):
        raise ValueError("No model is yet fully validated for Mod production")
    all_online = [x for x in online["rows"] if x["status"] != "not_observed"]
    all_offline = [x for x in offline["rows"] if x["status"] != "not_observed"]
    if any(x["provider_and_model_verified"] is not True for x in (all_online + all_offline)):
        raise ValueError("One or more model/effort identity attestations missing")
    if any(x.get("native_web_search_calls") != 0 for x in all_offline):
        raise ValueError("Purported no-web Codex used native web search")
    observed, online_web_calls = _total_web_calls()
    if observed != 36:
        raise ValueError("Native web-enabled Codex trace count mismatch")
    model_stats = {
        **{x["model"]: x for x in pi["models"]},
        "codex": online["stat"],
        "codex_no_web": offline["stat"],
    }
    frozen = json.loads((ROOT / "evals/p4_cases.json").read_text())["cases"]
    category_map = {x["id"]: x["category"] for x in frozen}
    case_ids = json.loads((ROOT / "evals/p5_pi_auto_12x3.json").read_text())["case_ids"]
    joined = pi["rows"] + online["rows"] + offline["rows"]
    per_case = []
    for case_id in case_ids:
        cat = category_map[case_id]
        field = {
            "positive": "exact_source_structural",
            "negative": "correct_no_skill_activation",
            "boundary": "detected_scope_violations",
        }[cat]
        entry = {"case_id": case_id, "category": cat, "scores": {}}
        for model_key, _label in LABELS:
            sample = [
                x for x in joined if x.get("case_id") == case_id and x.get("model") == model_key
            ]
            if len(sample) != 3 or {x.get("trial") for x in sample} != {1, 2, 3}:
                raise ValueError("Incomplete case-specific three-trial model comparison")
            if cat == "positive":
                success = {
                    "positive_source_structure_only",
                    "positive_source_pass_code_needs_native_validation",
                    "positive_additional_review_or_hazard",
                }
                number = sum(x["status"] in success for x in sample)
            elif cat == "negative":
                number = sum(x["status"] == "negative_nonactivation_observed" for x in sample)
            else:
                number = sum(x["status"] == "boundary_scope_violated" for x in sample)
            entry["scores"][model_key] = {field: number}
        per_case.append(entry)
    data = {
        "schema_version": 1,
        "reviewed_skill_source_revision": online["source_revision"],
        "frozen_cases_source_sha256": online["source_sha256"],
        "approved_claims_version": "Claude Code CLI 2.1.296 only",
        "case_count_per_stack": 12,
        "repetitions_per_case": 3,
        "total_native_model_calls": 144,
        "pi_native_model_calls": 72,
        "codex_web_available_model_calls": 36,
        "codex_web_disabled_model_calls": 36,
        "native_codex_web_search_calls_in_default_cohort": online_web_calls,
        "native_codex_web_search_calls_disabled_cohort": 0,
        "native_codex_web_disabled_config_verified": True,
        "codex_no_web_observed_timing_count": offline["complete_timing_observations"],
        "codex_no_web_timing_records_missing": 36 - offline["complete_timing_observations"],
        "pi_source_report_sha256": hashlib.sha256(pi_raw).hexdigest(),
        "models": model_stats,
        "per_case": per_case,
        "codex_web_available_rows": online["rows"],
        "codex_web_disabled_rows": offline["rows"],
        "pi_source_report_ref": "docs/reports/2026-10-17-p5-pi-qwen-gemma31-12x3.json",
        "full_p5_production_semantic_acceptance": False,
        "confounders": [
            "Identical original prompts and exact installed source but different Codex and Pi Agent runtimes",
            "Codex online cohort has built-in webSearch and additional globally configured Skills",
            "Codex offline cohort disables native webSearch; it still uses Codex read-only shell and installed plugins",
            "Pi local models use native read/ls/find/grep, provider/quantization and different prompting",
            "Completed-task timings exclude incomplete and include different hosted versus local provider conditions",
        ],
        "immutable_private_raw_model_transcripts_remain_on_mac": True,
    }
    bt = chr(96)
    cols = [model_stats[name] for name, _ in LABELS]
    lines = [
        "# P5 native AI Agent model comparison — Codex vs Qwen/Gemma, 12×3",
        "",
        "Date: 2026-10-17 (Sydney). Identical twelve approved frozen P4 prompts, "
        "three independent real model turns per Agent/model stack. "
        "144 total real native model turns, never synthetic or substituted.",
        "",
        "## Controlled provenance and fair interpretation",
        "",
        "- Codex CLI 0.163.0, OpenAI-hosted "
        + bt
        + "gpt-6.1-sol"
        + bt
        + ", per-turn "
        + bt
        + "medium"
        + bt
        + ". Verified twice through App Server same-thread model/effort "
        "return and authenticated native turns.",
        "- **Two separate Codex cohorts**: ordinary native environment, where "
        "webSearch is available; an offline model cohort with explicit "
        + bt
        + 'web_search="disabled"'
        + bt
        + " and **zero actual native webSearch items**.",
        "- Pi Agent 1.3.0 with existing local Qwen3.6 and Gemma 4 31B, "
        "thinking off. Identical SHA-pinned Mods Skill. "
        "Strict K-Claim ID and exact first-party official source fragment "
        "checker across all stacks.",
        "- This is NOT a fully controlled pure LLM architecture test: "
        "Codex uses hosted model+shell App Server and other globally installed "
        "plugin resources; Pi uses local model+read/ls/find/grep. "
        "Native web-disabled Codex is a closer, but not identical, comparison.",
        "- All boundary prompts run in private, buffer-only experimental sessions; "
        "unverified runnable code is never delivered to the end user.",
        "",
        "## Four-way frozen native results",
        "",
        "| Metric | " + " | ".join(label for _, label in LABELS) + " |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    fields = [
        ("Observed native model turns", "observed", "/36"),
        ("Native completed turns", "native_completed", "/36"),
        (
            "Positive exact Claim/official source structure",
            "positive_exact_source_structural",
            "/12",
        ),
        (
            "Unrelated negatives completed without Mods Skill",
            "negative_nonactivation_observed",
            "/12",
        ),
        (
            "Explicitly detected unreviewed-version scope violations",
            "boundary_scope_violations",
            "/12",
        ),
        (
            "Boundary responses with copyable code needing manual review",
            "boundary_copyable_code_requires_manual_review",
            "/12",
        ),
    ]
    for label, key, suffix in fields:
        lines.append("| " + label + " | " + " | ".join(f"{v[key]}{suffix}" for v in cols) + " |")
    lines.append(
        "| Native incomplete/tool loop or failure | "
        + " | ".join(
            str(v.get("incomplete_or_tool_failure", v.get("incomplete_or_loop"))) for v in cols
        )
        + " |"
    )
    lines.append(
        "| Completed-task median elapsed | "
        + " | ".join(str(v["median_seconds_completed"]) + " s" for v in cols)
        + " |"
    )
    lines.append(
        "| Completed-task P95 | "
        + " | ".join(str(v["p95_seconds_completed_nearest_rank"]) + " s" for v in cols)
        + " |"
    )
    lines += [
        "",
        "## Case-by-case three-run outcomes",
        "",
        "For positive cases this is exact Claim/source structure; for "
        "unrelated negatives it is completed no-Skill routing; for "
        "boundaries it is **detected violations** (lower is better, "
        "other results are NOT certified safe).",
        "",
        "| Frozen case | Kind | " + " | ".join(label for _, label in LABELS) + " |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for entry in per_case:
        field = {
            "positive": "exact_source_structural",
            "negative": "correct_no_skill_activation",
            "boundary": "detected_scope_violations",
        }[entry["category"]]
        lines.append(
            "| "
            + entry["case_id"]
            + " | "
            + entry["category"]
            + " | "
            + " | ".join(str(entry["scores"][model_key][field]) + "/3" for model_key, _ in LABELS)
            + " |"
        )
    lines += [
        "",
        "Positive source structure = presence of actual Skill read plus all "
        "required approved Claim IDs and official URL fragments. This does "
        "**NOT** mean that runnable code is semantically proven correct.",
        "",
        "Zero **detected** version violations is NOT a safety certificate. "
        "All other boundary answers remain manual-review/unverified. "
        "The code-shaped marker also catches explicitly negative examples, "
        "and is intentionally only a review signal.",
        "",
        "Codex no-web cohort has "
        + str(offline["complete_timing_observations"])
        + "/36 measured wall-clock times: one original first turn had "
        "a post-inference report-formatting exception but preserved native "
        "model/Skill/Claim event evidence; the missing duration remains "
        "null rather than fabricated or replayed.",
        "",
        "Codex ordinary-native cohort used "
        + str(online_web_calls)
        + " actual webSearch items across 36 turns; no-web cohort used 0. "
        "The first is an Agent-stack workflow result, not purely a model IQ metric.",
        "",
        "## Detailed verdict distribution",
        "",
    ]
    for key, name in LABELS:
        lines += [f"### {name}", "", "| Native evaluator outcome | Count |", "| --- | ---: |"]
        for status, count in model_stats[key]["states"].items():
            lines.append("| " + bt + status + bt + " | " + str(count) + " |")
        lines.append("")
    lines += [
        "## Independent code check and release gate",
        "",
        "Two eligible original model-generated Codex POS-E-01 observer "
        "snippets passed the retained real Claude Code CLI 2.1.296 "
        "strict validator and safe native mock. This does not "
        "establish downstream tool error identity in real production.",
        "",
        "No model, including Codex, is approved for unrestricted Mod API "
        "code generation until real target CLI event behavior, source "
        "evidence and deterministic version boundary gating all pass. "
        "The current Pi Agent global default Qwen and approved Skill were "
        "not changed; no Claude model calls or GPT-OSS 120B inference.",
        "",
        "All raw user/model content, native JSONL, thread identifiers and "
        "personal host paths remain privately on Mac. Public artifact "
        "contains only case IDs, verdicts, timings and SHA256 metadata.",
        "",
    ]
    return data, "\n".join(lines).rstrip("\n") + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        data, md = report()
    except ValueError:
        print(json.dumps({"ready": False, "reason": "incomplete_or_unverified_model_cohort"}))
        return 2
    if args.dry_run:
        print(json.dumps({"ready": True, "real_native_model_turns": 144, "no_web_verified": True}))
        return 0
    if OUT_JSON.exists() or OUT_MD.exists():
        parser.error("Refusing to overwrite immutable public QA report")
    OUT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    OUT_MD.write_text(md)
    print(
        json.dumps(
            {
                "ready": True,
                "real_native_model_turns": 144,
                "no_web_verified": True,
                "generated_reports": 2,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
