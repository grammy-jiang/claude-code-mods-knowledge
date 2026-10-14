"""Native loader observations remain correctly scoped and sanitized."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_native_host_discovery_baseline_no_model_response_fiction() -> None:
    file = ROOT / "docs/reports/2026-10-14-native-agent-skill-discovery.json"
    raw = file.read_text(encoding="utf-8")
    data = json.loads(raw)
    assert data["test_kind"] == "model_free_native_agent_skill_discovery"
    assert data["schema_version"] == 1
    assert data["full_agent_model_answer_tests"] == "not_run"
    assert data["cross_host_artifact_identical"] is True
    assert len(data["plugin_zip_sha256"]) == 64
    hosts = data["host_results"]
    assert set(hosts) == {"macbook", "raspberrypi", "sextant"}
    for host in hosts.values():
        assert host["checks"]["codex"]["status"] == "pass"
        assert host["checks"]["codex"]["native_loader"] == "app-server skills/list"
        assert host["checks"]["codex"]["skills_loaded"] == 1
        assert host["checks"]["claude_code"]["status"] == "pass"
        assert host["checks"]["claude_code"]["real_skill_invocation"] == "not_run"
        assert host["all_available_native_checks_pass"] is True
    assert hosts["macbook"]["checks"]["pi_agent"]["status"] == "pass"
    assert hosts["raspberrypi"]["checks"]["pi_agent"]["status"] == "pass"
    assert hosts["sextant"]["checks"]["pi_agent"]["status"] == "unavailable"
    assert hosts["sextant"]["versions"]["claude"] == "2.1.289"


def test_native_host_report_has_no_credentials_or_identity_leakage() -> None:
    text = (ROOT / "docs/reports/2026-10-14-native-agent-skill-discovery.json").read_text(
        encoding="utf-8"
    )
    for forbidden in (
        "/Users/",
        "/home/",
        "Plugin_",
        "conversation_id",
        "access_token",
        "refresh_token",
        "cookie",
        "Authorization: Bearer",
    ):
        assert forbidden not in text
