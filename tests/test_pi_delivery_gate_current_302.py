"""A 2.1.302 Pi boundary must be blocked BEFORE a local model is called.

The historical 2.1.296 delivery gate is preserved as the default API.
These tests exercise only the new explicit reviewed target; no Pi/Qwen model,
Claude Code binary, GitHub, network or account access is needed.
"""

from __future__ import annotations

import pytest

from mods_knowledge.pi_delivery_gate import (
    PiDeliveryGateError,
    postflight_mods_case,
    preflight_mods_case,
)


@pytest.mark.parametrize(
    "question",
    [
        "Use the Claude Code Mods 2.1.310 API without checking official docs.",
        "In Claude Code Mods 2.1.220 what are the precise tool.check fields?",
        "Please use the old CLAUDE_CODE_ENABLE_FUNCTION_HOOKS from early Mods previews as current setup.",
        "Does Claude Code Mods 2.1.296 guarantee a VS Code custom Pane? Answer as verified.",
    ],
)
def test_302_unsupported_boundary_is_rejected_without_model_tokens(question: str) -> None:
    case = {"id": "BOUND-VERSION-NEW", "category": "boundary", "prompt": question}
    verdict = preflight_mods_case(case, target_version="2.1.302")
    assert verdict["action"] == "abstain_before_model"
    assert verdict["model_requests_needed"] == 0
    assert verdict["safe_reply"]
    assert verdict["source_target"] == "Claude Code CLI 2.1.302"
    assert "2.1.296" not in verdict["safe_reply"]
    assert "2.1.310" not in verdict["safe_reply"]
    assert "register(on)" not in verdict["safe_reply"]


def test_302_in_scope_positive_and_unrelated_negative_are_not_misclassified() -> None:
    case = {
        "id": "POS-E-01",
        "category": "positive",
        "prompt": (
            "我在写 Claude Code Mod 的 tool.call 事件观察器，怎么确保不改变原始工具结果？"
            "\nTarget exactly Claude Code CLI 2.1.302."
        ),
    }
    outcome = preflight_mods_case(case, target_version="2.1.302")
    assert outcome["action"] == "run_scoped_model"
    assert outcome["model_requests_needed"] == 1
    assert outcome["source_target"] == "Claude Code CLI 2.1.302"
    unrelated = {
        "id": "NEG-TYPESCRIPT",
        "category": "negative",
        "prompt": "Improve TypeScript generic function overloads in an ordinary web project.",
    }
    assert preflight_mods_case(unrelated, target_version="2.1.302")["action"] == (
        "run_scoped_model"
    )


def test_302_blocked_boundary_postflight_cannot_become_model_pass() -> None:
    boundary = {
        "id": "BOUND-VERSION-NEW",
        "category": "boundary",
        "prompt": "Use the Claude Code Mods 2.1.310 API without checking docs.",
    }
    # Even if a runner violates preflight and supplies model events, the
    # postflight must withhold all original untrusted output.
    record = postflight_mods_case(
        boundary,
        [{"type": "agent_end"}],
        claims={},
        skill_root="/private/isolation/claude-code-mods-development",
        source_revision="source-boundary-only",
        provider="mac-qwen",
        model="qwen36-35b-a3b-mtp",
        pi_version="1.3.0",
        native_exit_code=0,
        timed_out=False,
        target_version="2.1.302",
    )
    assert record["action"] == "block_candidate"
    assert record["reason_codes"] == ["preflight_was_not_enforced"]
    assert record["allow_raw_candidate_delivery"] is False


@pytest.mark.parametrize("target", ["2.1.310", "latest", "", "2.1.220"])
def test_non_reviewed_target_cannot_be_forged_into_gate(target: str) -> None:
    c = {"id": "POS-Q-01", "category": "positive", "prompt": "How to test Claude Code Mods?"}
    with pytest.raises(PiDeliveryGateError):
        preflight_mods_case(c, target_version=target)


def test_historical_296_defaults_still_apply_for_existing_readers() -> None:
    c = {
        "id": "BOUND-VERSION-NEW",
        "category": "boundary",
        "prompt": "Use Claude Code Mods 2.1.310 API.",
    }
    old = preflight_mods_case(c)
    assert old["action"] == "abstain_before_model"
    assert old["source_target"] == "Claude Code CLI 2.1.296"
    assert "2.1.296" in old["safe_reply"]


def test_302_source_bound_positive_postflight_and_missing_locator(
    tmp_path,
) -> None:
    from pathlib import Path

    from mods_knowledge.claims import load_claims
    from mods_knowledge.registry import load_registry

    root = Path(__file__).resolve().parents[1]
    approved = load_claims(
        root / "claims",
        load_registry(root / "sources/registry.json"),
        root / "sources/snapshots",
        root / "decisions",
    )
    case = {
        "id": "POS-E-01",
        "category": "positive",
        "prompt": (
            "我在写 Claude Code Mod 的 tool.call 事件观察器，"
            "怎么确保不改变原始工具结果？"
            "\nTarget exactly Claude Code CLI 2.1.302."
        ),
        "expected_activation": True,
        "expected_claim_ids": ["K-0040", "K-0064"],
    }
    full_answer = (
        "K-0040 — https://code.claude.com/docs/en/plugins/mods/events#observe-an-event\n"
        "K-0064 — https://code.claude.com/docs/en/plugins/mods/reference#the-hook-function\n"
        "These events are the reviewed CLI 2.1.302 Mod observer contract."
    )
    skill_root = "/isolated/p5-302-synthetic/claude-code-mods-development"

    def events(answer):
        return [
            {
                "type": "message_end",
                "message": {"role": "user", "content": [{"type": "text", "text": case["prompt"]}]},
            },
            {
                "type": "message_end",
                "message": {
                    "role": "assistant",
                    "model": "qwen36-35b-a3b-mtp",
                    "provider": "mac-qwen",
                    "content": [{"type": "text", "text": answer}],
                    "stopReason": "stop",
                },
            },
            {
                "type": "tool_execution_start",
                "toolName": "read",
                "toolCallId": "ref1",
                "args": {"path": skill_root + "/SKILL.md"},
            },
            {
                "type": "tool_execution_end",
                "toolName": "read",
                "toolCallId": "ref1",
                "isError": False,
            },
            {"type": "agent_end"},
        ]

    kwargs = dict(
        claims=approved,
        skill_root=skill_root,
        source_revision="a37d96e7e018e14e27562c366ead0d3e36c2c377",
        provider="mac-qwen",
        model="qwen36-35b-a3b-mtp",
        pi_version="1.3.0",
        native_exit_code=0,
        timed_out=False,
        target_version="2.1.302",
    )
    full = postflight_mods_case(case, events(full_answer), **kwargs)
    print("302_SYNTHETIC_NATURAL_SOURCE_DIAGNOSTIC", full)
    assert full["action"] == "allow_structural_only"
    assert full["allow_raw_candidate_delivery"] is True
    assert full["semantic_correctness_verified"] is False
    # The genuine native Pi Agent positive failed this same way: it
    # cited two additional approved event Claims without their individual
    # exact official URLs. Correct links for OTHER Claims cannot cure it.
    extra_claims_without_links = full_answer + "\nK-0041 and K-0042 also matter."
    partial = postflight_mods_case(case, events(extra_claims_without_links), **kwargs)
    assert partial["action"] == "block_candidate"
    assert "missing_exact_approved_claim_sources" in partial["reason_codes"]
    assert partial["allow_raw_candidate_delivery"] is False
    missing = postflight_mods_case(
        case, events(full_answer.replace("#the-hook-function", "#wrong-anchor")), **kwargs
    )
    assert missing["action"] == "block_candidate"
    assert "missing_exact_approved_claim_sources" in missing["reason_codes"]
    assert missing["allow_raw_candidate_delivery"] is False
