"""Fail-closed local classification of real Chat Mode send/recovery receipts.

This module never connects to ChatGPT, submits a prompt, retries a request,
or claims that an assistant used a Skill. It permits a human QA reviewer to
separate exact canonical FINAL_VERIFIED evidence from delivery-only, a read
429, or ambiguous sender timeouts without touching personal Chat content.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping

_TASK = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{5,128}\Z")


class ReceiptEvidenceError(ValueError):
    """An untrusted receipt cannot be treated as genuine evidence."""


def inspect_live_receipt(receipt: Mapping, *, expected_task_id: str) -> dict:
    """Validate exact self-consistent final receipt fields, preserving uncertainty.

    Verified means ONLY that the supplied receipt contains internally
    consistent canonical-final fields, not that its origin is authenticated.
    Nor does it prove a Plugin Skill resource was used.
    """
    if not isinstance(receipt, Mapping):
        raise ReceiptEvidenceError("Expected a parsed receipt mapping")
    if not isinstance(expected_task_id, str) or not _TASK.fullmatch(expected_task_id):
        raise ReceiptEvidenceError("Expected a bounded task identity")
    if receipt.get("request_id") != expected_task_id:
        raise ReceiptEvidenceError("Task identity mismatch")
    state = receipt.get("state")
    if state not in ("FINAL_VERIFIED", "OUTCOME_UNKNOWN", "DELIVERED", "FAILED"):
        raise ReceiptEvidenceError("Unknown or unrecognized transport state")
    sender = receipt.get("sender")
    watch = receipt.get("watch")
    if sender is not None and not isinstance(sender, Mapping):
        raise ReceiptEvidenceError("Malformed sender evidence")
    if watch is not None and not isinstance(watch, Mapping):
        raise ReceiptEvidenceError("Malformed watcher evidence")
    sender = sender or {}
    watch = watch or {}
    final = watch.get("final")
    if final is not None and not isinstance(final, Mapping):
        raise ReceiptEvidenceError("Malformed final evidence")
    final = final or {}
    conversation = receipt.get("conversation_id")
    matching_conversation = (
        isinstance(conversation, str)
        and bool(conversation)
        and final.get("conversation_id") == conversation
    )
    expected_turns = receipt.get("expected_user_turns")
    matching_turns = (
        type(expected_turns) is int
        and expected_turns >= 1
        and final.get("user_turns") == expected_turns
    )
    verified = (
        state == "FINAL_VERIFIED"
        and sender.get("state") == "DELIVERED"
        and watch.get("complete") is True
        and final.get("complete") is True
        and final.get("reason") == "verified"
        and isinstance(final.get("model"), str)
        and bool(final["model"])
        and isinstance(final.get("effort"), str)
        and bool(final["effort"])
        and final.get("task_id") == expected_task_id
        and matching_conversation
        and matching_turns
        and isinstance(final.get("turn_exchange_id"), str)
        and bool(final["turn_exchange_id"])
    )
    status = (
        "canonical_final_verified"
        if verified
        else "inconsistent_final_refuse"
        if state == "FINAL_VERIFIED"
        else "outcome_unknown_no_resend"
        if state in ("OUTCOME_UNKNOWN", "DELIVERED")
        else "failed_no_resend"
    )
    return {
        "status": status,
        "transport_state": state,
        "canonical_final_verified": verified,
        "may_resend_task": False,
        "read_only_recovery_permitted": status == "outcome_unknown_no_resend",
        "conversation_id_sha256": (
            hashlib.sha256(conversation.encode()).hexdigest()
            if isinstance(conversation, str) and conversation
            else None
        ),
        "model": final.get("model") if verified else None,
        "effort": final.get("effort") if verified else None,
        "skill_read_verified": False,
        "notes": "Receipt consistency only; real resource traces and semantics need separate review.",
    }
