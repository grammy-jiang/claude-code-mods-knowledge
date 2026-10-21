"""Pinned, fail-closed public audit of real installed, PTY and tool metadata evidence."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

from mods_knowledge.claims import (
    _requires_cli304_host_integration,
    approved_claims,
    load_claims,
)
from mods_knowledge.registry import load_registry

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/reports/2026-10-21-cli304-p1a-p1c-native-host-evidence.json"
AUDITOR = ROOT / "scripts/audit_cli304_p1a_p1c_live.py"
INSTALLED = ROOT / "evals/fixtures/cli304-p1a-installed-20261021/market"
MATRIX = ROOT / "evals/fixtures/cli304-p1c-readonly-20261021/qa-matrix"

_spec = importlib.util.spec_from_file_location("cli304_native_installed_p1_audit", AUDITOR)
assert _spec and _spec.loader
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


def digest(path: Path) -> str:
    assert path.is_file() and not path.is_symlink()
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evidence() -> dict:
    return json.loads(REPORT.read_text())


def test_installed_local_marketplace_source_and_private_auditor_pins():
    r = evidence()
    assert r["schema_version"] == 1
    assert r["target_cli"] == "2.1.304"
    assert r["official_native_sha256"] == _module.OFFICIAL_NATIVE_SHA
    assert r["private_auditor_sha256"] == digest(AUDITOR)
    assert digest(INSTALLED / ".claude-plugin/marketplace.json") == _module.MARKETPLACE_SHA
    assert (
        digest(INSTALLED / "plugins/qa-guard304-host/.claude-plugin/plugin.json")
        == _module.PLUGIN_MANIFEST_SHA
    )
    good_source = INSTALLED / "plugins/qa-guard304-host/hooks/register.js"
    assert digest(good_source) == _module.KNOWN_GOOD_HOOK_SHA
    assert (
        hashlib.sha256(good_source.read_bytes() + _module.BAD_SUFFIX).hexdigest()
        == _module.KNOWN_BAD_UPDATE_SHA
    )
    assert digest(MATRIX / ".claude-plugin/plugin.json") == _module.MATRIX_MANIFEST_SHA
    assert digest(MATRIX / "hooks/register.js") == _module.MATRIX_HOOK_SHA


def test_failed_installed_update_does_not_become_spurious_success():
    installed = evidence()["installed_reload"]
    assert installed["observed_profile"] == "local-marketplace-installed-0.0.1-to-invalid-0.0.2"
    assert installed["old_guard_denied_before_update"] is True
    assert installed["failed_versioned_reload_reported_zero_hooks"] is True
    assert installed["old_hook_unloaded_after_parse_error"] is True
    assert installed["identical_benign_prompt_entered_real_model_after_failed_reload"] is True
    assert installed["previous_safety_hook_preserved"] is False
    assert installed["result_turns"] == [0, 0, 1]
    assert "claude-sonnet-5-5" in installed["native_models"]
    assert installed["actual_tool_calls"] == []
    assert installed["broken_updated_hook_sha256"] == _module.KNOWN_BAD_UPDATE_SHA
    for name in ("wire_sha256", "debug_sha256", "stderr_sha256"):
        assert len(installed[name]) == 64


def test_readonly_metadata_is_actual_four_tool_native_matrix():
    result = evidence()["readonly_matrix"]
    assert result["coverage"] == "four tool kinds, not a complete built-in tool taxonomy"
    assert result["write_target_absent"] is True
    expected = {
        "Read": ("true", "allow"),
        "Glob": ("true", "allow"),
        "Grep": ("true", "allow"),
        "Write": ("undefined", "ask"),
    }
    assert set(result["cases"]) == set(expected)
    for tool, (readonly, permission) in expected.items():
        run = result["cases"][tool]
        assert run["actual_tool_calls"] == [tool]
        assert run["observed_isReadOnly"] == readonly
        assert run["original_host_verdict"] == permission
        assert run["test_hook_denied_actual_call"] is True
        assert "claude-sonnet-5-5" in run["native_models"]
        assert len(run["wire_sha256"]) == 64
        assert len(run["debug_sha256"]) == 64


def test_real_tui_approval_render_does_not_claim_approved_write():
    result = evidence()["interactive_permission"]
    assert result["real_interactive_toolcheck_ask"] is True
    assert result["actual_human_choice_ui_rendered"] is True
    assert result["write_target_absent"] is True
    assert result["positive_human_approval_and_write_tested"] is False
    assert result["managed_permissions_precedence_tested"] is False
    assert len(result["pty_sha256"]) == 64
    assert len(result["private_debug_sha256"]) == 64


def test_release_remains_blocked_and_no_user_private_receipts_enter_git():
    r = evidence()
    assert r["release"] == {
        "new_cli304_claims_approved": 0,
        "K0073_release_ready": False,
        "K0070_human_approval_full_pass": False,
        "K0071_complete_readonly_matrix": False,
        "stable_release_authorized": False,
    }
    for value in r["scope_limits"].values():
        assert value is True
    public = REPORT.read_text()
    for forbidden in (
        "/home/",
        "/Users/",
        "access_token",
        "Authorization:",
        "Cookie:",
        "QA304_BENIGN_BLOCK_THIS",
        "QA304_METADATA_FILE_CONTENT",
        "chatgpt.com/c/",
        "session_id",
        "conversation_id",
    ):
        assert forbidden not in public
    source_registry = load_registry(ROOT / "sources/registry.json")
    claims = load_claims(
        ROOT / "claims",
        source_registry,
        ROOT / "sources/snapshots",
        ROOT / "decisions",
    )
    assert approved_claims(claims, "2.1.304", "cli") == []
    for identifier in ("K-0070", "K-0071", "K-0072", "K-0073", "K-0074"):
        assert claims[identifier]["verification"]["runtime"] != "integration-pass"


def test_auditor_requires_original_private_binary_and_runtime(tmp_path: Path):
    with pytest.raises(_module.IncompleteNativeHostEvidence):
        _module.audit(tmp_path, tmp_path, tmp_path, tmp_path / "missing-official-304")


def test_new_permission_toolcheck_skip_and_reload_claims_require_real_host_integration():
    # Protect every known high-risk 2.1.304 delta, not only P-primary Claims.
    for i in range(70, 75):
        c = json.loads((ROOT / f"claims/K-{i:04d}.json").read_text())
        assert _requires_cli304_host_integration(c, (2, 1, 304)) is True
        assert _requires_cli304_host_integration(c, (2, 1, 302)) is False
    harmless = json.loads((ROOT / "claims/K-0073.json").read_text())
    harmless["subject"] = "mods.unrelated-benign-interface-documentation"
    harmless["areas"]["primary"] = ["S"]
    assert _requires_cli304_host_integration(harmless, (2, 1, 304)) is False
    # Never infer future-version safety approval solely from review/source pins.
    assert evidence()["release"]["new_cli304_claims_approved"] == 0
