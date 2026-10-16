"""Detection of repeated native read calls, not fabricated failure attribution."""

from __future__ import annotations

import json

import pytest

from mods_knowledge.pi_loop_evidence import (
    NativeRepeatGuard,
    PiLoopEvidenceError,
    summarize_pi_loop_trace,
)


def start(path: str, *, offset: int | None = None, tid: str = "a") -> dict:
    args: dict = {"path": path}
    if offset is not None:
        args["offset"] = offset
    return {
        "type": "tool_execution_start",
        "toolName": "read",
        "toolCallId": tid,
        "args": args,
    }


def test_repeated_native_identical_read_triggers_without_exposing_path() -> None:
    events = []
    private = "/secret/private/test/overloads.ts"
    for i in range(18):
        events += [
            start(private, tid=str(i)),
            {
                "type": "tool_execution_end",
                "toolName": "read",
                "toolCallId": str(i),
                "isError": False,
            },
        ]
    result = summarize_pi_loop_trace(events)
    assert result["tool_call_count"] == 18
    assert result["max_identical_invocation_count"] == 18
    assert result["longest_adjacent_identical_run"] == 18
    assert result["native_tool_loop_suspected"]
    assert result["tool_error_count"] == 0
    assert result["tool_execution_balanced"]
    assert private not in json.dumps(result)
    guard = NativeRepeatGuard()
    detected = [guard.observe(e) for e in events]
    assert next(i for i, reason in enumerate(detected) if reason) == 10


def test_offset_changes_are_not_mistaken_for_repeated_read() -> None:
    events = [start("/isolated-workspace/private/file.ts", offset=i, tid=str(i)) for i in range(10)]
    result = summarize_pi_loop_trace(events)
    assert result["longest_adjacent_identical_run"] == 1
    assert not result["native_tool_loop_suspected"]


def test_unrelated_errors_not_equivalent_to_false_skill_activation() -> None:
    records = [
        start("/different/path", tid="one"),
        {
            "type": "tool_execution_end",
            "toolName": "read",
            "toolCallId": "one",
            "isError": True,
        },
    ]
    result = summarize_pi_loop_trace(records)
    assert result["tool_error_count"] == 1
    assert result["native_tool_loop_suspected"] is False
    assert result["semantic_correctness_verified"] is False


def test_input_validation_and_unbounded_guards() -> None:
    with pytest.raises(PiLoopEvidenceError):
        NativeRepeatGuard(repeat_limit=1)
    with pytest.raises(PiLoopEvidenceError):
        summarize_pi_loop_trace([{}] * 100001)
    with pytest.raises(PiLoopEvidenceError):
        summarize_pi_loop_trace([{"type": "x"}, "secret"])
