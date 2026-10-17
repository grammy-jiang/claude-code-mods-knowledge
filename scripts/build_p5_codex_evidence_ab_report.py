#!/usr/bin/env python3
"""Publish honest frozen and heldout Codex V3 Skill evidence A/B/C results.

Can run only when 108 + 36 genuine native model trials are SHA-verified,
with the same pinned V3 Skill/model/effort across experimental conditions.
No original model reply, credential, session ID or private path is exported.
"""

from __future__ import annotations

import argparse
import json

from run_p5_codex_evidence_ab_case import ROOT
from score_p5_codex_ab_holdout import score as holdout_score
from score_p5_codex_evidence_ab import score as original_score

BASENAME = "2026-10-17-p5-codex-skill-evidence-context-ab"
BASE = ROOT / "docs/reports" / BASENAME
NAMES = {
    "A_v3": "A: historical V3 Skill",
    "B_context": "B: V3 + verified Evidence Pack",
    "C_context_gate": "C: B + buffered P3 gate",
}


def _paired_improvement(rows: list[dict]) -> dict:
    frozen = {
        (x["case_id"], x["trial"], x["condition"]): x for x in rows if x["category"] == "positive"
    }
    instances = {(x["case_id"], x["trial"]) for x in rows if x["category"] == "positive"}
    compared = {}
    for a, b in (("A_v3", "B_context"), ("B_context", "C_context_gate")):
        gains = regressions = unchanged_pass = unchanged_fail = 0
        for cid, trial in instances:
            before = frozen[(cid, trial, a)]["raw_exact_source_pass"]
            after = frozen[(cid, trial, b)]["raw_exact_source_pass"]
            if not before and after:
                gains += 1
            elif before and not after:
                regressions += 1
            elif before and after:
                unchanged_pass += 1
            else:
                unchanged_fail += 1
        compared[f"{a}_vs_{b}"] = {
            "paired_cases_and_trial_slots": len(instances),
            "improved": gains,
            "regressed": regressions,
            "both_pass": unchanged_pass,
            "both_fail": unchanged_fail,
        }
    return compared


def report() -> tuple[dict, str]:
    a = original_score(complete=True)
    b = holdout_score(complete=True)
    if (
        a["verified_original_native_turns"] != 108
        or b["verified_original_native_turns"] != 36
        or a["frozen_v3_skill_sha256"] != b["frozen_v3_skill_sha256"]
        or a["model"] != "gpt-6.1-sol"
        or b["model"] != "gpt-6.1-sol"
        or a["effort"] != "medium"
        or b["effort"] != "medium"
        or a["web_search"] != "disabled"
        or b["web_search"] != "disabled"
    ):
        raise ValueError("Incomplete or differently attributed Codex V3 A/B/C evidence")
    paired = _paired_improvement(a["rows"])
    heldout_paired = _paired_improvement(b["rows"])
    data = {
        "schema_version": 1,
        "title": "Skill-only Codex Sol medium task Evidence Pack A/B/C experiment",
        "research_date": "2026-10-17",
        "model": "gpt-6.1-sol",
        "thinking": "medium",
        "web_search": "disabled",
        "reviewed_mods_cli": "2.1.296 only",
        "freeze_v3_skill_sha256": a["frozen_v3_skill_sha256"],
        "frozen_original_12x3": a,
        "new_independent_holdout_4x3": b,
        "paired_original_raw_source_comparison": paired,
        "paired_holdout_raw_source_comparison": heldout_paired,
        "total_real_original_native_model_turns": 144,
        "experimental_intervention": (
            "Native Codex thread/start.developerInstructions is injected only "
            "for reviewed Mods positive tasks in conditions B and C; original "
            "user prompts, model, effort, no-web, read-only sandbox and V3 Skill "
            "bytes are constant. C adds a postflight research-only gate."
        ),
        "authoritative_evidence_source": "31 approved version-scoped SSOT Claims",
        "developer_context_delivery_is_not_proven_model_consumption": True,
        "P3_is_a_postflight_filter_not_raw_model_intelligence": True,
        "native_2_1_296_mod_semantics_verified": False,
        "production_codex_gate_deployed": False,
        "chatgpt_chat_mode_verified": False,
        "production_skill_replaced": False,
        "model_weights_or_settings_changed": False,
        "raw_original_model_text_and_prompts_private": True,
    }

    head = [
        "# Codex Sol medium — task-scoped Skill evidence A/B/C native comparison",
        "",
        "Date: 2026-10-17 (Sydney). **144 genuine native Codex App Server",
        "turns**: 108 old frozen 12-case × 3-condition × 3-repeat turns and",
        "36 independent heldout 4-case × 3-condition × 3-repeat turns.",
        "",
        "All conditions used the same approved V3 Skill bytes, GPT-6.1 Sol",
        "medium, web search disabled, read-only sandbox, single-turn ephemeral",
        "native App Server process and identical original user prompt bytes.",
        "There was NO fine-tuning, model setting/weight adjustment or global",
        "Skill/ChatGPT Plugin installation.",
        "",
        "## Exact frozen twelve-case comparison",
        "",
        "| Metric | " + " | ".join(NAMES[c] for c in NAMES) + " |",
        "| --- | " + " | ".join("---:" for _ in NAMES) + " |",
    ]
    for label, key, denominator in (
        ("Raw exact approved Claim + official URL (positive)", "positive_raw_exact_source", 12),
        (
            "Exact source plus actual new V3 Skill read",
            "positive_source_with_verified_skill_read",
            12,
        ),
        ("Normal unrelated no-Skill completion", "negative_correct_nonactivation", 12),
        ("Original native turn completed", "completed", 36),
        ("Selected SSOT context submitted (positive only)", "context_submitted", 12),
        ("Rule-detected version boundary risks", "boundary_rule_risks", 12),
    ):
        head.append(
            "| "
            + label
            + " | "
            + " | ".join(f"{a['conditions'][c][key]}/{denominator}" for c in NAMES)
            + " |"
        )
    head += [
        "",
        "**Raw model scores are measured on actual assistant messages,**",
        "not on postfilled citations. B/C developer context receipts confirm",
        "delivery to the native Codex thread, not that the model internally",
        "used every cited Claim. C's gate executes AFTER generation and",
        "therefore cannot improve the model's underlying raw accuracy.",
        "",
        "## Separately frozen heldout four-case comparison",
        "",
        "| Metric | " + " | ".join(NAMES[c] for c in NAMES) + " |",
        "| --- | " + " | ".join("---:" for _ in NAMES) + " |",
    ]
    for label, key, denominator in (
        ("Raw exact approved Claim + official URL (positive)", "positive_raw_exact_source", 6),
        (
            "Exact source with actual new V3 Skill read",
            "positive_source_with_verified_skill_read",
            6,
        ),
        ("Unrelated no-Skill completion", "negative_correct_nonactivation", 3),
        ("Native completed turns", "completed", 12),
        ("Task-selected developer context submitted", "context_submitted", 6),
        ("Detected boundary implementation risks", "boundary_rule_risks", 3),
    ):
        head.append(
            "| "
            + label
            + " | "
            + " | ".join(f"{b['conditions'][c][key]}/{denominator}" for c in NAMES)
            + " |"
        )
    head += [
        "",
        "Heldout prompts were frozen independently of the original P4 source,",
        "covering transparent observers, strict validation path, unrelated",
        "asyncio reentry and a genuinely unreviewed CLI target. There is",
        "no historical external holdout baseline.",
        "",
        "## Paired evidence of impact",
        "",
    ]
    for title, comparisons in (("Frozen cases", paired), ("Heldout", heldout_paired)):
        head.append(f"### {title}")
        for label, entry in comparisons.items():
            head.append(
                f"- {label}: improved {entry['improved']}, regressed {entry['regressed']}, "
                f"both-pass {entry['both_pass']}, both-fail {entry['both_fail']} "
                f"(n={entry['paired_cases_and_trial_slots']})"
            )
        head.append("")
    head += [
        "## P3 postflight buffer and release safety",
        "",
        "C used a deterministic, privately buffered gate. For an approved",
        "positive case, it checks model/Skill provenance, actual Claim/URL",
        "links, target version and executable Mod code risks. No unknown",
        "API version code is released. A result with copyable Mod code",
        "still needs independent reviewed CLI native runtime verification.",
        "",
        f"- Frozen C condition: {a['conditions']['C_context_gate']['P3_buffered_structural_candidates_permitted']}/36 "
        "structural-only candidate outcomes passed the gate.",
        f"- Heldout C condition: {b['conditions']['C_context_gate']['P3_buffered_structural_candidates_permitted']}/12 "
        "structural-only candidate outcomes passed the gate.",
        "",
        "Neither result is production semantic approval; the experiment",
        "withheld all raw model text from end users.",
        "",
        "## Limitations and next decision",
        "",
        "- Historical previous Codex no-web exact-source baselines were 12/12",
        "  and 6/12 under different Skill/agent environments. This A/B/C",
        "  uses a newly fixed frozen V3 and one isolated Codex App Server",
        "  environment, which is the cleaner causal comparison.",
        "- Independent runs, changing service conditions and small samples",
        "  can produce sampling noise. Results are a workflow comparison,",
        "  not a proof that model weights or any Agent are inherently poor.",
        "- Developer context delivery is explicit and recorded, but there",
        "  is no verifiable internal model-consumption signal.",
        "- A structural Claim/URL match does NOT verify target-native",
        "  Mods tool values, exceptions or runnable code.",
        "- Full ChatGPT Chat-mode Plugin activation and production P3",
        "  delivery controls remain outside this Codex-only experiment.",
        "",
        "**Do not install/promote the Skill or close P5 Issue #3 on this",
        "experiment alone.** All original private model text, thread IDs,",
        "account details and host paths remain on Mac.",
        "",
    ]
    return data, "\n".join(head)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        data, text = report()
    except (ValueError, OSError):
        print(
            json.dumps(
                {"ready": False, "reason": "original_and_holdout_native_evidence_incomplete"}
            )
        )
        return 2
    if args.dry_run:
        print(
            json.dumps(
                {
                    "ready": True,
                    "native_original_turns": 144,
                    "separate_holdout_cases": 4,
                    "production_semantic_acceptance": False,
                }
            )
        )
        return 0
    jpath = BASE.with_suffix(".json")
    mpath = BASE.with_suffix(".md")
    if jpath.exists() or mpath.exists():
        parser.error("Previous immutable study report already exists")
    jpath.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    mpath.write_text(text)
    print(
        json.dumps({"published": True, "native_turns": 144, "raw_content_in_public_files": False})
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
