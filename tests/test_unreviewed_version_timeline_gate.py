"""Prevent exact unsupported API-introduction chronology from source-weak replies.

This is a deterministic MANUAL-REVIEW signal, not unverified claims of
correctness or an attempt to silently alter the frozen P4 activation gate.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mods_knowledge.answer_lint import lint_mods_answer
from mods_knowledge.compiler import compile_knowledge

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "text",
    (
        "第三方版本资料将 tool.check 事件的引入时间标为 Claude Code 2.1.269。",
        "This blog says that tool.check was introduced in Claude Code 2.1.269.",
        "据社区资料推测：tool.check 最早于 2.1.269 引入，但尚未证实。",
        "The tool.check hook was first available in version 2.1.269 (unconfirmed).",
    ),
)
def test_unapproved_historical_event_introduction_is_never_unflagged(text: str) -> None:
    report = lint_mods_answer(
        "Claude Code Mods API version-history answer:\n" + text,
        case_id="BOUND-VERSION-OLD",
    )
    assert (
        "unverified-api-version-introduction-needs-primary-proof"
        in report["requires_manual_review"]
    )
    assert report["semantic_review_complete"] is False
    assert report["verdict"] == "unverified"


@pytest.mark.parametrize(
    "text",
    (
        "Target Claude Code CLI 2.1.220 is not reviewed by the installed Skill.",
        "已审查版本 2.1.302；用户请求 2.1.220 的字段无法核验。",
        "Without first-party 2.1.220 types, I cannot confirm tool.check fields.",
        "Do not assume tool.check was introduced in 2.1.269 without proof.",
    ),
)
def test_scoped_abstention_does_not_trigger_false_version_history_flag(text: str) -> None:
    report = lint_mods_answer(
        "Claude Code Mods version boundary:\n" + text,
        case_id="BOUND-VERSION-OLD",
    )
    assert (
        "unverified-api-version-introduction-needs-primary-proof"
        not in report["requires_manual_review"]
    )


@pytest.mark.parametrize("cli", ("2.1.296", "2.1.302"))
def test_every_compiled_skill_prohibits_unreviewed_api_timeline_claims(cli: str) -> None:
    artifacts = compile_knowledge(
        ROOT, api_version=cli, surface="cli", source_revision="version-timeline-qa"
    )
    expected = "Do not claim when a Mod event or API was first introduced, removed or deprecated"
    for path, raw in artifacts.items():
        if path.endswith("/SKILL.md"):
            assert expected in raw.decode()
    assert len([name for name in artifacts if name.endswith("/SKILL.md")]) == 5
