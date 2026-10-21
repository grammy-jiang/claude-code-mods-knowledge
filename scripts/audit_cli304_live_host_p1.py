#!/usr/bin/env python3
"""Re-evaluate private *actual-host* CLI304 wire/debug receipts; emit only redacted facts.

This is not a model runner. Full prompts, tool arguments, account details and
raw debug/wire JSONL must remain off Git. The pinned evidence includes a
reproducible failed-reload safety-regression scenario and does not approve any
new version Claim. It should never be mistaken for synthetic plugin tests.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

OFFICIAL_NATIVE_SHA = "c487117526509ab6d2ee6013e14f181faf68d6d6afe6bb0d4b2b4a9feca5ecb3"
OFFICIAL_ASSET_SHA = "17cc5d933babad064bed65b3a4fbafab29556fbbfc12aa7888ae1f6c320e08c5"
ORIGINAL_COMMAND = "QA304_KEEP_COMMAND_AVAILABLE_20261021"
MODIFIED_COMMAND = "QA304_NEW_CONTENT_MUST_NOT_ACTIVATE_20261021"
EXPECTED_SOURCES = {
    "read/qa-read304/hooks/register.js": "bb1d2ee24573e98b5a1fe6c768eb39d59afe996817fe564c25e5a8baa4039ef7",
    "ask/qa-person304/hooks/register.js": "a3e7742ab6e9027105ff43e405292d8cabfcbb456bb7e26ece8df7ffd8539814",
    "raw/qa-outer-original-shortcircuit.private.js": "907e51989b2d302626d4dd59f674112c92099e1a78594158d4ff7463de585e59",
    "chain/qa-outer304/hooks/register.js": "5b5424981a808947fb646689f2e600c625337cd368a83f2d3b6211f9566aa544",
    "chain/qa-inner304/hooks/register.js": "3cd813a31b40cceaf10c856a3461f29a4bcddd4b79d45fcef9579355df79cf85",
    "reload/qa-reload304/hooks/register.js": "2498376f524d1e02979f7e3c4dd288577ffd051171141609853f60f6198e1fc9",
    "reload/qa-reload304/commands/qa-keep304.md": "64344d6728cc3e658a7ab899573d91d40bb4e6b9983fee66b0756ddffd35659f",
    "guard/qa-guard304/hooks/register.js": "d612de08145f36bfb296a1dcba4765cf614838ffbf00b907125e510365a7922c",
}
RUNS = ("read", "person", "chain", "chain-control", "reload-corrected", "guard-reload")


class IncompleteHostEvidence(ValueError):
    """The genuine host receipt cannot support the claimed observation."""


def digest(path: Path) -> str:
    if not path.is_file() or path.is_symlink():
        raise IncompleteHostEvidence("Required regular evidence file missing")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, code: str) -> None:
    if not condition:
        raise IncompleteHostEvidence(code)


def load_run(raw: Path, name: str) -> tuple[dict, list[dict], str, str]:
    wire_path = raw / f"live-{name}-wire.private.jsonl"
    debug_path = raw / f"live-{name}-debug.private.log"
    stderr_path = raw / f"live-{name}-stderr.private.log"
    require(all(p.is_file() and not p.is_symlink() for p in (wire_path, debug_path, stderr_path)), "MISSING_RECEIPT")
    require(all(p.stat().st_size <= 8_000_000 for p in (wire_path, debug_path, stderr_path)), "RECEIPT_TOO_LARGE")
    require(stderr_path.stat().st_size == 0, "NATIVE_STDERR_NOT_EMPTY")
    records = []
    for line in wire_path.read_text().splitlines():
        if line.strip():
            try:
                value = json.loads(line)
            except ValueError as exc:
                raise IncompleteHostEvidence("MALFORMED_NATIVE_WIRE") from exc
            require(isinstance(value, dict), "MALFORMED_NATIVE_WIRE_EVENT")
            records.append(value)
    results = [event for event in records if event.get("type") == "result"]
    require(bool(results) and all(x.get("subtype") == "success" and x.get("is_error") is False for x in results), "INCOMPLETE_NATIVE_HOST_RESULT")
    tool_names = []
    tool_results = []
    models = set()
    for event in records:
        msg = event.get("message")
        if event.get("type") == "assistant" and isinstance(msg, dict):
            model = msg.get("model")
            if isinstance(model, str):
                models.add(model)
            for part in msg.get("content", []):
                if isinstance(part, dict) and part.get("type") == "tool_use":
                    tool_names.append(part.get("name"))
        if event.get("type") == "user" and isinstance(msg, dict):
            for part in msg.get("content", []):
                if isinstance(part, dict) and part.get("type") == "tool_result":
                    tool_results.append(part)
    require(all(x in ("Read", "Write") for x in tool_names), "UNEXPECTED_HOST_TOOL")
    require("claude-sonnet-5-5" in models, "NO_AUTHENTICATED_MODEL_TURN")
    debug = debug_path.read_text(errors="replace")
    result_cost = sum(float(x.get("total_cost_usd") or 0) for x in results)
    require(0 <= result_cost < 0.40, "COST_BOUND_EXCEEDED")
    receipt = {
        "wire_sha256": digest(wire_path),
        "debug_sha256": digest(debug_path),
        "stderr_sha256": digest(stderr_path),
        "event_counts": dict(sorted(Counter(x.get("type") for x in records).items())),
        "real_tool_use_names": tool_names,
        "real_tool_result_errors": sum(x.get("is_error") is True for x in tool_results),
        "model_names_from_native_wire": sorted(models),
        "result_turns": [x.get("num_turns") for x in results],
        "cost_usd": round(result_cost, 8),
    }
    return receipt, results, debug, json.dumps(tool_results, ensure_ascii=False)


def audit(root: Path, binary: Path, asset: Path) -> dict:
    require(digest(binary) == OFFICIAL_NATIVE_SHA, "WRONG_NATIVE_CLI304_BINARY")
    require(digest(asset) == OFFICIAL_ASSET_SHA, "WRONG_NATIVE_CLI304_ASSET")
    for relative, expected_sha in EXPECTED_SOURCES.items():
        require(digest(root / relative) == expected_sha, "UNREVIEWED_FIXTURE_BYTES")
    raw = root / "raw"
    data = {name: load_run(raw, name) for name in RUNS}
    read, person, chain, control, reload, guard = [data[name] for name in RUNS]
    require(read[0]["real_tool_use_names"] == ["Read", "Read"], "READ_HOST_TOOLS_MISSING")
    require(read[0]["real_tool_result_errors"] == 2, "READ_DENY_MISSING")
    require("QA304_READ_EVENT_NORMAL_READONLY_true_BASE_allow" in read[2], "READ_ONLY_METADATA_NOT_REAL")
    require("QA304_READ_EVENT_THROW_READONLY_true_BASE_allow" in read[2], "READ_HOOK_THROW_NOT_REAL")
    require("QA304_READ_HOST_READONLY_true" in read[3] and "QA304_CATCH_FAIL_CLOSED" in read[3], "READ_OR_CATCH_NOT_DENIED")
    require(person[0]["real_tool_use_names"] == ["Write"], "PERSON_WRITE_NOT_ATTEMPTED")
    require(person[0]["real_tool_result_errors"] == 1, "PERSON_WRITE_NOT_DENIED")
    require("QA304_PERSON_WRITE_BASE_ask" in person[2], "PERSON_ORIGIN_NOT_ASK")
    require("QA304_PERSON_REQUIRED" in person[3], "HUMAN_DECIDER_MISSING")
    require(not (root / "ask/work/qa-person-unattended.txt").exists(), "UNATTENDED_WRITE_EXECUTED")
    require(chain[0]["real_tool_use_names"] == ["Read"], "CHAIN_SHORT_CIRCUIT_NOT_HOST")
    require("QA304_OUTER_ENTER" in chain[2] and "QA304_INNER_ENTER" not in chain[2], "CHAIN_SHORTCIRCUIT_NOT_PROVEN")
    require("QA304_OUTER_SHORT_CIRCUIT" in chain[3], "CHAIN_DENIAL_NOT_PROPAGATED")
    require(control[0]["real_tool_use_names"] == ["Read"], "CHAIN_CONTROL_NOT_HOST")
    require("QA304_OUTER_PASS_ENTER" in control[2] and "QA304_INNER_ENTER" in control[2], "INNER_PLUGIN_NOT_CONFIRMED_LOADED")
    require("QA_CHAIN_UNSENSITIVE_CONTENT" in control[3], "CHAIN_CONTROL_DID_NOT_READ_FILE")

    reload_results = reload[1]
    require(len(reload_results) == 3, "RELOAD_MULTI_TURN_INCOMPLETE")
    require(ORIGINAL_COMMAND in str(reload_results[0].get("result")), "BASELINE_COMMAND_NOT_AVAILABLE")
    require("Reloaded:" in str(reload_results[1].get("result")), "RELOAD_WAS_NOT_ACKED")
    require(MODIFIED_COMMAND in str(reload_results[2].get("result")), "MODIFIED_COMMAND_NOT_LIVE")
    require(ORIGINAL_COMMAND not in str(reload_results[2].get("result")), "COMMAND_VERSION_AMBIGUOUS")
    require("does not parse:" in reload[2] and "the version loaded before is unloaded" in reload[2], "FAILED_RELOAD_NOT_PROVEN")
    require(reload[2].count("QA304_RELOAD_PREVIOUS_HOOK_ACTIVE") == 1, "OLD_HOOK_CONTINUITY_UNCLEAR")
    source = (root / "reload/qa-reload304/hooks/register.js").read_bytes()
    new_command = (root / "reload/qa-reload304/commands/qa-keep304.md").read_text().replace(ORIGINAL_COMMAND, MODIFIED_COMMAND)
    require(hashlib.sha256(source + b"\nexport function invalid_js( {\n").hexdigest() == "d23f7b712a4f3821fa234704b95acde2cc4d50e27cb0621506e49971ebc22114", "BROKEN_MODULE_FINGERPRINT_DRIFT")
    require(hashlib.sha256(new_command.encode()).hexdigest() == "f5f9a99970ccb9db37f58a1468ec149aa89c70aaf54a696550e971a0c7bb1863", "MODIFIED_COMMAND_FINGERPRINT_DRIFT")

    guard_results = guard[1]
    require(len(guard_results) == 3, "GUARD_MULTI_TURN_INCOMPLETE")
    require(guard_results[0].get("num_turns") == 0 and "QA304_GUARD_DENIED_TEST_ONLY" in str(guard_results[0].get("result")), "BASELINE_GUARD_DID_NOT_BLOCK")
    require("Reloaded:" in str(guard_results[1].get("result")), "FAILED_GUARD_RELOAD_NOT_ACKED")
    require(guard_results[2].get("num_turns") == 1 and "QA304_SAFE_AFTER_RELOAD_RESULT" in str(guard_results[2].get("result")), "POST_RELOAD_GUARD_BYPASS_NOT_PROVEN")
    require(guard[2].count("QA304_GUARD_ENTRY") == 1 and "does not parse:" in guard[2] and "the version loaded before is unloaded" in guard[2], "GUARD_WAS_NOT_UNLOADED")
    guard_source = (root / "guard/qa-guard304/hooks/register.js").read_bytes()
    require(hashlib.sha256(guard_source + b"\nexport function broken_syntax( {\n").hexdigest() == "e969946874c1ff8a19c276b3aac32d943ecc6c93dc2ad9ea9a29a4b7f39851d5", "BROKEN_GUARD_FINGERPRINT_DRIFT")
    costs = round(sum(item[0]["cost_usd"] for item in data.values()), 8)
    return {
        "schema_version": 1,
        "observed_date_australia_sydney": "2026-10-21",
        "target_cli": "2.1.304",
        "host_profile": "Raspberry Pi 5, Linux ARM64, native authenticated CLI --print stream-json",
        "actual_model_identified_by_native_wire": "claude-sonnet-5-5",
        "official_native_binary_sha256": OFFICIAL_NATIVE_SHA,
        "official_release_archive_sha256": OFFICIAL_ASSET_SHA,
        "audit_script_sha256": digest(Path(__file__)),
        "tested_source_sha256": EXPECTED_SOURCES,
        "runs": {name: data[name][0] for name in RUNS},
        "total_reported_model_cost_usd": costs,
        "observations": {
            "K-0070": {"actual_ask_to_person_unattended_denied": True, "target_write_absent": True, "interactive_human_approval_tested": False},
            "K-0071": {"real_host_read_isReadOnly_true": True, "full_readonly_classification_matrix_tested": False},
            "K-0072": {"real_two_plugin_short_circuit": True, "real_two_plugin_passthrough_control": True, "user_visible_skipped_hook_transcript_proven": False},
            "K-0073": {"old_command_name_still_callable": True, "reload_ack_despite_parse_error": True, "previous_hook_module_unloaded": True, "new_command_content_active_after_failed_reload": True, "previous_benign_guard_denied_before_reload": True, "previous_benign_guard_lost_after_reload": True, "old_version_security_hook_preserved": False, "target_profile_pass": False},
            "K-0074": {"native_actual_tool_check_exception_caught_and_denied": True, "all_host_security_precedence_tested": False},
        },
        "privacy": {"private_prompts_wire_debug_and_account_data_excluded": True, "raw_logs_remain_on_source_host": True, "actual_write_tools_executed": False},
        "release": {"new_cli304_claims_approved": 0, "all_p1_host_semantics_verified": False, "cli304_skill_deployment_authorized": False, "stable_release_authorized": False},
        "qualifications": "Single authenticated Linux ARM64 --restricted --print profile; synthetic native tests are separate; no UI-visible skip transcript, real human approval, managed-policy matrix or cross-host coverage. Do not promote Claims based on this partial, adverse result.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--official-binary", type=Path, required=True)
    parser.add_argument("--official-archive", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists() or args.out.is_symlink():
        raise SystemExit("REFUSED: immutable redacted evidence output already exists")
    try:
        data = audit(args.private_root, args.official_binary, args.official_archive)
    except (IncompleteHostEvidence, OSError, TypeError, KeyError, ValueError) as exc:
        raise SystemExit(f"BLOCKED: real-host evidence incomplete ({type(exc).__name__})") from None
    args.out.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "actual_host_runs_verified": len(data["runs"]),
        "K0070_unattended": True, "K0071_isReadOnly": True,
        "K0072_transcript": False, "K0073_guard_preserved": False,
        "K0074_catch_denial": True, "stable_authorized": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
