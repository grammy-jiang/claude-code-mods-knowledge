#!/usr/bin/env python3
"""Independently replay real native 304 invalid-update / repaired-update evidence.

Reads SHA-addressed private original Raspberry Pi CLI receipts. Produces only
bounded sanitized facts; native JSONL, prompt contents and account identifiers
must never enter Git. Synthetic CI shape-tests cannot replace this run.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from guard_cli304_native_plugin import (
    NATIVE_CLI304_SHA,
    BlockedUpdate,
    file_digest,
    inspect_tree,
    postflight,
    preflight,
    require,
)

BAD_TREE = "e1a070492a80de5fa1f42f315e77608a7cfa57dd49b7c1f3b9a7dd5f61bdb427"
GOOD_TREE = "ea337f98d65631931ec59e71d1df9b2c11dae74a7bcf6df942c0126dc3d56dc2"
ORIGINAL_GUARD_SHA = "d612de08145f36bfb296a1dcba4765cf614838ffbf00b907125e510365a7922c"
EXPECTED_BAD_SOURCE = "d7c46579d47546c36d9006b9db8cb40e9bdb0a16214f6b1e343841fe4ea48e3d"


def audit(root: Path, binary: Path) -> dict:
    bad = root / "cache/cache/mods-recovery-qa-local-20261022/qa-guard304-host/0.0.2"
    good = root / "cache/cache/mods-recovery-qa-local-20261022/qa-guard304-host/0.0.3"
    raw = root / "raw"
    require(file_digest(binary, maximum=350_000_000) == NATIVE_CLI304_SHA, "WRONG_NATIVE_CLI")
    staged_bad = root / "staged/qa-guard-0.0.2"
    staged_good = root / "staged/qa-guard-0.0.3"
    require(inspect_tree(staged_bad)["content_tree_sha256"] == BAD_TREE, "BAD_SOURCE_TREE_CHANGED")
    require(
        inspect_tree(staged_good)["content_tree_sha256"] == GOOD_TREE, "GOOD_SOURCE_TREE_CHANGED"
    )
    require(inspect_tree(good)["content_tree_sha256"] == GOOD_TREE, "GOOD_CACHE_TREE_CHANGED")
    # Claude adds .orphaned_at to obsolete installed caches. That volatile
    # host metadata is deliberately NOT included in the candidate hash.
    # Instead attest the precise byte correspondence of candidate source
    # files and the installed obsolete cache, allowing ONLY the known
    # .orphaned_at marker as a fourth file in this private host profile.
    staged_paths = {
        p.relative_to(staged_bad).as_posix() for p in staged_bad.rglob("*") if p.is_file()
    }
    bad_cache_paths = {p.relative_to(bad).as_posix() for p in bad.rglob("*") if p.is_file()}
    require(
        bad_cache_paths == staged_paths | {".orphaned_at"},
        "OBSOLETE_CACHE_UNEXPECTED_FILE_SET",
    )
    for rel in staged_paths:
        require(file_digest(bad / rel) == file_digest(staged_bad / rel), "CACHE_SOURCE_DRIFT")
    orphan = bad / ".orphaned_at"
    require(
        orphan.is_file() and not orphan.is_symlink() and orphan.stat().st_size <= 128,
        "OBSOLETE_CACHE_MARKER_MISSING",
    )
    require(
        file_digest(bad / "hooks/register.js") == EXPECTED_BAD_SOURCE,
        "FAULT_INJECTION_SOURCE_CHANGED",
    )
    require(
        file_digest(good / "hooks/register.js") == ORIGINAL_GUARD_SHA,
        "GOOD_GUARD_NOT_RECOVERED",
    )
    rejected = False
    try:
        preflight(
            staged_bad,
            binary,
            expected_tree_sha256=BAD_TREE,
            expected_plugin_name="qa-guard304-host",
            expected_plugin_version="0.0.2",
        )
    except BlockedUpdate as exc:
        require("NATIVE_STRICT_PLUGIN_VALIDATION_FAILED" in str(exc), "BAD_PREFLIGHT_UNEXPECTED")
        rejected = True
    require(rejected, "INVALID_PLUGIN_WAS_NOT_REJECTED")
    verified = preflight(
        staged_good,
        binary,
        expected_tree_sha256=GOOD_TREE,
        expected_plugin_name="qa-guard304-host",
        expected_plugin_version="0.0.3",
    )
    recorded_pre = json.loads((raw / "preflight-repaired.private.json").read_text())
    require(recorded_pre == verified, "PRIVATE_PREFLIGHT_REPLAY_CHANGED")
    proof = postflight(
        verified,
        current_installed=good,
        native_wire=raw / "recovery-wire.private.jsonl",
        native_debug=raw / "recovery-debug.private.log",
    )
    recorded_post = json.loads((raw / "postflight-repaired.private.json").read_text())
    require(recorded_post == proof, "PRIVATE_POSTFLIGHT_REPLAY_CHANGED")
    prior = json.loads((raw / "recovery-summary.private.json").read_text())
    require(prior["native_version"] == "2.1.304", "WRONG_RECORDED_VERSION")
    require(prior["source_restored"] is True, "QA_MARKETPLACE_SOURCE_NOT_RESTORED")
    require(
        prior["preflight_bad_exit"] == 1 and prior["preflight_good_exit"] == 0,
        "VALIDATOR_EXIT_CODES_WRONG",
    )
    require(
        [x["version_label"] for x in prior["updates"]]
        == [
            "faulted-0.0.2",
            "repaired-0.0.3",
        ]
        and all(x["exit_code"] == 0 and x["outcome"] == "ok" for x in prior["updates"]),
        "ACTUAL_TWO_OFFICIAL_UPDATES_NOT_VERIFIED",
    )
    require(
        [x["case"] for x in prior["phases"]]
        == [
            "initial-good-0.0.1",
            "reload-invalid-0.0.2",
            "after-invalid-0.0.2",
            "reload-good-0.0.3",
            "after-good-0.0.3",
        ],
        "NATIVE_LIFECYCLE_INCOMPLETE",
    )
    require(
        [x["guard_denial"] for x in prior["phases"]]
        == [
            True,
            False,
            False,
            False,
            True,
        ],
        "ACTUAL_GUARD_LOSS_RECOVERY_NOT_MATCHED",
    )
    require(
        prior["wire_sha256"] == proof["native_wire_sha256"]
        and prior["debug_sha256"] == proof["native_debug_sha256"],
        "RAW_NATIVE_FINGERPRINT_MISMATCH",
    )
    require(verified["protected_session_ready"] is False, "PREFLIGHT_MUST_NOT_GRANT_SESSION")
    require(
        proof["other_session_or_production_host_protected"] is False,
        "IMPROPER_PRODUCTION_ASSURANCE",
    )
    return {
        "schema_version": 1,
        "observed_local_date": "2026-10-22",
        "target_cli": "2.1.304",
        "native_host": "Raspberry Pi 5, Linux ARM64, authenticated Sonnet 5.5",
        "official_cli_sha256": NATIVE_CLI304_SHA,
        "preflight_gate_script_sha256": file_digest(
            Path(__file__).with_name("guard_cli304_native_plugin.py")
        ),
        "recovery_audit_script_sha256": file_digest(Path(__file__)),
        "qa_invalid_candidate_tree_sha256": BAD_TREE,
        "qa_valid_candidate_tree_sha256": GOOD_TREE,
        "obsolete_cache_had_host_generated_orphan_marker": True,
        "obsolete_cache_host_metadata_excluded_from_reviewed_package_sha": True,
        "qa_original_guard_sha256": ORIGINAL_GUARD_SHA,
        "qa_invalid_module_sha256": EXPECTED_BAD_SOURCE,
        "private_native_wire_sha256": proof["native_wire_sha256"],
        "private_native_debug_sha256": proof["native_debug_sha256"],
        "private_preflight_receipt_sha256": file_digest(raw / "preflight-repaired.private.json"),
        "private_postflight_receipt_sha256": file_digest(raw / "postflight-repaired.private.json"),
        "same_native_session": proof["same_native_session_observed"],
        "actual_result_turns": proof["actual_native_result_turns"],
        "bad_plugin_preflight_rejected": True,
        "valid_recovery_plugin_preflight_passed": True,
        "both_actual_official_plugin_updates_returned_success": True,
        "invalid_reload_dropped_active_safety_guard": True,
        "repaired_plugin_reloaded_and_guard_activated": True,
        "recovery_qa_sentinel_refused_before_model_inference": True,
        "public_release_eligible": False,
        "stable_release_authorized": False,
        "tui_recovery_validation": "NOT_VERIFIED_COMMAND_NOT_RELIABLY_SUBMITTED",
        "evidence_safety": {
            "private_raw_prompts_wires_and_terminal_not_published": True,
            "actual_user_files_or_external_tools_not_executed": True,
            "no_approved_cli304_claims_modified": True,
            "postflight_covers_this_one_qa_session_only": True,
            "unattested_future_session_not_authorized": True,
        },
        "limitations": (
            "Native records and SHA256 support auditable reproducibility but are "
            "not cryptographically signed host attestations. Isolated benign "
            "local Plugin only; no production, managed-policy or TUI reload guarantee."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--official-binary", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists() or args.out.is_symlink():
        raise SystemExit("REFUSED: immutable sanitized recovery report already exists")
    try:
        result = audit(args.private_root, args.official_binary)
    except (BlockedUpdate, OSError, TypeError, KeyError, ValueError):
        raise SystemExit(
            "BLOCKED: native recovery record cannot be independently verified"
        ) from None
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "invalid_preflight_rejected": True,
                "valid_recovery_verified_for_this_qa_session": True,
                "production_claim": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
