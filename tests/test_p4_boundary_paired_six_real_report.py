"""Real beta010 paired control evidence is scoped; no 100% inference claims."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/reports/2026-10-18-cli302-beta010-boundary-paired-six.json"


def test_boundary_pair_results_do_not_count_safe_no_skill_as_real_activation() -> None:
    r = json.loads(REPORT.read_text())
    assert r["plugin_version"] == "0.4.10-beta.1"
    assert r["target_cli"] == "2.1.302"
    assert r["source_revision"] == "b9ea3063393e33259298ddcac02104b16c42b208"
    assert r["total_distinct_sent_and_read_originals"] == 6
    assert r["observed_counts"] == {
        "natural_cases": 3,
        "natural_actual_skill_reads": 2,
        "natural_skill_and_reference_reads": 2,
        "explicit_cases": 3,
        "explicit_actual_skill_reads": 3,
        "explicit_skill_and_reference_reads": 3,
    }
    assert r["has_full_boundary_qualification"] is False
    assert r["stable_release_authorized"] is False
    assert r["tool_metadata_independently_refetched"] is False
    rows = r["paired_cases"]
    assert len(rows) == 6
    assert [(x["case_id"], x["condition"], x["actual_plugin_skill_read"]) for x in rows] == [
        ("BOUND-VERSION-OLD", "natural", True),
        ("BOUND-VERSION-OLD", "explicit", True),
        ("BOUND-VERSION-NEW", "natural", True),
        ("BOUND-VERSION-NEW", "explicit", True),
        ("BOUND-PLUGIN-PRIV", "natural", False),
        ("BOUND-PLUGIN-PRIV", "explicit", True),
    ]
    assert all(x["generated_code_and_safety_semantics_pass"] is False for x in rows)


def test_original_paired_report_is_private_content_free() -> None:
    raw = REPORT.read_text()
    for forbidden in (
        "/home/",
        "/Users/",
        "Cookie:",
        "Authorization:",
        "Plugin_",
        "TASK_ID:",
        "chatgpt.com/c/",
        "raw_reply",
        "sandbox:/mnt/data",
    ):
        assert forbidden not in raw
    assert re.search(r"gh[pousr]_[A-Za-z0-9]{20,}", raw) is None
    assert all(
        re.fullmatch(r"[0-9a-f]{64}", row["original_visible_answer_sha256"])
        for row in json.loads(raw)["paired_cases"]
    )
