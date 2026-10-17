"""Latest host observations may append, not overwrite historical profiles."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_current_302_hosts_preserve_historical_profiles() -> None:
    profiles = json.loads((ROOT / "targets/profiles.json").read_text())
    by_id = {profile["profile_id"]: profile for profile in profiles}
    assert len(by_id) == len(profiles)
    for old in ("macbook-20261013", "raspberry-pi-20261013"):
        assert by_id[old]["claude_code_version"] == "2.1.296"
    for host, os_name, arch in (
        ("macbook-20261017-claude302", "macos", "arm64"),
        ("raspberry-pi-20261017-claude302", "linux", "aarch64"),
        ("sextant-20261017-claude302", "linux", "aarch64"),
    ):
        row = by_id[host]
        assert row["claude_code_version"] == "2.1.302"
        assert row["codex_version"] == "0.163.0"
        assert row["pi_version"] == "1.3.0"
        assert row["os"] == os_name and row["architecture"] == arch
        assert "no restart" in row["notes"].lower()


def test_latest_source_delta_cannot_be_mistaken_for_new_approval() -> None:
    report = json.loads(
        (ROOT / "docs/reports/2026-10-17-claude-code-2.1.302-refresh.json").read_text()
    )
    assert report["official_latest_claude_code"] == "2.1.302"
    assert report["source_collection"]["eligible_official_sources"] == 43
    assert report["source_collection"]["changed_since_old_pin"] == 43
    assert report["markdown_review_delta"]["section_status_counts"] == {
        "UNCHANGED": 18,
        "CHANGED": 8,
        "HEADING_MISSING_OR_AMBIGUOUS": 1,
    }
    gap = report["claims_version_gap"]
    assert gap["old_approved_count"] == 31
    assert gap["current_version_approved"] == 0
    assert gap["old_decisions_not_modified"] is True
    assert gap["latest_build_and_chat_plugin_release_blocked"] is True
    assert gap["claim_review_status"] == {"unchanged_only": 23, "needs_review": 8}
    assert report["host_native_smoke"]["real_model_inference"] is False
    assert len(report["installed_hosts"]) == 3
