"""Release blockers and actual Codex host evidence remain honest and public-safe."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_current_gate_does_not_claim_stable_release_pass() -> None:
    record = json.loads(
        (ROOT / "docs/reports/2026-10-14-stable-readiness-blocked.json").read_text()
    )
    assert record["schema_version"] == 1
    assert record["status"] == "STABLE_RELEASE_BLOCKED"
    assert record["eligible_for_stable_release"] is False
    assert record["checks"]["package_integrity"] == "pass"
    assert record["checks"]["chat_46_case_quality"] == "fail"
    assert record["checks"]["three_agent_model_validation"] == "fail"
    assert record["checks"]["account_install_rollback"] == "fail"
    assert record["blockers"]
    assert re.fullmatch(r"[a-f0-9]{64}", record["plugin_zip_sha256"])


def test_real_codex_inference_report_does_not_upgrade_partial_to_full_host_pass() -> None:
    record = json.loads((ROOT / "docs/reports/2026-10-14-codex-real-model-qa.json").read_text())
    assert record["origin"] == "real_Codex_CLI_inference"
    assert record["model_calls"] == 3
    assert record["model_test_status"] == "partial"
    assert record["full_p5_host_acceptance"] is False
    items = {c["category"]: c for c in record["cases"]}
    assert set(items) == {"positive", "negative", "boundary"}
    assert all(c["real_model_inference"] for c in items.values())
    assert items["positive"]["canonical_skill_read"] is True
    assert "references/events.md" in items["positive"]["reference_files_read"]
    assert items["positive"]["correct_callback_arity"] is True
    assert items["negative"]["canonical_skill_read"] is False
    assert items["boundary"]["canonical_skill_read"] is True
    assert items["boundary"]["abstains_unverified_version"] is True
    assert items["boundary"]["verdict"] == "partial"
    assert items["boundary"]["first_party_official_url_present"] is False


def test_public_reports_contain_hashes_not_raw_sensitive_conversations() -> None:
    for name in ("2026-10-14-stable-readiness-blocked.json", "2026-10-14-codex-real-model-qa.json"):
        raw = (ROOT / "docs/reports" / name).read_text()
        assert not any(
            s in raw
            for s in (
                "conversation_id",
                "chatgpt.com/c/",
                "/Users/",
                "/home/",
                "Cookie:",
                "Authorization: Bearer",
                "OPENAI_API_KEY",
                "raw_reply",
            )
        )
        assert not re.search(r"gh[pousr]_[A-Za-z0-9]{20,}", raw)
