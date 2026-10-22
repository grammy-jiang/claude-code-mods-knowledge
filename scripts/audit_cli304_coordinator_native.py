#!/usr/bin/env python3
"""Re-audit Mac-issued epoch and both native Claude 304 host sessions privately.

Only bounded SHA-pinned facts leave each Pi. The real native wire/debug,
per-session grant requests, supervisor PID/boot identity and private Mac
signing key are never copied into this source repository. Historical signed
authorization validity does NOT establish current host liveness or a true
network link outage; production remains HOLD.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

from mods_knowledge.cli304_coordinator_grant import (
    NATIVE_304,
    GrantBlocked,
    canonical,
    validate_request,
    verify,
)

EXPECTED_MAC_PUB_SHA = "96531a05ee8bb1a1ba107c17d06028e9fb2f09b152067bf9adff210430f6150d"
MARKER = "QA_SUPERVISED_READ_OK_20261022"
SOURCE = (
    "src/mods_knowledge/cli304_coordinator_grant.py",
    "src/mods_knowledge/cli304_supervised_lease.py",
    "scripts/cli304_coordinator_pretool.py",
    "scripts/cli304_supervised_pretool.py",
    "scripts/cli304_supervised_qa.py",
    "scripts/cli304_mac_granted_supervisor_qa.py",
)


class NativeCoordinatorEvidenceError(ValueError):
    """Fail closed if any original host evidence is missing or contradictory."""


def must(ok: bool, reason: str) -> None:
    if not ok:
        raise NativeCoordinatorEvidenceError(reason)


def sha(file: Path, max_size: int = 7_000_000) -> str:
    must(file.is_file() and not file.is_symlink(), "MISSING_OR_UNSAFE_ORIGINAL_FILE")
    must(0 <= file.stat().st_size <= max_size, "OVERSIZE_ORIGINAL_EVIDENCE")
    with file.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def inspect(
    private_root: Path, epoch: int, host: str, pub: Path, openssl: Path
) -> tuple[dict, dict, dict]:
    folder = private_root / f"run-epoch{epoch}"
    request_file = folder / "private/coordinator-request.private.json"
    grant_file = folder / "private/coordinator-grant.private.json"
    receipt_file = folder / "private/coordinator-receipt.private.json"
    req, envelope, receipt = (
        json.loads(request_file.read_text()),
        json.loads(grant_file.read_text()),
        json.loads(receipt_file.read_text()),
    )
    validate_request(req)
    must(req["host"] == host and envelope["payload"]["epoch"] == epoch, "WRONG_NATIVE_COHORT_EPOCH")
    issued = envelope["payload"]["issued_at"]
    verified = verify(
        envelope,
        request=req,
        public_key=pub,
        openssl=openssl,
        now=issued + 1,
        min_epoch=epoch,
    )
    must(verified["epoch"] == epoch, "SIGNED_MAC_EPOCH_INCORRECT")
    must(
        receipt["epoch"] == epoch
        and receipt["generation"] == req["generation"]
        and receipt["signed_payload_sha256"]
        == hashlib.sha256(
            canonical(envelope, expected={"schema", "payload", "signature"})
        ).hexdigest(),
        "RECEIPT_NOT_BOUND_TO_SIGNED_MAC_GRANT",
    )
    raw = folder / "raw"
    wire = raw / "native-wire.private.jsonl"
    debug_file = raw / "native-debug.private.log"
    stderr = raw / "native-stderr.private.log"
    must(stderr.stat().st_size == 0, "NONEMPTY_NATIVE_STDERR")
    events = [json.loads(line) for line in wire.read_text().splitlines() if line.strip()]
    must(bool(events) and all(isinstance(e, dict) for e in events), "MISSING_NATIVE_JSONL")
    init = [e for e in events if e.get("type") == "system" and e.get("subtype") == "init"]
    must(
        len(init) == (2 if epoch == 1 else 1)
        and all(e.get("claude_code_version") == "2.1.304" for e in init),
        "NOT_ORIGINAL_NATIVE_304",
    )
    native_sessions = {e.get("session_id") for e in events if e.get("session_id")}
    must(
        len(native_sessions) == 1
        and hashlib.sha256(next(iter(native_sessions)).encode()).hexdigest()
        == req["session_sha256"],
        "MIXED_NATIVE_SESSIONS_OR_WRONG_MAC_GRANT",
    )
    model_names = {
        (e.get("message") or {}).get("model") for e in events if e.get("type") == "assistant"
    }
    must("claude-sonnet-5-5" in model_names, "NO_ACTUAL_AUTHENTICATED_MODEL")
    tool_uses = [
        x.get("name")
        for e in events
        if e.get("type") == "assistant"
        for x in (e.get("message") or {}).get("content", [])
        if isinstance(x, dict) and x.get("type") == "tool_use"
    ]
    tool_results = [
        x
        for e in events
        if e.get("type") == "user"
        for x in (e.get("message") or {}).get("content", [])
        if isinstance(x, dict) and x.get("type") == "tool_result"
    ]
    responses = [e for e in events if e.get("type") == "result"]
    n = 2 if epoch == 1 else 1
    must(
        tool_uses == ["Read"] * n
        and len(tool_results) == n
        and len(responses) == n
        and all(x.get("subtype") == "success" and x.get("is_error") is False for x in responses),
        "NATIVE_HOST_MODEL_TOOL_RESULTS_INCOMPLETE",
    )
    must(
        MARKER in json.dumps(tool_results[0]) and tool_results[0].get("is_error") is not True,
        "NATIVE_READ_DID_NOT_WORK_WITH_VALID_MAC_GRANT",
    )
    if epoch == 1:
        must(
            tool_results[1].get("is_error") is True
            and "MAC_AUTHORITY_QA_DENIED" in json.dumps(tool_results[1])
            and MARKER not in json.dumps(tool_results[1]),
            "EXPIRED_MAC_GRANT_DID_NOT_BLOCK_NATIVE_TOOL",
        )
        must(
            time.time() > verified["expires_at"],
            "ORIGINAL_GRANT_NOT_EXPIRED_FOR_REPLAY",
        )
    debug = debug_file.read_text(errors="replace")
    must(
        "managed-settings.json" in debug and debug.count("PreToolUse:Read") >= n,
        "INDEPENDENT_MANAGED_NATIVE_HOST_HOOK_UNPROVEN",
    )
    local = json.loads((folder / "private/supervisor-lease.json").read_text())
    must(
        local["phase"] == "blocked"
        and local["generation"] == req["generation"]
        and local["session"] in native_sessions,
        "UNSAFE_LINGERING_LOCAL_SUPERVISOR",
    )
    policy = folder / "managed/managed-settings.json"
    must(sha(policy) == req["policy_sha256"], "MAC_GRANT_POLICY_NOT_EXACT_INSTALLED_SOURCE")
    setting = json.loads(policy.read_text())
    args = setting["hooks"]["PreToolUse"][0]["hooks"][0]["args"]
    must(
        setting["allowManagedHooksOnly"] is True
        and setting["allowManagedPermissionRulesOnly"] is True
        and setting["hooks"]["PreToolUse"][0]["hooks"][0]["onFailure"] == "block"
        and any(x.endswith("cli304_coordinator_pretool.py") for x in args)
        and "--request" in args
        and "--grant" in args
        and "--receipt" in args
        and "--public" in args,
        "NOT_AN_INDEPENDENT_MAC_REQUIRED_MANAGED_HOOK",
    )
    original = json.loads((folder / "private/sanitized-outcome.json").read_text())
    must(
        original["epoch"] == epoch
        and original["host"] == host
        and original["source_grant_sha256"] == sha(grant_file)
        and original["original_native_wire_sha256"] == sha(wire)
        and original["original_native_debug_sha256"] == sha(debug_file)
        and original["policy_sha256"] == sha(policy)
        and original["native_binary_sha256"] == NATIVE_304,
        "CLAIMED_RESULT_NOT_SUPPORTED_BY_ORIGINAL_NATIVE_BYTES",
    )
    if epoch == 1:
        must(
            original["local_supervisor_froze_on_coordinator_expiry"] is True
            and original["actual_native_tool_blocked_after_mac_grant_expiry"] is True,
            "MISSING_SUPERVISOR_FREEZE_NEGATIVE_CONTROL",
        )
    else:
        must(
            original["scenario"] == "recovered-new-generation"
            and original["native_turns"][0]["read_marker"] is True,
            "NO_NEW_EPOCH_NATIVE_RECOVERY",
        )
    return (
        {
            "epoch": epoch,
            "actual_native_tool_uses": tool_uses,
            "actual_native_model_turn_counts": [r.get("num_turns") for r in responses],
            "valid_mac_grant_native_read": True,
            "expired_grant_native_read_denied": epoch == 1,
            "local_supervisor_left_blocked_after_test": True,
            "original_native_wire_sha256": sha(wire),
            "original_native_debug_sha256": sha(debug_file),
            "mac_signed_grant_sha256": sha(grant_file),
            "mac_signed_request_sha256": sha(request_file),
            "managed_policy_sha256": sha(policy),
        },
        req,
        envelope,
    )


def audit(root: Path, native: Path, host: str, openssl: Path) -> dict:
    must(host in ("rpi-a", "rpi-b"), "INVALID_EXPLICIT_QA_HOST")
    must(native.is_file() and not native.is_symlink(), "OFFICIAL_CLAUDE_BINARY_MISSING")
    with native.open("rb") as f:
        must(
            hashlib.file_digest(f, "sha256").hexdigest() == NATIVE_304,
            "WRONG_NATIVE_CLAUDE_EXECUTABLE",
        )
    pub = root / "private/mac-coordinator.pub.pem"
    must(sha(pub, 8192) == EXPECTED_MAC_PUB_SHA, "UNPINNED_MAC_PUBLIC_KEY")
    sources = {name: sha(root / name) for name in SOURCE}
    old, old_req, old_grant = inspect(root, 1, host, pub, openssl)
    new, new_req, new_grant = inspect(root, 2, host, pub, openssl)
    must(
        old_req["generation"] != new_req["generation"]
        and old_req["session_sha256"] != new_req["session_sha256"]
        and old_req["cohort"] == new_req["cohort"]
        and old_grant["payload"]["epoch"] == 1
        and new_grant["payload"]["epoch"] == 2,
        "UNSAFE_SUPERVISOR_RESTART_OR_EPOCH_REUSE",
    )
    try:
        verify(
            old_grant,
            request=new_req,
            public_key=pub,
            openssl=openssl,
            now=old_grant["payload"]["issued_at"] + 1,
        )
    except GrantBlocked:
        pass
    else:
        raise NativeCoordinatorEvidenceError("OLD_MAC_GRANT_REPLAY_WAS_ALLOWED")
    return {
        "schema_version": 1,
        "target_cli": "2.1.304",
        "host": host,
        "native_binary_sha256": NATIVE_304,
        "source_sha256": sources,
        "auditor_sha256": sha(Path(__file__)),
        "mac_coordinator_public_key_sha256": EXPECTED_MAC_PUB_SHA,
        "real_native_epochs": {"1": old, "2": new},
        "first_epoch_mac_delivery_stopped_and_tool_denied": True,
        "same_original_host_process_for_pre_post_expiry": True,
        "old_mac_grant_cannot_be_reused_in_new_host_generation": True,
        "recovery_requires_new_supervisor_and_mac_signed_epoch": True,
        "physically_disconnected_network_tested": False,
        "unregistered_native_hosts_protected": False,
        "stable_release_authorized": False,
        "new_cli304_claims_approved": 0,
        "raw_session_identifiers_and_mac_private_signer_not_committed": True,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--private-root", type=Path, required=True)
    p.add_argument("--native", type=Path, required=True)
    p.add_argument("--host", choices=("rpi-a", "rpi-b"), required=True)
    p.add_argument("--openssl", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    if a.out.exists() or a.out.is_symlink():
        raise SystemExit("REFUSED: immutable sanitized native evidence already exists")
    try:
        report = audit(a.private_root, a.native, a.host, a.openssl)
    except (OSError, ValueError, KeyError, TypeError, GrantBlocked, NativeCoordinatorEvidenceError):
        raise SystemExit(
            "BLOCKED: original signed Mac grant/native host evidence invalid"
        ) from None
    a.out.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    print(
        json.dumps(
            {
                "host": a.host,
                "epochs": 2,
                "real_native_model_scenarios": 2,
                "physical_network_partition_tested": False,
                "stable": False,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
