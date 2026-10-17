#!/usr/bin/env python3
"""Validate original 24 genuine Codex delivery A/B turns and publish safe metrics.

Never publish full native wire, model answer, user path, account identifier or
developer evidence payload. Every wire digest must match its private report.
Do not repair incomplete runs or substitute aggregate evidence for native logs.
"""

from __future__ import annotations

import hashlib
import json
import shlex
import statistics
from pathlib import Path

from mods_knowledge.claims import load_claims
from mods_knowledge.knowledge_delivery import prepare_delivery
from mods_knowledge.registry import load_registry
from mods_knowledge.task_evidence import render_evidence_pack, select_task_evidence

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "evals/p1_codex_delivery_ab.json"
PRIVATE = Path.home() / "Models.noindex/benchmarks/p1-skill-delivery-20261017"
JSON_OUT = ROOT / "docs/reports/2026-10-17-p1-codex-knowledge-delivery-ab.json"
MD_OUT = JSON_OUT.with_suffix(".md")


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _codex_verified_selected_read(trace: Path) -> bool:
    """Recognize successful native read commands, never infer from citations."""
    for line in trace.read_text(errors="replace").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get("method") != "item/completed":
            continue
        item = event.get("params", {}).get("item")
        if (
            not isinstance(item, dict)
            or item.get("type") != "commandExecution"
            or item.get("status") != "completed"
            or item.get("exitCode") != 0
            or not isinstance(item.get("command"), str)
        ):
            continue
        try:
            args = shlex.split(item["command"])
            if (
                len(args) >= 3
                and args[0].endswith(("/zsh", "/bash", "/sh"))
                and args[1] == "-lc"
            ):
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


def summarize_rows(rows: list[dict], plan: dict) -> dict:
    """Pure A/B summary; testable without model calls or private content."""
    positives = set(plan["positive_cases"])
    negatives = set(plan["negative_cases"])
    expected = {
        (arm, cid, t)
        for arm in plan["arms"]
        for cid in positives | negatives
        for t in range(1, (plan["positive_repetitions"] if cid in positives else plan["negative_repetitions"]) + 1)
    }
    keys = [(r["arm"], r["case_id"], r["trial"]) for r in rows]
    if len(keys) != len(set(keys)) or set(keys) != expected:
        raise ValueError("Native A/B trial matrix missing, duplicated or contaminated")
    if len(rows) != plan["planned_trials"]:
        raise ValueError("P1 trial count does not match frozen manifest")
    summary: dict = {}
    for arm in plan["arms"]:
        selected = [r for r in rows if r["arm"] == arm]
        positive = [r for r in selected if r["category"] == "positive"]
        negative = [r for r in selected if r["category"] == "negative"]
        if len(positive) != 8 or len(negative) != 4:
            raise ValueError("Unexpected positive/negative split")
        summary[arm] = {
            "native_turns": len(selected),
            "native_completed": sum(r["native_completed"] is True for r in selected),
            "positive_exact_claim_source_structure_pass": sum(
                r["source_verdict"] == "pass" for r in positive
            ),
            "positive_attempts": len(positive),
            "positive_skill_reads": sum(r["skill_read"] is True for r in positive),
            "positive_selected_pack_file_reads": sum(r["selected_pack_read"] is True for r in positive),
            "positive_developer_payload_thread_accepted": sum(
                r["thread_accepted_evidence"] is True for r in positive
            ),
            "negative_completed_without_mod_skill": sum(
                r["native_completed"] is True and r["skill_read"] is False
                for r in negative
            ),
            "negative_attempts": len(negative),
            "negative_wrongly_injected": sum(r["payload_sha256"] is not None for r in negative),
            "median_elapsed_seconds": round(statistics.median(r["elapsed_s"] for r in selected), 2),
        }
    return summary


def build_report() -> dict:
    plan = json.loads(MANIFEST.read_text())
    if _sha((ROOT / plan["source_file"]).read_bytes()) != plan["source_sha256"]:
        raise ValueError("Frozen original prompt source checksum drift")
    claims = load_claims(
        ROOT / "claims",
        load_registry(ROOT / "sources/registry.json"),
        ROOT / "sources/snapshots",
        ROOT / "decisions",
    )
    case_map = {
        r["id"]: r for r in json.loads((ROOT / plan["source_file"]).read_text())["cases"]
    }
    rows = []
    for arm in plan["arms"]:
        for cid in plan["positive_cases"] + plan["negative_cases"]:
            cat = case_map[cid]["category"]
            limit = plan["positive_repetitions"] if cat == "positive" else plan["negative_repetitions"]
            for trial in range(1, limit + 1):
                root = PRIVATE / "p1-codex-delivery" / arm / "codex_no_web" / cid / f"trial-{trial}"
                report_file = root / "report.json"
                trace = root / "native-wire.jsonl"
                native_file = root / "sanitized-report.json"
                if not (report_file.is_file() and trace.is_file() and native_file.is_file()):
                    raise ValueError("Missing original native model report, no replay/substitution")
                report = json.loads(report_file.read_text())
                native = json.loads(native_file.read_text())
                if report.get("case_id") != cid or report.get("trial") != trial:
                    raise ValueError("Native case/report identity mismatch")
                if report.get("P1_delivery_mode") != arm:
                    raise ValueError("Trial A/B treatment mismatch")
                if report.get("private_wire_sha256") != _sha(trace.read_bytes()):
                    raise ValueError("Native private wire digest mismatch")
                if report.get("model_server_resolved") != plan["model"]:
                    raise ValueError("Model configuration changed in A/B")
                if report.get("effort_server_resolved") != plan["effort"]:
                    raise ValueError("Effort configuration changed in A/B")
                if report.get("native_web_search_count") != 0 or not report.get("web_search_disabled"):
                    raise ValueError("Unexpected web search exposure in A/B")
                if native.get("prompt_matched") is not True:
                    raise ValueError("Original user prompt bytes were not verified")
                if (
                    native.get("model_provenance")
                    != "same-thread-app-server-response+thread-read"
                    or native.get("model_server_resolved") != plan["model"]
                    or native.get("model_provider_server_resolved") != "openai"
                    or native.get("effort_server_resolved") != plan["effort"]
                ):
                    raise ValueError("Native model App Server provenance rejected")
                selected = select_task_evidence(case_map[cid]["prompt"], claims)
                path = root / ".agents/skills/claude-code-mods-development/references/selected-evidence.md"
                selected_sha = report.get("selected_evidence_sha256")
                if cat == "positive":
                    if not selected["ready"]:
                        raise ValueError("Frozen positive selection no longer approved")
                    expected_bytes = render_evidence_pack(selected).encode("utf-8")
                    if not path.is_file() or _sha(path.read_bytes()) != _sha(expected_bytes):
                        raise ValueError("Original selected evidence file missing or changed")
                    if selected_sha != _sha(expected_bytes):
                        raise ValueError("Evidence file report digest mismatch")
                elif selected_sha is not None or path.exists():
                    raise ValueError("Unrelated negative case was given Mods selected evidence")
                delivery = (
                    prepare_delivery(case_map[cid]["prompt"], claims, "codex")
                    if arm == "preload" and cat == "positive" else None
                )
                expected_payload = delivery.sha256 if delivery else None
                if report.get("P1_payload_sha256") != expected_payload:
                    raise ValueError("P1 request payload fingerprint mismatch")
                if report.get("P1_native_thread_accepted_delivery") is not (
                    delivery is not None
                ):
                    raise ValueError("Host did not accept expected treatment")
                if not report.get("native_case_completed"):
                    raise ValueError("Original native model turn incomplete")
                if report.get("semantic_mods_correctness_verified") is not False:
                    raise ValueError("No native Mod semantic acceptance performed")
                rows.append(
                    {
                        "arm": arm,
                        "case_id": cid,
                        "trial": trial,
                        "category": cat,
                        "native_completed": True,
                        "model_verified": True,
                        "skill_read": report.get("actual_candidate_skill_read"),
                        "source_verdict": report.get("source_verdict"),
                        "selected_pack_read": _codex_verified_selected_read(trace),
                        "thread_accepted_evidence": report.get("P1_native_thread_accepted_delivery"),
                        "payload_sha256": expected_payload,
                        "native_wire_sha256": report["private_wire_sha256"],
                        "elapsed_s": report["elapsed_s"],
                    }
                )
    if len(rows) != plan["planned_trials"]:
        raise ValueError("Not all real native model turns are present")
    summary = summarize_rows(rows, plan)
    result = {
        "schema": "p1-skill-knowledge-delivery-ab-v1",
        "reviewed_target": plan["reviewed_target"],
        "source_sha256": plan["source_sha256"],
        "frozen_skill_sha256": plan["frozen_skill_sha256"],
        "cohort": plan["suite_id"],
        "native_host": plan["agent"],
        "model": plan["model"],
        "reasoning_effort": plan["effort"],
        "web_search": "disabled",
        "real_native_turns": len(rows),
        "arms": summary,
        "rows": rows,
        "original_model_text_private": True,
        "raw_native_events_public": False,
        "delivered_payload_proves_semantic_use": False,
        "generated_mod_code_semantics_verified": False,
        "pi_native_payload_accepted": None,
        "chatgpt_chat_mode_plugin_activation_verified": False,
        "stable_release_qualified": False,
        "interpretation_limits": [
            "Tiny same-agent, frozen-prompt hosted-model pilot, not a randomized large-sample study",
            "Exact Claim/source format is structural; no executed Mod semantic acceptance",
            "Original task question and candidate Skill equal in both arms",
            "Baseline and treatment have identical selected-evidence file available",
            "Thread-start metadata acknowledgment does NOT independently prove model consumed it",
            "All private outputs, user-specific paths, transcripts and credentials remain on Mac",
        ],
    }
    return result


def main() -> int:
    result = build_report()
    JSON_OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    summary = result["arms"]
    lines = [
        "# P1 scoped knowledge delivery — 24 native Codex A/B turns",
        "",
        "Date: 2026-10-17 (Australia/Sydney). Archived, SHA-verified original native turns; "
        "no synthetic or replay-substituted model results.",
        "",
        "## Treatment and controls",
        "",
        "The two arms share *byte-identical original task prompts*, the same frozen "
        "Skill (SHA-256 pinned), optional task-selected evidence files, reviewed Claims, "
        "hosted model and medium effort. The only treatment is sending that same "
        "selected SSOT evidence as thread-scoped `developerInstructions` at native "
        "Codex App Server `thread/start`. Web search is disabled. Negative controls "
        "never receive a Mods payload.",
        "",
        "| Metric | File only | Preloaded evidence |",
        "| --- | ---: | ---: |",
    ]
    for title, key in [
        ("Real native turns", "native_turns"),
        ("Completed native turns", "native_completed"),
        ("Positive exact Claim/URL structural pass (of 8)", "positive_exact_claim_source_structure_pass"),
        ("Positive actual Skill reads (of 8)", "positive_skill_reads"),
        ("Positive optional selected-file reads (of 8)", "positive_selected_pack_file_reads"),
        ("Positive preload accepted by App Server (of 8)", "positive_developer_payload_thread_accepted"),
        ("Negative completed without Mods Skill (of 4)", "negative_completed_without_mod_skill"),
        ("Negative Mods payloads wrongly injected (of 4)", "negative_wrongly_injected"),
        ("Completed-turn median wall time (s)", "median_elapsed_seconds"),
    ]:
        lines.append(f"| {title} | {summary['file_only'][key]} | {summary['preload'][key]} |")
    lines.extend([
        "",
        "## Interpretation",
        "",
        "The pre-inference delivery transport demonstrably worked: each treatment "
        "thread-start was accepted, with a SHA-pinned evidence payload selected "
        "from reviewed SSOT, without changing the user prompt or installing a Skill. "
        "However, *transport acceptance is not model knowledge utilization*; some "
        "outputs still fail exact source structure even with the payload available. "
        "The positive structural pass-rate difference is exploratory, not causal "
        "proof of a reliable/general improvement. No target CLI generated-code "
        "semantic review, local Pi native inference, or ChatGPT ordinary Chat-mode "
        "Plugin activation was performed during this P1 pilot.",
        "",
        "## Release decision",
        "",
        "**No Stable promotion or production installation.** Retain the approved "
        "Claude Code CLI 2.1.296 boundary; the Mac's newer installed CLI is not "
        "qualified by this SSOT. Keep P5 semantic/Chat-mode gates open. The Pi "
        "file-backed `--append-system-prompt` transport is implemented and unit "
        "tested, but still requires a dedicated native Pi model acceptance run.",
        "",
    ])
    MD_OUT.write_text("\n".join(lines))
    print(json.dumps({"real_native_turns":len(result["rows"]),"arms":summary},sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
