"""Privacy-preserving native Pi tool-loop diagnostics and bounded repeat detector.

A repeated *identical tool invocation* is diagnostic evidence, not proof
of an incorrect model. No model, filesystem or network access here.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Mapping, Sequence

TOOLS = frozenset(("read", "ls", "find", "grep"))
MAX_EVENTS = 100_000
MAX_ARG_CHARS = 5000


class PiLoopEvidenceError(ValueError):
    """A native trace is not bounded or structurally usable."""


def tool_signature(event: Mapping) -> str | None:
    """Only signature safe read-only tools with bounded, parseable JSON args."""
    if event.get("type") != "tool_execution_start" or event.get("toolName") not in TOOLS:
        return None
    args = event.get("args")
    if not isinstance(args, Mapping):
        return None
    try:
        serialized = json.dumps(args, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    except (TypeError, ValueError):
        return None
    if not serialized or len(serialized) > MAX_ARG_CHARS:
        return None
    return hashlib.sha256((event["toolName"] + "\x00" + serialized).encode()).hexdigest()


class NativeRepeatGuard:
    """Tracks read-only attempts; runner may stop the whole private QA process.

    Do not falsify tool output or change native Pi results. A repeat guard
    only causes the testing runner to terminate the bounded inference run.
    """

    def __init__(self, *, repeat_limit: int = 6, total_tool_limit: int = 48) -> None:
        if not 3 <= repeat_limit <= 32 or not 8 <= total_tool_limit <= 128:
            raise PiLoopEvidenceError("Invalid bounded guard limits")
        self.repeat_limit = repeat_limit
        self.total_tool_limit = total_tool_limit
        self.tools_seen = 0
        self.last_signature: str | None = None
        self.consecutive = 0
        self.max_consecutive = 0
        self.counts: Counter[str] = Counter()
        self.reason: str | None = None

    def observe(self, event: Mapping) -> str | None:
        if event.get("type") != "tool_execution_start":
            return self.reason
        self.tools_seen += 1
        signature = tool_signature(event)
        if signature is None:
            self.last_signature = None
            self.consecutive = 0
        elif signature == self.last_signature:
            self.consecutive += 1
        else:
            self.last_signature = signature
            self.consecutive = 1
        if signature is not None:
            self.counts[signature] += 1
        self.max_consecutive = max(self.max_consecutive, self.consecutive)
        if self.tools_seen >= self.total_tool_limit:
            self.reason = "tool_call_budget_exhausted"
        elif self.consecutive >= self.repeat_limit:
            self.reason = "repeated_identical_tool_call"
        return self.reason


def summarize_pi_loop_trace(events: Sequence[Mapping]) -> dict:
    """One immutable, redacted diagnostic summary, never raw paths/args."""
    if (
        not isinstance(events, (tuple, list))
        or len(events) > MAX_EVENTS
        or any(not isinstance(e, Mapping) for e in events)
    ):
        raise PiLoopEvidenceError("Invalid or unbounded native Pi events")
    guard = NativeRepeatGuard()
    errors: Counter[str] = Counter()
    tools: Counter[str] = Counter()
    starts: set[str] = set()
    ends: set[str] = set()
    agent_ends = 0
    model_errors = 0
    for e in events:
        guard.observe(e)
        if e.get("type") == "tool_execution_start":
            name = e.get("toolName")
            if isinstance(name, str) and name in TOOLS:
                tools[name] += 1
            tid = e.get("toolCallId")
            if isinstance(tid, str):
                starts.add(tid)
        elif e.get("type") == "tool_execution_end":
            tid = e.get("toolCallId")
            if isinstance(tid, str):
                ends.add(tid)
            if e.get("isError") is True:
                name = e.get("toolName")
                errors[name if isinstance(name, str) and name in TOOLS else "other"] += 1
        elif e.get("type") == "agent_end":
            agent_ends += 1
        elif e.get("type") == "message_end":
            message = e.get("message")
            if isinstance(message, Mapping) and message.get("errorMessage"):
                model_errors += 1
    return {
        "schema_version": 1,
        "tool_call_count": guard.tools_seen,
        "tool_counts": dict(sorted(tools.items())),
        "tool_error_count": sum(errors.values()),
        "tool_errors": dict(sorted(errors.items())),
        "distinct_tool_invocations": len(guard.counts),
        "max_identical_invocation_count": max(guard.counts.values(), default=0),
        "longest_adjacent_identical_run": guard.max_consecutive,
        "duplicate_call_limit_reached": guard.max_consecutive >= guard.repeat_limit,
        "tool_call_budget_reached": guard.tools_seen >= guard.total_tool_limit,
        "agent_end_count": agent_ends,
        "model_error_messages": model_errors,
        "tool_execution_balanced": starts <= ends,
        "native_tool_loop_suspected": (
            guard.max_consecutive >= guard.repeat_limit
            or guard.tools_seen >= guard.total_tool_limit
        ),
        "semantic_correctness_verified": False,
    }
