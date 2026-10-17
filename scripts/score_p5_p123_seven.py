#!/usr/bin/env python3
"""Exact 12x3 native model/Skill study scorer, original evidence only.

No prompts, original replies, account/session IDs, or private paths in
published artifacts. Structural Claim/official URL success is NOT native
Mods code semantics. P3 buffering counts are separate from raw model QA.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shlex
from collections import Counter
from pathlib import Path

from run_p5_p123_local_case import MODELS, PLAN, PRIVATE, ROOT

from mods_knowledge.claims import load_claims
from mods_knowledge.registry import load_registry
from mods_knowledge.task_evidence import render_evidence_pack, select_task_evidence

MODEL_IDS = {
    **{x: xval[0] + "/" + xval[1] for x, xval in MODELS.items()},
    "codex": "openai/gpt-6.1-sol",
    "codex_no_web": "openai/gpt-6.1-sol",
}
OLD_BASELINE = ROOT / "docs/reports/2026-10-17-p5-four-way-codex-vs-local-12x3.json"
OLD_SEVEN = ROOT / "docs/reports/2026-10-17-p5-120b-three-way-12x3.json"


class ModelQAEvidenceError(ValueError):
    """Incomplete native evidence must not be counted as model success."""


def frozen() -> tuple[dict, dict[str, dict], dict[str, dict]]:
    manifest = json.loads(PLAN.read_text())
    original = ROOT / manifest["source_file"]
    if (
        hashlib.sha256(original.read_bytes()).hexdigest() != manifest["source_sha256"]
        or len(manifest["case_ids"]) != len(set(manifest["case_ids"])) != 12
        or manifest["repetitions"] != 3
        or manifest["expected_total_local_trials"] != 180
        or manifest["expected_total_codex_trials"] != 72
    ):
        raise ModelQAEvidenceError("Original frozen 12x3 trial source mismatch")
    catalog = {c["id"]: c for c in json.loads(original.read_text())["cases"]}
    approved = load_claims(
        ROOT / "claims",
        load_registry(ROOT / "sources/registry.json"),
        ROOT / "sources/snapshots",
        ROOT / "decisions",
    )
    return manifest, catalog, approved


def _hash_events(path: Path) -> str:
    if not path.is_file() or path.is_symlink() or not 0 < path.stat().st_size < 50_000_000:
        raise ModelQAEvidenceError("Missing or unbounded original event trace")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _task_pack_digest(selected: dict) -> str | None:
    if not selected["ready"]:
        return None
    return hashlib.sha256(render_evidence_pack(selected).encode()).hexdigest()


def _pi_verified_selected_read(trace: Path) -> bool:
    starts = {}
    for line in trace.read_text(errors="replace").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get("type") == "tool_execution_start" and event.get("toolName") == "read":
            args = event.get("args")
            tid = event.get("toolCallId")
            if isinstance(args, dict) and isinstance(tid, str):
                starts[tid] = Path(str(args.get("path", ""))).name
        elif event.get("type") == "tool_execution_end":
            if (
                event.get("toolName") == "read"
                and event.get("isError") is False
                and starts.get(event.get("toolCallId")) == "selected-evidence.md"
            ):
                return True
    return False


def _codex_verified_selected_read(trace: Path) -> bool:
    for line in trace.read_text(errors="replace").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get("method") != "item/completed":
            continue
        item = event.get("params", {}).get("item")
        if not isinstance(item, dict) or (
            item.get("type") != "commandExecution"
            or item.get("status") != "completed"
            or item.get("exitCode") != 0
            or not isinstance(item.get("command"), str)
        ):
            continue
        try:
            args = shlex.split(item["command"])
            if len(args) >= 3 and args[0].endswith(("/zsh", "/bash", "/sh")) and args[1] == "-lc":
                args = shlex.split(args[2])
        except ValueError:
            continue
        if (
            args
            and args[0] in {"cat", "sed", "head", "tail"}
            and any(Path(arg).name == "selected-evidence.md" for arg in args[1:])
        ):
            return True
    return False


def grade(
    category: str,
    *,
    completed: bool,
    skill_read: bool | None,
    exact_source: str | None,
    boundary_flag: bool,
) -> str:
    if boundary_flag and category == "boundary":
        return "boundary_scope_violated"
    if not completed:
        return "native_incomplete_or_loop"
    if category == "negative":
        return (
            "negative_nonactivation_observed"
            if skill_read is False
            else "negative_false_skill_activation"
        )
    if skill_read is not True:
        return "expected_skill_not_loaded"
    if category == "boundary":
        return "boundary_manual_review_required"
    if exact_source != "pass":
        return "positive_exact_source_missing"
    return "positive_source_structure_only"


def local_rows(manifest: dict, cases: dict, approved: dict) -> list[dict]:
    rows = []
    for candidate, info in MODELS.items():
        for cid in manifest["case_ids"]:
            original = cases[cid]
            selected = select_task_evidence(original["prompt"], approved, version="2.1.296")
            for trial in (1, 2, 3):
                folder = PRIVATE / "paired" / candidate / cid / f"trial-{trial}"
                fp = folder / "report.json"
                if not fp.is_file():
                    rows.append(
                        {
                            "model": candidate,
                            "case_id": cid,
                            "trial": trial,
                            "category": original["category"],
                            "status": "not_observed",
                        }
                    )
                    continue
                report = json.loads(fp.read_text())
                wire = folder / "events.jsonl"
                if (
                    report.get("case_id") != cid
                    or report.get("candidate") != candidate
                    or report.get("trial") != trial
                    or report.get("raw_output_exposed") is not False
                    or report.get("P123_raw_reply_exposed") is not False
                    or report.get("model_calls") != 1
                    or report.get("P123_true_model_calls") != 1
                    or report.get("P123_skill_bundled_sha256") != manifest["candidate_skill_sha256"]
                    or report.get("skill_sha256") != manifest["candidate_skill_sha256"]
                    or report.get("candidate_prompt_sha256")
                    != hashlib.sha256(original["prompt"].encode()).hexdigest()
                    or report.get("P123_selected_claim_ids")
                    != [c["claim_id"] for c in selected["claims"]]
                    or report.get("P123_selection_intent") != selected["intent"]
                    or report.get("P123_selected_evidence_sha256") != _task_pack_digest(selected)
                    or report.get("P123_effective_thinking") != info[3]
                    or report.get("P123_effective_context_window") != info[4]
                    or report.get("P123_effective_max_output_tokens") != info[5]
                    or report.get("event_sha256") != _hash_events(wire)
                ):
                    raise ModelQAEvidenceError("Native local source/Skill/case evidence changed")
                evidence_file = (
                    folder
                    / "agent/skills/claude-code-mods-development/references/selected-evidence.md"
                )
                if selected["ready"]:
                    if _hash_events(evidence_file) != _task_pack_digest(selected):
                        raise ModelQAEvidenceError("Local task-specific evidence has changed")
                elif evidence_file.exists():
                    raise ModelQAEvidenceError(
                        "Unrelated model trial received unexpected Mods evidence"
                    )
                selected_actual_read = _pi_verified_selected_read(wire)
                gate = report.get("gate") or {}
                if original["category"] == "boundary":
                    identity = report.get("observed_model") == MODEL_IDS[candidate]
                    skill_read = report.get("research_actual_skill_read")
                    scope = report.get("research_verdict") == "boundary_scope_violated"
                else:
                    identity = gate.get("model_provenance_matched") is True
                    skill_read = gate.get("skill_read_observed")
                    scope = False
                completed = (
                    identity
                    and report.get("native_exit_code") == 0
                    and report.get("timed_out") is False
                    and not report.get("repeat_abort_reason")
                    and report.get("final_stop_reason") == "stop"
                    and report.get("agent_end_count", 0) > 0
                    and report.get("substantive_completed_answer") is True
                )
                rows.append(
                    {
                        "model": candidate,
                        "case_id": cid,
                        "trial": trial,
                        "category": original["category"],
                        "status": grade(
                            original["category"],
                            completed=completed,
                            skill_read=skill_read,
                            exact_source=gate.get("source_verdict"),
                            boundary_flag=scope,
                        ),
                        "native_completed": report.get("native_exit_code") == 0 and identity,
                        "strict_substantive_completed": completed,
                        "model_provenance_verified": identity,
                        "actual_skill_read": skill_read,
                        "raw_exact_source_verdict": gate.get("source_verdict"),
                        "boundary_rule_flag": scope,
                        "P3_buffered_delivery_permitted": gate.get("allow_raw_candidate_delivery")
                        is True
                        and original["category"] != "boundary",
                        "P3_research_boundary_never_delivered": original["category"] == "boundary",
                        "P3_semantic_code_approval": False,
                        "raw_events_sha256": report["event_sha256"],
                        "elapsed_seconds": report.get("elapsed_s"),
                        "model_original_prompt_unchanged": True,
                        "selected_evidence_actually_read": selected_actual_read,
                        "private_model_text_released": False,
                    }
                )
    return rows


def codex_rows(manifest: dict, cases: dict, approved: dict) -> list[dict]:
    """Require attributable same-thread Codex metadata and original native wire."""
    rows = []
    for cohort, web_disabled in (("codex_no_web", True), ("codex", False)):
        for cid in manifest["case_ids"]:
            original = cases[cid]
            selected = select_task_evidence(original["prompt"], approved, version="2.1.296")
            for trial in (1, 2, 3):
                folder = PRIVATE / "codex-v2" / cohort / cid / f"trial-{trial}"
                fp = folder / "report.json"
                if not fp.is_file():
                    rows.append(
                        {
                            "model": cohort,
                            "case_id": cid,
                            "trial": trial,
                            "category": original["category"],
                            "status": "not_observed",
                        }
                    )
                    continue
                report = json.loads(fp.read_text())
                wire = folder / "native-wire.jsonl"
                source_sha = _hash_events(wire)
                if (
                    report.get("case_id") != cid
                    or report.get("candidate") != cohort
                    or report.get("trial") != trial
                    or report.get("raw_reply_exposed") is not False
                    or report.get("original_source_sha256") != manifest["source_sha256"]
                    or report.get("candidate_skill_sha256") != manifest["candidate_skill_sha256"]
                    or report.get("private_wire_sha256") != source_sha
                    or report.get("registered_isolated_skill") is not True
                    or report.get("model_requested") != "gpt-6.1-sol"
                    or report.get("effort_requested") != "medium"
                    or (
                        report.get("native_case_completed") is True
                        and (
                            report.get("model_server_resolved") != "gpt-6.1-sol"
                            or report.get("effort_server_resolved") != "medium"
                        )
                    )
                    or report.get("web_search_disabled") is not web_disabled
                    or report.get("selected_claim_ids")
                    != [row["claim_id"] for row in selected["claims"]]
                    or report.get("selected_evidence_sha256") != _task_pack_digest(selected)
                    or report.get("semantic_mods_correctness_verified") is not False
                    or report.get("production_delivery") is not False
                    or report.get("boundary_preflight_would_block")
                    is not (original["category"] == "boundary")
                ):
                    raise ModelQAEvidenceError("Native Codex source or Skill provenance changed")
                evidence_file = (
                    folder
                    / ".agents/skills/claude-code-mods-development/references/selected-evidence.md"
                )
                if selected["ready"]:
                    if _hash_events(evidence_file) != _task_pack_digest(selected):
                        raise ModelQAEvidenceError("Codex task-specific evidence has changed")
                elif evidence_file.exists():
                    raise ModelQAEvidenceError("Codex unrelated trial received Mods evidence")
                selected_actual_read = _codex_verified_selected_read(wire)
                count = report.get("native_web_search_count")
                if type(count) is not int or count < 0 or (web_disabled and count):
                    raise ModelQAEvidenceError("Web search constraint violated")
                # Keep original scoring rubric separate from environment
                # attribution. A correct URL without a proved Skill read
                # is raw structural success, NOT successful Skill adoption.
                identity = (
                    report.get("model_server_resolved") == "gpt-6.1-sol"
                    and report.get("effort_server_resolved") == "medium"
                )
                complete = report.get("native_case_completed") is True and identity
                read = report.get("actual_candidate_skill_read")
                if type(read) is not bool:
                    if complete:
                        raise ModelQAEvidenceError(
                            "Completed Codex turn lacks native Skill-read attestation"
                        )
                    read = None
                if complete and read == original["expected_activation"]:
                    status = grade(
                        original["category"],
                        completed=True,
                        skill_read=read,
                        exact_source=report.get("source_verdict"),
                        boundary_flag=report.get("native_scorer_verdict")
                        == "boundary_scope_violated",
                    )
                else:
                    status = grade(
                        original["category"],
                        completed=complete,
                        skill_read=read,
                        exact_source=report.get("source_verdict"),
                        boundary_flag=report.get("native_scorer_verdict")
                        == "boundary_scope_violated",
                    )
                if original["category"] == "positive" and complete and not read:
                    status = "expected_skill_not_loaded"
                if original["category"] == "negative" and complete and read:
                    status = "negative_false_skill_activation"
                rows.append(
                    {
                        "model": cohort,
                        "case_id": cid,
                        "trial": trial,
                        "category": original["category"],
                        "status": status,
                        "native_completed": complete,
                        "strict_substantive_completed": complete,
                        "model_provenance_verified": True,
                        "actual_skill_read": read,
                        "raw_exact_source_verdict": report.get("source_verdict"),
                        "boundary_rule_flag": report.get("native_scorer_verdict")
                        == "boundary_scope_violated",
                        # Codex's native App Server QA is research-only; the
                        # Pi buffering gate is NOT assumed to protect it.
                        "P3_buffered_delivery_permitted": False,
                        "P3_gate_available_for_host": False,
                        "P3_research_boundary_never_delivered": True,
                        "P3_semantic_code_approval": False,
                        "native_web_search_count": count,
                        "registered_isolated_skill": True,
                        "selected_evidence_actually_read": selected_actual_read,
                        "raw_events_sha256": source_sha,
                        "model_original_prompt_unchanged": True,
                        "private_model_text_released": False,
                    }
                )
    return rows


def resource_verdict() -> dict:
    path = PRIVATE / "local-campaign.json"
    if not path.is_file():
        raise ModelQAEvidenceError("Missing local Mac test campaign state")
    campaign = json.loads(path.read_text())
    reference = campaign.get("original_services")
    if not isinstance(reference, dict) or len(reference) != 5:
        raise ModelQAEvidenceError("Original Mac service state not preserved")
    windows = campaign.get("verified_windows")
    if (
        campaign.get("status") != "all_180_original_turns_observed"
        or not isinstance(windows, list)
        or len(windows) != 30
    ):
        raise ModelQAEvidenceError("Original model service windows incomplete")
    seen = set()
    for window in windows:
        key = (window.get("candidate"), window.get("trial"), window.get("part"))
        if (
            key in seen
            or key[0] not in MODELS
            or key[1] not in (1, 2, 3)
            or key[2] not in (1, 2)
            or window.get("native_cases") != 6
            or window.get("temporary_model_stopped") is not True
            or window.get("original_user_services_preserved") is not True
            or window.get("port_8011_closed") is not True
        ):
            raise ModelQAEvidenceError("Mac service stop/preserve evidence incomplete")
        seen.add(key)
        path = (
            PRIVATE
            / "windows"
            / window["candidate"]
            / f"round-{window['trial']}"
            / f"part-{window['part']}"
            / "active-model-state.json"
        )
        if not path.is_file():
            raise ModelQAEvidenceError("Original per-window resource evidence missing")
        actual = json.loads(path.read_text())
        if (
            actual.get("phase") != "completed_and_unloaded"
            or actual.get("test_model_unloaded") is not True
            or actual.get("original_services_preserved") is not True
            or actual.get("port_8011_closed") is not True
            or actual.get("resource_emergency")
            or len(actual.get("native_cases", [])) != 6
        ):
            raise ModelQAEvidenceError("Unverified original model window clean-up")
        for item in actual["native_cases"]:
            report_path = (
                PRIVATE
                / "paired"
                / window["candidate"]
                / item["case_id"]
                / f"trial-{window['trial']}"
                / "report.json"
            )
            if (
                not report_path.is_file()
                or hashlib.sha256(report_path.read_bytes()).hexdigest()
                != item["native_result_sha256"]
            ):
                raise ModelQAEvidenceError("Missing or modified window/native report SHA")
    return {
        "windows_verified": 30,
        "local_native_attempts": 180,
        "original_service_state_preserved": True,
        "original_service_running_count": sum(v is True for v in reference.values()),
        "temporary_model_stopped_per_window": True,
        "original_model_port_closed_per_window": True,
        "windows": [
            {
                "model": w["candidate"],
                "trial": w["trial"],
                "part": w["part"],
                "cases": w["native_cases"],
                "min_macos_memorystatus_level": w.get("minimum_memorystatus"),
                "peak_swap_mib": w.get("peak_swap_mib"),
                "model_peak_process_rss_mib": w.get("peak_model_rss_mib"),
            }
            for w in windows
        ],
    }


def complete_report() -> dict:
    manifest, cases, approved = frozen()
    local = local_rows(manifest, cases, approved)
    codex = codex_rows(manifest, cases, approved)
    rows = local + codex
    if len(rows) != 252 or any(row["status"] == "not_observed" for row in rows):
        raise ModelQAEvidenceError("Missing original native QA turn(s)")
    if {(r["model"], r["case_id"], r["trial"]) for r in rows} != {
        (candidate, cid, trial)
        for candidate in (*MODELS, "codex_no_web", "codex")
        for cid in manifest["case_ids"]
        for trial in (1, 2, 3)
    }:
        raise ModelQAEvidenceError("Native seven-stack case/trial identity not exact")
    resources = resource_verdict()
    older = json.loads(OLD_SEVEN.read_text())
    historical = older.get("models", {})
    if (
        older.get("frozen_p4_cases_sha256") != manifest["source_sha256"]
        or older.get("combined_native_turn_evidence") != 252
        or set(historical) != {*MODELS, "codex", "codex_no_web"}
    ):
        raise ModelQAEvidenceError("Historical seven-stack baseline not independently verified")
    summary = {}
    for candidate in (*MODELS, "codex_no_web", "codex"):
        subset = [r for r in rows if r["model"] == candidate]
        positives = [r for r in subset if r["category"] == "positive"]
        negatives = [r for r in subset if r["category"] == "negative"]
        boundaries = [r for r in subset if r["category"] == "boundary"]
        summary[candidate] = {
            "observed": len(subset),
            "native_completed": sum(x["native_completed"] for x in subset),
            "strict_substantive_completed": sum(x["strict_substantive_completed"] for x in subset),
            "positive_exact_source_structural": sum(
                x["strict_substantive_completed"] and x["raw_exact_source_verdict"] == "pass"
                for x in positives
            ),
            "positive_source_with_actual_new_skill_read": sum(
                x["status"] == "positive_source_structure_only" for x in positives
            ),
            "negative_nonactivation_observed": sum(
                x["status"] == "negative_nonactivation_observed" for x in negatives
            ),
            "detected_boundary_violations": sum(
                x["status"] == "boundary_scope_violated" for x in boundaries
            ),
            "boundary_incomplete_or_not_final": sum(
                x["status"] == "native_incomplete_or_loop" for x in boundaries
            ),
            "boundary_manual_review_required": sum(
                x["status"] == "boundary_manual_review_required" for x in boundaries
            ),
            "P3_buffered_delivery_permitted": sum(
                x["P3_buffered_delivery_permitted"] is True for x in subset
            ),
            "positive_selected_evidence_actually_read": sum(
                x["selected_evidence_actually_read"] is True for x in positives
            ),
            "status_counts": dict(sorted(Counter(x["status"] for x in subset).items())),
            "old_positive_exact_source_structural": historical[candidate][
                "positive_exact_source_structural"
            ],
            "old_negative_nonactivation_observed": historical[candidate][
                "negative_nonactivation_observed"
            ],
            "old_detected_boundary_violations": historical[candidate]["boundary_scope_violations"],
        }
    return {
        "schema_version": 1,
        "benchmark": "P5-P123-SEVEN-STACK-12X3",
        "source_revision": manifest["source_sha256"],
        "candidate_skill_sha256": manifest["candidate_skill_sha256"],
        "reviewed_target": "Claude Code CLI 2.1.296 only",
        "host_context": "Mac native Pi Agent and Codex App Server",
        "model_stacks": 7,
        "frozen_cases": 12,
        "repetitions": 3,
        "actual_native_attempts": 252,
        "local_native_attempts": 180,
        "codex_native_attempts": 72,
        "models": summary,
        "rows": rows,
        "resources": resources,
        "original_model_text_private": True,
        "production_mod_semantics_verified": False,
        "chatgpt_chat_mode_skill_activation_verified": False,
        "target_native_cli_test_2_1_296_completed": False,
        "P3_delivery_gate_available_in_all_hosts": False,
        "strict_skill_automation_not_fine_tuning": True,
        "model_parameters_unchanged": True,
        "comparison_limitations": [
            "Seven original new-Skill cohorts use the same frozen user prompts.",
            "Identical source/Claim structural scores are not semantic Mods code correctness.",
            "Native model runtimes, tools and context budgets differ by model; not a weight-only comparison.",
            "Host Codex App Server did not use the same buffered Pi delivery gate.",
            "Boundaries were private research trials and never delivered as unchecked Mod code.",
            "No old evidence is overwritten; historical and new cohorts were recorded sequentially.",
            "The Mac's five original AI services were unloaded when this campaign began and left unchanged.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    result = complete_report()
    if args.out and not args.dry_run:
        if args.out.exists():
            parser.error("Immutable report exists; refusing overwrite")
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(
        json.dumps(
            {
                "observed": result["actual_native_attempts"],
                "models": {
                    name: {
                        key: stat[key]
                        for key in (
                            "positive_exact_source_structural",
                            "positive_source_with_actual_new_skill_read",
                            "negative_nonactivation_observed",
                            "detected_boundary_violations",
                            "P3_buffered_delivery_permitted",
                        )
                    }
                    for name, stat in result["models"].items()
                },
                "actual_model_text_exposed": False,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
