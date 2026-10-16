"""Public status is sourced from actual approved Claims, not stale prose."""

from __future__ import annotations

import re
from pathlib import Path

from mods_knowledge.claims import approved_claims, load_claims
from mods_knowledge.registry import load_registry

ROOT = Path(__file__).resolve().parents[1]


def test_current_readme_approved_claim_count_matches_version_scoped_ssot() -> None:
    registry = load_registry(ROOT / "sources/registry.json")
    all_claims = load_claims(
        ROOT / "claims", registry, ROOT / "sources/snapshots", ROOT / "decisions"
    )
    total = len(approved_claims(all_claims, "2.1.296", "cli"))
    other = sum(c["lifecycle"] == "candidate" for c in all_claims.values())
    text = (ROOT / "README.md").read_text()
    assert f"**{total} approved, strictly Claude Code CLI 2.1.296-scoped Claims**" in text
    assert f"**{total} approved, CLI 2.1.296-scoped Claims**" in text
    assert f"plus {other} unapproved candidates" in text


def test_chat_mode_user_prompt_includes_latest_approved_guardrails() -> None:
    text = (ROOT / "docs/operations/p4-chat-mode-explicit-usage-contract.md").read_text()
    for cid in ("K-0032", "K-0033", "K-0034", "K-0035", "K-0037", "K-0038"):
        assert cid in text
    assert "claude plugin validate --strict <mod-directory>" in text
    assert "日志" in text and "原始" in text and "异常" in text
    assert "普通 ChatGPT Chat Mode" in text
    assert not re.search(r"`claude plugin validate --strict`\s+and safe", text)
