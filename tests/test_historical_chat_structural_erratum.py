"""Historical Chat QA may not silently promote old final-fragment-only scores."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_archived_p4_auto_qa_marks_structural_0_of_30_as_superseded() -> None:
    text = (ROOT / "docs/reports/2026-10-14-v030beta1-full46-automatic-chat.md").read_text()
    assert "Historical structural-score correction (2026-10-16)" in text
    assert "0/30" in text
    assert "last-fragment-only" in text
    assert "MUST NOT be cited as a valid full-answer structural outcome" in text
    assert "POS-E-01" in text and "FAIL to PASS" in text
    assert "comprehensively re-scored" in text
    # A genuine model-tool read count is independent of which visible answer
    # fragments are concatenated for Claim/source structural scoring.
    assert "**3/30**" in text and "**0/8**" in text
    assert "still **FAILED P4 routing**" in text
    assert "immutable" in text


def test_checklist_does_not_silently_call_old_structural_score_final() -> None:
    text = (ROOT / "docs/operations/p4-p6-closeout-checklist.md").read_text()
    assert "The originally reported **0/30 positive structural PASS rate" in text
    assert "retracted as a reliable full-turn total" in text
    assert "corrected structural score still unknown" in text
    assert "3/30 positive actual Skill reads" in text
