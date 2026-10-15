"""Unit controls: preserve all user-visible Chat Mode answer segments."""

from __future__ import annotations

import hashlib

import pytest

from mods_knowledge.chat_visible_reply import ChatVisibleReplyError, collect_latest_visible_reply


def msg(
    role: str,
    text: str,
    *,
    recipient: str = "all",
    status: str = "finished_successfully",
    content_type: str = "text",
) -> dict:
    return {
        "author": {"role": role},
        "recipient": recipient,
        "status": status,
        "content": {"content_type": content_type, "parts": [text]},
    }


def test_three_visible_chat_segments_become_one_complete_answer() -> None:
    msgs = [
        msg("user", "Explain observer"),
        msg("assistant", "I will check the Mods Skill."),
        msg(
            "assistant",
            "K-0007 K-0031 from https://code.claude.com/docs/en/plugins/mods/events#observe-an-event\n```ts\nexport function register(on) {}\n```",
        ),
        msg("tool", "Resource content", recipient="all"),
        msg("assistant", "Then return next(e) without changing the result."),
    ]
    result = collect_latest_visible_reply(msgs)
    assert result.segment_count == 3
    assert result.reply_text.startswith("I will check the Mods Skill.")
    assert "K-0007 K-0031" in result.reply_text
    assert "export function register(on)" in result.reply_text
    assert result.reply_text.endswith("without changing the result.")
    assert result.reply_sha256 == hashlib.sha256(result.reply_text.encode()).hexdigest()
    assert result.segment_lengths == (
        28,
        len(msgs[2]["content"]["parts"][0]),
        len(msgs[4]["content"]["parts"][0]),
    )


def test_repeated_user_turn_does_not_leak_previous_turn_to_new_reply() -> None:
    msgs = [
        msg("user", "old"),
        msg("assistant", "K-9999 older response"),
        msg("user", "new"),
        msg("assistant", "current part 1"),
        msg("assistant", "current part 2"),
    ]
    output = collect_latest_visible_reply(msgs)
    assert output.reply_text == "current part 1\n\ncurrent part 2"
    assert output.segment_count == 2
    assert "K-9999" not in output.reply_text


def test_tool_receipts_analysis_and_nonvisible_assistant_are_excluded() -> None:
    msgs = [
        msg("user", "request"),
        msg("assistant", "internal recipient content", recipient="api_tool.read_resource"),
        msg("assistant", "not text output", content_type="code"),
        msg("tool", "SYSTEM TOKEN PRIVATE"),
        msg("assistant", "The visible answer."),
    ]
    output = collect_latest_visible_reply(msgs)
    assert output.reply_text == "The visible answer."
    assert output.segment_count == 1


def test_final_turn_has_to_be_finished_visible_assistant() -> None:
    with pytest.raises(ChatVisibleReplyError):
        collect_latest_visible_reply(
            [msg("user", "hello"), msg("assistant", "still working", status="in_progress")]
        )
    with pytest.raises(ChatVisibleReplyError):
        collect_latest_visible_reply(
            [msg("user", "hello"), msg("assistant", "some narration"), msg("tool", "pending")]
        )


def test_requires_explicit_user_turn_and_nonempty_visible_answer() -> None:
    with pytest.raises(ChatVisibleReplyError):
        collect_latest_visible_reply([msg("assistant", "looks complete but no user turn")])
    with pytest.raises(ChatVisibleReplyError):
        collect_latest_visible_reply([msg("user", "question"), msg("assistant", "  ")])


def test_rejects_malformed_message_content_without_guessing() -> None:
    with pytest.raises(ChatVisibleReplyError):
        collect_latest_visible_reply(
            [
                msg("user", "question"),
                {
                    "author": {"role": "assistant"},
                    "recipient": "all",
                    "status": "finished_successfully",
                    "content": {"content_type": "text", "parts": "not an array"},
                },
            ]
        )
