"""Official v2.1.303/304 facts are pinned, never silently promoted to CLI302."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

from mods_knowledge.compiler import CompilerError, compile_knowledge
from mods_knowledge.pi_delivery_gate import PiDeliveryGateError, preflight_mods_case

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "evidence/upstream/claude_code_v2_1_303_304_release_notes_20261020.json"
CORE302 = "8afa71883ecfa52901eb7a04cf31fef700d8ba565eaad244f4884cc620f8d56e"
CORE304 = "6694767741c445872577d96a55fb08816d0f4b5783bc49e1eacd55f27b383308"
UPSTREAM304 = "7a6144fde0e5e4733c1108e1890430722c12839159aeb1a5be7bec8aaa881cf8"


def test_upstream_release_facts_are_exact_scoped_and_not_approved_claims():
    data = json.loads(REPORT.read_text())
    assert data["schema_version"] == 1
    assert data["upstream_project"] == "anthropics/claude-code"
    assert (
        data["source_review_status"] == "RELEASE_NOTE_FACTS_CAPTURED_NOT_APPROVED_CLI304_API_CLAIMS"
    )
    assert len(data["releases"]) == 2
    old, new = data["releases"]
    assert old["version"] == "2.1.303"
    assert old["official_body_sha256"] == (
        "dd490d3f4e93c8165c0322324024d1202fe097b1be5a232b6035fd40bfee97cc"
    )
    assert old["release_notes_are_generic"] is True
    assert old["no_api_change_assertion_is_not_justified"] is True
    assert old["upstream_url"] == (
        "https://github.com/anthropics/claude-code/releases/tag/v2.1.303"
    )
    assert new["version"] == "2.1.304"
    assert new["official_body_sha256"] == UPSTREAM304
    assert new["upstream_url"] == (
        "https://github.com/anthropics/claude-code/releases/tag/v2.1.304"
    )
    assert len(new["relevant_mods_deltas"]) == 4
    assert {x["kind"] for x in new["relevant_mods_deltas"]} == {
        "tool.check.answer.decider.person",
        "tool.check.event.isReadOnly",
        "mod.hook.skip.transcript.diagnostic",
        "mod.hot_reload.failure.recovery",
    }
    for row in new["relevant_mods_deltas"]:
        assert row["review_status"] == "PENDING_NATIVE_TYPE_AND_RUNTIME_VALIDATION"
        assert re.fullmatch(r"[0-9a-f]{64}", row["upstream_release_bullet_sha256"])
        assert row["first_party_release_line_verified"] is True
    assert data["compiler_version_304_publish_authorized"] is False
    assert data["version_303_api_compatibility_proven"] is False
    assert data["version_304_api_compatibility_proven"] is False
    assert data["chatgpt_plugin_stable_release_authorized"] is False


def test_exact_official_native_304_archive_core_provenance_and_bounded_mocks():
    data = json.loads(REPORT.read_text())
    new = data["releases"][1]
    asset = new["asset_linux_arm64"]
    runtime = new["native_sandbox_target_review"]
    assert asset["size_bytes"] == 128633972
    assert asset["release_asset_sha256"] == (
        "sha256:17cc5d933babad064bed65b3a4fbafab29556fbbfc12aa7888ae1f6c320e08c5"
    )
    assert runtime["asset_tarball_checksum_matched_first_party_release"] is True
    assert runtime["official_linux_arm64_binary_sha256"] == (
        "c487117526509ab6d2ee6013e14f181faf68d6d6afe6bb0d4b2b4a9feca5ecb3"
    )
    assert runtime["native_version_in_networkless_bubblewrap"] == "2.1.304 (Claude Code)"
    assert runtime["native_core_type_bytes"] == 661289
    assert runtime["native_core_types_sha256"] == CORE304
    assert runtime["native_302_core_types_sha256_comparison"] == CORE302
    assert runtime["typecheck_transition"] == {
        "source_sha256": "d103f782bea523878d6978354498c25111c1384df60a9d37cb9be83e32c80884",
        "target_302_outcome": "rejected missing input.isReadOnly and invalid decider person",
        "target_304_outcome": "strict TypeScript 6.0.3 pass",
    }
    assert runtime["native_304_synthetic_permission_tests_passed"] == 4
    assert runtime["native_304_synthetic_permission_tests_failed"] == 0
    assert runtime["native_304_gating_hook_with_catch_confirmed"] is True
    assert runtime["native_304_forced_hook_throw_failed_closed_to_deny"] is True
    assert runtime["native_304_backward_mock_validations_passed"] == 5
    assert runtime["native_304_backward_mocked_read_denial_tests_passed"] == 10
    assert runtime["native_304_backward_negative_wrong_tool_result_rejected"] is True
    assert runtime["native_live_permission_dialog_and_host_callback_verified"] is False
    assert runtime["fully_reviewed_new_304_api_claims_authorized"] is False
    assert data["native_304_source_original_private_type_declarations_not_published"] is True


@pytest.mark.parametrize("unreviewed", ("2.1.303", "2.1.304"))
def test_unreviewed_cli_cannot_inherit_302_skill_or_pi_delivery_approval(unreviewed: str):
    with pytest.raises(CompilerError, match="No approved Claims"):
        compile_knowledge(
            ROOT, api_version=unreviewed, surface="cli", source_revision="304-unapproved"
        )
    with pytest.raises(PiDeliveryGateError):
        preflight_mods_case(
            {
                "id": "BOUND-VERSION-NEW",
                "category": "boundary",
                "prompt": "Use the unsupported Claude Code Mods interface.",
            },
            target_version=unreviewed,
        )


def test_302_approved_skill_output_is_not_rewritten_by_unreviewed_304_notes():
    artifact = compile_knowledge(
        ROOT,
        api_version="2.1.302",
        surface="cli",
        knowledge_version="0.4.13",
        package_version="0.4.13-beta.1",
        source_revision="304-unapproved",
    )
    skill = artifact["common/claude-code-mods-development/SKILL.md"]
    assert hashlib.sha256(skill).hexdigest() == (
        "2bf40148db70ef435cc0993614d95e57074cfcd036ed8e9ff97d19dfd9cfc109"
    )
    text = skill.decode()
    assert "CLI 2.1.302 hook types" in text
    assert 'decider: "person"' not in text
    assert "e.isReadOnly" not in text
    assert len(text) < 9000


def test_public_review_does_not_export_original_complete_types_or_secrets():
    text = REPORT.read_text()
    for forbidden in (
        "/Users/",
        "/home/",
        "Authorization:",
        "Cookie:",
        "Plugin_",
        "TASK_ID:",
        "chatgpt.com/c/",
        "raw_reply",
        "sandbox:/mnt/data",
        "declare module 'claude-code'",
    ):
        assert forbidden not in text
    assert not re.search(r"gh[pousr]_[A-Za-z0-9]{20,}", text)
    assert not any(
        path.name.endswith(".d.ts")
        for path in (ROOT / "evidence/upstream").rglob("*")
        if path.is_file()
    )
