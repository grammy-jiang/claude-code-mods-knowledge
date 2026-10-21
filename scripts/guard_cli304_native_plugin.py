#!/usr/bin/env python3
"""Offline CLI304 QA candidate preflight and SAME-HOST recovery attestation.

No plugin install/update is performed here. A PRECHECK success cannot promise
that a running Claude Code session is protected; POSTCHECK demands original
single-session native wire plus live debug observations after actual reload.
Both checks fail closed and write no raw model/session content to Git.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

NATIVE_CLI304_SHA = "c487117526509ab6d2ee6013e14f181faf68d6d6afe6bb0d4b2b4a9feca5ecb3"
QA_GUARD_MESSAGE = "QA304_GUARD_DENIED_TEST_ONLY"
QA_MODEL_RESULT = "QA304_SAFE_AFTER_RELOAD_RESULT"
QA_HOOK_MARKER = "QA304_GUARD_ENTRY"
QA_PLUGIN_NAME = "qa-guard304-host"
QA_PLUGIN_ID = "qa-guard304-host@mods-recovery-qa-local-20261022"
MAX_PLUGIN_FILES = 100
MAX_PLUGIN_BYTES = 8_000_000
MAX_RECEIPT_BYTES = 8_000_000


class BlockedUpdate(ValueError):
    """Expected fail-closed rejection, not an approval claim."""


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise BlockedUpdate(reason)


def file_digest(file: Path, maximum: int = MAX_RECEIPT_BYTES) -> str:
    require(file.is_file() and not file.is_symlink(), "MISSING_OR_SYMLINK_FILE")
    require(file.stat().st_size <= maximum, "OVERSIZE_FILE")
    with file.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def inspect_tree(root: Path) -> dict:
    """Length-delimited stable content digest; reject symlinks and special files."""
    require(root.is_dir() and not root.is_symlink(), "INVALID_PLUGIN_ROOT")
    files: list[Path] = []
    sizes = 0
    for path in sorted(root.rglob("*")):
        require(
            path.relative_to(root).as_posix() != ".orphaned_at",
            "RUNTIME_CACHE_METADATA_IN_CANDIDATE",
        )
        require(not path.is_symlink(), "SYMLINK_IN_PLUGIN")
        require(path.is_file() or path.is_dir(), "NONREGULAR_PLUGIN_FILE")
        if path.is_file():
            files.append(path)
            sizes += path.stat().st_size
            require(len(files) <= MAX_PLUGIN_FILES, "TOO_MANY_PLUGIN_FILES")
            require(sizes <= MAX_PLUGIN_BYTES, "PLUGIN_TOO_LARGE")
    require(files, "EMPTY_PLUGIN")
    digest = hashlib.sha256()
    for file in files:
        name = file.relative_to(root).as_posix().encode("utf-8")
        data = file.read_bytes()
        digest.update(len(name).to_bytes(4, "big"))
        digest.update(name)
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    manifest = root / ".claude-plugin/plugin.json"
    require(manifest in files, "PLUGIN_MANIFEST_REQUIRED")
    try:
        parsed = json.loads(manifest.read_text(encoding="utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise BlockedUpdate("INVALID_PLUGIN_MANIFEST") from exc
    require(isinstance(parsed, dict), "INVALID_PLUGIN_MANIFEST")
    return {
        "content_tree_sha256": digest.hexdigest(),
        "file_count": len(files),
        "total_bytes": sizes,
        "plugin_name": parsed.get("name"),
        "plugin_version": parsed.get("version"),
        "hook_source_files": [
            file.relative_to(root).as_posix()
            for file in files
            if file.suffix in {".js", ".ts", ".tsx"} and "hooks" in file.relative_to(root).parts
        ],
    }


def preflight(
    root: Path,
    binary: Path,
    *,
    expected_tree_sha256: str,
    expected_plugin_name: str,
    expected_plugin_version: str,
    expected_native_sha256: str = NATIVE_CLI304_SHA,
) -> dict:
    """Strict syntax + registration checks against a private frozen package copy."""
    require(
        re.fullmatch(r"[0-9a-f]{64}", expected_tree_sha256) is not None,
        "EXPECTED_REVIEWED_PACKAGE_SHA_REQUIRED",
    )
    require(
        file_digest(binary, maximum=350_000_000) == expected_native_sha256,
        "OFFICIAL_NATIVE_BINARY_MISMATCH",
    )
    observed = inspect_tree(root)
    require(
        observed["content_tree_sha256"] == expected_tree_sha256,
        "UNREVIEWED_PACKAGE_BYTES",
    )
    require(
        observed["plugin_name"] == expected_plugin_name
        and observed["plugin_version"] == expected_plugin_version,
        "WRONG_PLUGIN_IDENTITY_OR_VERSION",
    )
    require(bool(observed["hook_source_files"]), "REVIEWED_QA_HOOK_SOURCE_MISSING")
    with tempfile.TemporaryDirectory(prefix="mods-cli304-review-frozen-") as temp:
        frozen = Path(temp) / "reviewed-plugin"
        shutil.copytree(root, frozen, symlinks=False)
        require(
            inspect_tree(frozen)["content_tree_sha256"] == expected_tree_sha256,
            "FROZEN_BYTES_CHANGED_ON_COPY",
        )
        try:
            result = subprocess.run(  # noqa: S603 - SHA-pinned official CLI, no shell
                [str(binary), "plugin", "validate", "--strict", str(frozen)],
                capture_output=True,
                text=True,
                timeout=25,
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise BlockedUpdate("OFFICIAL_STRICT_VALIDATOR_UNAVAILABLE") from exc
        native_text = result.stdout + "\n" + result.stderr
        require(
            result.returncode == 0
            and "Validation passed" in native_text
            and "Validation failed" not in native_text
            and "gating hook without .catch" not in native_text
            and re.search(r"\b(?:warning|error)\b", native_text, flags=re.I) is None,
            "NATIVE_STRICT_PLUGIN_VALIDATION_FAILED",
        )
        require(
            inspect_tree(frozen)["content_tree_sha256"] == expected_tree_sha256,
            "FROZEN_PACKAGE_CHANGED_DURING_VALIDATION",
        )
    require(
        inspect_tree(root)["content_tree_sha256"] == expected_tree_sha256,
        "ORIGINAL_PACKAGE_CHANGED_DURING_VALIDATION",
    )
    return {
        "schema_version": 1,
        "target_cli": "2.1.304",
        "official_native_sha256": expected_native_sha256,
        **observed,
        "native_strict_validator_pass": True,
        "native_validator_only_reviewed_frozen_package": True,
        "eligible_for_controlled_qa_update": True,
        "active_host_guard_attested": False,
        "protected_session_ready": False,
        "stable_release_authorized": False,
    }


def postflight(
    preflight_report: dict,
    *,
    current_installed: Path,
    native_wire: Path,
    native_debug: Path,
    plugin_id: str = QA_PLUGIN_ID,
) -> dict:
    """Narrow native QA-only actual-host guard-continuity receipt gate.

    Require a single CLI process, a genuine recovery reload, and a fresh guard
    denial after that reload. This cannot validate a production host, TUI or a
    different Plugin's safety semantics.
    """
    require(
        preflight_report.get("schema_version") == 1
        and preflight_report.get("native_strict_validator_pass") is True
        and preflight_report.get("target_cli") == "2.1.304"
        and preflight_report.get("plugin_name") == QA_PLUGIN_NAME,
        "REVIEWED_PREFLIGHT_RECEIPT_REQUIRED",
    )
    observed = inspect_tree(current_installed)
    require(
        observed["content_tree_sha256"] == preflight_report["content_tree_sha256"]
        and observed["plugin_name"] == preflight_report["plugin_name"]
        and observed["plugin_version"] == preflight_report["plugin_version"],
        "ACTIVE_INSTALLED_PACKAGE_DOES_NOT_MATCH_PREFLIGHT",
    )
    wire_sha = file_digest(native_wire)
    debug_sha = file_digest(native_debug)
    try:
        events = [
            json.loads(line)
            for line in native_wire.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    except (UnicodeError, ValueError) as exc:
        raise BlockedUpdate("INVALID_PRIVATE_NATIVE_JSONL") from exc
    require(events and all(isinstance(e, dict) for e in events), "INVALID_NATIVE_EVENTS")
    ids = [e.get("session_id") for e in events]
    require(
        all(isinstance(s, str) and s for s in ids) and len(set(ids)) == 1, "NOT_ONE_NATIVE_SESSION"
    )
    init_events = [e for e in events if e.get("type") == "system" and e.get("subtype") == "init"]
    require(
        init_events
        and all(e.get("claude_code_version", "").startswith("2.1.304") for e in init_events),
        "WRONG_NATIVE_TARGET_SESSION",
    )
    results = [e for e in events if e.get("type") == "result"]
    require(
        len(results) == 5
        and all(e.get("subtype") == "success" and e.get("is_error") is False for e in results),
        "NATIVE_FIVE_STEP_RECOVERY_SEQUENCE_INCOMPLETE",
    )
    require(
        [r.get("num_turns") for r in results] == [0, 0, 1, 0, 0],
        "ACTUAL_GUARD_LOSS_AND_RECOVERY_SEQUENCE_UNPROVEN",
    )
    require(
        QA_GUARD_MESSAGE in str(results[0].get("result"))
        and QA_MODEL_RESULT in str(results[2].get("result"))
        and "Reloaded:" in str(results[1].get("result"))
        and "Reloaded:" in str(results[3].get("result"))
        and QA_GUARD_MESSAGE in str(results[4].get("result")),
        "SAME_HOST_RECOVERY_GUARD_RESULT_UNPROVEN",
    )
    debug = native_debug.read_text(encoding="utf-8", errors="replace")
    tag = f"hooks module {plugin_id} loaded"
    # Not just two occurrence counts: the actual invalid load must fall between
    # the original guarded event and a later successful registration and denial.
    before = debug.find(tag)
    first_guard = debug.find(QA_HOOK_MARKER)
    failure = debug.find("does not parse:", first_guard)
    recovered = debug.find(tag, failure)
    final_guard = debug.find(QA_HOOK_MARKER, recovered)
    require(
        -1 not in (before, first_guard, failure, recovered, final_guard)
        and before < first_guard < failure < recovered < final_guard
        and debug.count(QA_HOOK_MARKER) == 2
        and "the version loaded before is unloaded" in debug,
        "IN_PROCESS_RELOADED_GUARD_CONTINUITY_NOT_ATTESTED",
    )
    require(
        "plugin.register: " + QA_PLUGIN_NAME in debug[recovered:final_guard],
        "RECOVERED_MOD_NOT_REGISTERED",
    )
    model_names = {
        e.get("message", {}).get("model")
        for e in events
        if e.get("type") == "assistant" and isinstance(e.get("message"), dict)
    }
    require("claude-sonnet-5-5" in model_names, "ACTUAL_SONNET_INFERENCE_NOT_FOUND")
    return {
        "schema_version": 1,
        "target_cli": "2.1.304",
        "plugin": QA_PLUGIN_ID,
        "candidate_tree_sha256": observed["content_tree_sha256"],
        "candidate_version": observed["plugin_version"],
        "same_native_session_observed": True,
        "native_wire_sha256": wire_sha,
        "native_debug_sha256": debug_sha,
        "actual_native_result_turns": [0, 0, 1, 0, 0],
        "previous_host_guard_lost_during_invalid_reload": True,
        "fresh_guard_loaded_and_registered_after_valid_reload": True,
        "last_benign_qa_prompt_denied_before_model_inference": True,
        "qa_recovery_guard_attested_in_this_session": True,
        "other_session_or_production_host_protected": False,
        "stable_release_authorized": False,
    }


def _save_new(out: Path, result: dict) -> None:
    require(not out.exists() and not out.is_symlink(), "EVIDENCE_OUTPUT_ALREADY_EXISTS")
    out.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation protects immutable evidence against a second writer.
    try:
        with out.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(result, sort_keys=True, indent=2) + "\n")
    except FileExistsError as exc:
        raise BlockedUpdate("EVIDENCE_OUTPUT_ALREADY_EXISTS") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    pre = sub.add_parser("preflight")
    pre.add_argument("--official-binary", type=Path, required=True)
    pre.add_argument("--candidate", type=Path, required=True)
    pre.add_argument("--expected-tree-sha256", required=True)
    pre.add_argument("--plugin-name", required=True)
    pre.add_argument("--plugin-version", required=True)
    pre.add_argument("--out", type=Path, required=True)
    post = sub.add_parser("postflight-qa")
    post.add_argument("--preflight-receipt", type=Path, required=True)
    post.add_argument("--installed", type=Path, required=True)
    post.add_argument("--private-wire", type=Path, required=True)
    post.add_argument("--private-debug", type=Path, required=True)
    post.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.action == "preflight":
            data = preflight(
                args.candidate,
                args.official_binary,
                expected_tree_sha256=args.expected_tree_sha256,
                expected_plugin_name=args.plugin_name,
                expected_plugin_version=args.plugin_version,
            )
        else:
            receipt = json.loads(args.preflight_receipt.read_text(encoding="utf-8"))
            data = postflight(
                receipt,
                current_installed=args.installed,
                native_wire=args.private_wire,
                native_debug=args.private_debug,
            )
        _save_new(args.out, data)
    except (BlockedUpdate, OSError, ValueError, TypeError, KeyError) as exc:
        reason = str(exc) if isinstance(exc, BlockedUpdate) else type(exc).__name__
        raise SystemExit(f"BLOCKED: CLI304 update safety gate: {reason}") from None
    print(
        json.dumps(
            {
                "action": args.action,
                "qa_candidate_preflight_pass": args.action == "preflight",
                "same_host_recovery_attested": args.action == "postflight-qa",
                "production_safe_claim": False,
                "stable_release_authorized": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
