#!/usr/bin/env python3
"""Re-audit genuine 2.1.309 /verify and /code-review across a shell-side edit.

Only read original private native JSONL/debug and a dedicated throwaway Git
repository. Public report contains bounded SHA256/source/result summaries,
never original prompts, model text, account/session identifiers, or host paths.
Crucially, dynamic discovery, direct SKILL.md reads, and real Skill tool
invocations are separate evidence classes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

BINARY_SHA = "9796dd26899337f687739a0b39a7353b639f062a3436a7b941fcf19a1b757a9b"
FIXTURE_HASHES = {
    "repo/README.md": "0e8eaeb9ffccc8cf4fb9901d70bd2428ec4d64b3d10a4c34a5d93ceb5356426d",
    "repo/packages/widget/index.js": "5b63136552577a64d788dc3cd4552739d0d60f9e1adb63ec4dfb6932d56fc75d",
    "repo/packages/widget/.claude/skills/mods-qa-widget-check/SKILL.md": "b658192da1377c1402fa74a1625529c80fef23616a747f245213e963e0285715",
    "shell-modified.index.js": "45a5b1828e8c9b67b3ce34c46d17386691f3a69f3dd938bb2b78140a6e68736a",
}
MARKER = "WIDGET_AUDIT_RECIPE_BRINE_63821"
SKILL = "mods-qa-widget-check"
EXPECTED_TOOL_NAMES = {
    "rpi-a": {
        "initial": [],
        "verify": ["Bash", "Skill", "Bash", "Bash"],
        "code-review": ["Bash", "Read"],
    },
    "rpi-b": {
        "initial": [],
        "verify": ["Bash", "Bash", "Bash"],
        "code-review": ["Bash"],
    },
}
MAX_WIRE = 5_000_000
MAX_DEBUG = 8_000_000


class BundledNativeInvalid(ValueError):
    """Missing or contradictory original target-host evidence."""


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise BundledNativeInvalid(reason)


def sha(path: Path, *, max_bytes: int = MAX_WIRE) -> str:
    require(
        path.is_file() and not path.is_symlink() and 0 <= path.stat().st_size <= max_bytes,
        "MISSING_OR_OVERLARGE_ORIGINAL_EVIDENCE",
    )
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _git_capture(repo: Path, *args: str) -> str:
    p = subprocess.run(  # noqa: S603 - only fixed git inspection in private scratch repo
        ["/usr/bin/git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        timeout=9,
        check=False,
    )
    require(p.returncode == 0, "ORIGINAL_SCRATCH_GIT_HISTORY_MISSING")
    return p.stdout


def _tool_events(e: dict) -> list[dict]:
    if e.get("type") != "assistant":
        return []
    return [
        content
        for content in (e.get("message") or {}).get("content", [])
        if isinstance(content, dict) and content.get("type") == "tool_use"
    ]


def _actual_tools(group: list[dict]) -> list[dict]:
    return [tool for event in group for tool in _tool_events(event)]


def _test_results(events: list[dict]) -> tuple[list[list[dict]], list[dict]]:
    groups = [[], [], []]
    results = []
    slot = 0
    for e in events:
        if e.get("type") == "result":
            require(slot < 3, "EXTRA_NATIVE_QA_TURN")
            results.append(e)
            slot += 1
        else:
            require(slot < 3, "EVENTS_AFTER_FINAL_NATIVE_RESULT")
            groups[slot].append(e)
    require(slot == 3, "MISSING_NATIVE_BUNDLED_COMMAND_TURNS")
    return groups, results


def audit(root: Path, fixture: Path, binary: Path, *, host: str) -> dict:
    require(host in EXPECTED_TOOL_NAMES, "UNKNOWN_NATIVE_QA_HOST")
    require(root.is_dir() and not root.is_symlink(), "MISSING_ORIGINAL_QA_ROOT")
    require(fixture.is_dir() and not fixture.is_symlink(), "MISSING_FIXED_QA_SOURCE")
    require(sha(binary, max_bytes=350_000_000) == BINARY_SHA, "UNVERIFIED_OFFICIAL_CLAUDE309")
    for name, expected in FIXTURE_HASHES.items():
        require(sha(fixture / name) == expected, "REVIEWED_FIXTURE_HAS_CHANGED")
    repo = root / "repo-stream"
    require(repo.is_dir() and (repo / ".git").is_dir(), "MISSING_SHELL_MODIFIED_SCRATCH_GIT")
    require(
        sha(repo / "README.md") == FIXTURE_HASHES["repo/README.md"]
        and sha(repo / "packages/widget/.claude/skills/mods-qa-widget-check/SKILL.md")
        == FIXTURE_HASHES["repo/packages/widget/.claude/skills/mods-qa-widget-check/SKILL.md"]
        and sha(repo / "packages/widget/index.js") == FIXTURE_HASHES["shell-modified.index.js"],
        "MISSING_ACTUAL_CHANGED_NESTED_PACKAGE",
    )
    baseline = _git_capture(repo, "show", "HEAD:packages/widget/index.js")
    require(
        hashlib.sha256(baseline.encode()).hexdigest()
        == FIXTURE_HASHES["repo/packages/widget/index.js"],
        "SHELL_QA_BASELINE_NOT_ORIGINAL",
    )
    require(
        _git_capture(repo, "status", "--porcelain=v1").strip() == "M packages/widget/index.js",
        "OUT_OF_SCOPE_QA_REPO_MODIFICATIONS",
    )
    directory = root / "private/stream"
    wire = directory / "native-wire.private.jsonl"
    debug = directory / "debug.private.log"
    stderr = directory / "stderr.private.log"
    require(sha(stderr) == hashlib.sha256(b"").hexdigest(), "NATIVE_QA_STDERR_NOT_EMPTY")
    try:
        events = [json.loads(row) for row in wire.read_text().splitlines() if row.strip()]
    except (UnicodeError, ValueError) as exc:
        raise BundledNativeInvalid("INVALID_ORIGINAL_MODEL_JSONL") from exc
    require(bool(events) and all(isinstance(r, dict) for r in events), "EMPTY_MODEL_STREAM")
    IDs = {e["session_id"] for e in events if isinstance(e.get("session_id"), str)}
    require(len(IDs) == 1, "BUNDLED_RUN_NOT_SAME_NATIVE_SESSION")
    init = [e for e in events if e.get("type") == "system" and e.get("subtype") == "init"]
    require(
        len(init) == 3 and all(e.get("claude_code_version") == "2.1.309" for e in init),
        "NOT_ORIGINAL_CLAUDE309_TURNS",
    )
    models = {(e.get("message") or {}).get("model") for e in events if e.get("type") == "assistant"}
    # Bundled slash workflows may insert synthetic assistant events beside
    # actual authenticated Sonnet turns. Keep the distinction explicit.
    require(
        "claude-sonnet-5-5" in models and models <= {"claude-sonnet-5-5", "<synthetic>"},
        "WRONG_OR_MISSING_AUTHENTICATED_MODEL",
    )
    groups, results = _test_results(events)
    require(
        all(r.get("subtype") == "success" and r.get("is_error") is False for r in results),
        "HOST_RESULT_INCOMPLETE",
    )
    require(
        str(results[0].get("result", "")).strip() == "QA_ROOT_ONLY"
        and _actual_tools(groups[0]) == [],
        "INITIAL_QA_TURN_WAS_NOT_HARMLESS",
    )
    verify_tools = _actual_tools(groups[1])
    review_tools = _actual_tools(groups[2])
    require(
        [t.get("name") for t in verify_tools] == EXPECTED_TOOL_NAMES[host]["verify"]
        and [t.get("name") for t in review_tools] == EXPECTED_TOOL_NAMES[host]["code-review"],
        "REAL_HOST_TOOL_INVOCATIONS_DIFFER_FROM_REVIEWED_TRACE",
    )
    nested_calls = [
        (t.get("input") or {}).get("skill") for t in verify_tools if t.get("name") == "Skill"
    ]
    require(
        nested_calls == ([SKILL] if host == "rpi-a" else []),
        "FALSE_NATIVE_SKILL_TOOL_ASSERTION",
    )
    verify_output = str(results[1].get("result", ""))
    require(
        re.search(r"off.by.one|a \+ b \+ 1|breaks the invariant", verify_output, re.I) is not None,
        "VERIFY_DID_NOT_RECOGNIZE_CONTROLLED_CALCULATION_REGRESSION",
    )
    # The deliberately denied Node execution is a negative control: never
    # declare runtime verification successful from a diff-only answer.
    node_attempts = [
        t
        for t in verify_tools
        if t.get("name") == "Bash" and "node " in str((t.get("input") or {}).get("command", ""))
    ]
    require(node_attempts, "NO_ACTUAL_ATTEMPT_TO_EXECUTE_NATIVE_APP")
    verify_tool_results = [
        b
        for e in groups[1]
        if e.get("type") == "user"
        for b in (e.get("message") or {}).get("content", [])
        if isinstance(b, dict) and b.get("type") == "tool_result"
    ]
    require(
        any(b.get("is_error") is True for b in verify_tool_results),
        "NATIVE_TEST_EXECUTION_WAS_NOT_DENIED",
    )
    dbg = debug.read_text(errors="replace")
    require(
        "[skills] Dynamically discovered 1 skills from 1 directories" in dbg,
        "NATIVE_NESTED_SKILL_DISCOVERY_MISSING",
    )
    if host == "rpi-a":
        require(
            MARKER in verify_output and nested_calls == [SKILL],
            "PI_BUNDLED_VERIFY_DID_NOT_INVOKE_NESTED_SKILL",
        )
        require(
            any(t.get("name") == "Read" for t in review_tools)
            and re.search(r"off.by.one|a \+ b \+ 1", str(results[2].get("result", "")), re.I),
            "PI_BUNDLED_CODE_REVIEW_NO_VALID_FINDING",
        )
        code_review_status = "partial_read_fallback_found_correct_regression"
    else:
        require(
            MARKER not in verify_output
            and any(
                "cat packages/widget/.claude/skills/mods-qa-widget-check/SKILL.md"
                in str((t.get("input") or {}).get("command", ""))
                for t in verify_tools
            ),
            "SEXTANT_READ_RECIPE_MUST_NOT_COUNT_AS_SKILL_TOOL",
        )
        require(
            "denied" in str(results[2].get("result", "")).lower()
            and not any(t.get("name") == "Read" for t in review_tools),
            "SEXTANT_REVIEW_PERMISSION_BLOCK_NOT_RECORDED",
        )
        code_review_status = "read_only_git_diff_permission_blocked"
    return {
        "schema_version": 1,
        "host": host,
        "original_target_native": "2.1.309",
        "original_native_binary_sha256": BINARY_SHA,
        "original_official_asset_sha256": "8ecd1f2d06ccbd3f89c8886e840e42b57a19063f3de9cfe5f7d90fe875ba99ef",
        "auditor_source_sha256": sha(Path(__file__)),
        "fixture_sha256": FIXTURE_HASHES,
        "preexisting_git_baseline_verified": True,
        "shell_side_changed_file_sha256": sha(repo / "packages/widget/index.js"),
        "shell_change_only_one_nested_file": True,
        "one_continuing_native_session": True,
        "three_actual_model_results": len(results),
        "actual_models": ["claude-sonnet-5-5"],
        "original_wire_sha256": sha(wire),
        "original_debug_sha256": sha(debug, max_bytes=MAX_DEBUG),
        "native_dynamic_nested_skill_discovery_logged": True,
        "verify_uses": [t.get("name") for t in verify_tools],
        "verify_actual_skill_tool_targets": nested_calls,
        "verify_detected_off_by_one": True,
        "verify_runtime_execution_blocked": True,
        "verify_full_runtime_pass": False,
        "verify_used_natively_invoked_nested_skill": host == "rpi-a",
        "verify_only_read_nested_skill_source": host == "rpi-b",
        "code_review_uses": [t.get("name") for t in review_tools],
        "code_review_native_skill_tool_invoked": False,
        "code_review_status": code_review_status,
        "no_unrelated_production_code_or_skills_changed": True,
        "complete_mods_ssot_model_answer_quality_pass": False,
        "full_bundled_verify_and_review_skill_invocation_across_hosts_pass": False,
        "new_309_claims_approved": 0,
        "stable_release_authorized": False,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--private-root", type=Path, required=True)
    p.add_argument("--fixture", type=Path, required=True)
    p.add_argument("--native-binary", type=Path, required=True)
    p.add_argument("--host", choices=("rpi-a", "rpi-b"), required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    if args.out.exists() or args.out.is_symlink():
        raise SystemExit("REFUSED: immutable original host evidence output already exists")
    try:
        result = audit(args.private_root, args.fixture, args.native_binary, host=args.host)
    except (BundledNativeInvalid, ValueError, OSError, KeyError, TypeError):
        raise SystemExit("BLOCKED: original native bundled Skill evidence incomplete") from None
    args.out.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(
        json.dumps(
            {
                "host": args.host,
                "original_native_bundled_turns": 3,
                "full_skill_invocation": False,
                "stable": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
