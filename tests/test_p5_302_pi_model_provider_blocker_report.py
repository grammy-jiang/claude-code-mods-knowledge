"""Synthetic Pi native completion guards and original environmental blockage."""

from __future__ import annotations

import json
from pathlib import Path

R = Path(__file__).resolve().parents[1] / "docs/reports"
FILE = R / "2026-10-18-pi-model-provider-connection-error.json"


def test_original_two_pi_provider_trials_did_not_complete_model_inference() -> None:
    text = FILE.read_text(encoding="utf-8")
    data = json.loads(text)
    assert data["target_claude_code_cli"] == "2.1.302"
    assert data["pi_agent_version"] == "1.3.0"
    assert data["original_trial_count"] == 2
    assert data["endpoint_listening_when_checked"] is False
    assert data["provider_endpoint"] == "127.0.0.1:18080 (loopback only)"
    assert len(data["trials"]) == 2
    for item in data["trials"]:
        assert len(item["private_native_wire_sha256"]) == 64
        assert item["native_pi_process_exit_code"] == 0
        assert item["assistant_final_model_stop_reason"] == "error"
        assert item["assistant_error_type"] == "connection_error"
        assert item["failed_model_requests"] == 4
        assert item["automatic_native_retry_starts"] == 3
        assert item["automatic_native_retry_exhausted"] is True
        assert item["agent_end_or_settled_emitted"] is True
        assert item["native_model_final_success"] is False
        assert item["real_skill_read_events"] == 0
        assert item["source_and_semantic_acceptance"] is False
    assert data["model_generated_code_executed"] is False
    assert data["private_model_text_or_account_content_exported"] is False
    assert data["release_gate"] == "HOLD"
    for forbidden in (
        "/Users/",
        "/home/",
        "Models.noindex",
        "private-wire",
        "conversation_id",
        "Plugin_26915045",
        "Bearer ",
    ):
        assert forbidden not in text
