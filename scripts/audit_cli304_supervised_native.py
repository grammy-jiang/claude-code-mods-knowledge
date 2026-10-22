#!/usr/bin/env python3
"""Independently replay exact private native supervised-host QA runs.

Only bounded sanitized per-host facts are emitted; original native model
wires, debug logs, process/session identity and signing private keys stay
outside Git. Real host-specific runtime authentication is not signed by Claude.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

OFFICIAL_SHA = "c487117526509ab6d2ee6013e14f181faf68d6d6afe6bb0d4b2b4a9feca5ecb3"
MARKER = "QA_SUPERVISED_READ_OK_20261022"
RUNS = {
    "freeze": "run-live-signed-2",
    "lease-expiry": "run-final-expiry",
}
FILES = [
    "code/mods_knowledge/cli304_supervised_lease.py",
    "code/mods_knowledge/cli304_supervised_attestation.py",
    "scripts/cli304_supervised_pretool.py",
    "scripts/cli304_supervised_qa.py",
]


class NativeQAInvalid(ValueError):
    """Actual native evidence is missing, ambiguous or not source-pinned."""


def require(value: bool, why: str) -> None:
    if not value:
        raise NativeQAInvalid(why)


def sha(path: Path, max_size: int = 8_000_000) -> str:
    require(
        path.is_file() and not path.is_symlink() and 0 <= path.stat().st_size <= max_size,
        "MISSING_OR_UNSAFE_EVIDENCE_FILE",
    )
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def inspect_one(run: Path, mode: str) -> dict:
    raw = run / "raw"
    wire = raw / "native-wire.private.jsonl"
    debug = raw / "native-debug.private.log"
    stderr = raw / "native-stderr.private.log"
    require(sha(stderr) == hashlib.sha256(b"").hexdigest(), "NATIVE_STDERR_NOT_EMPTY")
    lines = wire.read_text().splitlines()
    records = [json.loads(line) for line in lines if line.strip()]
    require(records and all(isinstance(x, dict) for x in records), "MISSING_NATIVE_EVENTS")
    ids = {x.get("session_id") for x in records if x.get("session_id")}
    require(len(ids) == 1, "MULTIPLE_OR_UNKNOWN_HOST_SESSIONS")
    session = next(iter(ids))
    starts = [e for e in records if e.get("type") == "system" and e.get("subtype") == "init"]
    require(
        bool(starts)
        and all(
            isinstance(x.get("claude_code_version"), str)
            and x["claude_code_version"].startswith("2.1.304")
            for x in starts
        ),
        "NOT_ORIGINAL_TARGET_CLAUDE304",
    )
    models = {
        x.get("message", {}).get("model")
        for x in records
        if x.get("type") == "assistant" and isinstance(x.get("message"), dict)
    }
    require("claude-sonnet-5-5" in models, "NO_NATIVE_MODEL_INFERENCE")
    uses = [
        c.get("name")
        for e in records
        if e.get("type") == "assistant"
        for c in (e.get("message") or {}).get("content", [])
        if isinstance(c, dict) and c.get("type") == "tool_use"
    ]
    result_events = [
        c
        for e in records
        if e.get("type") == "user"
        for c in (e.get("message") or {}).get("content", [])
        if isinstance(c, dict) and c.get("type") == "tool_result"
    ]
    end = [e for e in records if e.get("type") == "result"]
    require(
        uses == ["Read", "Read"]
        and len(result_events) == 2
        and len(end) == 2
        and all(e.get("subtype") == "success" and e.get("is_error") is False for e in end),
        "INCOMPLETE_SAME_NATIVE_HOST_TWO_TURNS",
    )
    require(
        MARKER in json.dumps(result_events[0])
        and not result_events[0].get("is_error")
        and result_events[1].get("is_error") is True
        and "SUPERVISOR_QA_DENIED" in json.dumps(result_events[1])
        and MARKER not in json.dumps(result_events[1]),
        "SUPERVISED_READ_BEFORE_AFTER_NOT_PROVEN",
    )
    log = debug.read_text(errors="replace")
    require(
        log.count("PreToolUse:Read") >= 2
        and "managed-settings.json" in log
        and "allowManagedHooksOnly" in log,
        "ORIGINAL_MANAGED_PRETOOL_HOOK_MISSING",
    )
    result_path = run / "private/sanitized-outcome.json"
    result = json.loads(result_path.read_text())
    require(
        result["schema"] == 1
        and result["scenario"] == mode
        and result["official_binary_sha256"] == OFFICIAL_SHA
        and result["single_continuous_native_host"] is True
        and result["read_allowed_when_healthy"] is True
        and result["read_denied_after_freeze_or_lease_loss"] is True
        and result["production_global_session_coverage"] is False,
        "ORIGINAL_SUPERVISOR_REPORT_NOT_SUPPORTED",
    )
    require(result["wire_sha256"] == sha(wire), "ORIGINAL_WIRE_SHA_MISMATCH")
    require(result["debug_sha256"] == sha(debug), "ORIGINAL_DEBUG_SHA_MISMATCH")
    policy_path = run / "managed/managed-settings.json"
    require(result["managed_policy_sha256"] == sha(policy_path), "MANAGED_SOURCE_CHANGED")
    policy = json.loads(policy_path.read_text())
    require(
        policy.get("allowManagedHooksOnly") is True
        and policy.get("allowManagedPermissionRulesOnly") is True
        and set(policy["permissions"]["deny"]) == {"Write", "Edit", "Bash"}
        and policy["hooks"]["PreToolUse"][0]["hooks"][0]["onFailure"] == "block",
        "UNSAFE_REVIEWED_MANAGED_POLICY",
    )
    lease = json.loads((run / "private/supervisor-lease.json").read_text())
    require(
        lease["phase"] == "blocked" and lease["session"] == session, "HOST_NOT_BLOCKED_AFTER_QA"
    )
    status = json.loads((run / "private/live-status.private.json").read_text())
    require(
        status["live_native_read_verified"] is True
        and status["session_sha256"] == hashlib.sha256(session.encode()).hexdigest()
        and status["policy_sha256"] == sha(policy_path)
        and status["global_session_coverage"] is False,
        "NO_PRESERVED_LIVE_NATIVE_BASELINE",
    )
    require(
        (run / "work/safe-read.txt").read_text().strip() == MARKER,
        "BENIGN_READ_FILE_CHANGED",
    )
    return {
        "mode": mode,
        "actual_native_tools": uses,
        "original_native_result_turn_counts": [e.get("num_turns") for e in end],
        "read_allowed_before_freeze": True,
        "read_denied_after_freeze_or_expiry": True,
        "same_native_session_reused": True,
        "managed_policy_onFailure_block": True,
        "managed_policy_sha256": sha(policy_path),
        "original_host_wire_sha256": sha(wire),
        "original_host_debug_sha256": sha(debug),
        "private_original_native_result_present": True,
        "global_host_coverage_proven": False,
    }


def audit(root: Path, binary: Path, *, host: str) -> dict:
    require(bool(re.fullmatch(r"[a-z0-9-]{3,25}", host)), "INVALID_QA_HOST_LABEL")
    require(binary.is_file() and not binary.is_symlink(), "OFFICIAL_NATIVE_BINARY_MISSING")
    with binary.open("rb") as f:
        native_sha = hashlib.file_digest(f, "sha256").hexdigest()
    require(native_sha == OFFICIAL_SHA, "UNVERIFIED_NATIVE_CLAUDE_BINARY")
    source = {file: sha(root / file) for file in FILES}
    modes = {mode: inspect_one(root / folder, mode) for mode, folder in RUNS.items()}
    return {
        "schema": 1,
        "host_label": host,
        "native_target": "2.1.304",
        "actual_official_native_binary_sha256": native_sha,
        "auditor_sha256": sha(Path(__file__)),
        "reviewed_source_sha256": source,
        "actual_native_modes": modes,
        "proof_of_heartbeat_expiry_refusal": True,
        "proof_of_active_external_freeze_refusal": True,
        "full_running_host_inventory_attested": False,
        "global_tool_enforcement_proven": False,
        "stable_release_authorized": False,
        "qa_raw_session_data_excluded": True,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--native-binary", type=Path, required=True)
    p.add_argument("--host-label", required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    if a.out.exists() or a.out.is_symlink():
        raise SystemExit("REFUSED: immutable original QA report already exists")
    try:
        result = audit(a.root, a.native_binary, host=a.host_label)
    except (OSError, ValueError, TypeError, KeyError, NativeQAInvalid):
        raise SystemExit("BLOCKED: original CLI304 supervised native evidence incomplete") from None
    a.out.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"host": a.host_label, "native_modes": 2, "global_coverage": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
