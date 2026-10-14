"""Native Pi Agent evidence must pin the *observed* model, not CLI defaults."""

from __future__ import annotations

import pytest

from mods_knowledge.pi_model_evidence import PiModelEvidenceError, summarize_pi_model_trace

ROOT_SKILL = "/workspace/p5-test-project/skill"
SOURCE = "81fdf78656238f8383cbeed54ed3420bdc480231"
URL = "https://code.claude.com/docs/en/plugins/mods/reference#the-hook-function"


def case(category: str = "positive") -> dict:
    return {
        "id": "POS-E-01"
        if category == "positive"
        else ("NEG-TYPESCRIPT" if category == "negative" else "BOUND-VERSION-NEW"),
        "prompt": "Example original P4 case prompt",
        "category": category,
        "expected_activation": category != "negative",
        "expected_claim_ids": ["K-0007", "K-0031"] if category == "positive" else [],
    }


def events(
    *,
    category: str = "positive",
    source_read: bool = True,
    model: str = "gpt-5.5",
    answer: str | None = None,
) -> list[dict]:
    c = case(category)
    if answer is None:
        answer = (
            "K-0007 K-0031 see "
            + URL
            + "\n```ts\nexport function register(on) {\n  on('tool.call', async ($, e, next) => next(e))\n}\n```"
            if category == "positive"
            else "Scope unverified for other versions."
        )
    values = [
        {
            "type": "message_end",
            "message": {"role": "user", "content": [{"type": "text", "text": c["prompt"]}]},
        },
        {
            "type": "message_end",
            "message": {
                "role": "assistant",
                "provider": "openai-codex" if model == "gpt-5.5" else "mac-qwen",
                "model": model,
                "content": [{"type": "text", "text": answer}],
                "stopReason": "stop",
            },
        },
    ]
    if source_read:
        values.extend(
            [
                {
                    "type": "tool_execution_start",
                    "toolName": "read",
                    "toolCallId": "tc1",
                    "args": {"path": ROOT_SKILL + "/SKILL.md"},
                },
                {
                    "type": "tool_execution_end",
                    "toolName": "read",
                    "toolCallId": "tc1",
                    "isError": False,
                },
            ]
        )
    return [*values, {"type": "agent_end"}]


def scan(case_data: dict, trace: list[dict], *, model: str = "gpt-5.5") -> dict:
    return summarize_pi_model_trace(
        case_data,
        trace,
        expected_provider="openai-codex",
        expected_model=model,
        model_was_pinned=True,
        skill_root=ROOT_SKILL,
        source_revision=SOURCE,
        pi_version="1.1.0",
    )


def test_real_model_and_exact_prompt_required_for_structural_result() -> None:
    data = scan(case(), events())
    assert data["verdict"] == "structural_ok_semantics_unverified"
    assert data["model_observed"] == "openai-codex/gpt-5.5"
    assert data["model_pin_matched"] and data["prompt_matched"]
    assert data["skill_loaded"] and data["reference_files_read"] == []
    assert data["has_required_claims"] and data["official_source_cited"]
    assert data["semantic_review_complete"] is False
    assert data["response_sha256"] and len(data["response_sha256"]) == 64
    assert data["source_revision"] == SOURCE


def test_cli_model_parameter_does_not_fake_actual_model() -> None:
    report = scan(case(), events(model="qwen36-35b-a3b-mtp"))
    assert report["model_observed"] == "mac-qwen/qwen36-35b-a3b-mtp"
    assert report["model_pin_matched"] is False
    assert report["verdict"] == "invalid_provenance"


def test_mismatched_user_prompt_never_qualifies() -> None:
    trace = events()
    trace[0]["message"]["content"][0]["text"] = "Another prompt"
    report = scan(case(), trace)
    assert report["prompt_matched"] is False
    assert report["verdict"] == "invalid_provenance"


def test_required_skill_read_and_official_citation_are_independent() -> None:
    no_read = scan(case(), events(source_read=False))
    no_link = scan(case(), events(answer="K-0007 K-0031 without a direct official URL"))
    assert no_read["verdict"] == "activation_failed"
    assert no_link["skill_loaded"] is True
    assert no_link["verdict"] == "structural_failed"


def test_unrelated_negative_without_skill_read_does_not_need_claims() -> None:
    result = scan(case("negative"), events(category="negative", source_read=False))
    assert result["verdict"] == "negative_nonactivation_observed"
    assert result["skill_loaded"] is False


def test_negative_skill_read_is_a_false_activation() -> None:
    result = scan(case("negative"), events(category="negative", source_read=True))
    assert result["verdict"] == "activation_failed"


def test_boundary_requires_manual_semantic_review_even_when_skill_read() -> None:
    result = scan(case("boundary"), events(category="boundary"))
    assert result["verdict"] == "boundary_manual_review_required"
    assert result["semantic_review_complete"] is False


def test_missing_final_turn_or_empty_terminal_answer_is_not_a_pass() -> None:
    trace = events()[:-1]
    assert scan(case(), trace)["verdict"] == "blocked_or_incomplete"
    data = scan(case(), events(answer=""))
    assert data["verdict"] == "blocked_or_incomplete"


def test_error_reported_by_native_model_is_not_a_negative_control_success() -> None:
    trace = events(category="negative", source_read=False)
    trace[1]["message"]["errorMessage"] = "expired authorization: PRIVATE_SECRET"
    result = scan(case("negative"), trace)
    assert result["verdict"] == "blocked_or_incomplete"
    assert "PRIVATE_SECRET" not in str(result)


def test_external_paths_and_user_secret_never_leave_sanitized_summary() -> None:
    trace = events()
    trace.insert(
        2,
        {
            "type": "tool_execution_start",
            "toolName": "read",
            "toolCallId": "external",
            "args": {"path": "/home/private/secret-file"},
        },
    )
    trace.insert(
        3,
        {
            "type": "tool_execution_end",
            "toolName": "read",
            "toolCallId": "external",
            "isError": True,
        },
    )
    report = scan(case(), trace)
    assert report["tool_calls_outside_skill"] == 1
    assert "/home/private" not in str(report)
    assert report["verdict"] != "structural_ok_semantics_unverified"


def test_model_provenance_and_revision_args_are_strict() -> None:
    with pytest.raises(PiModelEvidenceError):
        summarize_pi_model_trace(
            case(),
            events(),
            expected_provider="",
            expected_model="gpt-5.5",
            model_was_pinned=True,
            skill_root=ROOT_SKILL,
            source_revision=SOURCE,
            pi_version="1.1.0",
        )
    with pytest.raises(PiModelEvidenceError):
        summarize_pi_model_trace(
            case(),
            events(),
            expected_provider="openai-codex",
            expected_model="gpt-5.5",
            model_was_pinned=True,
            skill_root=ROOT_SKILL,
            source_revision="unverified",
            pi_version="1.1.0",
        )


def test_unpinned_default_is_never_mislabeled_as_explicit_provider_selection() -> None:
    summary = summarize_pi_model_trace(
        case(),
        events(),
        expected_provider="openai-codex",
        expected_model="gpt-5.5",
        model_was_pinned=False,
        skill_root=ROOT_SKILL,
        source_revision=SOURCE,
        pi_version="1.1.0",
    )
    assert summary["model_observed"] == "openai-codex/gpt-5.5"
    assert summary["model_requested"] is None
    assert summary["model_flag_explicit"] is False
    assert summary["model_pin_matched"] is False
    assert summary["verdict"] == "invalid_provenance"


def test_negative_skill_nonactivation_is_not_overruled_by_unrelated_tool_errors() -> None:
    # An unrelated TypeScript task may read its own files (and some may fail).
    # Neither is evidence that the Mods Skill was activated or its API failed.
    trace = events(category="negative", source_read=False)
    trace.insert(
        2,
        {
            "type": "tool_execution_start",
            "toolName": "read",
            "toolCallId": "out",
            "args": {"path": "/workspace/ordinary-web-project/missing.ts"},
        },
    )
    trace.insert(
        3,
        {"type": "tool_execution_end", "toolName": "read", "toolCallId": "out", "isError": True},
    )
    report = scan(case("negative"), trace)
    assert report["tool_calls_outside_skill"] == 1
    assert report["read_tool_errors"] == 1
    assert report["verdict"] == "negative_nonactivation_observed"
