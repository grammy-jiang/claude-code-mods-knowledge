"""SSOT-bound CLI302 hook-registration error-handling evidence and native QA.

Old 2.1.296 Skills and original approved 302 Claims must remain unchanged.
A synthetic native host test is not a fully approved 303/304 Claim.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from mods_knowledge.compiler import (
    CompilerError,
    _verified_cli302_hook_catch_notes,
    compile_knowledge,
)

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/cli302/hook_registration_catch_guidance.json"
NATIVE = ROOT / "docs/reports/2026-10-20-p5-hook-catch-native-three-version-review.json"
FIXTURES = ROOT / "evals/fixtures/p5-cli302-hook-catch"
OFFICIAL = "https://code.claude.com/docs/en/plugins/mods/events#handle-a-hook-that-fails"
BASELINE_296_SHA = "b831b476463c1b3aac8edc74dd579fc57dfa1c68c802ebfea0d738d73564f416"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_native_report_proves_before_after_catch_with_bounded_mock_results():
    report = json.loads(NATIVE.read_text())
    src = json.loads((FIXTURES / "manifest.json").read_text())
    assert report["schema_version"] == 1
    assert report["scope"] == "safe-synthetic-native-cli-mock-not-production"
    assert report["versions"] == ["2.1.302", "2.1.303", "2.1.304"]
    assert report["original_model_302_missing_catch_warnings"] == 5
    assert report["fixed_native_validate_with_catch_count"] == 9
    assert report["fixed_native_mock_pass_count"] == 18
    assert report["wrong_result_or_deny_catch_native_rejected_per_version"] == 3
    assert report["fixture_manifest_sha256"] == sha(FIXTURES / "manifest.json")
    assert set(src["sources"]) == {
        "normal.js",
        "prethrow.js",
        "postthrow.js",
        "wrong-deny.js",
        "observer.test.ts",
    }
    for name, original_hash in src["sources"].items():
        assert sha(FIXTURES / name) == original_hash
    rows = report["cases"]
    assert len(rows) == 9
    assert {(r["native_cli"], r["variant"]) for r in rows} == {
        (v, mode) for v in report["versions"] for mode in ("normal", "prethrow", "postthrow")
    }
    for row in rows:
        assert row["source_sha256"] == src["sources"][row["variant"] + ".js"]
        assert row["native_strict_catch_warning_free"] is True
        assert row["native_mock_read_and_denial_passed"] == 2
        assert row["native_mock_downstream_invocations_per_case"] == 1
    for field in (
        "native_thrown_error_object_identity_proven",
        "full_runtime_generated_tool_types_proven",
        "latest_cli_api_claims_approved",
        "stable_release_authorized",
        "real_user_tool_calls_or_host_home_mounted",
        "original_model_code_modified",
    ):
        assert report[field] is False
    assert report["real_model_inference_requests"] == 0
    assert report["real_user_permission_calls"] == 0


def test_302_compiled_skill_same_on_all_five_hosts_and_reference_surfaces():
    artifacts = compile_knowledge(
        ROOT, api_version="2.1.302", surface="cli", source_revision="hook-catch-p5"
    )
    skill_files = [v.decode() for k, v in artifacts.items() if k.endswith("/SKILL.md")]
    assert len(skill_files) == 5
    assert len(set(skill_files)) == 1
    skill = skill_files[0]
    assert len(skill) < 9000
    assert ".catch(($ , e, next) => next(e))" in skill
    assert "Local `try/catch` does not satisfy this hook" in skill
    assert "K-0040/K-0064/K-0068" in skill
    for ref in ("references/events.md", "references/claim-evidence.md"):
        body = artifacts["common/claude-code-mods-development/" + ref].decode()
        assert "P5 native hook-registration QA" in body
        assert OFFICIAL in body
        assert "not a new approved Claim" in body
        assert "console.log(" in body
        assert "K-0068" in body
    assert all(
        "CLI302 `tool.call` observers" not in v.decode()
        for k, v in artifacts.items()
        if k.endswith("references/security.md")
    )


def test_296_skill_is_byte_identical_to_historical_compilation():
    result = compile_knowledge(
        ROOT, api_version="2.1.296", surface="cli", source_revision="hook-catch-p5"
    )
    text = result["common/claude-code-mods-development/SKILL.md"]
    assert hashlib.sha256(text).hexdigest() == BASELINE_296_SHA
    assert (
        "P5 native hook-registration QA"
        not in result["common/claude-code-mods-development/references/events.md"].decode()
    )


def test_303_304_cannot_inherit_302_hook_catch_approval():
    for target in ("2.1.303", "2.1.304"):
        assert _verified_cli302_hook_catch_notes(ROOT, version=target, surface="cli") == (
            None,
            None,
        )
        with pytest.raises(CompilerError, match="No approved Claims"):
            compile_knowledge(ROOT, api_version=target, surface="cli", source_revision="p5")


def _staged_proof(base: Path) -> Path:
    files = (
        "evidence/cli302/hook_registration_catch_guidance.json",
        "docs/reports/2026-10-20-p5-hook-catch-native-three-version-review.json",
        "evals/fixtures/p5-cli302-hook-catch/manifest.json",
        "sources/registry.json",
        "claims/K-0068.json",
    )
    for relative in files:
        dest = base / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, dest)
    return base


@pytest.mark.parametrize(
    "tamper",
    (
        "missing_report",
        "wrong_model_count",
        "changed_note",
        "fake_version",
        "claim_widening",
        "fake_approval",
        "fake_permission_proof",
    ),
)
def test_source_bound_302_recovery_refuses_tampering(tmp_path: Path, tamper: str):
    stage = _staged_proof(tmp_path)
    note = stage / "evidence/cli302/hook_registration_catch_guidance.json"
    report = stage / "docs/reports/2026-10-20-p5-hook-catch-native-three-version-review.json"
    claim = stage / "claims/K-0068.json"
    if tamper == "missing_report":
        report.unlink()
    elif tamper == "wrong_model_count":
        obj = json.loads(report.read_text())
        obj["fixed_native_mock_pass_count"] = 19
        report.write_text(json.dumps(obj))
    elif tamper == "changed_note":
        obj = json.loads(note.read_text())
        obj["skill_step5"] = obj["skill_step5"].replace("next(e)", "{ deny: 'everything' }")
        note.write_text(json.dumps(obj))
    elif tamper == "fake_version":
        obj = json.loads(note.read_text())
        obj["reviewed_target_cli"] = "2.1.304"
        note.write_text(json.dumps(obj))
    elif tamper == "claim_widening":
        obj = json.loads(claim.read_text())
        obj["applies_to"]["claude_code"]["max_exclusive"] = "2.1.305"
        claim.write_text(json.dumps(obj))
    elif tamper == "fake_approval":
        obj = json.loads(note.read_text())
        obj["is_not_new_approved_api_claim"] = False
        note.write_text(json.dumps(obj))
    elif tamper == "fake_permission_proof":
        obj = json.loads(note.read_text())
        obj["interactive_user_permission_host_verified"] = True
        note.write_text(json.dumps(obj))
    with pytest.raises(CompilerError):
        _verified_cli302_hook_catch_notes(stage, version="2.1.302", surface="cli")


def test_original_source_catch_instruction_stays_public_and_private_data_excluded():
    assert sha(EVIDENCE) != sha(NATIVE)
    note = json.loads(EVIDENCE.read_text())
    assert note["first_party_locator"] == OFFICIAL
    assert note["native_report_sha256"] == sha(NATIVE)
    assert hashlib.sha256(note["skill_step5"].encode()).hexdigest() == note["skill_step5_sha256"]
    assert (
        hashlib.sha256(note["reference_note"].encode()).hexdigest() == note["reference_note_sha256"]
    )
    for file in (EVIDENCE, NATIVE):
        raw = file.read_text()
        for forbidden in (
            "/Users/",
            "/home/",
            "Cookie:",
            "Authorization:",
            "Plugin_",
            "TASK_ID:",
            "chatgpt.com/c/",
            "raw_reply",
            "sandbox:/mnt/data",
            "declare module 'claude-code'",
        ):
            assert forbidden not in raw
