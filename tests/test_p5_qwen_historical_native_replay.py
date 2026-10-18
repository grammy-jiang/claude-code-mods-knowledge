"""Historical real Qwen source/code errors must remain demonstrably blocked.

The complete native trace itself stays in private local evidence; CI only
reads an immutable redacted public SHA-linked replay report.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REPLAY_SOURCE = ROOT / "scripts/audit_p5_qwen_historical_native_replay.py"
HISTORY = ROOT / "docs/reports/2026-10-18-claude302-pi-local-native-recovered.json"
RESULT = ROOT / "docs/reports/2026-10-18-p5-qwen302-real-historical-replay.json"


def _module():
    spec = importlib.util.spec_from_file_location("qwen302_old_real_replay", REPLAY_SOURCE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _small_wire(*, stop_reason: str = "stop", users: int = 1) -> bytes:
    items = []
    for n in range(users):
        items.append(
            {
                "type": "message_end",
                "message": {
                    "role": "user",
                    "stopReason": "stop",
                    "content": [{"type": "text", "text": f"TASK_ID: FAKE-{n}\nOriginal task"}],
                },
            }
        )
    items.append(
        {
            "type": "message_end",
            "message": {
                "role": "assistant",
                "stopReason": stop_reason,
                "content": [{"type": "text", "text": "Original completed answer"}],
            },
        }
    )
    return ("\n".join(json.dumps(x) for x in items) + "\n").encode()


def test_trace_verification_requires_full_wire_and_final_answer_hash() -> None:
    mod = _module()
    raw = _small_wire()
    events, prompt, answer = mod.verify_original_trace(
        raw,
        expected_wire_sha256=hashlib.sha256(raw).hexdigest(),
        expected_answer_sha256=hashlib.sha256(b"Original completed answer").hexdigest(),
    )
    assert len(events) == 2
    assert prompt.startswith("TASK_ID: FAKE-0")
    assert answer == "Original completed answer"
    with pytest.raises(mod.HistoricalQwenReplayBlocked):
        mod.verify_original_trace(
            raw + b" ",
            expected_wire_sha256=hashlib.sha256(raw).hexdigest(),
            expected_answer_sha256=hashlib.sha256(b"Original completed answer").hexdigest(),
        )
    with pytest.raises(mod.HistoricalQwenReplayBlocked):
        mod.verify_original_trace(
            raw,
            expected_wire_sha256=hashlib.sha256(raw).hexdigest(),
            expected_answer_sha256=hashlib.sha256(b"Different answer").hexdigest(),
        )


@pytest.mark.parametrize(
    "wire",
    [
        _small_wire(stop_reason="error"),
        _small_wire(users=2),
        b"not jsonl\n",
    ],
)
def test_nonterminal_multiple_user_or_nonjson_originals_rejected(wire: bytes) -> None:
    mod = _module()
    with pytest.raises(mod.HistoricalQwenReplayBlocked):
        mod.verify_original_trace(
            wire,
            expected_wire_sha256=hashlib.sha256(wire).hexdigest(),
            expected_answer_sha256=hashlib.sha256(b"Original completed answer").hexdigest(),
        )


def test_true_original_qwen_old_failure_is_not_falsely_promoted() -> None:
    report = json.loads(RESULT.read_text())
    baseline = json.loads(HISTORY.read_text())
    assert report["reviewed_current_target"] == "2.1.302"
    assert report["native_model"] == "mac-qwen/qwen36-35b-a3b-mtp"
    assert report["original_historical_genuine_completed_turns"] == 3
    assert report["original_model_wire_and_final_sha256_verified"] == 3
    assert report["original_beta_model_rerun"] is False
    assert report["new_model_or_browser_requests_performed"] == 0
    assert report["positive_exact_source_error_blocked"] is True
    assert report["historical_unsupported_future_model_output_blocked"] is True
    assert report["unrelated_negative_structural_pass"] is True
    assert report["complete_p5_host_acceptance"] is False
    assert report["entire_native_qwen_semantics_certified"] is False
    assert report["stable_release_authorized"] is False
    assert (
        report["offline_replay_verifier_source_sha256"]
        == hashlib.sha256(REPLAY_SOURCE.read_bytes()).hexdigest()
    )
    records = report["cases"]
    assert len(records) == 3
    originals = {x["case_id"]: x for x in baseline["cases"]}
    assert len(originals) == 3
    for case in records:
        original = originals[case["original_case_type"]]
        assert case["original_native_wire_sha256"] == original["original_native_wire_sha256"]
        assert case["original_visible_answer_sha256"] == original["original_final_answer_sha256"]
        assert case["original_model_and_final_sha_verified"] is True
        assert case["output_of_historical_model_newly_delivered"] is False
        assert case["full_generated_mod_runtime_semantics_verified"] is False
    assert [(x["original_case_type"], x["current_postflight_action"]) for x in records] == [
        ("positive", "block_candidate"),
        ("negative", "allow_structural_only"),
        ("boundary", "block_candidate"),
    ]
    assert "missing_exact_approved_claim_sources" in records[0]["current_postflight_reason_codes"]
    assert records[1]["current_postflight_reason_codes"] == []
    assert records[2]["preflight_action_if_current_gate_were_used"] == "abstain_before_model"
    assert records[2]["current_postflight_reason_codes"] == ["preflight_was_not_enforced"]


def test_public_native_historical_replay_exposes_no_original_user_content() -> None:
    text = RESULT.read_text()
    for forbidden in (
        "/Users/",
        "/home/",
        "Plugin_",
        "Authorization:",
        "Cookie:",
        "TASK_ID:",
        "chatgpt.com/c/",
        "raw_reply",
        "raw_prompt",
        "sandbox:/mnt/data",
    ):
        assert forbidden not in text
    assert re.search(r"gh[pousr]_[A-Za-z0-9]{20,}", text) is None
    obj = json.loads(text)
    assert all(
        re.fullmatch(r"[a-f0-9]{64}", x["original_native_wire_sha256"])
        and re.fullmatch(r"[a-f0-9]{64}", x["original_visible_answer_sha256"])
        and re.fullmatch(r"[a-f0-9]{64}", x["original_user_prompt_sha256"])
        for x in obj["cases"]
    )
