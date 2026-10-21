"""Immutable public facts from actual CLI304 failed-reload recovery.

Original model transcripts and runtime files live in the private Pi record;
this offline check only validates hashes, QA fixtures, source-scoped outcomes,
and the continuing denial of any general release authorization.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

from mods_knowledge.claims import approved_claims, load_claims
from mods_knowledge.registry import load_registry

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/reports/2026-10-22-cli304-failed-reload-recovery-evidence.json"
GATE = ROOT / "scripts/guard_cli304_native_plugin.py"
AUDIT = ROOT / "scripts/audit_cli304_update_recovery_evidence.py"
BAD = ROOT / "evals/fixtures/cli304-recovery-20261022/invalid-0.0.2"
GOOD = ROOT / "evals/fixtures/cli304-recovery-20261022/repaired-0.0.3"

_spec = importlib.util.spec_from_file_location("cli304_guard_source", GATE)
assert _spec and _spec.loader
_gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_gate)


def sha(path: Path) -> str:
    assert path.is_file() and not path.is_symlink()
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evidence() -> dict:
    return json.loads(REPORT.read_text(encoding="utf-8"))


def test_real_recovery_evidence_matches_reviewed_clean_source_trees():
    r = evidence()
    assert r["schema_version"] == 1 and r["target_cli"] == "2.1.304"
    assert r["official_cli_sha256"] == _gate.NATIVE_CLI304_SHA
    assert r["preflight_gate_script_sha256"] == sha(GATE)
    assert r["recovery_audit_script_sha256"] == sha(AUDIT)
    assert _gate.inspect_tree(BAD)["content_tree_sha256"] == r["qa_invalid_candidate_tree_sha256"]
    assert _gate.inspect_tree(GOOD)["content_tree_sha256"] == r["qa_valid_candidate_tree_sha256"]
    assert _gate.inspect_tree(BAD)["plugin_version"] == "0.0.2"
    assert _gate.inspect_tree(GOOD)["plugin_version"] == "0.0.3"
    assert sha(BAD / "hooks/register.js") == r["qa_invalid_module_sha256"]
    assert sha(GOOD / "hooks/register.js") == r["qa_original_guard_sha256"]
    assert "export function corrupted_qa_only( {" in (BAD / "hooks/register.js").read_text()
    assert ".orphaned_at" not in {p.name for p in BAD.iterdir()}
    assert r["obsolete_cache_had_host_generated_orphan_marker"] is True
    assert r["obsolete_cache_host_metadata_excluded_from_reviewed_package_sha"] is True


def test_failed_reload_was_observed_and_good_reload_recovered_same_qa_session():
    r = evidence()
    assert r["same_native_session"] is True
    assert r["actual_result_turns"] == [0, 0, 1, 0, 0]
    for key in (
        "bad_plugin_preflight_rejected",
        "valid_recovery_plugin_preflight_passed",
        "both_actual_official_plugin_updates_returned_success",
        "invalid_reload_dropped_active_safety_guard",
        "repaired_plugin_reloaded_and_guard_activated",
        "recovery_qa_sentinel_refused_before_model_inference",
    ):
        assert r[key] is True
    for key in (
        "private_native_wire_sha256",
        "private_native_debug_sha256",
        "private_preflight_receipt_sha256",
        "private_postflight_receipt_sha256",
    ):
        assert len(r[key]) == 64 and all(c in "0123456789abcdef" for c in r[key])


def test_qa_recovery_does_not_pretend_tui_or_production_approval():
    r = evidence()
    assert r["public_release_eligible"] is False
    assert r["stable_release_authorized"] is False
    assert r["tui_recovery_validation"] == "NOT_VERIFIED_COMMAND_NOT_RELIABLY_SUBMITTED"
    assert "not cryptographically signed" in r["limitations"]
    assert all(r["evidence_safety"].values())
    registry = load_registry(ROOT / "sources/registry.json")
    claims = load_claims(ROOT / "claims", registry, ROOT / "sources/snapshots", ROOT / "decisions")
    assert approved_claims(claims, "2.1.304", "cli") == []
    for number in range(70, 75):
        assert claims[f"K-{number:04}"]["verification"]["runtime"] != "integration-pass"


def test_public_report_does_not_copy_original_private_model_or_host_details():
    report = REPORT.read_text(encoding="utf-8")
    assert all(
        token not in report
        for token in (
            "/tmp/mods-cli304",  # noqa: S108 - negative privacy sentinel only
            "/home/",
            "/Users/",
            "Cookie:",
            "Authorization:",
            "access_token",
            "conversation_id",
            "session_id",
            "QA304_BENIGN_BLOCK_THIS",
            "https://chatgpt.com/c/",
        )
    )
    assert len(report) < 9_000
