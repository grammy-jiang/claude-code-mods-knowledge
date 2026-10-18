"""Real original model code 2/5 type FAIL must not be upgraded to release PASS."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/reports/2026-10-19-p5-cli302-original-code-core-type-audit.json"
SOURCE = ROOT / "evals/fixtures/p5-native-model-code-302"
CORE_SHA = "8afa71883ecfa52901eb7a04cf31fef700d8ba565eaad244f4884cc620f8d56e"


def test_native_core_checks_preserve_original_failures_and_test_only_repair():
    r = json.loads(REPORT.read_text())
    assert r["target_claude_cli"] == "2.1.302"
    assert r["typescript_version"] == "Version 6.0.3"
    assert r["core_declarations_sha256"] == CORE_SHA
    assert r["core_declarations_length"] == 651_852
    assert r["source_native_binary_sha256"] == (
        "2bd4f4e5ed5cb09955b490098f745321cb5491e7ea8c752ba1e3bb010cdadb10"
    )
    assert r["original_model_snippets_sha256_verified"] == 5
    assert r["original_pass"] == 2 and r["original_fail"] == 3
    assert r["original_known_console_type_errors"] == 3
    assert r["test_only_ui_log_remediation_typecheck_pass"] == 5
    assert {(d["file"], d["code"]) for d in r["diagnostic_errors"]} == {
        ("codex-02.mjs", "TS2584"),
        ("sonnet-02.mjs", "TS2584"),
        ("sonnet-03.mjs", "TS2584"),
    }
    assert all(d["description_signal"] == "unknown_console_global" for d in r["diagnostic_errors"])
    cases = r["original_cases"]
    assert len(cases) == 5
    assert sum(c["original_core_typecheck_pass"] for c in cases) == 2
    assert sum(c["proposed_ui_log_replacement_applied"] for c in cases) == 3
    assert sum(c["fragment_has_synthetic_wrapper"] for c in cases) == 2
    for c in cases:
        assert (
            hashlib.sha256((SOURCE / c["origin"]).read_bytes()).hexdigest() == c["original_sha256"]
        )
        assert c["actual_model_generated_code_unchanged_in_git"] is True
        assert c["test_only_remediation_core_typecheck_pass"] is True


def test_type_core_does_not_claim_dynamic_complete_types_or_live_permissions():
    r = json.loads(REPORT.read_text())
    assert r["runtime_generated_builtin_tool_type_merge_verified"] is False
    assert r["real_interactive_mod_host_permission_semantics_verified"] is False
    assert r["whole_model_generated_code_semantics_approved"] is False
    assert r["stable_release_authorized"] is False
    assert r["proprietary_full_declaration_exported_to_public_git"] is False
    assert r["original_model_code_executed_during_typecheck"] is False
    assert r["model_or_account_network_requests"] == 0
    assert r["only_local_no_emit_typechecking_used"] is True


def test_no_raw_model_messages_or_upstream_declaration_published():
    text = REPORT.read_text()
    for marker in (
        "/Users/",
        "/home/",
        "Plugin_",
        "Authorization:",
        "Cookie:",
        "TASK_ID:",
        "chatgpt.com/c/",
        "raw_reply",
        "sandbox:/mnt/data",
        "declare module 'claude-code'",
    ):
        assert marker not in text
    assert re.search(r"gh[pousr]_[A-Za-z0-9]{20,}", text) is None
