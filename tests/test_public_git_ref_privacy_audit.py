"""Prevent UUID-shaped private ChatGPT conversation links in published docs.

The historical-audit report is a point-in-time count, not a remote deletion
mechanism or a representation that old Git objects have been removed.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/reports/2026-10-15-public-git-ref-privacy-audit.json"
SUMMARY = ROOT / "docs/reports/2026-10-15-public-git-ref-privacy-audit.md"
REAL_CHAT_LINK = re.compile(
    r"https?://(?:chatgpt[.]com|chat[.]openai[.]com)/c/"
    r"[a-fA-F0-9]{8}(?:-[a-fA-F0-9]{4}){3}-[a-fA-F0-9]{12}"
    r"(?![a-zA-Z0-9-])"
)


def test_real_conversation_deeplink_detection_does_not_confuse_regex_literal() -> None:
    real_shaped = "https://" + "chatgpt.com/c/" + "6acf1234-1111-2222-3333-000000000001"
    assert REAL_CHAT_LINK.search(real_shaped)
    assert REAL_CHAT_LINK.search(r"https?://chatgpt[.]com/c/[a-f0-9]{8}") is None
    assert REAL_CHAT_LINK.search("https://chatgpt.com/c/REDACTED") is None


def test_public_current_docs_do_not_publish_real_uuid_shaped_chat_links() -> None:
    files = [ROOT / "README.md", *ROOT.joinpath("docs").rglob("*")]
    checked = 0
    for path in files:
        if not path.is_file() or path.is_symlink():
            continue
        if path.suffix not in (".md", ".json", ".txt", ".yml", ".yaml"):
            continue
        assert REAL_CHAT_LINK.search(path.read_text(encoding="utf-8", errors="replace")) is None, (
            f"Direct private ChatGPT conversation URL in public source: {path.relative_to(ROOT)}"
        )
        checked += 1
    assert checked >= 20


def test_historical_ref_exposure_is_not_marked_remediated() -> None:
    record = json.loads(REPORT.read_text())
    assert record["schema_version"] == 1
    assert record["audit_date"] == "2026-10-15"
    assert record["public_branch_tips_checked"] == 27
    assert record["public_tags_checked"] == 1
    assert record["current_main_tip_real_link_count"] == 0
    assert record["branch_tips_containing_real_links"] == 20
    assert record["tags_containing_real_links"] == 1
    assert record["distinct_real_links_across_public_ref_tips"] == 2
    assert record["historical_reachable_commits_with_real_links"] == 47
    assert record["main_ancestral_commits_with_real_links"] == 35
    assert "coordinated" in record["action"]
    assert len(record["caveats"]) >= 3
    assert "P6-D stays open" in SUMMARY.read_text()


def test_sanitized_report_contains_no_raw_deeplink() -> None:
    text = REPORT.read_text() + SUMMARY.read_text()
    assert REAL_CHAT_LINK.search(text) is None
    for marker in ("Plugin_", "github_pat_", "session_token=", "Bearer "):
        assert marker not in text
