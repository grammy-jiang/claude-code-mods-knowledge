"""Guard public multi-Skill experiment data and avoid overstated acceptance."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/reports/2026-10-14-multiskill-routing-a-b.json"


def test_public_ab_has_48_distinct_actual_chat_mode_observations() -> None:
    data = json.loads(REPORT.read_text(encoding="utf-8"))
    assert data["schema_version"] == 1
    assert data["test_mode"] == "real ChatGPT ordinary Chat; NO Work"
    assert data["overall_counts"]["conversations"] == 48
    assert len(data["cohorts"]) == 4
    assert all(x["count"] == 12 for x in data["cohorts"])
    assert data["same_prompt_hashes_and_effort_across_cohorts"] is True
    assert (
        data["original_canonical_skill_and_plugin_description_unchanged_during_two_skill_test"]
        is True
    )
    for row in data["cohorts"]:
        assert row["by_category"]["boundary"]["observed"] == 8
        assert row["by_category"]["negative"]["observed"] == 2
        assert row["by_category"]["positive"]["observed"] == 2
        assert len(row["cases"]) == 12


def test_no_routing_success_or_semantic_claim_is_fabricated() -> None:
    data = json.loads(REPORT.read_text())
    a = data["overall_counts"]
    assert a["two_skill"]["boundary"]["plugin_loaded"] == 7
    assert a["two_skill"]["boundary"]["observed"] == 16
    assert a["single_skill"]["boundary"]["plugin_loaded"] == 3
    assert a["single_skill"]["boundary"]["observed"] == 16
    assert a["two_skill"]["positive"]["plugin_loaded"] == 3
    assert a["single_skill"]["positive"]["plugin_loaded"] == 1
    assert a["two_skill"]["negative"]["plugin_loaded"] == 0
    assert a["single_skill"]["negative"]["plugin_loaded"] == 0
    assert 0.25 < data["boundary_fisher_exact_two_sided_p"] < 0.26
    assert data["statistical_significance_asserted"] is False
    assert data["full_46_case_p4_pass"] is False
    assert data["answered_semantically_approved"] is False
    assert data["account_final_version"] == "0.2.0-beta.1"
    assert data["account_final_status"] == "installed and enabled"
    assert any("NOT byte-identical" in note for note in data["caveats"])


def test_account_content_not_in_public_report() -> None:
    raw = REPORT.read_text()
    for forbidden in (
        "conversation_id",
        "chatgpt.com/c/",
        "/Users/",
        "/home/",
        "Plugin_",
        "Cookie:",
        "Authorization: Bearer",
        "refresh_token",
        "PRIVATE KEY",
    ):
        assert forbidden not in raw
    data = json.loads(raw)
    ids = {c["case_id"] for cohort in data["cohorts"] for c in cohort["cases"]}
    assert len(ids) == 12
    checks = {}
    for cohort in data["cohorts"]:
        assert cohort["plugin_version"] in ("0.2.0-router.1", "0.2.0-beta.1")
        for case in cohort["cases"]:
            assert set(case) == {
                "case_id",
                "category",
                "actual_plugin_resource_read",
                "loaded_skill_names",
                "read_resource_count",
                "prompt_sha256",
            }
            checksum = case["prompt_sha256"]
            assert re.fullmatch(r"[a-f0-9]{64}", checksum)
            checks.setdefault(case["case_id"], set()).add(checksum)
    assert all(len(v) == 1 for v in checks.values())
