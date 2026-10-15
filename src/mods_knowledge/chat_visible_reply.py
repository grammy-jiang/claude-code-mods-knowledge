"""Assemble the complete last Chat Mode turn from user-visible assistant text.

ChatGPT may emit one answer over multiple ``assistant``/``all``/``text``
messages. Grading only the last message silently drops Claims, sources,
code examples and intermediate response sections. This is a pure, bounded
transform over a separately fetched PRIVATE conversation's linear chain.
No network, account API, provider identity or semantic acceptance here.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass


class ChatVisibleReplyError(ValueError):
    """Cannot safely determine a complete visible assistant response."""


@dataclass(frozen=True)
class VisibleReply:
    reply_text: str
    reply_sha256: str
    segment_count: int
    segment_lengths: tuple[int, ...]


def _is_visible_assistant(message: Mapping) -> bool:
    content = message.get("content")
    return (
        isinstance(message.get("author"), Mapping)
        and message["author"].get("role") == "assistant"
        and message.get("recipient") in (None, "all")
        and isinstance(content, Mapping)
        and content.get("content_type") == "text"
    )


def _text_parts(message: Mapping) -> str:
    content = message["content"]
    parts = content.get("parts")
    if not isinstance(parts, list):
        raise ChatVisibleReplyError("Visible message has non-array content parts")
    if not all(
        isinstance(part, (str, dict, list, int, float, bool)) or part is None for part in parts
    ):
        raise ChatVisibleReplyError("Visible message has unsupported content part")
    return "\n".join(
        part if isinstance(part, str) else json.dumps(part, ensure_ascii=False) for part in parts
    )


def collect_latest_visible_reply(messages: Sequence[Mapping]) -> VisibleReply:
    """Concatenate every visible segment after the *last* user message.

    Only messages addressed to the user count: never include tool outputs,
    analysis messages, or earlier user turns. Refuse incomplete terminal turns
    rather than treating a model's partial narration as a complete answer.
    """
    if not isinstance(messages, (tuple, list)) or len(messages) > 2000:
        raise ChatVisibleReplyError("Unbounded or invalid conversation chain")
    if not all(isinstance(message, Mapping) for message in messages):
        raise ChatVisibleReplyError("Invalid conversation message")
    user_indices = [
        i
        for i, message in enumerate(messages)
        if isinstance(message.get("author"), Mapping) and message["author"].get("role") == "user"
    ]
    if not user_indices:
        raise ChatVisibleReplyError("No user request to grade")
    last_turn = messages[user_indices[-1] + 1 :]
    if not last_turn:
        raise ChatVisibleReplyError("No assistant response for the latest user turn")
    final = last_turn[-1]
    if not _is_visible_assistant(final) or final.get("status") != "finished_successfully":
        raise ChatVisibleReplyError("Last Chat Mode turn has no finished visible response")
    segments: list[str] = []
    for message in last_turn:
        if not _is_visible_assistant(message):
            continue
        text = _text_parts(message)
        if text.strip():
            segments.append(text)
        if len(segments) > 100:
            raise ChatVisibleReplyError("Unbounded visible Chat Mode response segments")
    if not segments:
        raise ChatVisibleReplyError("No visible assistant answer text")
    reply = "\n\n".join(segments)
    if len(reply) > 500_000:
        raise ChatVisibleReplyError("Unbounded visible answer size")
    return VisibleReply(
        reply_text=reply,
        reply_sha256=hashlib.sha256(reply.encode("utf-8")).hexdigest(),
        segment_count=len(segments),
        segment_lengths=tuple(map(len, segments)),
    )
