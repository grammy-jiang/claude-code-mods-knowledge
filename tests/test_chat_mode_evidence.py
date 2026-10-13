"""ChatGPT Chat-mode actual resource-read telemetry and answer regression checks.

No model invocation: evaluate a supplied conversation structure and the visible
assistant reply. The caller obtains those using a separate authorized session.
"""

from __future__ import annotations

from mods_knowledge.chat_mode_evidence import ChatEvidenceError, summarize_chat_mode_case

PLUGIN_ID = "Plugin_testplugin"
RESOURCE = "skills://plugins/claude-code-mods-knowledge/claude-code-mods-development"


def _case(id: str = "POS-E-01", category: str = "positive") -> dict:
    return {
        "id": id,
        "category": category,
        "prompt": "Design Claude Code Mods tool.call pass-through for CLI 2.1.296.",
        "expected_activation": category != "negative",
        "expected_behavior": "source_cited" if category == "positive" else "no_activation",
        "expected_claim_ids": ["K-0007", "K-0031"] if category == "positive" else [],
    }


def _messages(include_skill: bool = True) -> list[dict]:
    if not include_skill:
        return [{"author": {"role": "assistant"}, "content": {"content_type": "text"}}]
    return [
        {
            "author": {"role": "tool", "name": "api_tool.read_resource"},
            "metadata": {
                "skill_plugin_id": PLUGIN_ID,
                "skill_name": "claude-code-mods-development",
                "invoked_resource": {"resource_uri": RESOURCE + "/references/events.md"},
            },
        }
    ]


def _answer(correct: bool = True) -> str:
    signature = (
        "on('tool.call', async ($, e, next) => { return next(e) })"
        if correct
        else "on('tool.call', async (e, next) => { return next(e) })"
    )
    return (
        signature + "\n"
        "K-0007, K-0031.\n"
        "https://code.claude.com/docs/en/plugins/mods/reference#the-hook-function\n"
    )


def test_chat_mode_success_requires_actual_plugin_read_resource_and_correct_arity() -> None:
    rec = summarize_chat_mode_case(
        _case(),
        "0.1.0-rc.2",
        "valid-test-id",
        _answer(),
        _messages(),
    )
    assert rec["skill_loaded"] is True
    assert rec["answer_quality"] == "pass"
    assert rec["case_id"] == "POS-E-01"
    assert rec["plugin_version"] == "0.1.0-rc.2"
    assert rec["resource_uris"] == [RESOURCE + "/references/events.md"]
    assert rec["code_callback_signature_correct"] is True
    assert len(rec["response_sha256"]) == 64
    assert len(rec["conversation_sha256"]) == 64
    assert "valid-test-id" not in str(rec)
    assert "on('tool.call'" not in str(rec)


def test_chat_mode_regression_missing_api_argument_is_classified_failure() -> None:
    rec = summarize_chat_mode_case(
        _case(), "0.1.0-rc.1", "previous-test", _answer(correct=False), _messages()
    )
    assert rec["skill_loaded"] is True
    assert rec["answer_quality"] == "fail"
    assert rec["code_callback_signature_correct"] is False
    assert "missing-hook-first-argument" in rec["quality_flags"]


def test_chat_mode_negative_case_requires_no_skill_read() -> None:
    case = _case("NEG-HVAC", "negative")
    rec = summarize_chat_mode_case(
        case,
        "0.1.0-rc.2",
        "test-negative",
        "HVAC cooling load requires assumptions.",
        _messages(False),
    )
    assert rec["skill_loaded"] is False
    assert rec["answer_quality"] == "pass"
    assert rec["quality_flags"] == ["nonactivation-observed"]


def test_negative_case_skill_read_is_evaluated_as_false_activation() -> None:
    case = _case("NEG-HVAC", "negative")
    rec = summarize_chat_mode_case(
        case, "0.1.0-rc.2", "test-negative", "Generic HVAC answer", _messages()
    )
    assert rec["skill_loaded"] is True
    assert rec["answer_quality"] == "fail"


def test_answer_without_plugin_read_cannot_count_as_positive_activation() -> None:
    rec = summarize_chat_mode_case(_case(), "0.1.0-rc.2", "id", _answer(), _messages(False))
    assert rec["skill_loaded"] is False
    assert rec["answer_quality"] == "fail"


def test_chat_mode_never_embeds_raw_prompts_or_full_model_replies() -> None:
    rec = summarize_chat_mode_case(
        _case(), "0.1.0-rc.2", "conversation-123", _answer(), _messages()
    )
    serialized = str(rec)
    assert "Design Claude Code" not in serialized
    assert "conversation-123" not in serialized
    assert "https://code.claude.com/docs/en/plugins/mods/reference" not in serialized


def test_untrusted_resource_without_skill_plugin_id_is_not_proof() -> None:
    messages = _messages()
    messages[0]["metadata"].pop("skill_plugin_id")
    rec = summarize_chat_mode_case(_case(), "0.1.0-rc.2", "id", _answer(), messages)
    assert rec["skill_loaded"] is False


def test_invalid_target_version_rejected() -> None:
    from pytest import raises

    with raises(ChatEvidenceError):
        summarize_chat_mode_case(_case(), "latest", "id", _answer(), _messages())
