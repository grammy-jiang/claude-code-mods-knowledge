#!/usr/bin/env python3
"""Single genuine Codex Sol/medium no-web Skill evidence A/B/C trial.

Model, effort, original user prompt, frozen V3 Skill bytes and hosted tool
sandbox are identical across conditions. B/C pass a SSOT Evidence Pack via
the official Codex thread/start.developerInstructions field; C also applies
a postflight buffer gate but NEVER substitutes a fake successful model answer.

All original JSON-RPC, model responses, user prompts and account/session
identifiers remain in an owner-only private directory on Mac.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import time
from pathlib import Path

import run_p5_codex_ab_holdout_native as native

from mods_knowledge.answer_lint import lint_mods_answer
from mods_knowledge.claim_source_link_coverage import audit_claim_source_links
from mods_knowledge.claims import load_claims
from mods_knowledge.evidence_delivery import evidence_fingerprint, make_verified_task_context
from mods_knowledge.registry import load_registry
from mods_knowledge.task_evidence import select_task_evidence

ROOT = Path(__file__).resolve().parents[1]
FROZEN_SOURCE = (
    Path.home()
    / "Projects/claude-code-mods-knowledge-p5-codex-v3-frozen-20261017"
    / "dist/common/claude-code-mods-development"
)
PRIVATE = Path.home() / "Models.noindex/benchmarks/p5-codex-evidence-ab-20261017"
MANIFEST = ROOT / "evals/p5_codex_ab_holdout_20261017.json"
CONDITIONS = ("A_v3", "B_context", "C_context_gate")
TARGET_SKILL_SHA = "259535287ef965e516a79283144445228ff84653aae67189b5d2476c70f10baf"
_VERSION_EXCEEDS = re.compile(r"(?<!\d)2\.1\.(?!296\b)\d+(?!\d)")
_CODE = re.compile(
    r"\x60{3}(?:javascript|typescript|jsx|tsx|js|ts|bash|sh)\b"
    r"|\bexport\s+(?:function|const)\s+register\b"
    r"|\bon\s*\(\s*['\"]tool\.call['\"]",
    re.I,
)


def _claims() -> dict:
    return load_claims(
        ROOT / "claims",
        load_registry(ROOT / "sources/registry.json"),
        ROOT / "sources/snapshots",
        ROOT / "decisions",
    )


def _manifest() -> dict:
    obj = json.loads(MANIFEST.read_text())
    source = ROOT / obj["source_file"]
    if (
        hashlib.sha256(source.read_bytes()).hexdigest() != obj["source_sha256"]
        or len(obj["case_ids"]) != 4
        or len(set(obj["case_ids"])) != 4
        or obj["conditions"] != list(CONDITIONS)
        or obj["repetitions"] != 3
        or obj["native_turns_planned"] != 36
        or obj["frozen_skill_sha256"] != TARGET_SKILL_SHA
    ):
        raise ValueError("Original A/B/C frozen research plan changed")
    return obj


def _native_model_answer(events: Path) -> str:
    if not events.is_file() or not 0 < events.stat().st_size < 30_000_000:
        raise ValueError("Missing or unbounded native original Codex events")
    chunks = []
    for line in events.read_text(errors="replace").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get("method") != "item/completed":
            continue
        item = event.get("params", {}).get("item")
        if isinstance(item, dict) and item.get("type") == "agentMessage":
            if isinstance(item.get("text"), str) and item["text"].strip():
                chunks.append(item["text"])
    return "\n".join(chunks)


def _postflight_gate(
    case: dict,
    *,
    raw_answer: str,
    selection: dict,
    model_resolved: bool,
    skill_read: bool,
    native_completed: bool,
    claims: dict,
) -> dict:
    """The blocker is research-only; never claim native Mods semantic safety."""
    reasons = []
    if case["category"] == "boundary":
        reasons.append("unsupported_boundary_preflight")
    elif case["category"] == "negative":
        if skill_read:
            reasons.append("unrelated_task_triggered_mods_skill")
    else:
        if not skill_read:
            reasons.append("new_v3_skill_was_not_read")
        if not selection["ready"]:
            reasons.append("no_reviewed_task_evidence")
        elif raw_answer:
            judged = audit_claim_source_links(
                raw_answer,
                claims,
                version="2.1.296",
                surface="cli",
                required_claim_ids=[item["claim_id"] for item in selection["claims"]],
            )
            if judged["structural_verdict"] != "pass":
                reasons.append("missing_exact_ssot_task_claim_or_url")
        if _VERSION_EXCEEDS.search(raw_answer):
            reasons.append("unreviewed_cli_version_mentioned")
        if _CODE.search(raw_answer):
            reasons.append("runnable_mod_code_needs_native_target_semantic_test")
        lint = lint_mods_answer(raw_answer, case_id=case["id"])
        if lint["risk_flags"] or lint["requires_manual_review"]:
            reasons.append("model_mods_code_or_sources_need_manual_review")
    if not model_resolved:
        reasons.append("native_model_provenance_unverified")
    if not native_completed:
        reasons.append("native_model_turn_not_completed")
    if not raw_answer.strip():
        reasons.append("missing_substantive_model_text")
    # This only approves *structural* candidate text; no executable
    # Mod code is certified by Claim citations or buffered gating.
    return {
        "buffered": True,
        "host": "Codex App Server research harness",
        "allowed_structural_candidate_only": not reasons,
        "blocked": bool(reasons),
        "reasons": sorted(set(reasons)),
        "original_model_text_delivered_to_user": False,
        "native_mod_semantics_approved": False,
    }


def run(case_id: str, trial: int, condition: str) -> dict:
    plan = _manifest()
    if case_id not in plan["case_ids"] or trial not in (1, 2, 3) or condition not in CONDITIONS:
        raise ValueError("Unapproved original P4 trial/model or condition")
    if (
        not FROZEN_SOURCE.is_dir()
        or hashlib.sha256((FROZEN_SOURCE / "SKILL.md").read_bytes()).hexdigest() != TARGET_SKILL_SHA
    ):
        raise RuntimeError("Frozen exact V3 Skill archive digest changed")
    catalog = {
        row["id"]: row for row in json.loads((ROOT / plan["source_file"]).read_text())["cases"]
    }
    case = catalog[case_id]
    claims = _claims()
    selection = select_task_evidence(case["prompt"], claims, version="2.1.296")
    if (
        (case["category"] == "positive" and not selection["ready"])
        or (case["category"] == "negative" and selection["intent"] != "unrelated")
        or (case["category"] == "boundary" and selection["intent"] != "blocked")
    ):
        raise ValueError("Selection disagrees with frozen case category")
    context = (
        make_verified_task_context(selection)
        if condition != "A_v3" and case["category"] == "positive"
        else None
    )
    # Exactly the same frozen Skill is available via the native Codex
    # skills/list API in ALL three conditions; context is the only
    # per-thread evidence treatment.
    case_root = PRIVATE / "holdout-cases" / condition / case_id / f"trial-{trial}"
    if case_root.exists():
        raise RuntimeError("Immutable original native trial already exists")
    case_root.mkdir(parents=True, mode=0o700)
    case_root.chmod(0o700)
    skill = case_root / ".agents/skills/claude-code-mods-development"
    skill.parent.mkdir(parents=True, mode=0o700)
    shutil.copytree(FROZEN_SOURCE, skill)
    if hashlib.sha256((skill / "SKILL.md").read_bytes()).hexdigest() != TARGET_SKILL_SHA:
        raise RuntimeError("Candidate Skill copy did not preserve frozen bytes")
    # New heldout cases intentionally did not receive train/dev fixtures.
    # The negative Python question is self-contained; its prompt is frozen.
    started = time.monotonic()
    observed, result = native.run_native_case(
        case_id,
        "macbook-pro",
        120,
        private_workspace=case_root,
        approved_case_ids=set(plan["case_ids"]),
        disable_web_search=True,
        developer_instructions=context,
        case_override=case,
    )
    native_trace = observed / "native-wire.jsonl"
    answer = _native_model_answer(native_trace)
    provenance = (
        result.get("model_server_resolved") == "gpt-6.1-sol"
        and result.get("effort_server_resolved") == "medium"
        and result.get("prompt_matched") is True
        and result.get("registered_candidate_skill_before_model") is True
        and result.get("state") == "native_turn_recorded"
    )
    completed = provenance and result.get("agent_completed") is True and bool(answer.strip())
    receipt_ok = result.get("skill_context_submitted_to_native_thread") is (
        context is not None
    ) and result.get("skill_context_sha256") == (
        evidence_fingerprint(context) if context is not None else None
    )
    if not receipt_ok:
        raise RuntimeError("Actual native developer context request mismatch")
    web_calls = 0
    for line in native_trace.read_text(errors="replace").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get("method") != "item/completed":
            continue
        item = event.get("params", {}).get("item")
        if isinstance(item, dict) and item.get("type") == "webSearch":
            web_calls += 1
    if web_calls:
        raise RuntimeError("Web-disabled research nonetheless made web-search calls")
    gate = (
        _postflight_gate(
            case,
            raw_answer=answer,
            selection=selection,
            model_resolved=provenance,
            skill_read=result.get("skill_loaded") is True,
            native_completed=completed,
            claims=claims,
        )
        if condition == "C_context_gate"
        else None
    )
    evidence = {
        "case_id": case_id,
        "category": case["category"],
        "condition": condition,
        "trial": trial,
        "frozen_original_prompt_sha256": hashlib.sha256(case["prompt"].encode()).hexdigest(),
        "frozen_suite_sha256": plan["source_sha256"],
        "frozen_v3_skill_sha256": TARGET_SKILL_SHA,
        "native_model": "gpt-6.1-sol",
        "native_effort": "medium",
        "no_web": True,
        "native_web_search_count": web_calls,
        "isolate_registered": result.get("registered_candidate_skill_before_model"),
        "actual_v3_skill_read": result.get("skill_loaded"),
        "native_model_resolved": provenance,
        "native_turn_completed": completed,
        "native_source_verdict": result.get("source_verdict"),
        "native_source_scorer_verdict": result.get("verdict"),
        "selected_claim_ids": [item["claim_id"] for item in selection["claims"]],
        "task_evidence_submitted": context is not None,
        "task_evidence_sha256": evidence_fingerprint(context) if context else None,
        "task_evidence_confirmed_consumed_by_model": False,
        "original_answer_sha256": hashlib.sha256(answer.encode()).hexdigest(),
        "original_native_wire_sha256": hashlib.sha256(native_trace.read_bytes()).hexdigest(),
        "duration_seconds": round(time.monotonic() - started, 2),
        "research_only": True,
        "buffered_gate": gate,
        "semantic_mod_runtime_verified": False,
        "raw_user_or_model_text_exported": False,
    }
    report = case_root / "ab-report.json"
    if report.exists():
        raise RuntimeError("Original AB report already exists")
    report.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n")
    report.chmod(0o600)
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--condition", choices=CONDITIONS, required=True)
    parser.add_argument("--case", choices=_manifest()["case_ids"], required=True)
    parser.add_argument("--trial", choices=(1, 2, 3), type=int, required=True)
    args = parser.parse_args()
    row = run(args.case, args.trial, args.condition)
    print(
        json.dumps(
            {
                "condition": row["condition"],
                "case_id": row["case_id"],
                "trial": row["trial"],
                "completed": row["native_turn_completed"],
                "skill_read": row["actual_v3_skill_read"],
                "source_verdict": row["native_source_verdict"],
                "context_submitted": row["task_evidence_submitted"],
                "gate_permitted": (
                    row["buffered_gate"]["allowed_structural_candidate_only"]
                    if row["buffered_gate"]
                    else None
                ),
                "raw_content_exported": False,
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
