"""Avoid contradictory current status claims in the public project README."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_public_readme_separates_public_beta_from_private_account_candidate() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "repository is public" in readme
    assert "last **published GitHub Beta**" in readme
    assert "unpublished experimental `0.3.0-beta.1`" in readme
    assert "2026-10-14-v030beta1-real-chat-targeted.md" in readme
    assert "normalized ZIP bytes" in readme
    assert "Stable release remains blocked" in readme
    for stale_claim in (
        "This project remains private",
        "currently installed, enabled ChatGPT account version",
        "No Knowledge Compiler, Agent Skill, Plugin, background update job",
        "Claude/Codex/Pi model-running acceptance remains deferred",
    ):
        assert stale_claim not in readme
