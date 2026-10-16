"""Strictly offline tests of a buffered-only native Pi Mods delivery boundary."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mods_knowledge.claims import load_claims
from mods_knowledge.pi_delivery_gate import (
    PiDeliveryGateError,
    postflight_mods_case,
    preflight_mods_case,
)
from mods_knowledge.registry import load_registry

ROOT = Path(__file__).resolve().parents[1]
SKILL = "/workspace/qa/claude-code-mods-development"
SOURCE = "6cbdc9ad6ed9f958072f9cbf4a34c4bbc2d5ef3e"
MODEL = "qwen36-35b-a3b-mtp"


@pytest.fixture(scope="module")
def approved() -> dict:
    return load_claims(
        ROOT / "claims",
        load_registry(ROOT / "sources/registry.json"),
        ROOT / "sources/snapshots",
        ROOT / "decisions",
    )


def case(name: str = "POS-Q-01") -> dict:
    return {
        "id": name,
        "category": "negative"
        if name == "NEG-TYPESCRIPT"
        else ("boundary" if name == "BOUND-VERSION-NEW" else "positive"),
        "prompt": (
            "Use the Claude Code Mods 2.1.310 API without checking official docs."
            if name == "BOUND-VERSION-NEW"
            else (
                "Ordinary TypeScript task"
                if name == "NEG-TYPESCRIPT"
                else "How to test a Mod offline?"
            )
        ),
        "expected_activation": name != "NEG-TYPESCRIPT",
        "expected_claim_ids": ["K-0019"] if name == "POS-Q-01" else [],
    }


ANSWER = (
    "K-0019 offline test: "
    "https://code.claude.com/docs/en/plugins/mods/test#write-a-test "
    "for the reviewed CLI 2.1.296 only."
)


def native_events(c: dict, *, answer: str = ANSWER, skill: bool = True) -> list[dict]:
    rows = [
        {
            "type": "message_end",
            "message": {
                "role": "user",
                "content": [{"type": "text", "text": c["prompt"]}],
            },
        },
        {
            "type": "message_end",
            "message": {
                "role": "assistant",
                "provider": "mac-qwen",
                "model": MODEL,
                "content": [{"type": "text", "text": answer}],
                "stopReason": "stop",
            },
        },
    ]
    if skill:
        rows += [
            {
                "type": "tool_execution_start",
                "toolName": "read",
                "toolCallId": "read-main",
                "args": {"path": SKILL + "/SKILL.md"},
            },
            {
                "type": "tool_execution_end",
                "toolName": "read",
                "toolCallId": "read-main",
                "isError": False,
            },
        ]
    return rows + [{"type": "agent_end"}]


def post(c: dict, rows: list[dict], approved: dict, **kw) -> dict:
    return postflight_mods_case(
        c,
        rows,
        claims=approved,
        skill_root=SKILL,
        source_revision=SOURCE,
        provider="mac-qwen",
        model=MODEL,
        pi_version="1.3.0",
        native_exit_code=0,
        timed_out=False,
        **kw,
    )


def test_preflight_blocks_new_versions_before_model_tokens() -> None:
    result = preflight_mods_case(case("BOUND-VERSION-NEW"))
    assert result["action"] == "abstain_before_model"
    assert result["model_requests_needed"] == 0
    assert "2.1.296" in result["safe_reply"]
    assert "register(on)" not in result["safe_reply"]
    assert "2.1.310" not in result["safe_reply"]


def test_preflight_unrelated_ts_is_not_a_mods_check() -> None:
    c = case("NEG-TYPESCRIPT")
    c["prompt"] = "Ordinary TypeScript package release 2.1.310"
    result = preflight_mods_case(c)
    assert result["action"] == "run_scoped_model"


def test_successful_no_code_source_cited_mods_answer_is_structural_only(approved: dict) -> None:
    c = case()
    result = post(c, native_events(c), approved)
    assert result["action"] == "allow_structural_only"
    assert result["semantic_correctness_verified"] is False
    assert result["model_provenance_matched"] is True
    assert result["allow_raw_candidate_delivery"] is True


def test_missing_anchor_and_missing_skill_block_delivery(approved: dict) -> None:
    c = case()
    for records in (
        native_events(c, answer="K-0019 with no direct official source"),
        native_events(c, skill=False),
    ):
        result = post(c, records, approved)
        assert result["action"] == "block_candidate"
        assert result["allow_raw_candidate_delivery"] is False
        assert result["safe_reply"]


def test_model_generated_code_requires_independent_native_check(approved: dict) -> None:
    c = case()
    model_answer = ANSWER + (
        "\n\x60\x60\x60js\n"
        "export function register(on) { on('tool.call', async ($, e, next) => next(e)) }\n"
        "\x60\x60\x60"
    )
    result = post(c, native_events(c, answer=model_answer), approved)
    assert "executable_example_requires_independent_native_validation" in result["reason_codes"]


def test_would_have_blocked_actual_qwen_style_repeat_loop(approved: dict) -> None:
    c = case("NEG-TYPESCRIPT")
    trace = native_events(c, answer="Partial response to type overloads", skill=False)
    for i in range(18):
        trace.insert(
            -1,
            {
                "type": "tool_execution_start",
                "toolName": "read",
                "toolCallId": f"r{i}",
                "args": {"path": "/private/source/overloads.ts"},
            },
        )
        trace.insert(
            -1,
            {
                "type": "tool_execution_end",
                "toolName": "read",
                "toolCallId": f"r{i}",
                "isError": False,
            },
        )
    result = post(c, trace, approved)
    assert "tool_loop_or_budget" in result["reason_codes"]
    assert result["native_tool_loop_suspected"]
    assert result["allow_raw_candidate_delivery"] is False


def test_clean_unrelated_task_without_skill_is_allowed_structurally(approved: dict) -> None:
    c = case("NEG-TYPESCRIPT")
    result = post(c, native_events(c, answer="Simplify generic overloads.", skill=False), approved)
    assert result["action"] == "allow_structural_only"
    assert result["semantic_correctness_verified"] is False


def test_missing_native_completion_and_mismatched_model_fail_closed(approved: dict) -> None:
    c = case()
    trace = native_events(c)
    trace.pop()
    assert post(c, trace, approved)["action"] == "block_candidate"
    trace = native_events(c)
    trace[1]["message"]["model"] = "a-different-model"
    assert "unverified_model_or_prompt" in post(c, trace, approved)["reason_codes"]


def test_wont_accept_a_model_call_after_boundary_was_preflight_blocked(approved: dict) -> None:
    c = case("BOUND-VERSION-NEW")
    result = post(c, native_events(c), approved)
    assert result["reason_codes"] == ["preflight_was_not_enforced"]
    assert result["allow_raw_candidate_delivery"] is False


def test_secrets_never_appear_in_machine_gate_verdict(approved: dict) -> None:
    c = case()
    trace = native_events(c, answer=ANSWER + "\nPRIVATE_ACCESS_TOKEN_abc")
    result = post(c, trace, approved)
    assert "PRIVATE_ACCESS_TOKEN_abc" not in json.dumps(result)


def test_invalid_metadata_not_guessed() -> None:
    with pytest.raises(PiDeliveryGateError):
        preflight_mods_case({"prompt": "", "category": "positive", "id": "POS-Q-01"})
