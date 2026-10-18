"""Authentic Pi host preflight reports do not certify an offline model."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/reports/2026-10-18-p5-pi302-native-real-preflight.json"


def test_real_pi_host_preflight_never_masquerades_as_successful_model_inference():
    data = json.loads(REPORT.read_text())
    assert data["source_revision"] == "2aabca277cb947e9eb0d90e5554a03cd603c06af"
    assert data["target_claude_cli"] == "2.1.302"
    assert data["native_pi_version"] == "1.3.0"
    assert data["candidate_package_build"] == "0.4.12-p5gate.1"
    assert data["source_package_artifacts_verified"] == 53
    assert data["host_skill_yaml_files_checked"] == 5
    assert data["standalone_and_plugin_zip_files_checked"] == 2
    assert data["original_real_native_preflight_invocations"] == 3
    assert data["model_backend_live_health"] is False
    assert data["model_inference_requests_completed"] == 0
    assert data["model_inference_http_request_count"] == 0
    assert data["complete_p5_native_host_acceptance"] is False
    assert data["strict_p4_boundary_gate_was_modified"] is False
    assert data["stable_release_authorized"] is False
    assert [(x["case_id"], x["action"]) for x in data["cases"]] == [
        ("BOUND-VERSION-NEW", "abstain_before_model"),
        ("POS-E-01", "blocked_model_backend_unavailable"),
        ("NEG-TYPESCRIPT", "model_backend_required_after_preflight"),
    ]
    assert all(x["model_requests_performed"] == 0 for x in data["cases"])
    assert all(not x["actual_native_inference"] for x in data["cases"])
    assert all(not x["raw_model_output_delivered"] for x in data["cases"])


def test_real_pi_host_report_does_not_include_private_account_or_model_text():
    text = REPORT.read_text()
    for secret in (
        "/home/",
        "/Users/",
        "Plugin_",
        "Authorization:",
        "Cookie:",
        "chatgpt.com/c/",
        "TASK_ID:",
        "raw_reply",
    ):
        assert secret not in text
    assert re.search(r"gh[pousr]_[A-Za-z0-9]{20,}", text) is None
    obj = json.loads(text)
    assert all(re.fullmatch(r"[0-9a-f]{64}", row["original_report_sha256"]) for row in obj["cases"])
