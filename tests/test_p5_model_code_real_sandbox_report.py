"""Genuine Codex/Sonnet code: immutable native CLI302 mock acceptance evidence.

The P5 sandbox report is an offline, SHA-bound original observation.
Public CI never executes model snippets: those were executed only inside
Linux Bubblewrap on Pi; these tests validate immutable narrow outcomes.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/reports/2026-10-19-cli302-codex-sonnet-original-js-native-mock.json"
FIXTURE = ROOT / "evals/fixtures/p5-native-model-code-302"


def test_observer_behavior_and_native_mock_do_not_upgrade_to_production_pass() -> None:
    report = json.loads(REPORT.read_text())
    assert report["schema_version"] == 1
    assert report["date"] == "2026-10-19"
    assert report["target_cli"] == "2.1.302"
    assert report["native_model_origin_code_files_sha256_verified"] == 5
    assert report["self_contained_original_register_modules"] == 3
    assert report["sonnet_original_bare_fragments_wrapped_for_test_only"] == 2
    assert report["sonnet_bash_documentation_examples_not_executed"] == 1
    assert report["node_parse_checks_passed"] == 5
    assert report["node_synthetic_next_event_contract_checks_passed"] == 48
    assert report["node_synthetic_next_event_contract_checks_failed"] == 0
    assert report["node_bad_result_replacement_control_detected"] is True
    assert report["node_bad_result_replacement_failing_checks"] >= 1
    assert report["real_cli302_native_mod_strict_validator_passed"] == 5
    assert report["real_cli302_native_mock_read_result_and_denial_checks_passed"] == 10
    assert report["real_cli302_native_mock_read_result_and_denial_checks_failed"] == 0
    assert report["real_cli302_wrong_downstream_mock_counterexample_rejected"] is True
    assert report["bubblewrap_full_os_isolation"] is True
    assert report["network_namespace_unshared"] is True
    assert report["original_host_home_mounted"] is False
    assert report["native_model_http_inference_requests"] == 0
    assert report["raw_user_tools_or_commands_executed"] is False
    assert report["model_generated_mod_code_executed_only_in_os_sandbox"] is True
    assert report["official_cli302_generated_typescript_declarations_typechecked"] is False
    assert report["real_interactive_claude_mods_session_permission_semantics_verified"] is False
    assert report["entire_real_model_answer_production_approved"] is False
    assert report["stable_release_authorized"] is False


def test_frozen_mock_report_binds_to_exact_original_fixtures_and_tests() -> None:
    report = json.loads(REPORT.read_text())
    assert (
        report["original_evidence_fingerprint_manifest_sha256"]
        == hashlib.sha256((FIXTURE / "manifest.json").read_bytes()).hexdigest()
    )
    assert (
        report["trusted_synthetic_next_event_contract_sha256"]
        == hashlib.sha256((FIXTURE / "observer-contract.test.mjs").read_bytes()).hexdigest()
    )
    assert (
        report["trusted_native_mod_mock_tool_test_sha256"]
        == hashlib.sha256((FIXTURE / "mod-host-mock.test.ts").read_bytes()).hexdigest()
    )
    originals = json.loads((FIXTURE / "manifest.json").read_text())["model_candidate_sources"]
    fixture_map = {
        **{x["code_sha256"]: x["path"] for x in originals[0]["fixtures"]},
        **{x["code_sha256"]: x["fixture_path"] for x in originals[1]["source"]["blocks"]},
    }
    assert len(fixture_map) == 5
    rows = report["per_actual_native_model_code_block"]
    assert len(rows) == 5
    assert len({x["model_source_code_sha256"] for x in rows}) == 5
    assert [x["fragment_requires_nonoriginal_wrapper"] for x in rows] == [
        False,
        False,
        True,
        True,
        False,
    ]
    for row in rows:
        filename = fixture_map[row["model_source_code_sha256"]]
        assert (
            hashlib.sha256((FIXTURE / filename).read_bytes()).hexdigest()
            == (row["model_source_code_sha256"])
        )
        assert row["native_claude_2_1_302_plugin_validate_strict"] == "pass"
        assert row["native_claude_2_1_302_mocked_mod_tests_passed"] == 2
        assert row["native_claude_2_1_302_mocked_mod_tests_failed"] == 0
        assert row["actual_interactive_user_session_approved"] is False
        assert row["real_user_tool_invoked"] is False


def test_public_host_results_exclude_private_account_and_model_text() -> None:
    text = REPORT.read_text()
    for banned in (
        "/home/",
        "/Users/",
        "Plugin_",
        "Authorization:",
        "Cookie:",
        "chatgpt.com/c/",
        "TASK_ID:",
        "raw_reply",
        "sandbox:/mnt/data",
    ):
        assert banned not in text
    assert re.search(r"gh[pousr]_[A-Za-z0-9]{20,}", text) is None
    doc = json.loads(text)
    for key in (
        "original_evidence_fingerprint_manifest_sha256",
        "trusted_synthetic_next_event_contract_sha256",
        "trusted_native_mod_mock_tool_test_sha256",
    ):
        assert re.fullmatch(r"[a-f0-9]{64}", doc[key])
