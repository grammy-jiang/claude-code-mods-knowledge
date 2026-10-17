"""Fail-closed, privacy-preserving summaries of real Pi Agent JSONL events.

The caller supplies events from a completed, *private* native CLI run. This
module does not run a model, read files, or assert complete semantic acceptance.
In particular, a requested --model cannot stand in for the *observed* model.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping, Sequence

from .answer_lint import lint_mods_answer

_IDENT = re.compile(r"[A-Za-z0-9_.:-]{1,96}\Z")
_REV = re.compile(r"[a-f0-9]{40}\Z")
_CASE = re.compile(r"[A-Z][A-Z0-9_-]{3,60}\Z")
_SKILL = "claude-code-mods-development"
_OFFICIAL = "https://code.claude.com/docs/en/plugins/mods/"
_CLAIM = re.compile(r"K-[0-9]{4,}\b")


class PiModelEvidenceError(ValueError):
    """Native model event evidence is malformed or fails a trust boundary."""


def _text(message: Mapping) -> str:
    content = message.get("content")
    if not isinstance(content, list):
        return ""
    return "\n".join(
        item["text"]
        for item in content
        if isinstance(item, Mapping)
        and item.get("type") == "text"
        and isinstance(item.get("text"), str)
    )


def _read_scope(path: object, skill_root: str) -> str | None:
    """Return a safe relative path only; never copy arbitrary host paths."""
    if not isinstance(path, str) or not path.startswith(skill_root + "/"):
        return None
    relative = path[len(skill_root) + 1 :]
    if relative == "SKILL.md":
        return relative
    if relative.startswith("references/"):
        parts = relative.split("/")
        if len(parts) == 2 and re.fullmatch(r"[A-Za-z0-9_-]+\.md", parts[1]):
            return relative
    return None


def summarize_pi_model_trace(
    case: Mapping,
    events: Sequence[dict],
    *,
    expected_provider: str,
    expected_model: str,
    model_was_pinned: bool,
    skill_root: str,
    source_revision: str,
    pi_version: str,
) -> dict:
    """Require actual user prompt/model/resource evidence; emit no raw data.

    A structural success is explicitly *not* independent semantic correctness.
    The Pi ``--skill`` argument exposes metadata, but only real ``read`` tool
    events show whether the model subsequently selected the scoped Skill.
    """
    if (
        not isinstance(case, Mapping)
        or not isinstance(case.get("id"), str)
        or not _CASE.fullmatch(case["id"])
        or not isinstance(case.get("prompt"), str)
        or not case["prompt"].strip()
        or case.get("category") not in ("positive", "negative", "boundary")
        or type(case.get("expected_activation")) is not bool
        or type(model_was_pinned) is not bool
        or not isinstance(events, (list, tuple))
        or not all(isinstance(event, Mapping) for event in events)
        or not isinstance(source_revision, str)
        or not _REV.fullmatch(source_revision)
        or not isinstance(skill_root, str)
        or not skill_root.startswith("/")
        or "/../" in skill_root
        or not isinstance(pi_version, str)
        or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", pi_version)
        or any(
            not isinstance(value, str) or not _IDENT.fullmatch(value)
            for value in (expected_provider, expected_model)
        )
    ):
        raise PiModelEvidenceError("Invalid scoped native model evidence configuration")
    claim_ids = case.get("expected_claim_ids") or []
    if not isinstance(claim_ids, list) or not all(
        isinstance(value, str) and _CLAIM.fullmatch(value) for value in claim_ids
    ):
        raise PiModelEvidenceError("Expected approved Claim IDs must be bounded")

    users: list[str] = []
    assistant: list[Mapping] = []
    started: dict[str, Mapping] = {}
    ended: set[str] = set()
    read_scopes: list[str] = []
    external_count = 0
    read_errors = 0
    for event in events:
        kind = event.get("type")
        if kind == "message_end":
            msg = event.get("message")
            if not isinstance(msg, Mapping):
                continue
            if msg.get("role") == "user":
                users.append(_text(msg))
            elif msg.get("role") == "assistant":
                assistant.append(msg)
        elif kind == "tool_execution_start" and event.get("toolName") == "read":
            tid = event.get("toolCallId")
            if isinstance(tid, str):
                started[tid] = event
            scope = (
                _read_scope((event.get("args") or {}).get("path"), skill_root)
                if isinstance(event.get("args"), Mapping)
                else None
            )
            if scope is None:
                external_count += 1
            else:
                read_scopes.append(scope)
        elif kind == "tool_execution_end" and event.get("toolName") == "read":
            tid = event.get("toolCallId")
            if isinstance(tid, str):
                ended.add(tid)
            if event.get("isError") is True:
                read_errors += 1

    models = {
        (message.get("provider"), message.get("model"))
        for message in assistant
        if isinstance(message.get("provider"), str) and isinstance(message.get("model"), str)
    }
    model = next(iter(models)) if len(models) == 1 else None
    identity_valid = model is not None and all(bool(_IDENT.fullmatch(value)) for value in model)
    observed_model = "/".join(model) if identity_valid else None
    pin_matched = (
        model_was_pinned and identity_valid and model == (expected_provider, expected_model)
    )
    prompt_matched = len(users) == 1 and users[0] == case["prompt"]
    final_message = assistant[-1] if assistant else {}
    answer = _text(final_message)
    process_settled = any(event.get("type") == "agent_end" for event in events)
    # Pi can exit with process code 0 and emit agent_end/agent_settled
    # even if the last model request was a Connection error and its own
    # retry budget was exhausted. Agent shutdown != completed inference.
    # Never accept a partial/max-token/tool-use or missing stopReason.
    stop_reason = final_message.get("stopReason")
    native_model_finished = stop_reason in ("stop", "end_turn")
    retry_exhausted = any(
        event.get("type") == "auto_retry_end" and event.get("success") is False for event in events
    )
    completed = process_settled and native_model_finished and not retry_exhausted
    has_answer = (
        bool(answer.strip())
        and native_model_finished
        and not retry_exhausted
        and not bool(final_message.get("errorMessage"))
    )
    tool_balanced = started.keys() <= ended
    resources = sorted(set(read_scopes))
    skill_loaded = "SKILL.md" in resources
    observed_claims = sorted(set(_CLAIM.findall(answer))) if has_answer else []
    required_claims = set(claim_ids) <= set(observed_claims)
    official_cited = _OFFICIAL in answer
    lint = lint_mods_answer(answer, case_id=case["id"]) if has_answer else None
    risk = lint["risk_flags"] if lint else []
    review = lint["requires_manual_review"] if lint else []

    if not completed or not has_answer or not identity_valid or not tool_balanced:
        verdict = "blocked_or_incomplete"
    elif not prompt_matched or not pin_matched:
        verdict = "invalid_provenance"
    elif skill_loaded is not case["expected_activation"]:
        verdict = "activation_failed"
    elif case["category"] == "negative":
        # Unrelated file-read errors must not be confused with Mods activation.
        verdict = "negative_nonactivation_observed"
    elif read_errors:
        verdict = "structural_failed"
    elif case["category"] == "boundary":
        verdict = "boundary_manual_review_required"
    elif not required_claims or not official_cited or risk:
        verdict = "structural_failed"
    else:
        verdict = "structural_ok_semantics_unverified"

    return {
        "schema_version": 1,
        "case_id": case["id"],
        "category": case["category"],
        "source_revision": source_revision,
        "target_version": "Claude Code CLI 2.1.296",
        "pi_agent_version": pi_version,
        "invocation_mode": "native-cli-skill-exposed-via-flag",
        "user_prompt_sha256": hashlib.sha256(case["prompt"].encode()).hexdigest(),
        "prompt_matched": prompt_matched,
        "model_requested": f"{expected_provider}/{expected_model}" if model_was_pinned else None,
        "model_flag_explicit": model_was_pinned,
        "model_observed": observed_model,
        "model_pin_matched": pin_matched,
        "agent_completed": completed,
        "native_model_finished_successfully": native_model_finished,
        "auto_retry_exhausted": retry_exhausted,
        "answer_present": has_answer,
        "response_sha256": hashlib.sha256(answer.encode()).hexdigest() if has_answer else None,
        "skill_loaded": skill_loaded,
        "reference_files_read": [path for path in resources if path.startswith("references/")],
        "read_tool_calls": len(started),
        "read_tool_completed": len(ended & started.keys()),
        "read_tool_errors": read_errors,
        "tool_calls_outside_skill": external_count,
        "observed_claim_ids": observed_claims,
        "has_required_claims": required_claims,
        "official_source_cited": official_cited,
        "known_risk_flags": risk,
        "needs_manual_review": review,
        "semantic_review_complete": False,
        "verdict": verdict,
    }
