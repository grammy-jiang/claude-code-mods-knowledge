#!/usr/bin/env python3
"""Audit actual installed-plugin reload, PTY permission UI and read-only host event traces.

Raw native model wires, logs, account data and prompts are private to the
originating Raspberry Pi. Only strictly bounded, source-bound facts and hashes
may be published. This script is NOT a substitute for an independent human
review of the source and native traces.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

OFFICIAL_NATIVE_SHA = "c487117526509ab6d2ee6013e14f181faf68d6d6afe6bb0d4b2b4a9feca5ecb3"
KNOWN_GOOD_HOOK_SHA = "d612de08145f36bfb296a1dcba4765cf614838ffbf00b907125e510365a7922c"
KNOWN_BAD_UPDATE_SHA = "4939490afc990afd9265365775668a3d5d5e2af5899dcc68e55bb410c9b31b93"
MATRIX_HOOK_SHA = "12b0b9f2f53c6693b99fc5f4ae68a88c356eda4f15f0018831ef10b780075e45"
MARKETPLACE_SHA = "36d990dd2c0cf20a3f2f354da1bdd2b08e824bc859cc4b587edf04ac6e3c16bf"
PLUGIN_MANIFEST_SHA = "cacbab64f6d1000ec7d4e9d52a411b07857a807e62b1af22218078db9215e948"
MATRIX_MANIFEST_SHA = "d2386fa1865b4f3987a5016463f86fe77b33e5390a5aa43fcac037195a5b3965"
BAD_SUFFIX = b"\nexport function intentionally_invalid_installed_update( {\n"
CASES = {
    "Read": ("true", "allow"),
    "Glob": ("true", "allow"),
    "Grep": ("true", "allow"),
    "Write": ("undefined", "ask"),
}


class IncompleteNativeHostEvidence(ValueError):
    """Reject unverified source, runtime, privacy or actual model observations."""


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise IncompleteNativeHostEvidence(reason)


def digest(path: Path, *, max_bytes: int = 10_000_000) -> str:
    require(path.is_file() and not path.is_symlink(), "MISSING_REAL_REGULAR_FILE")
    require(path.stat().st_size <= max_bytes, "OVERSIZE_PRIVATE_EVIDENCE_FILE")
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def native_run(wire: Path, debug: Path, stderr: Path) -> tuple[dict, list[dict], str, str]:
    hashes = {
        "wire_sha256": digest(wire),
        "debug_sha256": digest(debug),
        "stderr_sha256": digest(stderr),
    }
    require(stderr.stat().st_size == 0, "NONEMPTY_PRIVATE_STDERR")
    events = []
    for line in wire.read_text().splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except ValueError as exc:
            raise IncompleteNativeHostEvidence("INVALID_NATIVE_EVENT_JSON") from exc
        require(isinstance(event, dict), "INVALID_NATIVE_EVENT")
        events.append(event)
    results = [event for event in events if event.get("type") == "result"]
    require(bool(results), "NATIVE_RESULTS_MISSING")
    require(
        all(x.get("subtype") == "success" and x.get("is_error") is False for x in results),
        "INCOMPLETE_NATIVE_RESULT",
    )
    models = {
        m.get("message", {}).get("model")
        for m in events
        if m.get("type") == "assistant" and isinstance(m.get("message"), dict)
    }
    require("claude-sonnet-5-5" in models, "GENUINE_SONNET_MODEL_NOT_ATTESTED")
    tool_names = [
        chunk.get("name")
        for event in events
        if event.get("type") == "assistant"
        for chunk in (event.get("message") or {}).get("content", [])
        if isinstance(chunk, dict) and chunk.get("type") == "tool_use"
    ]
    data = {
        **hashes,
        "result_turns": [x.get("num_turns") for x in results],
        "native_models": sorted(x for x in models if isinstance(x, str)),
        "actual_tool_calls": tool_names,
        "native_event_count": len(events),
    }
    return data, results, debug.read_text(errors="replace"), wire.read_text(errors="replace")


def installed_plugin(installed: Path) -> dict:
    manifest_root = installed / "market"
    cached_good = manifest_root / "plugins/qa-guard304-host/hooks/register.js"
    cached_bad = (
        installed
        / "cache/cache/mods-p1a-private-local-20261021/qa-guard304-host/0.0.2/hooks/register.js"
    )
    require(digest(cached_good) == KNOWN_GOOD_HOOK_SHA, "OLD_GOOD_SOURCE_CHANGED")
    require(digest(cached_bad) == KNOWN_BAD_UPDATE_SHA, "BAD_RELEASE_SOURCE_CHANGED")
    require(
        hashlib.sha256(cached_good.read_bytes() + BAD_SUFFIX).hexdigest() == KNOWN_BAD_UPDATE_SHA,
        "BAD_RELEASE_DIFFERENCE_NOT_VERIFIED",
    )
    require(
        digest(manifest_root / ".claude-plugin/marketplace.json") == MARKETPLACE_SHA,
        "QA_MARKETPLACE_CHANGED",
    )
    manifest = manifest_root / "plugins/qa-guard304-host/.claude-plugin/plugin.json"
    require(digest(manifest) == PLUGIN_MANIFEST_SHA, "QA_PLUGIN_MANIFEST_CHANGED")
    require(json.loads(manifest.read_text())["version"] == "0.0.1", "QA_SOURCE_NOT_RESTORED")
    cache_registry = json.loads((installed / "cache/installed_plugins.json").read_text())
    require(
        "qa-guard304-host@mods-p1a-private-local-20261021" in str(cache_registry),
        "Genuine_installed_plugin_record_missing",
    )
    raw = installed / "raw"
    a, results, debug, wire = native_run(
        raw / "installed-304-versioned-failed-reload-wire.private.jsonl",
        raw / "installed-304-versioned-failed-reload-debug.private.log",
        raw / "installed-304-versioned-failed-reload-stderr.private.log",
    )
    require(len(results) == 3, "INSTALLED_VERSIONED_SEQUENCE_INCOMPLETE")
    require(
        results[0].get("num_turns") == 0
        and "QA304_GUARD_DENIED_TEST_ONLY" in str(results[0].get("result")),
        "OLD_INSTALLED_SAFETY_GUARD_NOT_VERIFIED",
    )
    require(
        results[1].get("num_turns") == 0
        and "Reloaded: 1 plugin" in str(results[1].get("result"))
        and "0 hooks" in str(results[1].get("result")),
        "INSTALL_UPDATE_RELOAD_MESSAGE_MISSING",
    )
    require(
        results[2].get("num_turns") == 1
        and "QA304_SAFE_AFTER_RELOAD_RESULT" in str(results[2].get("result")),
        "REAL_POST_RELOAD_GUARD_LOSS_NOT_VERIFIED",
    )
    require(
        debug.count("QA304_GUARD_ENTRY") == 1
        and "hooks module qa-guard304-host@" in debug
        and "does not parse: Unexpected token" in debug
        and "the version loaded before is unloaded" in debug,
        "CORRUPTED_INSTALLED_HOOK_NOT_REJECTED_AND_UNLOADED",
    )
    require("QA304_GUARD_DENIED_TEST_ONLY" in wire, "OLD_GUARD_MISSING_FROM_WIRE")
    require("QA304_SAFE_AFTER_RELOAD_RESULT" in wire, "POST_RELOAD_MODEL_MISSING_FROM_WIRE")
    return {
        **a,
        "original_installed_hook_sha256": KNOWN_GOOD_HOOK_SHA,
        "broken_updated_hook_sha256": KNOWN_BAD_UPDATE_SHA,
        "marketplace_sha256": MARKETPLACE_SHA,
        "original_plugin_manifest_sha256": PLUGIN_MANIFEST_SHA,
        "old_guard_denied_before_update": True,
        "failed_versioned_reload_reported_zero_hooks": True,
        "old_hook_unloaded_after_parse_error": True,
        "identical_benign_prompt_entered_real_model_after_failed_reload": True,
        "previous_safety_hook_preserved": False,
        "observed_profile": "local-marketplace-installed-0.0.1-to-invalid-0.0.2",
    }


def tool_matrix(matrix: Path) -> dict:
    require(digest(matrix / "qa-matrix/hooks/register.js") == MATRIX_HOOK_SHA, "MATRIX_HOOK_DRIFT")
    require(
        digest(matrix / "qa-matrix/.claude-plugin/plugin.json") == MATRIX_MANIFEST_SHA,
        "MATRIX_MANIFEST_DRIFT",
    )
    require(not (matrix / "work/qa-matrix-new-write.txt").exists(), "REAL_WRITE_WAS_NOT_DENIED")
    cases = {}
    for name, (readonly, base_decision) in CASES.items():
        low = name.lower()
        raw = matrix / "raw"
        a, results, debug, wire = native_run(
            raw / f"{low}-wire.private.jsonl",
            raw / f"{low}-debug.private.log",
            raw / f"{low}-stderr.private.log",
        )
        require(a["actual_tool_calls"] == [name], "WRONG_ACTUAL_TOOL")
        marker = f"QA304_META_TOOL_{name}_RO_{readonly}_BASE_{base_decision}"
        require(marker in debug, "REAL_HOST_TOOL_METADATA_MISSING")
        require(f"QA304_META_DENY_{name}_RO_{readonly}" in wire, "DENY_NOT_IN_NATIVE_TOOL_RESULT")
        require(len(results) == 1, "MULTIPLE_UNEXPECTED_RESULTS")
        cases[name] = {
            **a,
            "observed_isReadOnly": readonly,
            "original_host_verdict": base_decision,
            "test_hook_denied_actual_call": True,
        }
    return {
        "reviewed_fixture_hook_sha256": MATRIX_HOOK_SHA,
        "reviewed_fixture_manifest_sha256": MATRIX_MANIFEST_SHA,
        "cases": cases,
        "write_target_absent": True,
        "coverage": "four tool kinds, not a complete built-in tool taxonomy",
    }


def interactive_tty(tty: Path) -> dict:
    raw = tty / "raw"
    debug_file = raw / "p1b-tui-render-debug.private.log"
    term_file = raw / "p1b-tui-render-terminal.private.log"
    debug = debug_file.read_text(errors="replace")
    screen = term_file.read_bytes().decode(errors="replace")
    require(digest(debug_file) != "" and digest(term_file) != "", "MISSING_INTERACTIVE_PTY")
    require("hooks module qa-person304-host@inline loaded" in debug, "TUI_QA_MOD_MISSING")
    require("QA304_PERSON_WRITE_BASE_ask" in debug, "REAL_TUI_TOOLCHECK_ASK_MISSING")
    # Terminal escape sequences are stripped only inside this private replay,
    # never exported to the public SSOT.
    normalized = re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", screen)
    require("Doyouwanttocreatep1b-denied-test.txt?" in normalized, "TUI_APPROVAL_NOT_RENDERED")
    require("3.No" in normalized and "1.Yes" in normalized, "TUI_PERSON_CHOICE_NOT_PRESENT")
    require(not (tty / "work/p1b-denied-test.txt").exists(), "TUI_WRITE_TARGET_PRESENT")
    return {
        "pty_sha256": digest(term_file),
        "private_debug_sha256": digest(debug_file),
        "real_interactive_toolcheck_ask": True,
        "actual_human_choice_ui_rendered": True,
        "write_target_absent": True,
        "positive_human_approval_and_write_tested": False,
        "managed_permissions_precedence_tested": False,
        "profile": "pseudo-terminal simulated operator, private inline QA plugin",
    }


def audit(installed: Path, matrix: Path, tty: Path, binary: Path) -> dict:
    require(
        digest(binary, max_bytes=350_000_000) == OFFICIAL_NATIVE_SHA,
        "OFFICIAL_304_BINARY_MISMATCH",
    )
    return {
        "schema_version": 1,
        "target_cli": "2.1.304",
        "recorded_on": "2026-10-21",
        "native_host": "Raspberry Pi 5, Linux ARM64",
        "official_native_sha256": OFFICIAL_NATIVE_SHA,
        "private_auditor_sha256": digest(Path(__file__)),
        "installed_reload": installed_plugin(installed),
        "readonly_matrix": tool_matrix(matrix),
        "interactive_permission": interactive_tty(tty),
        "scope_limits": {
            "local_marketplace_plugin_only": True,
            "installed_project_user_managed_scopes_not_verified": True,
            "interactive_successful_human_write_not_verified": True,
            "interactive_managed_guard_precedence_not_verified": True,
            "all_built_in_tool_metadata_not_verified": True,
            "real_chat_mode_plugin_account_not_touched": True,
            "raw_model_messages_and_terminal_not_committed": True,
        },
        "release": {
            "new_cli304_claims_approved": 0,
            "K0073_release_ready": False,
            "K0070_human_approval_full_pass": False,
            "K0071_complete_readonly_matrix": False,
            "stable_release_authorized": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--installed", type=Path, required=True)
    parser.add_argument("--matrix", type=Path, required=True)
    parser.add_argument("--tty", type=Path, required=True)
    parser.add_argument("--official-binary", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    opts = parser.parse_args()
    if opts.out.exists() or opts.out.is_symlink():
        raise SystemExit("REFUSED: immutable sanitized QA report already exists")
    try:
        result = audit(opts.installed, opts.matrix, opts.tty, opts.official_binary)
    except (IncompleteNativeHostEvidence, OSError, ValueError, TypeError, KeyError):
        raise SystemExit("BLOCKED: 304 native installed/metadata/TUI evidence incomplete") from None
    opts.out.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(
        json.dumps(
            {
                "actual_installed_bad_reload_guard_preserved": False,
                "real_tool_metadata_cases": len(result["readonly_matrix"]["cases"]),
                "real_tui_ask_rendered": True,
                "full_host_integration_approved": False,
                "stable_authorized": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
