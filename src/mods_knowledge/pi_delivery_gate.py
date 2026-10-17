"""Deterministic Pi Agent Mods answer gate; never trust Skill text alone.

Only a buffering caller can withhold unsafe model output. Native Pi streams
cannot be assumed safe just because a post-generation audit runs.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping, Sequence

from .claim_source_link_coverage import audit_claim_source_links
from .p5_native_evidence import summarize_pi_native_trace
from .pi_loop_evidence import summarize_pi_loop_trace
from .task_evidence import route_task, select_task_evidence

TARGET = "2.1.296"
_VERSION = re.compile(r"(?<!\d)2\.1\.\d{3,}(?!\d)")
_CODE = re.compile(
    r"\x60{3}(?:javascript|typescript|jsx|tsx|js|ts|bash|sh)\b"
    r"|\bexport\s+(?:function|const)\s+register\b"
    r"|\bon\s*\(\s*['\"]tool\.call['\"]",
    re.I,
)
_REFUSAL = (
    "The available Claude Code Mods knowledge is reviewed only for CLI 2.1.296. "
    "I cannot verify this requested version's API without current first-party "
    "documentation and the target build's declarations. I will not supply "
    "unverified implementation instructions."
)


class PiDeliveryGateError(ValueError):
    """The gate cannot verify the supplied bounded evidence."""


def preflight_mods_case(case: Mapping) -> dict:
    """Deny out-of-scope Mods API requests before any model inference."""
    if (
        not isinstance(case, Mapping)
        or not isinstance(case.get("prompt"), str)
        or not case["prompt"].strip()
        or case.get("category") not in {"positive", "negative", "boundary"}
        or not isinstance(case.get("id"), str)
    ):
        raise PiDeliveryGateError("Expected frozen, typed Mods case metadata")
    decision = route_task(case["prompt"], target_version="2.1.296")
    # Metadata cannot override a prompt that does not actually belong
    # to the reviewed Mods API; conversely explicitly unrelated code
    # must never be given artificial Mods requirements.
    if case["category"] == "positive" and decision["intent"] != "mods":
        return {
            "action": "abstain_before_model",
            "reason": decision["reason"] or "unverified_mods_intent",
            "source_target": "Claude Code CLI " + TARGET,
            "model_requests_needed": 0,
            "safe_reply": _REFUSAL,
        }
    if case["category"] == "boundary" or decision["intent"] == "blocked":
        return {
            "action": "abstain_before_model",
            "reason": decision["reason"] or "unreviewed_target_version_or_surface",
            "source_target": "Claude Code CLI " + TARGET,
            "model_requests_needed": 0,
            "safe_reply": _REFUSAL,
        }
    return {
        "action": "run_scoped_model",
        "reason": None,
        "source_target": "Claude Code CLI " + TARGET,
        "model_requests_needed": 1,
        "safe_reply": None,
    }


def postflight_mods_case(
    case: Mapping,
    events: Sequence[dict],
    *,
    claims: Mapping[str, dict],
    skill_root: str,
    source_revision: str,
    provider: str,
    model: str,
    pi_version: str,
    native_exit_code: int | None,
    timed_out: bool,
    terminated_for_repeat: bool = False,
    enforce_task_evidence: bool = False,
) -> dict:
    """Assess buffered native events and emit only safe metadata and refusal.

    The calling runner must not stream Pi events/answers to the end user;
    otherwise final gate enforcement cannot retract already-visible text.
    """
    if preflight_mods_case(case)["action"] != "run_scoped_model":
        return {
            "action": "block_candidate",
            "reason_codes": ["preflight_was_not_enforced"],
            "safe_reply": _REFUSAL,
            "allow_raw_candidate_delivery": False,
        }
    if type(timed_out) is not bool or type(terminated_for_repeat) is not bool:
        raise PiDeliveryGateError("Invalid runner termination status")
    if native_exit_code is not None and type(native_exit_code) is not int:
        raise PiDeliveryGateError("Native process exit must be int or null")

    evidence = summarize_pi_native_trace(
        case,
        events,
        source_revision=source_revision,
        host="macbook-pro",
        cli_version=pi_version,
        skill_root=skill_root,
        claims=claims,
        expected_provider=provider,
        expected_model=model,
        model_was_pinned=True,
    )
    loop = summarize_pi_loop_trace(events)
    failures = set()
    if timed_out or native_exit_code != 0 or terminated_for_repeat:
        failures.add("native_run_incomplete")
    if loop["native_tool_loop_suspected"]:
        failures.add("tool_loop_or_budget")
    if not loop["tool_execution_balanced"]:
        failures.add("tool_execution_unbalanced")
    if not evidence["model_pin_matched"] or not evidence["prompt_matched"]:
        failures.add("unverified_model_or_prompt")
    if not evidence["agent_completed"] or not evidence["answer_present"]:
        failures.add("missing_completed_answer")
    last_stop = None
    for ev in events:
        if ev.get("type") == "message_end":
            msg = ev.get("message")
            if isinstance(msg, Mapping) and msg.get("role") == "assistant":
                last_stop = msg.get("stopReason")
    if last_stop != "stop":
        failures.add("native_answer_not_final_stop")
    if evidence["skill_loaded"] != case.get("expected_activation"):
        failures.add("skill_activation_mismatch")
    if case["category"] == "positive":
        if evidence["source_verdict"] != "pass":
            failures.add("missing_exact_approved_claim_sources")
        if evidence.get("risk_flags"):
            failures.add("known_code_hazard")
        if evidence.get("manual_review_flags"):
            failures.add("manual_code_or_source_review_needed")
        if evidence["verdict"] != "structural_ok_semantics_unverified":
            failures.add("nonpassing_structural_evidence")

    answer = ""
    for event in events:
        if event.get("type") != "message_end":
            continue
        msg = event.get("message")
        if not isinstance(msg, Mapping) or msg.get("role") != "assistant":
            continue
        content = msg.get("content")
        if isinstance(content, list):
            candidate = "".join(
                part.get("text", "")
                for part in content
                if isinstance(part, Mapping) and part.get("type") == "text"
            )
            if candidate.strip():
                answer = candidate
    if case["category"] == "positive" and enforce_task_evidence:
        # Selection is independent of frozen expected_claim_ids. The
        # original raw response still MUST cite each selected approved
        # source exactly. The pack cannot be stapled onto the answer to
        # turn a missing citation into a model success.
        selected = select_task_evidence(case["prompt"], claims, version="2.1.296")
        if not selected["ready"]:
            failures.add("no_approved_task_evidence")
        elif answer:
            report = audit_claim_source_links(
                answer,
                claims,
                version=TARGET,
                surface="cli",
                required_claim_ids=[item["claim_id"] for item in selected["claims"]],
            )
            if report["structural_verdict"] != "pass":
                failures.add("selected_evidence_missing_or_misquoted")
    if case["category"] == "positive" and any(v != TARGET for v in _VERSION.findall(answer)):
        failures.add("unreviewed_version_mentioned_in_mods_answer")
    if case["category"] == "positive" and _CODE.search(answer):
        failures.add("executable_example_requires_independent_native_validation")
    reasons = sorted(failures)
    passed = not reasons and case["category"] in {"positive", "negative"}
    return {
        "action": "allow_structural_only" if passed else "block_candidate",
        "reason_codes": reasons,
        "native_exit_ok": native_exit_code == 0 and not timed_out,
        "model_provenance_matched": evidence["model_pin_matched"],
        "skill_read_observed": evidence["skill_loaded"],
        "source_verdict": evidence["source_verdict"],
        "native_tool_loop_suspected": loop["native_tool_loop_suspected"],
        "native_tool_calls": loop["tool_call_count"],
        "answer_sha256": hashlib.sha256(answer.encode()).hexdigest() if answer else None,
        "allow_raw_candidate_delivery": passed,
        "semantic_correctness_verified": False,
        "safe_reply": None
        if passed
        else (
            "The local Agent's draft did not pass required Mods source, version, "
            "model-provenance or tool-safety checks. The unverified answer is withheld."
        ),
    }
