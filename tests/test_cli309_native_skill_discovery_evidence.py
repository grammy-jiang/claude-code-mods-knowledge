"""Original official CLI309 model Skill calls, source routing and Mod alias QA."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from pathlib import Path

import pytest

from mods_knowledge.claims import approved_claims, load_claims
from mods_knowledge.compiler import CompilerError, compile_knowledge
from mods_knowledge.registry import load_registry

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/reports/2026-10-23-cli309-two-pi-native-skill-evidence.json"
AUDIT = ROOT / "scripts/audit_cli309_native_skill_evidence.py"
FIXTURE = ROOT / "evals/fixtures/cli309-skill-discovery-20261023"
EXPECTED_BINARY = "9796dd26899337f687739a0b39a7353b639f062a3436a7b941fcf19a1b757a9b"
EXPECTED_ASSET = "8ecd1f2d06ccbd3f89c8886e840e42b57a19063f3de9cfe5f7d90fe875ba99ef"

_spec = importlib.util.spec_from_file_location("cli309_native_skill_original_evidence", AUDIT)
assert _spec and _spec.loader
audit = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(audit)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evidence() -> dict:
    return json.loads(REPORT.read_text())


def test_original_two_pi_native_309_target_and_fixture_source_provenance():
    r = evidence()
    assert r["schema_version"] == 1
    assert r["target_version"] == "2.1.309"
    assert r["official_tarball_sha256"] == EXPECTED_ASSET
    assert r["official_native_binary_sha256"] == EXPECTED_BINARY
    assert set(r["real_native_hosts"]) == {"rpi-a", "rpi-b"}
    for host, original in r["real_native_hosts"].items():
        assert original["schema"] == 1
        assert original["host"] == host
        assert original["official_native_cli_version"] == "2.1.309"
        assert original["official_native_cli_sha256"] == EXPECTED_BINARY
        assert original["official_asset_sha256"] == EXPECTED_ASSET
        assert original["auditor_source_sha256"] == sha(AUDIT)
        assert original["fixture_sha256"] == audit.EXPECTED_FIXTURES
        assert len(r["original_host_private_reports_sha256"][host]) == 64
        for filename, wanted in original["fixture_sha256"].items():
            assert sha(FIXTURE / filename) == wanted
        assert original["stable_release_authorized"] is False
        assert original["exact_309_claims_approved"] == 0


@pytest.mark.parametrize(
    ("host", "cases"),
    [
        (
            "rpi-a",
            {
                "unrestricted": "mods-qa-route",
                "add-dir-qualified": "addons:mods-qa-route",
                "nested-cwd": "mods-qa-nested",
                "automatic-project": "mods-qa-route",
                "automatic-addons": "addons:mods-qa-route",
            },
        ),
        (
            "rpi-b",
            {
                "s-root": "mods-qa-route",
                "s-addons": "addons:mods-qa-route",
                "s-nested": "mods-qa-nested",
            },
        ),
    ],
)
def test_named_and_qualified_skill_sources_were_real_native_tool_calls(host, cases):
    rows = evidence()["real_native_hosts"][host]["scenarios"]
    for case, skill in cases.items():
        data = rows[case]
        assert data["actual_assistant_model"] == "claude-sonnet-5-5"
        assert data["real_tool_names"] == ["Skill"]
        assert data["actual_skill_tool_arguments"] == [skill]
        assert data["actual_native_skill_invocation_pass"] is True
        assert data["source_selected_correctly"] is True
        assert data["true_skill_tool_use_not_just_model_text"] is True
        assert len(data["native_result_turns"]) == 1
        assert data["native_result_turns"][0] >= 1
        for key in ("source_private_wire_sha256", "source_private_debug_sha256"):
            assert re.fullmatch(r"[0-9a-f]{64}", data[key])


def test_same_native_process_nested_read_then_skill_and_no_tool_control():
    rows = evidence()["real_native_hosts"]["rpi-a"]["scenarios"]
    nested = rows["nested-dynamic"]
    assert nested["same_native_session_two_turns"] is True
    assert nested["native_read_then_skill_tool"] is True
    assert nested["nested_skill_marker_correct"] is True
    assert nested["actual_native_skill_invocation_pass"] is True
    assert nested["real_tool_names"] == ["Read", "Skill"]
    assert nested["actual_skill_tool_arguments"] == ["mods-qa-nested"]
    assert len(nested["native_result_turns"]) == 2
    control = rows["unrelated-control"]
    assert control["actual_assistant_model"] == "claude-sonnet-5-5"
    assert control["real_tool_names"] == []
    assert control["actual_skill_tool_arguments"] == []
    assert control["unrelated_question_answer_correct"] is True
    assert control["no_unrelated_skill_or_tool_invoked"] is True


def test_real_mod_alias_observed_as_haiku_on_both_native_hosts():
    for host in ("rpi-a", "rpi-b"):
        alias = evidence()["real_native_hosts"][host]["scenarios"]["alias"]
        assert alias["actual_assistant_model"] == "claude-haiku-5-5"
        assert alias["requested_model_alias"] == "haiku"
        assert alias["actual_model_alias_resolved_to"] == "claude-haiku-5-5"
        assert alias["official_native_plugin_validate_strict"] is True
        assert alias["real_turn_step_hook_executed"] is True
        assert alias["real_model_result_without_tools"] is True
        assert alias["real_tool_names"] == []
        assert len(alias["native_result_turns"]) == 1


def test_restricted_negative_is_not_misclassified_from_guess_or_direct_file_read():
    case = evidence()["real_native_hosts"]["rpi-a"]["scenarios"]["restricted-natural"]
    assert case["actual_assistant_model"] == "claude-sonnet-5-5"
    assert "Skill" in case["real_tool_names"]
    assert "Read" in case["real_tool_names"]
    assert case["native_skill_invocation_failed_unknown_skill"] is True
    assert case["direct_read_cannot_be_counted_as_skill_invocation"] is True
    assert case["source_marker_not_sufficient_for_pass"] is True
    assert "actual_native_skill_invocation_pass" not in case


def test_old_approved_claims_cannot_be_promoted_by_genuine_fixture_success():
    r = evidence()
    assert r["host_private_source_and_native_wire_replay_byte_identical"] is True
    assert r["project_skill_automatic_selection_with_generic_use_skill_instruction_tested"] is True
    assert r["full_generated_mods_ssot_skill_content_quality_not_validated"] is True
    assert r["bundled_verify_and_code_review_nested_flows_not_tested"] is True
    assert r["genuine_codex_and_pi_agent_latest_skill_matrix_not_tested"] is True
    assert r["new_309_claims_approved"] == 0
    assert r["production_user_skills_changed"] is False
    assert r["production_claude_cli_changed_by_this_QA"] is False
    assert r["stable_release_authorized"] is False
    registry = load_registry(ROOT / "sources/registry.json")
    claims = load_claims(ROOT / "claims", registry, ROOT / "sources/snapshots", ROOT / "decisions")
    assert len(approved_claims(claims, "2.1.302", "cli")) == 31
    assert approved_claims(claims, "2.1.309", "cli") == []
    with pytest.raises(CompilerError, match="No approved Claims"):
        compile_knowledge(ROOT, api_version="2.1.309", surface="cli", source_revision="qa-only")


def test_private_logs_not_shipped_or_inferable_as_sandbox_links():
    data = REPORT.read_text()
    for forbidden in (
        "/home/",
        "/Users/",
        "Authorization:",
        "Cookie:",
        "access_token",
        "BEGIN PRIVATE KEY",
        "sandbox:/mnt/data",
        "session_id",
        "tool_use_id",
    ):
        assert forbidden not in data
    assert (
        re.search(
            r"(?<![0-9a-f])[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}(?![0-9a-f])",
            data,
        )
        is None
    )


def test_unavailable_original_native_host_cannot_be_passed_from_public_report(tmp_path):
    with pytest.raises((audit.SkillEvidenceBlocked, OSError, ValueError)):
        audit.audit(tmp_path, FIXTURE, host="rpi-a")
