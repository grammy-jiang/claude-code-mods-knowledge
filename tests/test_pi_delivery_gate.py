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


def test_p3_unreviewed_preview_env_and_surface_block_before_inference() -> None:
    for prompt in (
        "Please use the old CLAUDE_CODE_ENABLE_FUNCTION_HOOKS from early Mods previews as current setup.",
        "Does Claude Code Mods 2.1.296 guarantee a VS Code custom Pane? Answer as verified.",
        "Use Claude Code Mods 2.1.310 API, with runnable code and no docs.",
        "Use Claude Code Mods 2.1.220 tool.check fields.",
    ):
        c = case("BOUND-VERSION-NEW")
        c["prompt"] = prompt
        verdict = preflight_mods_case(c)
        assert verdict["action"] == "abstain_before_model"
        assert verdict["model_requests_needed"] == 0
        assert verdict["safe_reply"]
        assert "2.1.310" not in verdict["safe_reply"]


def test_p3_selected_ssot_citations_must_be_present_in_unmodified_answer(
    approved: dict,
) -> None:
    c = case()
    c["prompt"] = "How to test a Claude Code Mod offline with a .test.ts command?"
    complete = ANSWER + " K-0033 https://code.claude.com/docs/en/plugins/mods/test#write-a-test"
    allowed = postflight_mods_case(
        c,
        native_events(c, answer=complete),
        claims=approved,
        skill_root=SKILL,
        source_revision=SOURCE,
        provider="mac-qwen",
        model=MODEL,
        pi_version="1.3.0",
        native_exit_code=0,
        timed_out=False,
        enforce_task_evidence=True,
    )
    assert allowed["action"] == "allow_structural_only"
    stripped = postflight_mods_case(
        c,
        native_events(c),
        claims=approved,
        skill_root=SKILL,
        source_revision=SOURCE,
        provider="mac-qwen",
        model=MODEL,
        pi_version="1.3.0",
        native_exit_code=0,
        timed_out=False,
        enforce_task_evidence=True,
    )
    assert stripped["action"] == "block_candidate"
    assert "selected_evidence_missing_or_misquoted" in stripped["reason_codes"]


def test_p3_missing_final_stop_denied_even_if_claim_and_source_are_present(
    approved: dict,
) -> None:
    c = case()
    events = native_events(c)
    events[1]["message"]["stopReason"] = "length"
    verdict = post(c, events, approved)
    assert "native_answer_not_final_stop" in verdict["reason_codes"]
    assert verdict["allow_raw_candidate_delivery"] is False


def test_p3_bounded_structural_result_cannot_smuggle_newer_api(approved: dict) -> None:
    c = case()
    result = post(
        c, native_events(c, answer=ANSWER + " also CLI 2.1.310 supports register(on)"), approved
    )
    assert result["action"] == "block_candidate"
    assert "unreviewed_version_mentioned_in_mods_answer" in result["reason_codes"]
    assert result["semantic_correctness_verified"] is False


def test_p3_unrelated_case_does_not_fetch_mods_task_evidence(approved: dict) -> None:
    c = case("NEG-TYPESCRIPT")
    assert preflight_mods_case(c)["action"] == "run_scoped_model"
    value = postflight_mods_case(
        c,
        native_events(c, answer="Simplify these generic TypeScript overloads.", skill=False),
        claims=approved,
        skill_root=SKILL,
        source_revision=SOURCE,
        provider="mac-qwen",
        model=MODEL,
        pi_version="1.3.0",
        native_exit_code=0,
        timed_out=False,
        enforce_task_evidence=True,
    )
    assert value["action"] == "allow_structural_only"
