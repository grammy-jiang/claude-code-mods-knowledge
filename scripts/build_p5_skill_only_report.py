#!/usr/bin/env python3
"""Publish a privacy-safe, source-pinned 12x3 Skill-only native Pi comparison.

Requires all 36 original candidate Qwen turns and their SHA-verified native
events; does NOT confuse citations with target-CLI code semantic acceptance.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter

from score_p5_skill_only_evidence import ROOT, private_candidate_status

BASENAME = "2026-10-17-p5-skill-only-automatic-evidence"
RESULTS = ROOT / "docs/reports"


def build() -> tuple[dict, str]:
    result = private_candidate_status()
    if (
        result["actual_native_turns_observed"] != 36
        or len(result["rows"]) != 36
        or not result["three_independent_turns_per_case"]
        or result["model_or_plugin_production_approved"] is not False
    ):
        raise ValueError("Incomplete frozen native model/Skill evidence")
    by_case = {}
    for case in sorted({row["case_id"] for row in result["rows"]}):
        three = [row for row in result["rows"] if row["case_id"] == case]
        if len(three) != 3 or {r["trial"] for r in three} != {1, 2, 3}:
            raise ValueError("Missing independent trials or conflicting case identity")
        by_case[case] = {
            "category": three[0]["category"],
            "statuses": dict(sorted(Counter(r["status"] for r in three).items())),
            "skill_reads": sum(r["actual_skill_read"] is True for r in three),
        }
    public = {
        **result,
        "frozen_case_results": by_case,
        "all_original_native_turns_sha_verified": True,
        "same_original_model_provider_and_weights": True,
        "skill_only_source_or_reference_change": True,
        "source_citation_pass_is_not_semantic_mods_pass": True,
    }
    old_pos, new_pos = (
        result["historical_old_skill_positive_source_passes"],
        result["candidate_positive_source_passes"],
    )
    lines = [
        "# P5 Skill-only Qwen3.6 experiment: automatic Claim/source evidence",
        "",
        "Date: 2026-10-17 (Sydney). These are authentic native Pi Agent 1.3.0",
        "auto-discovery turns on the **unchanged local Qwen3.6 35B-A3B**",
        "provider. There was no fine-tuning, model-weight swap, decoding",
        "configuration change, new inference server, or global Skill install.",
        "",
        "## What changed",
        "",
        "The SSOT compiler generates one citation contract for **both**",
        "automatic and explicit Mods Skill activation. Each topic reference",
        "begins with copy-ready approved K-Claim/first-party URL fragment",
        "pairs; a 31-Claim evidence index also derives from the reviewed",
        "single source of truth. No new or unapproved API fact was added.",
        "",
        "## Matched 12-case × 3-turn source and routing results",
        "",
        "| Metric | Historical Qwen Skill | Revised Skill candidate |",
        "| --- | ---: | ---: |",
        f"| Positive exact approved Claim+official URL structure | {old_pos}/12 | {new_pos}/12 |",
        "| Unrelated tasks completed without Mods Skill | "
        + str(
            json.loads((ROOT / "docs/reports/2026-10-17-p5-pi-qwen-gemma31-12x3.json").read_text())[
                "models"
            ][0]["negative_nonactivation_observed"]
        )
        + "/12 | "
        + str(result["candidate_negative_no_skill_completed"])
        + "/12 |",
        "| Rule-detected unreviewed version implementation violations | "
        + str(
            json.loads((ROOT / "docs/reports/2026-10-17-p5-pi-qwen-gemma31-12x3.json").read_text())[
                "models"
            ][0]["boundary_scope_violations"]
        )
        + "/12 | "
        + str(result["candidate_boundary_violations_detected"])
        + "/12 |",
        "",
        "Lower is better for version violations. Zero rule-detected violations",
        "is **NOT** proof of full safety; every other boundary response still",
        "requires code/version review.",
        "",
        "## Frozen original case observations",
        "",
        "| Case | Category | Exact source / correct negative / detected boundary | Skill reads |",
        "| --- | --- | ---: | ---: |",
    ]
    for cid, info in by_case.items():
        category = info["category"]
        success_status = {
            "positive": "positive_exact_source_structure_only",
            "negative": "negative_nonactivation_observed",
            "boundary": "boundary_scope_violated",
        }[category]
        success = info["statuses"].get(success_status, 0)
        lines.append(f"| {cid} | {category} | {success}/3 | {info['skill_reads']}/3 |")
    lines += [
        "",
        "For a boundary row, the value counts **detected failures**, not safety",
        "passes. The table is descriptive of native source/text evidence only.",
        "",
        "## Historical observations and limitations",
        "",
        "- In an initial two-positive native A/B, both the installed Skill",
        "  and an early revised candidate scored 0/2 exact Claim/source passes.",
        "- A follow-up candidate with evidence lines near the bottom of a",
        "  topic reference also failed. The strongest candidate moved",
        "  copy-ready citation pairs to the beginning of topic references",
        "  and placed the source contract in the Skill discovery description.",
        "- The strongest candidate was independently tested with four",
        "  positive cases repeated three times, plus four unrelated",
        "  negatives and four source/version boundaries repeated three times.",
        "- The old Qwen benchmark and this revised Skill pilot share",
        "  frozen prompt SHA/model identity but are **not an interleaved",
        "  randomized A/B** and were executed on separate occasions.",
        "- Exact citations establish evidence **structure**, not",
        "  independent factual correctness or executable Mod semantics.",
        "- The research version scope remains Claude Code CLI 2.1.296.",
        "  This result does not authorize newer API code or stable release.",
        "",
        "## Safety and delivery",
        "",
        "All generated Claude Code, Codex, Pi Agent and ChatGPT Skill/Plugin",
        "files are deterministic copies of the same reviewed source.",
        "A passing package verification is not real ChatGPT Chat-mode",
        "Plugin activation verification. Original native model replies,",
        "tool-event JSONL and personal paths remain in a private Mac",
        "directory; only bounded verdicts, case IDs, timings and SHA256",
        "are published. No production user Skill or Plugin is updated",
        "by this experiment. Keep P5 and stable release gates open.",
        "",
    ]
    return public, "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        data, md = build()
    except (OSError, KeyError, ValueError, TypeError):
        print(
            json.dumps({"ready": False, "reason": "incomplete_or_unverified_native_skill_cohort"})
        )
        return 2
    if args.dry_run:
        print(
            json.dumps(
                {
                    "ready": True,
                    "observed": data["actual_native_turns_observed"],
                    "old_exact_source": data["historical_old_skill_positive_source_passes"],
                    "new_exact_source": data["candidate_positive_source_passes"],
                    "models_modified": False,
                }
            )
        )
        return 0
    target_json = RESULTS / f"{BASENAME}.json"
    target_md = RESULTS / f"{BASENAME}.md"
    if target_json.exists() or target_md.exists():
        parser.error("Immutable public Skill evidence already exists")
    RESULTS.mkdir(parents=True, exist_ok=True)
    target_json.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    target_md.write_text(md)
    print(json.dumps({"report_generated": True, "actual_original_native_turns": 36}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
