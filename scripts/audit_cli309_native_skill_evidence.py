#!/usr/bin/env python3
"""Audit actual Claude Code 2.1.309 Skill tool calls from private native JSONL.

No private model text, account paths, session identifiers or credentials are
written into Git. This separates genuine native Skill tool invocations from
model guesses and from reading SKILL.md as an ordinary file.

This only proves bounded QA fixtures, not complete production Mods Skill
semantic correctness, ChatGPT Chat Mode behavior, or /verify built-in flows.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

EXPECTED_CLI_SHA = "9796dd26899337f687739a0b39a7353b639f062a3436a7b941fcf19a1b757a9b"
EXPECTED_ASSET_SHA = "8ecd1f2d06ccbd3f89c8886e840e42b57a19063f3de9cfe5f7d90fe875ba99ef"
EXPECTED_FIXTURES = {
    "project/.claude/skills/mods-qa-route/SKILL.md": "da3c5a2e6e550fd400ba53471ec6efdf702eccadec6bd1be4548fa5db3983f46",
    "addons/.claude/skills/mods-qa-route/SKILL.md": "5ffbf91686e30582f5cb068445cc6edb939054394219d728db4b308b7382d1d2",
    "project/packages/widget/.claude/skills/mods-qa-nested/SKILL.md": "6b0f1e0a5b3c245f705ec39f24f9cf867e7b7f7a43c56179ca8813707865277c",
    "project/packages/widget/README.md": "3504016b9439979c72e6213e5cfdb987d692bdaa8f5512c2e7940a501e80ca7f",
    "qa-mod-alias/.claude-plugin/plugin.json": "ff5d54e409b7e50e731005801ebdf0ead7ff85dc8385ca23f06322b6d83bead7",
    "qa-mod-alias/hooks/hooks.json": "f3d7fbcdc0577a6630103faeed14a6c49691f04ced58b6dc466843712d592d47",
    "qa-mod-alias/hooks/register.js": "fff5a2ff0299b0eaf2230e8e695afe5d8bc7701c438a1bcd58736778f627178b",
}
SKILL_SCENARIOS = {
    "unrestricted": ("mods-qa-route", "PROJECT_ROOT_LARCH_82736"),
    "add-dir-qualified": ("addons:mods-qa-route", "ADDITIONAL_DIR_WREN_58241"),
    "nested-cwd": ("mods-qa-nested", "NESTED_WIDGET_TERN_16739"),
    "automatic-project": ("mods-qa-route", "PROJECT_ROOT_LARCH_82736"),
    "automatic-addons": ("addons:mods-qa-route", "ADDITIONAL_DIR_WREN_58241"),
}
SEXTANT_SCENARIOS = {
    "s-root": ("mods-qa-route", "PROJECT_ROOT_LARCH_82736"),
    "s-addons": ("addons:mods-qa-route", "ADDITIONAL_DIR_WREN_58241"),
    "s-nested": ("mods-qa-nested", "NESTED_WIDGET_TERN_16739"),
}
ALL_MARKERS = {
    "PROJECT_ROOT_LARCH_82736",
    "ADDITIONAL_DIR_WREN_58241",
    "NESTED_WIDGET_TERN_16739",
}
MAX_WIRE = 5_000_000
MAX_DEBUG = 10_000_000


class SkillEvidenceBlocked(ValueError):
    """Incomplete or contradictory original official target-host evidence."""


def require(value: bool, why: str) -> None:
    if not value:
        raise SkillEvidenceBlocked(why)


def sha(file: Path, maximum: int = MAX_WIRE) -> str:
    require(file.is_file() and not file.is_symlink(), "MISSING_OR_UNSAFE_PRIVATE_EVIDENCE")
    require(0 <= file.stat().st_size <= maximum, "OVERSIZE_PRIVATE_EVIDENCE")
    with file.open("rb") as original:
        return hashlib.file_digest(original, "sha256").hexdigest()


def event_rows(run_dir: Path, case: str) -> tuple[dict, list[dict], list[dict], list[dict], str]:
    wire = run_dir / f"{case}-wire.private.jsonl"
    debug = run_dir / f"{case}-debug.private.log"
    stderr = run_dir / f"{case}-stderr.private.log"
    require(stderr.stat().st_size == 0, "PRIVATE_NATIVE_STDERR_NOT_EMPTY")
    raw = wire.read_text()
    try:
        events = [json.loads(line) for line in raw.splitlines() if line.strip()]
    except ValueError as exc:
        raise SkillEvidenceBlocked("INVALID_NATIVE_JSONL") from exc
    require(events and all(isinstance(e, dict) for e in events), "EMPTY_NATIVE_TRACE")
    initial = [e for e in events if e.get("type") == "system" and e.get("subtype") == "init"]
    require(
        initial and all(e.get("claude_code_version") == "2.1.309" for e in initial),
        "UNEXPECTED_NATIVE_CLAUDE_CLI_VERSION",
    )
    results = [e for e in events if e.get("type") == "result"]
    require(
        results
        and all(e.get("subtype") == "success" and e.get("is_error") is False for e in results),
        "NATIVE_MODEL_RESULT_UNAVAILABLE",
    )
    uses = [
        b
        for e in events
        if e.get("type") == "assistant"
        for b in (e.get("message") or {}).get("content", [])
        if isinstance(b, dict) and b.get("type") == "tool_use"
    ]
    tool_results = [
        b
        for e in events
        if e.get("type") == "user"
        for b in (e.get("message") or {}).get("content", [])
        if isinstance(b, dict) and b.get("type") == "tool_result"
    ]
    model = {
        (e.get("message") or {}).get("model")
        for e in events
        if e.get("type") == "assistant" and (e.get("message") or {}).get("model")
    }
    require(len(model) == 1, "MIXED_OR_MISSING_MODEL_IDENTITY")
    log = debug.read_text(errors="replace")
    summary = {
        "source_private_wire_sha256": sha(wire),
        "source_private_debug_sha256": sha(debug, MAX_DEBUG),
        "actual_assistant_model": next(iter(model)),
        "real_tool_names": [b.get("name") for b in uses],
        "actual_skill_tool_arguments": [
            (b.get("input") or {}).get("skill") for b in uses if b.get("name") == "Skill"
        ],
        "native_result_turns": [r.get("num_turns") for r in results],
        "private_original_events_examined": len(events),
    }
    return summary, results, uses, tool_results, log


def check_skill_case(run_dir: Path, case: str, skill: str, marker: str) -> dict:
    summary, results, tools, _responses, log = event_rows(run_dir, case)
    output = " ".join(str(r.get("result", "")) for r in results)
    require(
        summary["actual_assistant_model"] == "claude-sonnet-5-5"
        and len(results) == 1
        and len(tools) == 1
        and tools[0].get("name") == "Skill"
        and (tools[0].get("input") or {}).get("skill") == skill,
        "NATIVE_SKILL_TOOL_NOT_INVOKED_WITH_CORRECT_SOURCE",
    )
    require(
        marker in output and not any(m in output for m in ALL_MARKERS - {marker}),
        "SKILL_SOURCE_MARKER_WRONG_OR_MIXED",
    )
    require("Loaded " in log and "unique skills" in log, "NATIVE_SKILL_LOADER_NOT_OBSERVED")
    summary.update(
        actual_native_skill_invocation_pass=True,
        source_selected_correctly=True,
        true_skill_tool_use_not_just_model_text=True,
    )
    return summary


def audit(qa: Path, fixture: Path, *, host: str) -> dict:
    require(host in ("rpi-a", "rpi-b"), "INVALID_EXPLICIT_QA_HOST")
    require(qa.is_dir() and not qa.is_symlink(), "MISSING_PRIVATE_NATIVE_QA")
    require(fixture.is_dir() and not fixture.is_symlink(), "MISSING_REVIEWED_QA_FIXTURES")
    native = qa / "extracted/claude"
    require(sha(native, 350_000_000) == EXPECTED_CLI_SHA, "UNPINNED_NATIVE_309_BINARY")
    # This is a separately captured official asset hash. The auditor checks
    # the source archive only when that archive is available in the QA folder.
    tar = qa / "download/claude-linux-arm64.tar.gz"
    if tar.is_file():
        require(sha(tar, 155_000_000) == EXPECTED_ASSET_SHA, "OFFICIAL_ASSET_SHA_CHANGED")
    for path, expected in EXPECTED_FIXTURES.items():
        require(sha(fixture / path) == expected, "REVIEWED_SKILL_FIXTURE_CHANGED")
        require(sha(qa / "work" / path) == expected, "ACTUAL_NATIVE_SKILL_SOURCE_CHANGED")
    runs = qa / "private/runs"
    scenarios = SKILL_SCENARIOS if host == "rpi-a" else SEXTANT_SCENARIOS
    result: dict[str, dict] = {}
    for name, (skill, marker) in scenarios.items():
        result[name] = check_skill_case(runs, name, skill, marker)

    if host == "rpi-a":
        summary, answers, tools, _responses, dbg = event_rows(runs, "nested-dynamic")
        initial_sessions = {
            e.get("session_id")
            for e in [
                json.loads(line)
                for line in (runs / "nested-dynamic-wire.private.jsonl").read_text().splitlines()
                if line.strip()
            ]
            if e.get("session_id")
        }
        require(
            len(initial_sessions) == 1
            and len(answers) == 2
            and [t.get("name") for t in tools] == ["Read", "Skill"]
            and "packages/widget/README.md" in str((tools[0].get("input") or {}).get("file_path"))
            and (tools[1].get("input") or {}).get("skill") == "mods-qa-nested"
            and "NESTED_WIDGET_TERN_16739" in str(answers[1].get("result", ""))
            and "mods-qa-nested" in dbg,
            "NESTED_SKILL_DYNAMIC_DISCOVERY_NOT_REPRODUCED",
        )
        summary.update(
            same_native_session_two_turns=True,
            native_read_then_skill_tool=True,
            nested_skill_marker_correct=True,
            actual_native_skill_invocation_pass=True,
        )
        result["nested-dynamic"] = summary
        arithmetic, answer, tools, _, _ = event_rows(runs, "unrelated-control")
        require(
            len(answer) == 1 and not tools and str(answer[0].get("result", "")).strip() == "12",
            "UNRELATED_PROMPT_SPURIOUS_SKILL_INVOCATION",
        )
        arithmetic.update(
            real_tool_names=[],
            no_unrelated_skill_or_tool_invoked=True,
            unrelated_question_answer_correct=True,
        )
        result["unrelated-control"] = arithmetic
        restricted, answers, tools, responses, log = event_rows(runs, "restricted-natural")
        require(
            bool(re.search(r"Loaded 0 unique skills", log))
            and any(t.get("name") == "Skill" for t in tools)
            and any("Unknown skill" in json.dumps(x) for x in responses),
            "RESTRICTED_MODE_NEGATIVE_CONTROL_NOT_ACTUAL",
        )
        restricted.update(
            native_skill_invocation_failed_unknown_skill=True,
            direct_read_cannot_be_counted_as_skill_invocation=True,
            source_marker_not_sufficient_for_pass=True,
        )
        result["restricted-natural"] = restricted

    alias_name = "alias-native" if host == "rpi-a" else "s-alias"
    validate_name = "alias-validate" if host == "rpi-a" else "s-alias-validate"
    validation = json.loads((runs / f"{validate_name}.private.json").read_text())
    require(validation.get("success") is True, "ORIGINAL_STRICT_PLUGIN_VALIDATION_FAILED")
    alias, answer, tools, _, log = event_rows(runs, alias_name)
    require(
        alias["actual_assistant_model"] == "claude-haiku-5-5"
        and len(answer) == 1
        and "QATESTALIAS" in str(answer[0].get("result", ""))
        and not tools
        and "QA309_TURN_STEP_MODEL_ALIAS_REQUESTED" in log
        and "qa-cli309-model-alias" in log,
        "NATIVE_MOD_TURN_STEP_MODEL_ALIAS_NOT_ACTUALLY_RESOLVED",
    )
    alias.update(
        official_native_plugin_validate_strict=True,
        real_turn_step_hook_executed=True,
        requested_model_alias="haiku",
        actual_model_alias_resolved_to="claude-haiku-5-5",
        real_model_result_without_tools=True,
    )
    result["alias"] = alias

    require(
        all(not (qa / "work" / path).is_symlink() for path in EXPECTED_FIXTURES),
        "QA_SOURCE_SYMLINK_NOT_REVIEWED",
    )
    return {
        "schema": 1,
        "host": host,
        "official_native_cli_version": "2.1.309",
        "official_native_cli_sha256": EXPECTED_CLI_SHA,
        "official_asset_sha256": EXPECTED_ASSET_SHA,
        "fixture_sha256": dict(EXPECTED_FIXTURES),
        "auditor_source_sha256": sha(Path(__file__)),
        "scenarios": result,
        "separate_host_native_QA_evidence": True,
        "actual_sonnet_skill_tool_calls_verified": True,
        "actual_haiku_alias_runtime_verified": True,
        "automatic_selection_prompt_requested_use_of_relevant_skill": True,
        "full_real_mods_ssot_skill_quality_verified": False,
        "built_in_verify_code_review_nested_flow_verified": False,
        "full_chatgpt_chat_mode_plugin_accepted": False,
        "exact_309_claims_approved": 0,
        "new_skill_or_plugin_published": False,
        "production_cli_or_user_skill_modified": False,
        "stable_release_authorized": False,
        "raw_native_session_and_account_data_not_committed": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--reviewed-fixture", type=Path, required=True)
    parser.add_argument("--host", required=True, choices=("rpi-a", "rpi-b"))
    parser.add_argument("--out", type=Path, required=True)
    opts = parser.parse_args()
    if opts.out.exists() or opts.out.is_symlink():
        raise SystemExit("REFUSED: immutable evidence file already exists")
    try:
        report = audit(opts.private_root, opts.reviewed_fixture, host=opts.host)
    except (OSError, ValueError, KeyError, TypeError, SkillEvidenceBlocked):
        raise SystemExit("BLOCKED: actual native Skill QA evidence incomplete") from None
    opts.out.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    print(
        json.dumps(
            {
                "host": opts.host,
                "native_cases": len(report["scenarios"]),
                "complete_product_acceptance": False,
                "stable": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
