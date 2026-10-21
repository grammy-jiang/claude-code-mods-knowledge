#!/usr/bin/env python3
"""Reassess private actual Claude Code 2.1.304 interactive TUI recovery traces.

This is an evidence auditor, not a runner or a production Plugin updater.
The terminal/debug transcript and all identifying context remain on the Pi.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

from guard_cli304_native_plugin import (
    NATIVE_CLI304_SHA,
    BlockedUpdate,
    file_digest,
    inspect_tree,
    require,
)

INVALID_TREE = "071ec7394ba71b091b29176a8a541029418746960299efb056ae6d7ffbff2a70"
VALID_TREE = "eb4e6d8bc985131418c75c01170faf6c028ecb617fdf4cd59790904bb70d4455"
INVALID_HOOK_SHA = "66239abc8a598857a828950a062f31e12c027432d20eadeb6290b2022374088b"
GOOD_HOOK_SHA = "d612de08145f36bfb296a1dcba4765cf614838ffbf00b907125e510365a7922c"
TUI_PLUGIN_ID = "qa-guard304-host@mods-tui-qa-local-20261022"
TUI_TERMINAL_SHA = "30cd87e14f6290ad4eb21cae28d94c1297825dbc2112dd9c9b68a9701006e415"
TUI_DEBUG_SHA = "187eed8dbc8eb3ebf77106ff5808144fce31e517562c36d9dfb0d03d13c2deb9"
SUMMARY_SHA = "e1584fc6e0bd4c4bae6b1e9632f1c9d568ba3f95d06e4359e9cb22bd45e4b8cf"
MODEL_OUTPUT = "QA304_SAFE_AFTER_RELOAD_RESULT"
HOOK_MARKER = "QA304_GUARD_ENTRY"


def _native_validate(binary: Path, source: Path) -> int:
    try:
        result = subprocess.run(  # noqa: S603 - pinned official CLI; no shell
            [str(binary), "plugin", "validate", "--strict", str(source)],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise BlockedUpdate("OFFICIAL_PLUGIN_VALIDATOR_NOT_AVAILABLE") from exc
    text = result.stdout + "\n" + result.stderr
    require(
        ("Validation passed" in text) if result.returncode == 0 else ("Validation failed" in text),
        "VALIDATION_OUTPUT_MISMATCH",
    )
    return result.returncode


def audit(root: Path, binary: Path) -> dict:
    require(file_digest(binary, maximum=350_000_000) == NATIVE_CLI304_SHA, "WRONG_NATIVE_CLI")
    bad = root / "staged/qa-guard-0.0.6"
    good = root / "staged/qa-guard-0.0.7"
    observed_bad = inspect_tree(bad)
    observed_good = inspect_tree(good)
    require(observed_bad["content_tree_sha256"] == INVALID_TREE, "INVALID_CANDIDATE_NOT_PINNED")
    require(observed_good["content_tree_sha256"] == VALID_TREE, "REPAIRED_CANDIDATE_NOT_PINNED")
    require(
        observed_bad["plugin_name"] == observed_good["plugin_name"] == "qa-guard304-host"
        and observed_bad["plugin_version"] == "0.0.6"
        and observed_good["plugin_version"] == "0.0.7",
        "PLUGIN_SOURCE_VERSION_MISMATCH",
    )
    require(file_digest(bad / "hooks/register.js") == INVALID_HOOK_SHA, "BROKEN_HOOK_CHANGED")
    require(file_digest(good / "hooks/register.js") == GOOD_HOOK_SHA, "GOOD_HOOK_CHANGED")
    require(_native_validate(binary, bad) != 0, "SYNTAX_BROKEN_PACKAGE_NOT_REJECTED")
    require(_native_validate(binary, good) == 0, "REPAIRED_PACKAGE_NOT_NATIVE_VALID")
    cache = root / "cache/cache/mods-tui-qa-local-20261022/qa-guard304-host"
    for version, staged in (("0.0.6", bad), ("0.0.7", good)):
        installed = cache / version
        all_paths = {
            p.relative_to(installed).as_posix() for p in installed.rglob("*") if p.is_file()
        }
        original_paths = {
            p.relative_to(staged).as_posix() for p in staged.rglob("*") if p.is_file()
        }
        expected_paths = original_paths | ({".orphaned_at"} if version == "0.0.6" else set())
        require(all_paths == expected_paths, "CACHED_PLUGIN_FILE_SET_DRIFT")
        for name in original_paths:
            require(
                file_digest(installed / name) == file_digest(staged / name),
                "CACHED_PLUGIN_SOURCE_BYTES_DRIFT",
            )
        if version == "0.0.6":
            marker = installed / ".orphaned_at"
            require(marker.is_file() and not marker.is_symlink(), "OBSOLETE_CACHE_MARKER_MISSING")
            require(marker.stat().st_size <= 128, "OBSOLETE_CACHE_MARKER_OVERSIZE")
    raw = root / "raw"
    term_path = raw / "tui-reload-reliable.private.pty"
    debug_path = raw / "tui-reload-reliable.private.debug"
    summary_path = raw / "tui-reload-reliable-summary.private.json"
    require(file_digest(term_path) == TUI_TERMINAL_SHA, "ORIGINAL_TUI_TERMINAL_DIGEST_DRIFT")
    require(file_digest(debug_path) == TUI_DEBUG_SHA, "ORIGINAL_TUI_DEBUG_DIGEST_DRIFT")
    require(file_digest(summary_path) == SUMMARY_SHA, "ORIGINAL_QA_SUMMARY_DIGEST_DRIFT")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    milestones = summary.get("observed", {})
    require(summary.get("target_cli") == "2.1.304", "WRONG_TARGET_CLI_IN_QA_SUMMARY")
    require(summary.get("source_restored") is True, "PRIVATE_SOURCE_NOT_RESTORED")
    require(summary.get("guard_log_count") == 1, "UNEXPECTED_ACTUAL_GUARD_COUNT")
    require(summary.get("tty_sha256") == TUI_TERMINAL_SHA, "TUI_SOURCE_SUMMARY_CONFLICT")
    require(summary.get("debug_sha256") == TUI_DEBUG_SHA, "DEBUG_SOURCE_SUMMARY_CONFLICT")
    require(
        milestones.get("old_hook_loaded") is True
        and milestones.get("invalid_reload", {}).get("native_reload_observed") is True
        and milestones.get("invalid_reload", {}).get("parse_error") is True
        and milestones.get("invalid_reload", {}).get("last_good_unloaded") is True
        and milestones.get("after_bad_request", {}).get("old_guard_ran") is False
        and milestones.get("after_bad_request", {}).get("native_turn_complete_seen") is True
        and milestones.get("repaired_reload", {}).get("native_reload_observed") is True
        and milestones.get("repaired_reload", {}).get("parse_error") is False
        and milestones.get("recovered_guard_fired") is True,
        "TUI_MILESTONE_SEQUENCE_NOT_COMPLETE",
    )
    expected_updates = (
        ("0.0.6", True, 1, INVALID_HOOK_SHA),
        ("0.0.7", False, 0, GOOD_HOOK_SHA),
    )
    updates = summary.get("updates", [])
    require(isinstance(updates, list) and len(updates) == 2, "REAL_UPDATE_SEQUENCE_MISSING")
    for row, (version, bad_version, validator_rc, source_sha) in zip(
        updates, expected_updates, strict=True
    ):
        require(
            row.get("version") == version
            and row.get("bad") is bad_version
            and row.get("native_validator_exit") == validator_rc
            and row.get("official_update_exit") == 0
            and row.get("update_outcome") == "ok"
            and row.get("source_sha256") == source_sha,
            "OFFICIAL_UPDATE_OR_VALIDATOR_RESULT_INCONSISTENT",
        )
    debug = debug_path.read_text(encoding="utf-8", errors="replace")
    marker = f"hooks module {TUI_PLUGIN_ID} loaded"
    initial_load = debug.find(marker)
    bad_refresh = debug.find("refreshActivePlugins: clearing all plugin caches", initial_load)
    parse_failure = debug.find("does not parse: Unexpected token", bad_refresh)
    unloaded = debug.find("the version loaded before is unloaded", parse_failure)
    model_started = debug.find("turn.start settled", unloaded)
    model_completed = debug.find("turn.complete settled", model_started)
    next_refresh = debug.find("refreshActivePlugins: clearing all plugin caches", model_completed)
    recovered_load = debug.find(marker, next_refresh)
    registered = debug.find("plugin.register: qa-guard304-host", recovered_load)
    final_marker = debug.find(HOOK_MARKER, registered)
    short_circuit = debug.find("answered prompt.submit without next()", final_marker)
    values = (
        initial_load,
        bad_refresh,
        parse_failure,
        unloaded,
        model_started,
        model_completed,
        next_refresh,
        recovered_load,
        registered,
        final_marker,
        short_circuit,
    )
    require(all(i >= 0 for i in values), "NATIVE_TUI_EVENT_NOT_FOUND")
    require(list(values) == sorted(values), "NATIVE_TUI_EVENTS_OUT_OF_ORDER")
    require(debug.count(HOOK_MARKER) == 1, "GUARD_EXECUTED_DURING_INVALID_VERSION")
    require("0 hooks" in debug[parse_failure:recovered_load], "FAILING_RELOAD_NOT_OBSERVED")
    terminal = term_path.read_bytes().decode("utf-8", errors="replace")
    # ANSI cursor/color controls separate rendered assistant markup from
    # visible text. Remove only CSI controls for the display sentinel check,
    # so an echoed user prompt without the assistant bullet cannot qualify.
    visible = re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", terminal)
    require(
        re.search(r"●\s*" + re.escape(MODEL_OUTPUT), visible) is not None,
        "GENUINE_TUI_MODEL_OUTPUT_NOT_SHOWN",
    )
    require(terminal.count("Reloaded:") >= 2, "RELOAD_COMMANDS_NOT_VISIBLY_SUBMITTED")
    return {
        "schema_version": 1,
        "target_cli": "2.1.304",
        "tested_host": "Raspberry Pi 5, authenticated native interactive pseudo-terminal",
        "observed_local_date": "2026-10-22",
        "official_native_binary_sha256": NATIVE_CLI304_SHA,
        "independent_auditor_sha256": file_digest(Path(__file__)),
        "invalid_clean_candidate_tree_sha256": INVALID_TREE,
        "valid_clean_candidate_tree_sha256": VALID_TREE,
        "invalid_hook_sha256": INVALID_HOOK_SHA,
        "good_hook_sha256": GOOD_HOOK_SHA,
        "private_tui_terminal_sha256": TUI_TERMINAL_SHA,
        "private_tui_debug_sha256": TUI_DEBUG_SHA,
        "private_qa_summary_sha256": SUMMARY_SHA,
        "actual_tui_single_host_process_tested": True,
        "initial_qa_hook_module_loaded": True,
        "bad_version_native_strict_validator_rejected": True,
        "bad_version_official_update_succeeded": True,
        "failed_tui_reload_dropped_previous_hook": True,
        "real_model_turn_completed_while_hook_missing": True,
        "real_assistant_output_observed_not_just_prompt_echo": True,
        "repaired_version_native_strict_validator_passed": True,
        "repaired_version_official_update_succeeded": True,
        "valid_tui_reload_loaded_and_registered_new_hook": True,
        "subsequent_benign_prompt_stopped_before_model": True,
        "last_good_security_hook_preserved_during_failed_reload": False,
        "clean_package_checksum_excludes_host_generated_cache_metadata": True,
        "raw_model_and_terminal_not_published": True,
        "positive_human_permission_approval_tested": False,
        "managed_permission_precedence_tested": False,
        "other_plugin_scopes_or_hosts_validated": False,
        "unrelated_production_sessions_authorized": False,
        "approved_new_cli304_claims": 0,
        "stable_release_authorized": False,
        "limitations": (
            "Private unsigned host/debug/terminal receipts and one isolated TUI profile only; "
            "valid same-process Hook recovery is not universal transactional protection."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--official-binary", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists() or args.out.is_symlink():
        raise SystemExit("REFUSED: immutable sanitized TUI QA report already exists")
    try:
        data = audit(args.private_root, args.official_binary)
    except (BlockedUpdate, OSError, TypeError, KeyError, ValueError):
        raise SystemExit("BLOCKED: private interactive TUI recovery evidence incomplete") from None
    with args.out.open("x", encoding="utf-8") as out:
        out.write(json.dumps(data, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {"actual_tui_reload_verified": True, "production_approved": False},
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
