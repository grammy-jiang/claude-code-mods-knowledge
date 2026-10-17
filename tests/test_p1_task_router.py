"""P1 original-P0 regressions, multilingual paraphrases and version isolation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mods_knowledge.task_evidence import route_task

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    ("prompt", "intent", "reason", "versions"),
    [
        ("How do I create a Mod observer for CLI 2.1.296?", "mods", None, ["2.1.296"]),
        ("How do I test Mods 2.1.296 offline?", "mods", None, ["2.1.296"]),
        (
            "How to test a Claude Code Mod on CLI 2.1.296 with Python 3.14.8?",
            "mods",
            None,
            ["2.1.296"],
        ),
        (
            "Use Claude Code Mods 2.1.310 with Node.js 24.9.0.",
            "blocked",
            "unreviewed_version",
            ["2.1.310"],
        ),
        (
            "Build a VS Code pane Claude Code Mods implementation on 2.1.296.",
            "blocked",
            "unverified_host_surface",
            ["2.1.296"],
        ),
        (
            "What is the latest Claude Code Mods API for observer logging?",
            "blocked",
            "current_api_requires_first_party_verification",
            [],
        ),
        (
            "Claude Code Mods 最新的 tool.call 有什么改变？",
            "blocked",
            "current_api_requires_first_party_verification",
            [],
        ),
        (
            "Claude Code Mods 当前的 API 文档是什么？",
            "blocked",
            "current_api_requires_first_party_verification",
            [],
        ),
        (
            "Claude Code Mods 现在支持什么 API？",
            "blocked",
            "current_api_requires_first_party_verification",
            [],
        ),
        (
            "Which Claude Code Mods API is supported now?",
            "blocked",
            "current_api_requires_first_party_verification",
            [],
        ),
        (
            "请介绍 Claude Code Mods 2.1.301 的新功能。",
            "blocked",
            "unreviewed_version",
            ["2.1.301"],
        ),
        (
            "Can you verify compatibility of Claude Code Mods? I forgot which version.",
            "blocked",
            "unknown_target_version",
            [],
        ),
        (
            "Are Claude Code Mods 2.1.296 and 2.1.310 identical?",
            "blocked",
            "unreviewed_version",
            ["2.1.296", "2.1.310"],
        ),
        (
            "Explain the ordinary Python requests code, not Mods.",
            "unrelated",
            "explicit_non_mod_or_legacy_control",
            [],
        ),
        (
            "Help me build a Minecraft mods server for Python 3.14.8",
            "unrelated",
            "no_mod_api_signal",
            [],
        ),
        (
            "Use a normal Claude Code settings.json PreToolUse Bash hook.",
            "unrelated",
            "explicit_non_mod_or_legacy_control",
            [],
        ),
        (
            "My Claude Code Mod logs through tool.call on CLI 2.1.296",
            "mods",
            None,
            ["2.1.296"],
        ),
    ],
)
def test_intent_product_version_and_surface_are_not_conflated(
    prompt: str, intent: str, reason: str | None, versions: list[str]
) -> None:
    routed = route_task(prompt)
    assert (routed["intent"], routed["reason"], routed["versions"]) == (
        intent, reason, versions,
    )
    if intent == "blocked":
        assert routed["target"] is None


def test_unchanged_frozen_p4_case_bank_remains_classified_as_before() -> None:
    frozen = json.loads((ROOT / "evals/p4_cases.json").read_text())["cases"]
    for case in frozen:
        original = route_task(case["prompt"])
        if case["category"] == "positive":
            assert original["intent"] == "mods", case["id"]
        elif case["category"] == "negative":
            assert original["intent"] == "unrelated", case["id"]
        elif case["id"] in {
            "BOUND-VERSION-OLD", "BOUND-VERSION-NEW", "BOUND-UNKNOWN-VERSION",
            "BOUND-HISTORY", "BOUND-SURFACE",
        }:
            assert original["intent"] == "blocked", case["id"]


def test_regression_ambiguous_version_is_not_misrepresented_as_current() -> None:
    for text in (
        "I need the current Claude Code Mods version, not the old one.",
        "What is the latest Mod observer API for 2.1.296?",
    ):
        route = route_task(text)
        assert route["intent"] == "blocked"
        assert route["reason"] == "current_api_requires_first_party_verification"
