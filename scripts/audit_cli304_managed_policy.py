#!/usr/bin/env python3
"""Independently re-evaluate native CLI304 sandbox managed settings experiments.

Only private native tool events and SHA-pinned harmless sandbox files are
examined. No production /etc or authenticated user files are read or changed.
Original raw host transcripts and debug remain off Git.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

NATIVE_CLI_SHA = "c487117526509ab6d2ee6013e14f181faf68d6d6afe6bb0d4b2b4a9feca5ecb3"
PINNED_FILES = {
    "qa_only/managed-baseline-policy.json": "81bb8646751aa1936b2526c4f0c3668b25a4aa064ba96d7c8455f422efa8e02c",
    "qa_only/managed-priority-policy.json": "1bc1bd28eec6641a07ad4101608c851f7da4a18d88e61ba5a35731ea146c3bcd",
    "qa_only/user_attempt_disable_hooks.json": "6adc81a196a8af72536847a96f47b720556942efbe5f9a3df5ecf1a0a791f865",
    "qa_only/user-hook-attempt.json": "07ece7d050e31c8b3b8050866f4a45221afa216b3ea571758eb05e9996cc0857",
    "qa_only/managed_deny_read.py": "29e7369692972da2ef3178256380ba51c76b6b4e48e32b3c2fd2a5c187d8b319",
    "qa_only/user_deny_read.py": "7c62a2802f528868954def57c2db9d0d368e7bfa89893995269345aa9cd071d2",
}
RUNS = {
    "managed_deny_write": "raw/managed-native",
    "managed_hook_not_disabled": "raw/managed-hook-compare/managed-priority",
    "unmanaged_hook_suppressed": "raw/managed-hook-compare/managed-only",
}


class MissingNativePolicyEvidence(ValueError):
    """Missing, tampered, or incomplete first-party native host receipt."""


def must(value: bool, why: str) -> None:
    if not value:
        raise MissingNativePolicyEvidence(why)


def digest(path: Path, *, max_size: int = 12_000_000) -> str:
    must(path.is_file() and not path.is_symlink(), "INVALID_OR_MISSING_EVIDENCE_FILE")
    must(0 <= path.stat().st_size <= max_size, "UNEXPECTED_EVIDENCE_SIZE")
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def run(root: Path, prefix: str) -> tuple[dict, list[dict], list[dict], str]:
    wire = root / (prefix + "-wire.private.jsonl")
    debug_file = root / (prefix + "-debug.private.log")
    stderr = root / (prefix + "-stderr.private.log")
    must(stderr.is_file() and stderr.stat().st_size == 0, "NATIVE_STDERR_NOT_EMPTY")
    values = [json.loads(line) for line in wire.read_text().splitlines() if line.strip()]
    must(values and all(isinstance(e, dict) for e in values), "INVALID_NATIVE_JSONL")
    firstparty = [x for x in values if x.get("type") == "system" and x.get("subtype") == "init"]
    must(
        bool(firstparty)
        and all(
            isinstance(x.get("claude_code_version"), str)
            and x["claude_code_version"].startswith("2.1.304")
            for x in firstparty
        ),
        "NOT_ACTUAL_CLI304_NATIVE_HOST",
    )
    models = {(e.get("message") or {}).get("model") for e in values if e.get("type") == "assistant"}
    must("claude-sonnet-5-5" in models, "NO_ACTUAL_SONNET_MODEL")
    results = [e for e in values if e.get("type") == "result"]
    must(
        len(results) == 1
        and results[0].get("subtype") == "success"
        and results[0].get("is_error") is False,
        "NATIVE_MODEL_TURN_INCOMPLETE",
    )
    tool_calls = [
        c.get("name")
        for e in values
        if e.get("type") == "assistant"
        for c in (e.get("message") or {}).get("content", [])
        if isinstance(c, dict) and c.get("type") == "tool_use"
    ]
    output = [
        c
        for e in values
        if e.get("type") == "user"
        for c in (e.get("message") or {}).get("content", [])
        if isinstance(c, dict) and c.get("type") == "tool_result"
    ]
    debug = debug_file.read_text(errors="replace")
    must(
        "managed-settings.json" in debug and "allowManagedHooksOnly" in debug,
        "NATIVE_MANAGED_SOURCE_NOT_LOADED",
    )
    return (
        {
            "wire_sha256": digest(wire),
            "debug_sha256": digest(debug_file),
            "real_native_tool_calls": tool_calls,
            "actual_result_turns": results[0].get("num_turns"),
            "native_host_model_identified": True,
        },
        output,
        tool_calls,
        debug,
    )


def audit(root: Path, official_native: Path) -> dict:
    must(official_native.is_file() and not official_native.is_symlink(), "OFFICIAL_BINARY_MISSING")
    with official_native.open("rb") as inp:
        binary_sha = hashlib.file_digest(inp, "sha256").hexdigest()
    must(binary_sha == NATIVE_CLI_SHA, "OFFICIAL_NATIVE_BINARY_MISMATCH")
    for name, sha in PINNED_FILES.items():
        must(digest(root / name) == sha, "NOT_ORIGINAL_MANAGED_QA_FIXTURES")
    base_policy = json.loads((root / "qa_only/managed-baseline-policy.json").read_text())
    priority_policy = json.loads((root / "qa_only/managed-priority-policy.json").read_text())
    user_disable = json.loads((root / "qa_only/user_attempt_disable_hooks.json").read_text())
    nonmanaged_attempt = json.loads((root / "qa_only/user-hook-attempt.json").read_text())
    must(
        base_policy["allowManagedHooksOnly"] is True
        and base_policy["allowManagedPermissionRulesOnly"] is True
        and set(base_policy["permissions"]["deny"]) == {"Write", "Bash", "Edit"},
        "BASE_MANAGED_POLICY_NOT_REVIEWED",
    )
    must(
        priority_policy["hooks"]["PreToolUse"][0]["hooks"][0]["onFailure"] == "block"
        and user_disable["disableAllHooks"] is True
        and "PreToolUse" in nonmanaged_attempt["hooks"],
        "NOT_MANAGED_VS_NONMANAGED_CONTROL",
    )
    observed = {name: run(root, prefix) for name, prefix in RUNS.items()}
    base, br, bc, _ = observed["managed_deny_write"]
    control, cr, cc, _ = observed["managed_hook_not_disabled"]
    suppressed, sr, sc, _ = observed["unmanaged_hook_suppressed"]

    def has(row: dict, marker: str) -> bool:
        return marker in json.dumps(row, ensure_ascii=False)

    must(
        bc == ["Read", "Write"]
        and len(br) == 2
        and has(br[0], "QA_MANAGED_READ_ALLOWED_ONLY")
        and br[1].get("is_error") is True
        and not has(br[1], "QA_MANAGED_WRITE"),
        "MANAGED_PERMISSION_PRIORITY_NOT_OBSERVED",
    )
    must(
        cc == ["Read"]
        and len(cr) == 1
        and cr[0].get("is_error") is True
        and has(cr[0], "QA_MANAGED_HOOK_DENY_READ"),
        "MANAGED_HOOK_DISABLED_BY_USER_SETTING",
    )
    must(
        sc == ["Read"]
        and len(sr) == 1
        and has(sr[0], "QA_MANAGED_READ_ALLOWED_ONLY")
        and not has(sr[0], "QA_NONMANAGED_HOOK_SHOULD_BE_SUPPRESSED"),
        "NONMANAGED_HOOK_WAS_NOT_SUPPRESSED",
    )
    must(
        not (root / "working/managed-write-denied.txt").exists(),
        "UNAUTHORIZED_FILE_WRITE_OBSERVED",
    )
    return {
        "schema_version": 1,
        "target_cli": "2.1.304",
        "native_binary_sha256": binary_sha,
        "auditor_source_sha256": digest(Path(__file__)),
        "reviewed_source_sha256": PINNED_FILES,
        "native_cases": {key: value[0] for key, value in observed.items()},
        "observations": {
            "managed_policy_read_in_isolated_official_host": True,
            "managed_deny_rule_blocks_preallowed_write": True,
            "managed_command_hook_survives_user_disableAllHooks": True,
            "lower_priority_command_hook_suppressed_by_allowManagedHooksOnly": True,
            "no_test_file_created": True,
        },
        "real_system_etc_not_modified": True,
        "test_scope": "bwrap-only Linux ARM64 managed policy overlay",
        "managed_source_not_deployed_to_any_production_host": True,
        "organization_team_server_policy_precedence_not_verified": True,
        "complete_live_session_inventory_proven": False,
        "stable_release_authorized": False,
        "new_cli304_claims_approved": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--native-binary", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    o = parser.parse_args()
    if o.out.exists() or o.out.is_symlink():
        raise SystemExit("REFUSED: immutable sanitized audit output already exists")
    try:
        result = audit(o.private_root, o.native_binary)
    except (MissingNativePolicyEvidence, OSError, ValueError, TypeError, KeyError):
        raise SystemExit(
            "BLOCKED: missing or contradictory original native managed evidence"
        ) from None
    o.out.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(
        json.dumps(
            {"real_managed_cases": len(RUNS), "full_production_policy": False, "stable": False},
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
