#!/usr/bin/env python3
"""Independently audit exact native CLI304 host-level PreToolUse evidence.

The original native wire/debug, session IDs, local configuration and private
enrollment material MUST remain off Git. This replayer publishes only bounded
facts and per-file SHA256; it never certifies unknown/unmanaged Claude hosts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from mods_knowledge.guarded_host_probe import verify_native_qa_probe
from mods_knowledge.guarded_rollout import NATIVE_CLI304_SHA, UpdateBlocked, installed_tree

NATIVE_MODEL = "claude-sonnet-5-5"
SOURCE_FILES = (
    "src/mods_knowledge/guarded_rollout.py",
    "src/mods_knowledge/guarded_host_probe.py",
    "scripts/cli304_host_tool_gate.py",
    "scripts/cli304_host_tool_settings.py",
    "evals/fixtures/cli304-p1d-cohort-20261022/hooks/register.js",
)
RUNS = {
    "unenrolled_refusal": (
        "private/host-ready-wire.private.jsonl",
        "private/host-ready-debug.private.log",
    ),
    "enrolled_read_and_write": (
        "private/host-enrolled-wire.private.jsonl",
        "private/host-enrolled-debug.private.log",
    ),
    "bad_mod_still_denied": (
        "private/host-failed-mod-wire.private.jsonl",
        "private/host-failed-mod-debug.private.log",
    ),
    "broken_hook_no_block": (
        "private/control-no_failure_block-wire.private.jsonl",
        "private/control-no_failure_block-debug.private.log",
    ),
    "broken_hook_block": (
        "private/control-failure_block-wire.private.jsonl",
        "private/control-failure_block-debug.private.log",
    ),
    "same_host_live_freeze": (
        "private/live-freeze-valid-lease/live-wire.private.jsonl",
        "private/live-freeze-valid-lease/live-debug.private.log",
    ),
}


def require(ok: bool, code: str) -> None:
    if not ok:
        raise UpdateBlocked(code)


def read(path: Path, *, max_bytes: int = 4_000_000) -> bytes:
    require(path.is_file() and not path.is_symlink(), "MISSING_REVIEWED_PRIVATE_FILE")
    require(path.stat().st_size <= max_bytes, "OVERSIZE_PRIVATE_EVIDENCE")
    return path.read_bytes()


def sha(path: Path) -> str:
    return hashlib.sha256(read(path)).hexdigest()


def run_events(root: Path, key: str) -> tuple[dict, list[dict], list[dict], list[dict], str]:
    wire_rel, debug_rel = RUNS[key]
    wire_path, debug_path = root / wire_rel, root / debug_rel
    wire = read(wire_path)
    debug = read(debug_path).decode(errors="replace")
    suffix = wire_rel.replace("-wire.private.jsonl", "-stderr.private.log")
    stderr_path = root / suffix
    require(read(stderr_path) == b"", "NONEMPTY_NATIVE_HOST_STDERR")
    try:
        events = [json.loads(line) for line in wire.decode().splitlines() if line.strip()]
    except (UnicodeError, ValueError) as exc:
        raise UpdateBlocked("INVALID_PRIVATE_NATIVE_EVENTS") from exc
    require(bool(events) and all(isinstance(x, dict) for x in events), "EMPTY_NATIVE_EVENTS")
    init = [x for x in events if x.get("type") == "system" and x.get("subtype") == "init"]
    require(
        bool(init)
        and all(
            isinstance(x.get("claude_code_version"), str)
            and x["claude_code_version"].startswith("2.1.304")
            for x in init
        ),
        "WRONG_NATIVE_CLI_TARGET",
    )
    results = [x for x in events if x.get("type") == "result"]
    require(
        results
        and all(x.get("subtype") == "success" and x.get("is_error") is False for x in results),
        "INCOMPLETE_MODEL_RESULTS",
    )
    models = {(x.get("message") or {}).get("model") for x in events if x.get("type") == "assistant"}
    require(NATIVE_MODEL in models, "ACTUAL_AUTHENTICATED_SONNET_MISSING")
    uses = [
        entry.get("name")
        for x in events
        if x.get("type") == "assistant"
        for entry in (x.get("message") or {}).get("content", [])
        if isinstance(entry, dict) and entry.get("type") == "tool_use"
    ]
    responses = [
        entry
        for x in events
        if x.get("type") == "user"
        for entry in (x.get("message") or {}).get("content", [])
        if isinstance(entry, dict) and entry.get("type") == "tool_result"
    ]
    info = {
        "native_wire_sha256": hashlib.sha256(wire).hexdigest(),
        "native_debug_sha256": hashlib.sha256(read(debug_path)).hexdigest(),
        "native_tool_names": uses,
        "tool_result_count": len(responses),
        "native_result_turn_counts": [x.get("num_turns") for x in results],
        "actual_sonnet_model_seen": True,
    }
    return info, results, responses, events, debug


def has_data(response: dict) -> bool:
    return "QA_HOST_READ_OK_20261022" in json.dumps(response)


def denied(response: dict) -> bool:
    return response.get("is_error") is True and "HOST_GATE_REFUSED" in json.dumps(response)


def verify_bootstrap(root: Path, folder: str, tree: str) -> str:
    base = root / folder
    manifest = json.loads(
        read(
            base
            / (
                "host-proof.private.json"
                if folder.endswith("bootstrap")
                else "bootstrap-proof.private.json"
            )
        )
    )
    wire_path = base / (
        "wire.private.jsonl" if folder.endswith("bootstrap") else "bootstrap-wire.private.jsonl"
    )
    debug_path = base / (
        "debug.private.log" if folder.endswith("bootstrap") else "bootstrap-debug.private.log"
    )
    events = [json.loads(x) for x in read(wire_path).decode().splitlines() if x.strip()]
    results = [x for x in events if x.get("type") == "result"]
    require(len(results) == 1 and results[0].get("num_turns") == 0, "BOOTSTRAP_HOST_PROBE_NOT_SAFE")
    m = re.search(r"P1D_GUARD_DENIED_([0-9a-f]{40})", str(results[0].get("result", "")))
    require(m is not None, "BOOTSTRAP_NONCE_MISSING")
    require(manifest["tree_sha"] == tree and manifest["epoch"] == 0, "BOOTSTRAP_WRONG_VERSION")
    # The manifest original absolute pointers refer to the disposable /tmp
    # copy. Rebind to the preserved matching original file bytes.
    from tempfile import TemporaryDirectory

    with TemporaryDirectory() as tmp:
        proof = Path(tmp) / "manifest.json"
        proof.write_text(
            json.dumps(
                {
                    "schema": 1,
                    "session_id": manifest["session_id"],
                    "epoch": 0,
                    "tree_sha": tree,
                    "wire": str(wire_path.resolve()),
                    "debug": str(debug_path.resolve()),
                }
            )
        )
        return verify_native_qa_probe(proof, manifest["session_id"], m.group(1), tree, 0)


def audit(root: Path, binary: Path) -> dict:
    require(binary.is_file() and not binary.is_symlink(), "OFFICIAL_BINARY_MISSING")
    with binary.open("rb") as stream:
        native_digest = hashlib.file_digest(stream, "sha256").hexdigest()
    require(native_digest == NATIVE_CLI304_SHA, "OFFICIAL_NATIVE_BINARY_MISMATCH")
    source_hashes = {name: sha(root / name) for name in SOURCE_FILES}
    fixture = root / "evals/fixtures/cli304-p1d-cohort-20261022"
    fixture_tree = installed_tree(fixture)
    require(fixture_tree["name"] == "qa-cohort304-host", "WRONG_PRIVATE_PROBE_MOD")
    settings = json.loads(read(root / "private/host-settings.json"))
    for event in ("PreToolUse", "PostToolUse", "PostToolUseFailure"):
        sections = settings["hooks"][event]
        require(
            len(sections) == 1 and sections[0]["matcher"] == "", "HOST_HOOK_COVERAGE_INCOMPLETE"
        )
        hook = sections[0]["hooks"][0]
        require(
            hook["type"] == "command"
            and hook["onFailure"] == "block"
            and hook["timeout"] == 12
            and hook["args"][0].endswith("cli304_host_tool_gate.py")
            and "--state-root" in hook["args"]
            and "--secret-file" in hook["args"],
            "HOST_POLICY_NOT_FAIL_CLOSED",
        )
    ctrl_no = json.loads(read(root / "private/control-no_failure_block.private.json"))
    ctrl_yes = json.loads(read(root / "private/control-failure_block.private.json"))
    hook_off = ctrl_no["hooks"]["PreToolUse"][0]["hooks"][0]
    hook_on = ctrl_yes["hooks"]["PreToolUse"][0]["hooks"][0]
    require("onFailure" not in hook_off, "CONTROL_MUST_BE_UNGUARDED")
    require(hook_on["onFailure"] == "block", "CONTROL_MUST_BE_GUARDED")
    require(
        hook_off["command"] == hook_on["command"]
        and "definitely-missing-hook-executable" in hook_on["command"],
        "NOT_A_MATCHED_MISSING_EXECUTABLE_CONTROL",
    )
    raw = {name: run_events(root, name) for name in RUNS}
    (enrol, enrol_results, enrol_responses, _, _) = raw["enrolled_read_and_write"]
    (unknown, unknown_results, unknown_responses, _, _) = raw["unenrolled_refusal"]
    (modloss, mod_results, mod_responses, _, mod_debug) = raw["bad_mod_still_denied"]
    (no_block, _, no_block_responses, _, _) = raw["broken_hook_no_block"]
    (yes_block, _, yes_block_responses, _, _) = raw["broken_hook_block"]
    (freeze, freeze_results, freeze_responses, freeze_events, _) = raw["same_host_live_freeze"]
    require(enrol["native_tool_names"] == ["Read", "Write"], "ENROLLED_TOOLS_NOT_CALLED")
    require(
        len(enrol_responses) == 2 and has_data(enrol_responses[0]) and denied(enrol_responses[1]),
        "ENROLLED_READ_OR_WRITE_POLICY_FAILED",
    )
    require(
        unknown["native_tool_names"] == ["Read", "Write"]
        and len(unknown_responses) == 2
        and all(denied(x) for x in unknown_responses),
        "UNKNOWN_SESSION_WAS_NOT_DENIED",
    )
    require(
        modloss["native_tool_names"] == ["Write", "Write"]
        and len(mod_responses) == 2
        and all(denied(x) for x in mod_responses)
        and any("Reloaded:" in str(x.get("result")) for x in mod_results)
        and "does not parse:" in mod_debug
        and "the version loaded before is unloaded" in mod_debug,
        "BAD_MOD_REMOVED_NATIVE_HOST_PROTECTION",
    )
    require(
        no_block["native_tool_names"] == ["Read"]
        and len(no_block_responses) == 1
        and has_data(no_block_responses[0])
        and yes_block["native_tool_names"] == ["Read"]
        and len(yes_block_responses) == 1
        and yes_block_responses[0].get("is_error") is True
        and not has_data(yes_block_responses[0]),
        "MISSING_HOOK_MATCHED_FAILURE_BLOCK_CONTROL_FAILED",
    )
    require(
        freeze["native_tool_names"] == ["Read", "Read"]
        and len(freeze_responses) == 2
        and has_data(freeze_responses[0])
        and denied(freeze_responses[1])
        and len(freeze_results) == 2,
        "TRUE_LIVE_SAME_HOST_FREEZE_NOT_DEMONSTRATED",
    )
    ids = {x.get("session_id") for x in freeze_events if x.get("session_id")}
    require(len(ids) == 1, "NOT_SAME_NATIVE_PROCESS_SESSION")
    state = json.loads(read(root / "private/live-freeze-valid-lease/gate/state.json"))
    require(state["phase"] == "blocked", "FINAL_HOST_GATE_NOT_BLOCKED")
    require(
        sum(len(x["permits"]) for x in state["sessions"].values()) == 0
        and sum(len(x.get("native_tools", {})) for x in state["sessions"].values()) == 0,
        "LEAKED_NATIVE_TOOL_PERMIT",
    )
    require(
        not (root / "work/qa-write-should-stay-absent.txt").exists()
        and not (root / "work/qa-should-never-write-after-reload.txt").exists(),
        "HOST_PROTECTED_WRITE_FILE_EXISTED",
    )
    boot1 = verify_bootstrap(root, "private/bootstrap", fixture_tree["sha"])
    boot2 = verify_bootstrap(root, "private/live-freeze-valid-lease", fixture_tree["sha"])
    return {
        "schema_version": 1,
        "target_cli": "2.1.304",
        "official_native_binary_sha256": native_digest,
        "auditor_source_sha256": sha(Path(__file__)),
        "reviewed_host_sources_sha256": source_hashes,
        "reviewed_qa_mod_tree_sha256": fixture_tree["sha"],
        "settings_sha256": sha(root / "private/host-settings.json"),
        "native_proofs_sha256": [boot1, boot2],
        "native_runs": {key: value[0] for key, value in raw.items()},
        "observations": {
            "unregistered_native_session_refused_read_and_write": True,
            "enrolled_native_session_read_allowed_write_denied": True,
            "successful_read_released_held_native_permit": True,
            "malformed_reloadable_mod_lost_guard_but_external_settings_write_denied": True,
            "missing_policy_executable_fails_open_without_onFailure_block": True,
            "same_missing_executable_blocks_with_onFailure_block": True,
            "one_continuing_host_read_allowed_then_blocked_after_quiescence": True,
            "no_qa_write_targets_created": True,
        },
        "scope_limits": {
            "only_explicitly_launched_enrolled_host_sessions": True,
            "external_settings_are_not_organization_managed_policy": True,
            "unregistered_native_sessions_not_globally_controlled": True,
            "tools_except_qa_workspace_read_are_denied_not_live_qualified": True,
            "other_machine_session_coverage_not_proven": True,
            "private_wire_session_tokens_and_debug_excluded_from_git": True,
        },
        "new_cli304_claims_approved": 0,
        "production_wide_host_protection_proven": False,
        "stable_release_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--official-binary", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    options = parser.parse_args()
    if options.out.exists() or options.out.is_symlink():
        raise SystemExit("REFUSED: immutable public native evidence output exists")
    try:
        evidence = audit(options.private_root, options.official_binary)
    except (UpdateBlocked, ValueError, OSError, KeyError, TypeError):
        raise SystemExit("BLOCKED: private native host ToolUse evidence invalid") from None
    options.out.write_text(json.dumps(evidence, sort_keys=True, indent=2) + "\n")
    print(
        json.dumps(
            {
                "actual_native_scenarios": len(RUNS),
                "real_host_bootstrap_proofs": 2,
                "outside_managed_sessions_proven": False,
                "stable": False,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
