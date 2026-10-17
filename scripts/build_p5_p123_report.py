#!/usr/bin/env python3
"""Build a privacy-safe seven-Agent-stack comparison after all real 252 turns.

Publication never implies target CLI Mod runtime correctness or ChatGPT
Chat-mode Skill deployment. Raw model output stays on the original Mac.
"""

from __future__ import annotations

import argparse
import json

from score_p5_p123_seven import ROOT, complete_report

BASE = ROOT / "docs/reports/2026-10-17-p5-p123-seven-stack-12x3"
NAMES = {
    "qwen": "Qwen3.6 + Pi",
    "gemma31": "Gemma 31B + Pi",
    "gpt-oss": "GPT-OSS 120B + Pi",
    "mistral": "Mistral 119B + Pi",
    "heretic": "Qwen Heretic 122B + Pi",
    "codex_no_web": "Codex Sol medium / no web",
    "codex": "Codex Sol medium / web",
}


def build() -> tuple[dict, str]:
    result = complete_report()
    stats = result["models"]
    ordered = list(NAMES)
    if (
        result["actual_native_attempts"] != 252
        or result["resources"]["windows_verified"] != 30
        or len(result["rows"]) != 252
        or set(stats) != set(NAMES)
    ):
        raise ValueError("Cannot publish an incomplete or unverified model cohort")
    head = [
        "# P5 P1–P3 Skill-only evaluation: identical 12×3 benchmark, seven Agent stacks",
        "",
        "Date: 2026-10-17 Australia/Sydney. **252/252 real native model",
        "attempts recorded** (five local models × 36 = 180; two hosted Codex",
        "Sol medium configurations × 36 = 72). All 30 bounded local",
        "maintenance windows stopped their test model and preserved the",
        "initial state of five user AI services. No model fine-tuning,",
        "weights, global settings, current installed Skill or hosted model",
        "configuration changed.",
        "",
        "## What P1, P2 and P3 changed",
        "",
        "- **P1 — Deterministic evidence selection:** the Skill-side selector",
        "  maps a bounded Mod request to approved first-party Claim/URL",
        "  pairs, rendered as an optional task-specific evidence sheet.",
        "  The 31 approved atomic Claims remain the single source of truth.",
        "- **P2 — Task routing and native tool-call guard:** unrelated TypeScript,",
        "  Python, MCP and normal legacy hooks remain outside Mod scope.",
        "  A test-only Pi extension blocks repeated identical native reads",
        "  and excessive tool calls, without modifying their tool results.",
        "- **P3 — Fail-closed delivery:** a preflight gate rejects unreviewed",
        "  CLI versions and unsupported host surfaces; a postflight buffered",
        "  gate checks exact Claim/source evidence, model provenance, final",
        "  turn completion and known Mod code risks before allowing release.",
        "  This gate is measured on local Pi; it is **not implemented on",
        "  native Codex App Server or ChatGPT Chat mode**.",
        "",
        "## Raw model answer results (same frozen prompts)",
        "",
        "| Metric | " + " | ".join(NAMES[k] for k in ordered) + " |",
        "| --- | " + " | ".join("---:" for _ in ordered) + " |",
    ]
    metrics = [
        (
            "Prior exact Claim + official URL (12 positive)",
            "old_positive_exact_source_structural",
            12,
        ),
        (
            "New raw exact Claim + official URL (12 positive)",
            "positive_exact_source_structural",
            12,
        ),
        (
            "New exact URL **and actual candidate Skill read**",
            "positive_source_with_actual_new_skill_read",
            12,
        ),
        (
            "Prior unrelated cases completed, no Mod Skill (12)",
            "old_negative_nonactivation_observed",
            12,
        ),
        ("New unrelated cases completed, no Mod Skill", "negative_nonactivation_observed", 12),
        ("New native completed turns", "native_completed", 36),
        ("New substantive/final turns", "strict_substantive_completed", 36),
        ("Prior detected version/surface violations", "old_detected_boundary_violations", 12),
        ("New detected version/surface violations", "detected_boundary_violations", 12),
        (
            "Actually read the P1 selected-evidence file (positive)",
            "positive_selected_evidence_actually_read",
            12,
        ),
    ]
    for description, key, total in metrics:
        head.append(
            "| "
            + description
            + " | "
            + " | ".join(f"{stats[m][key]}/{total}" for m in ordered)
            + " |"
        )
    head += [
        "",
        "The source metric is **structural**; exact citation IDs and official",
        "URL anchors are not proof that the Mod code would work. A missing",
        "model-resolved identity or incomplete Codex turn is counted as a",
        "failure; original native evidence is preserved, never replaced.",
        "",
        "### P3 research-only buffered delivery gate",
        "",
        "| Local model | Permitted buffered candidate answers / 36 | Research boundaries blocked |",
        "| --- | ---: | ---: |",
    ]
    for m in ordered[:5]:
        head.append(f"| {NAMES[m]} | {stats[m]['P3_buffered_delivery_permitted']}/36 | 12/12 |")
    head += [
        "",
        "The gate can withhold unsafe or incomplete text; it cannot make",
        "the underlying model's knowledge correct. These permitted results",
        "are **not** target CLI Mod semantic acceptance. Both Codex cohorts",
        "remain research-only, so a zero delivery count is **N/A**, not a",
        "Codex model-quality result.",
        "",
        "## Why the new Skill is not ready to promote",
        "",
        "- P1 correctly generated task-specific approved evidence for all",
        "  four positive frozen cases, but **models almost never opened",
        "  the optional selected-evidence file**. The repeated raw results",
        "  reflect primarily the bundled Skill and topic references, not",
        "  confirmed consumption of the dynamically selected evidence.",
        "- The revised workflow improves the local models unevenly:",
        "  Qwen, Gemma, GPT-OSS and Heretic improved relative to their",
        "  original seven-stack source baseline; Mistral stayed at 0/12.",
        "- Codex's exact citation rates **regressed** despite confirming",
        "  that the new isolated Skill was registered. This rules out a",
        "  simple across-model success claim. The two Codex configurations",
        "  have different web-search exposure but identical frozen prompts.",
        "- Some unrelated tasks still triggered the Skill or failed to",
        "  finish, and several boundary answers require review. A zero",
        "  detected violation is never considered a verified safe response.",
        "- Earlier Qwen Skill V3 independently reached 9/12 positive",
        "  citations; this P1–P3 Qwen cohort reached a different score.",
        "  These independent cohorts are NOT an interleaved randomized",
        "  experiment or a controlled model-only comparison.",
        "",
        "## Mac resources and provenance",
        "",
        "- Temporary loopback port 8011 and one candidate model were used",
        "  at a time; initial five user AI services were already unloaded",
        "  before the campaign and were left in that same state afterward.",
        "- All local heavy models used the previously downloaded weights",
        "  and approved native Pi Agent tool interface. No arbitrary",
        "  artificial 50% RAM-free threshold was reintroduced; hardware",
        "  safety limits and bounded emergency Swap protections remained.",
        "- Codex used its actual App Server model/effort metadata and an",
        "  isolated HOME to avoid the old global same-name Skill. Successful",
        "  Skill reads are distinguished from mere registration.",
        "- Model context budgets, tool runtimes and hosted/non-hosted",
        "  inference conditions differ, so this is an **Agent workflow**",
        "  comparison, not causal isolation of model weights.",
        "- Raw events, model answers, host personal paths, provider tokens",
        "  and session identifiers are retained privately on Mac. Public",
        "  artifacts contain only original-case IDs, score diagnostics",
        "  and SHA-256 fingerprints.",
        "",
        "## Release decision",
        "",
        "**No new Skill/Plugin production installation or Stable promotion.**",
        "The reviewed API remains **Claude Code CLI 2.1.296 only**.",
        "The strict native downstream value/exception semantic gate,",
        "actual ChatGPT Chat-mode Plugin acceptance and deterministic",
        "Codex answer-delivery integration remain open. P5 Issue #3",
        "must not be closed based on exact citation counts.",
        "",
    ]
    return result, "\n".join(head)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        data, md = build()
    except ValueError:
        print(json.dumps({"ready": False, "reason": "incomplete_or_invalid_original_evidence"}))
        return 2
    if args.dry_run:
        print(
            json.dumps(
                {
                    "ready": True,
                    "genuine_native_turns": 252,
                    "Mac_windows_verified": 30,
                    "stable_mod_code_verified": False,
                }
            )
        )
        return 0
    target_json = BASE.with_suffix(".json")
    target_md = BASE.with_suffix(".md")
    if target_json.exists() or target_md.exists():
        parser.error("Original complete public report exists; refusing overwrite")
    target_json.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    target_md.write_text(md)
    print(
        json.dumps(
            {
                "ready": True,
                "total_real_turns": 252,
                "public_report_files": 2,
                "user_data_exported": False,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
