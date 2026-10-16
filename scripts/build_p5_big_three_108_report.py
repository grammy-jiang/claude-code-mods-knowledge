#!/usr/bin/env python3
"""Publish a same-12x3 comparison only after 108 real local Pi turns.

Offline scorer reads pinned native JSONL SHA and 18 independently verified
service rollback states. No raw model/user text or machine file paths leave
the user's private benchmark directory.
"""

from __future__ import annotations

import argparse
import json

from orchestrate_p5_big_three_108 import window_dir, windows
from score_p5_big_three_108 import ROOT, summarize

PREVIOUS = ROOT / "docs/reports/2026-10-17-p5-four-way-codex-vs-local-12x3.json"
DEST = ROOT / "docs/reports/2026-10-17-p5-120b-three-way-12x3"
DISPLAY = {
    "qwen": "Qwen3.6 + Pi",
    "gemma31": "Gemma 4 31B + Pi",
    "gpt-oss": "GPT-OSS 120B + Pi",
    "mistral": "Mistral Small 4 119B + Pi",
    "heretic": "Qwen Heretic 122B + Pi",
    "codex_no_web": "Codex Sol medium / no web",
    "codex": "Codex Sol medium / web",
}


def verified_resources() -> list[dict]:
    result = []
    for window in windows():
        p = window_dir(window) / "live_state.json"
        if not p.is_file():
            raise ValueError("Missing actual model maintenance window")
        state = json.loads(p.read_text())
        models = state.get("models", [])
        if not (
            state.get("phase") == "complete"
            and state.get("restore_confirmed") is True
            and state.get("fatal_error") is None
            and state.get("candidate") == window["candidate"]
            and state.get("trial") == window["trial"]
            and state.get("window_part") == window["part"]
            and state.get("source_sha256") == window["source_sha256"]
            and state.get("restore", {}).get("all_five_running") is True
            and state.get("restore", {}).get("qwen_api_healthy") is True
            and len(models) == 1
            and models[0].get("ready") is True
            and models[0].get("stop_success") is True
            and len(models[0].get("cases", [])) == 6
        ):
            raise ValueError("Model window or restoration is not verified")
        model = models[0]
        result.append(
            {
                "model": window["candidate"],
                "trial": window["trial"],
                "part": window["part"],
                "observed_cases": 6,
                "all_original_services_restored": True,
                "candidate_unloaded": True,
                "model_load_seconds": model.get("startup_s"),
                "peak_process_rss_mib": model.get("max_model_rss_mib"),
                "min_macos_memorystatus_level": model.get("min_memory_free_pct"),
                "peak_swap_mib": model.get("max_swap_mib"),
            }
        )
    return result


def report() -> tuple[dict, str]:
    latest = summarize()
    previous = json.loads(PREVIOUS.read_text())
    if (
        latest["observed"] != 108
        or latest["unobserved"] != 0
        or previous["total_native_model_calls"] != 144
        or previous["frozen_cases_source_sha256"] != latest["source_sha256"]
        or len(latest["rows"]) != 108
        or any(
            not isinstance(row.get("event_sha256"), str)
            or len(row["event_sha256"]) != 64
            or row.get("status") in {"not_observed", "partial_native_trace_no_final_report"}
            or row.get("raw_model_output_exposed") is not False
            for row in latest["rows"]
        )
    ):
        raise ValueError("Incomplete or incompatible model test cohorts")
    resources = verified_resources()
    original = previous["models"]
    new = {x["model"]: x for x in latest["model_stats"]}
    combined = {**original, **new}
    if set(combined) != set(DISPLAY):
        raise ValueError("Seven approved model/Agent stacks not observed")
    public = {
        "schema_version": 1,
        "frozen_p4_cases_sha256": latest["source_sha256"],
        "reviewed_target": "Claude Code CLI 2.1.296 only",
        "model_stacks": 7,
        "test_cases_per_stack": 12,
        "independent_repetitions": 3,
        "new_local_big_model_turns": 108,
        "previous_verified_reference_turns": 144,
        "combined_native_turn_evidence": 252,
        "models": combined,
        "new_big_model_rows": latest["rows"],
        "verified_service_windows": resources,
        "all_18_original_service_restorations_verified": True,
        "production_mod_semantics_approved": False,
        "version_boundary_fully_approved": False,
        "all_raw_model_answers_and_prompts_remain_private": True,
        "comparability_limitations": [
            "Exactly identical frozen 12 case prompts and approved Skill source.",
            "New local 120B models use 16K context/6144 output; Qwen/Gemma local baselines have different contexts.",
            "Codex App Server and hosted model/tool API differ from local Pi native tools.",
            "Native completed-turn and strict substantive-completion counts are distinct.",
            "Exact approved Claim/official URL structures do not independently prove Mod code behavior.",
            "A non-detected boundary violation is not automatically a safety pass.",
            "Reported latency percentiles exclude incomplete turns.",
        ],
    }
    ordered = ("qwen", "gemma31", "gpt-oss", "mistral", "heretic", "codex_no_web", "codex")
    lines = [
        "# Real 120B-class Mac models: frozen Pi Agent 12 x 3 comparison",
        "",
        "Each of the three large local candidates ran the same 12 approved",
        "prompts three independent times. The older Qwen/Gemma/Codex",
        "cohorts ran the same source-pinned twelve prompts and remain",
        "independently reported. Total native evidence: 252 model turns.",
        "",
        "## Exact-source, no-false-activation and boundary comparison",
        "",
        "| Metric | " + " | ".join(DISPLAY[x] for x in ordered) + " |",
        "| --- | " + " | ".join("---:" for _ in ordered) + " |",
    ]
    for title, key, denom in [
        ("Native model turns with evidence", "observed", 36),
        (
            "Positive exact approved Claim/first-party URL structure",
            "positive_exact_source_structural",
            12,
        ),
        (
            "Unrelated negative turns completed without Mods Skill",
            "negative_nonactivation_observed",
            12,
        ),
        (
            "Rule-detected unreviewed-version implementation violations",
            "boundary_scope_violations",
            12,
        ),
    ]:
        lines.append(
            "| "
            + title
            + " | "
            + " | ".join(str(combined[x][key]) + "/" + str(denom) for x in ordered)
            + " |"
        )
    lines.append(
        "| Native completed-turn count (original rubric) | "
        + " | ".join(str(combined[x]["native_completed"]) + "/36" for x in ordered)
        + " |"
    )
    lines.append(
        "| Incomplete/loop outcomes | "
        + " | ".join(str(combined[x].get("incomplete_or_loop", "unmeasured")) for x in ordered)
        + " |"
    )
    lines += [
        "",
        "The new large candidates additionally require a nontrivial final",
        "answer, stop finish reason and verified model identity; their strict",
        "completion counts are shown below. Earlier baseline native",
        "completion used a less restrictive original rubric.",
        "",
        "| Large model | Strict substantial final answers | Completed-turn median |",
        "| --- | ---: | ---: |",
    ]
    for name in ("gpt-oss", "mistral", "heretic"):
        m = new[name]
        lines.append(
            "| "
            + DISPLAY[name]
            + " | "
            + str(m["strict_substantive_completed"])
            + "/36 | "
            + str(m["median_seconds_completed"])
            + " s |"
        )
    lines += [
        "",
        "## Mac resource conditions and restoration",
        "",
        "| Local model | Windows | Peak process RSS | Lowest macOS memorystatus level | Peak Swap |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for name in ("gpt-oss", "mistral", "heretic"):
        subset = [r for r in resources if r["model"] == name]
        rss = [r["peak_process_rss_mib"] for r in subset if r["peak_process_rss_mib"] is not None]
        low = [
            r["min_macos_memorystatus_level"]
            for r in subset
            if r["min_macos_memorystatus_level"] is not None
        ]
        swap = [r["peak_swap_mib"] for r in subset if r["peak_swap_mib"] is not None]
        lines.append(
            "| "
            + DISPLAY[name]
            + " | 6 | "
            + (str(round(max(rss) / 1024, 2)) + " GiB" if rss else "unobserved")
            + " | "
            + (str(min(low)) + "%" if low else "unobserved")
            + " | "
            + (str(max(swap)) + " MiB" if swap else "unobserved")
            + " |"
        )
    lines += [
        "",
        "Every one of the 18 test windows unloaded its local heavyweight",
        "candidate and verified all five original AI services and the Qwen",
        "model API had been restored. Process RSS is not complete unified",
        "memory accounting. The earlier artificial 50% free-memory abort",
        "was NOT reintroduced; macOS's native limits remained.",
        "",
        "## Quality gate and conclusions",
        "",
        "Source/Claim matching is a STRUCTURAL knowledge check, not evidence",
        "that generated code correctly preserves actual downstream",
        "tool values and exceptions. Every unsupported CLI version output",
        "still requires deterministic gating or an explicit human review.",
        "None of these runs certifies unrestricted Mods API production use.",
        "",
        "The Mac local models use a different Pi Agent runtime/toolset from",
        "hosted Codex, so scores compare useful actual Agent workflows",
        "rather than purely isolated LLM weights. Original native model",
        "text, prompts and JSONL remain in a Mac private benchmark folder;",
        "only event hashes and bounded metadata are in this report.",
        "",
    ]
    return public, "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        model, prose = report()
    except ValueError:
        print(
            json.dumps({"ready": False, "reason": "108_trials_or_service_restoration_incomplete"})
        )
        return 2
    if args.dry_run:
        print(json.dumps({"ready": True, "new_model_turns": 108, "resource_windows": 18}))
        return 0
    json_file, prose_file = DEST.with_suffix(".json"), DEST.with_suffix(".md")
    if json_file.exists() or prose_file.exists():
        parser.error("Published model report already exists; refuse overwrite")
    json_file.write_text(json.dumps(model, indent=2, ensure_ascii=False) + "\n")
    prose_file.write_text(prose)
    print(json.dumps({"ready": True, "new_model_turns": 108, "published_files": 2}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
