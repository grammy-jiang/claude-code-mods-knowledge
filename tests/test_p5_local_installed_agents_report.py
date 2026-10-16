"""Fail-closed invariants for real local CLI/Skill installation proof.

The report is an attested native readback, not a generated model-host pass.
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILE = ROOT / "docs/reports/2026-10-16-p5-local-cli-and-skill-upgrade.json"


def load():
    return json.loads(FILE.read_text(encoding="utf-8"))


def test_three_distinct_hosts_report_latest_binaries_and_same_skill_digest():
    doc = load()
    hosts = doc["host_results"]
    assert len(hosts) == 3
    assert {h["name"] for h in hosts} == {"MacBook Pro", "Raspberry Pi", "sextant"}
    assert doc["deployed_skill_version"] == "0.3.4-beta.2"
    assert doc["matching_chatgpt_personal_plugin_version"] == "0.3.4-beta.2"
    assert doc["approved_claim_count"] == 31
    assert doc["installed_skill_file_count"] == 9
    assert re.fullmatch(r"[a-f0-9]{40}", doc["source_revision"])
    assert re.fullmatch(r"[a-f0-9]{64}", doc["skill_md_sha256"])
    assert re.fullmatch(r"[a-f0-9]{64}", doc["plugin_zip_sha256"])
    for host in hosts:
        assert host["native_codex_skill_match_count"] == 1
        assert host["native_pi_skill_match_count"] == 1
        assert host["native_skill_exact_hashes"] is True
        assert host["native_pi_relevant_diagnostics"] == 0
        assert host["claude_2_1_301_strict_synthetic_validate"] == "pass"
        assert host["claude_2_1_301_synthetic_mock_test"] == "1_pass_0_fail"
        assert host["cli_before"]["pi_agent"] == "1.3.0"
    assert doc["cli_versions_after"] == {
        "claude_code": "2.1.301",
        "codex": "0.163.0",
        "pi_agent": "1.3.0",
    }


def test_plugin_metadata_update_alone_never_counts_as_actual_codex_discovery():
    host = next(x for x in load()["host_results"] if x["name"] == "MacBook Pro")
    assert host["codex_local_plugin_prior_version"] == "0.1.0-rc.1"
    assert host["codex_local_plugin_installed_version"] == "0.3.4-beta.2"
    assert host["actual_native_codex_plugin_reregistered"] is True
    assert host["codex_global_skill_required_for_actual_discovery"] is True
    assert host["old_local_plugin_backed_up"] is True


def test_native_success_does_not_close_model_inference_or_version_compatibility():
    doc = load()
    assert doc["reviewed_mods_api_version"] == "Claude Code CLI 2.1.296 only"
    assert doc["all_native_installed_codex_checks_pass"] is True
    assert doc["all_native_installed_pi_checks_pass"] is True
    assert doc["all_native_claude_synthetic_tests_pass"] is True
    assert doc["native_actual_agent_model_inference_this_run"] is False
    assert doc["api_compatibility_2_1_301_full_reviewed"] is False
    assert doc["p5_complete"] is False
    assert doc["stable_release_ready"] is False
    assert doc["force_restarted_existing_agent_sessions"] is False


def test_three_real_claude_native_interactive_composers_show_enabled_skill_command():
    doc = load()
    assert doc["native_claude_interactive_discovery_hosts_passed"] == 3
    assert doc["native_claude_interactive_autocomplete_model_prompts_sent"] == 0
    assert doc["native_claude_headless_slash_list_status"] == (
        "not_supported_in_print_mode_not_a_skill_loader_failure"
    )
    assert doc["native_claude_headless_slash_list_probe_host"] == "MacBook Pro"
    assert len(doc["host_results"]) == 3
    for host in doc["host_results"]:
        assert host["claude_native_interactive_slash_autocomplete"] == "PASS"
        assert host["claude_native_interactive_skill_slug"] == ("claude-code-mods-development")
        assert host["claude_native_interactive_skill_description_shown"] is True
        assert host["claude_native_interactive_full_skill_slug_not_typed"] is True
        assert host["claude_native_model_prompt_submitted_for_autocomplete"] is False
        assert host["claude_native_interactive_only_trusted_own_disposable_empty_directory"] is True


def test_version_scoped_python_native_tests_skip_on_newer_cli_but_pass_pinned():
    result = load()["source_locked_regression"]
    for python in ("3_14", "3_11"):
        version = result[f"latest_cli_2_1_301_python_{python}"]
        assert version == {
            "passed": 633,
            "intentionally_skipped_for_2_1_296": 11,
            "failed": 0,
        }
    pin = result["temporarily_explicitly_pinned_2_1_296_binary_python_3_11"]
    assert pin == {"passed": 644, "skipped": 0, "failed": 0}
    assert result["pinned_cli_binary_replaces_global_install"] is False
    assert result["global_cli_still_2_1_301_after_test"] is True


def test_public_evidence_omits_private_urls_credentials_and_machine_user_paths():
    text = FILE.read_text(encoding="utf-8")
    assert re.search(r"[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}", text) is None
    assert "Plugin_" not in text
    assert "sandbox:/mnt/data/" not in text
    assert "/Users/" not in text
    assert "/home/" not in text
    assert "Bearer " not in text
    assert "cookie" not in text.lower()
    assert (
        re.search(r'"(?:access_token|api_key|client_secret|authorization)"\s*:', text, re.I) is None
    )
