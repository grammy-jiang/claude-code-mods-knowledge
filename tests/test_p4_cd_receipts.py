"""Bounded transport evidence: never retry an ambiguous Chat message."""

from __future__ import annotations

import hashlib

import pytest

from mods_knowledge.p4_cd_receipts import ReceiptEvidenceError, inspect_live_receipt

TASK = "MODS-P4CD-BOUND-EXPLICIT"
CHAT = "example-private-conversation"


def success() -> dict:
    return {
        "request_id": TASK,
        "state": "FINAL_VERIFIED",
        "conversation_id": CHAT,
        "expected_user_turns": 1,
        "sender": {"state": "DELIVERED"},
        "watch": {
            "complete": True,
            "final": {
                "complete": True,
                "reason": "verified",
                "task_id": TASK,
                "conversation_id": CHAT,
                "user_turns": 1,
                "turn_exchange_id": "exact-turn-exchange",
                "model": "gpt-6-thinking",
                "effort": "standard",
                "text": "PRIVATE_DATA_NEVER_ECHO",
            },
        },
    }


def inspect(receipt: dict) -> dict:
    result = inspect_live_receipt(receipt, expected_task_id=TASK)
    assert result["may_resend_task"] is False
    assert "PRIVATE_DATA_NEVER_ECHO" not in str(result)
    assert TASK not in str(result)
    assert CHAT not in str(result)
    return result


def test_success_requires_exact_completed_canonical_final() -> None:
    result = inspect(success())
    assert result["canonical_final_verified"] is True
    assert result["status"] == "canonical_final_verified"
    assert result["skill_read_verified"] is False
    assert result["conversation_id_sha256"] == hashlib.sha256(CHAT.encode()).hexdigest()


def test_read_429_after_browser_delivery_is_outcome_unknown_not_model_failure() -> None:
    receipt = success()
    receipt["state"] = "OUTCOME_UNKNOWN"
    receipt["watch"] = {"reason": "canonical-read-rejected-429", "final": None}
    result = inspect(receipt)
    assert result["status"] == "outcome_unknown_no_resend"
    assert result["read_only_recovery_permitted"] is True
    assert result["canonical_final_verified"] is False


def test_sender_timeout_without_id_is_not_safe_to_resend() -> None:
    receipt = success()
    receipt.update(state="OUTCOME_UNKNOWN", conversation_id=None)
    receipt["sender"] = {"state": "OUTCOME_UNKNOWN", "failure_class": "TimeoutExpired"}
    receipt["watch"] = None
    result = inspect(receipt)
    assert result["status"] == "outcome_unknown_no_resend"
    assert result["conversation_id_sha256"] is None
    assert result["read_only_recovery_permitted"] is True


@pytest.mark.parametrize("bad_field", ["watch", "sender"])
def test_null_transport_sections_do_not_crash(bad_field: str) -> None:
    receipt = success()
    receipt["state"] = "OUTCOME_UNKNOWN"
    receipt[bad_field] = None
    assert inspect(receipt)["status"] == "outcome_unknown_no_resend"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("state", "DELIVERED"),
        ("sender_state", "OUTCOME_UNKNOWN"),
        ("final", None),
        ("final_task", "UNRELATED-TASK"),
        ("final_chat", "unrelated-chat"),
        ("final_turns", 2),
        ("final_exchange", ""),
        ("watch_complete", False),
        ("final_complete", False),
        ("final_reason", "unconfirmed"),
        ("final_model", None),
        ("final_effort", None),
    ],
)
def test_no_false_verified_from_partial_or_mismatched_receipts(field: str, value: object) -> None:
    receipt = success()
    if field == "state":
        receipt["state"] = value
    elif field == "sender_state":
        receipt["sender"]["state"] = value
    elif field == "final":
        receipt["watch"]["final"] = value
    elif field == "final_task":
        receipt["watch"]["final"]["task_id"] = value
    elif field == "final_chat":
        receipt["watch"]["final"]["conversation_id"] = value
    elif field == "final_turns":
        receipt["watch"]["final"]["user_turns"] = value
    elif field == "final_exchange":
        receipt["watch"]["final"]["turn_exchange_id"] = value
    elif field == "watch_complete":
        receipt["watch"]["complete"] = value
    elif field == "final_complete":
        receipt["watch"]["final"]["complete"] = value
    elif field == "final_reason":
        receipt["watch"]["final"]["reason"] = value
    elif field == "final_model":
        receipt["watch"]["final"]["model"] = value
    elif field == "final_effort":
        receipt["watch"]["final"]["effort"] = value
    assert inspect(receipt)["canonical_final_verified"] is False


@pytest.mark.parametrize(
    ("which", "value"),
    [
        ("request_id", "other-task"),
        ("state", "SUCCESS_ASSUMED"),
        ("watch", "not-mapping"),
        ("sender", "not-mapping"),
    ],
)
def test_reject_malformed_or_unrecognized_receipts(which: str, value: object) -> None:
    receipt = success()
    receipt[which] = value
    with pytest.raises(ReceiptEvidenceError):
        inspect(receipt)


def test_an_unrecognized_final_state_does_not_prove_plugin_usage() -> None:
    receipt = success()
    result = inspect(receipt)
    assert result["skill_read_verified"] is False
    assert result["notes"].startswith("Receipt consistency only")
