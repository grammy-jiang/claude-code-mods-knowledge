"""QA evidence for native interactive TUI invalid/repaired Plugin reload.

All original tty bytes and hosted model messages remain private on the Pi.
These offline tests check strictly limited immutable host facts, not a new
TUI model execution or any production approval.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

from mods_knowledge.claims import approved_claims, load_claims
from mods_knowledge.registry import load_registry

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/reports/2026-10-22-cli304-tui-reload-host-evidence.json"
AUDITOR = ROOT / "scripts/audit_cli304_tui_recovery_evidence.py"
GATE = ROOT / "scripts/guard_cli304_native_plugin.py"
BAD = ROOT / "evals/fixtures/cli304-tui-recovery-20261022/invalid-0.0.6"
GOOD = ROOT / "evals/fixtures/cli304-tui-recovery-20261022/repaired-0.0.7"

_spec = importlib.util.spec_from_file_location("reviewed_clean_qa_source", GATE)
assert _spec and _spec.loader
_gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_gate)


def digest(p: Path) -> str:
    assert p.is_file() and not p.is_symlink()
    return hashlib.sha256(p.read_bytes()).hexdigest()


def report() -> dict:
    return json.loads(REPORT.read_text(encoding="utf-8"))


def test_source_clean_versions_and_auditor_hashes_are_frozen():
    r = report()
    assert r["schema_version"] == 1
    assert r["target_cli"] == "2.1.304"
    assert r["independent_auditor_sha256"] == digest(AUDITOR)
    assert r["official_native_binary_sha256"] == _gate.NATIVE_CLI304_SHA
    assert (
        _gate.inspect_tree(BAD)["content_tree_sha256"] == r["invalid_clean_candidate_tree_sha256"]
    )
    assert _gate.inspect_tree(GOOD)["content_tree_sha256"] == r["valid_clean_candidate_tree_sha256"]
    assert _gate.inspect_tree(BAD)["plugin_version"] == "0.0.6"
    assert _gate.inspect_tree(GOOD)["plugin_version"] == "0.0.7"
    assert digest(BAD / "hooks/register.js") == r["invalid_hook_sha256"]
    assert digest(GOOD / "hooks/register.js") == r["good_hook_sha256"]
    assert ".orphaned_at" not in {p.name for p in BAD.iterdir()}
    assert ".orphaned_at" not in {p.name for p in GOOD.iterdir()}


def test_actual_tui_failure_and_repair_not_mistaken_for_initial_protection():
    r = report()
    assert r["actual_tui_single_host_process_tested"] is True
    assert r["initial_qa_hook_module_loaded"] is True
    assert r["bad_version_native_strict_validator_rejected"] is True
    assert r["bad_version_official_update_succeeded"] is True
    assert r["failed_tui_reload_dropped_previous_hook"] is True
    assert r["real_model_turn_completed_while_hook_missing"] is True
    assert r["real_assistant_output_observed_not_just_prompt_echo"] is True
    assert r["repaired_version_native_strict_validator_passed"] is True
    assert r["repaired_version_official_update_succeeded"] is True
    assert r["valid_tui_reload_loaded_and_registered_new_hook"] is True
    assert r["subsequent_benign_prompt_stopped_before_model"] is True
    assert r["last_good_security_hook_preserved_during_failed_reload"] is False
    assert r["clean_package_checksum_excludes_host_generated_cache_metadata"] is True
    for key in (
        "private_tui_terminal_sha256",
        "private_tui_debug_sha256",
        "private_qa_summary_sha256",
    ):
        assert len(r[key]) == 64 and all(c in "0123456789abcdef" for c in r[key])


def test_evidence_never_promotes_api_version_or_production_sessions():
    r = report()
    assert r["approved_new_cli304_claims"] == 0
    assert r["stable_release_authorized"] is False
    assert r["unrelated_production_sessions_authorized"] is False
    assert r["managed_permission_precedence_tested"] is False
    assert r["positive_human_permission_approval_tested"] is False
    assert r["other_plugin_scopes_or_hosts_validated"] is False
    assert r["raw_model_and_terminal_not_published"] is True
    assert "unsigned" in r["limitations"]
    source_registry = load_registry(ROOT / "sources/registry.json")
    claims = load_claims(
        ROOT / "claims", source_registry, ROOT / "sources/snapshots", ROOT / "decisions"
    )
    assert approved_claims(claims, "2.1.304", "cli") == []
    for number in range(70, 75):
        assert claims[f"K-{number:04}"]["verification"]["runtime"] != "integration-pass"


def test_report_excludes_raw_model_prompt_and_private_session_content():
    text = REPORT.read_text()
    for forbidden in (
        "/home/",
        "/Users/",
        "access_token",
        "Authorization:",
        "Cookie:",
        "conversation_id",
        "session_id",
        "QA304_BENIGN_BLOCK_THIS",
        "chatgpt.com/c/",
    ):
        assert forbidden not in text
    assert len(text.encode()) < 8000


def test_auditor_cannot_accept_absent_private_native_trace(tmp_path: Path):
    completed = subprocess.run(  # noqa: S603 - controlled local Python script
        [
            sys.executable,
            str(AUDITOR),
            "--private-root",
            str(tmp_path),
            "--official-binary",
            str(tmp_path / "missing-cli"),
            "--out",
            str(tmp_path / "nonexistent-verdict.json"),
        ],
        capture_output=True,
        text=True,
        timeout=12,
        check=False,
    )
    assert completed.returncode != 0
    assert "BLOCKED" in completed.stderr or "BLOCKED" in completed.stdout
    assert not (tmp_path / "nonexistent-verdict.json").exists()
