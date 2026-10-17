"""Do not confuse genuine 252-turn source QA with model or Mod code certification."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_p5_p123_report as publisher  # noqa: E402
import score_p5_p123_seven as scorer  # noqa: E402

JSON = ROOT / "docs/reports/2026-10-17-p5-p123-seven-stack-12x3.json"
MD = JSON.with_suffix(".md")

EXPECTED = {
    "qwen": (7, 9, 0, 13, 0),
    "gemma31": (8, 9, 0, 15, 0),
    "gpt-oss": (3, 8, 0, 11, 0),
    "mistral": (0, 8, 1, 8, 0),
    "heretic": (7, 4, 2, 5, 0),
    "codex_no_web": (6, 12, 0, 0, 0),
    "codex": (8, 11, 0, 0, 1),
}


def test_new_study_has_exactly_252_hash_verified_original_turns() -> None:
    report = json.loads(JSON.read_text())
    assert report["schema_version"] == 1
    assert report["actual_native_attempts"] == 252
    assert report["local_native_attempts"] == 180
    assert report["codex_native_attempts"] == 72
    assert report["frozen_cases"] == 12 and report["repetitions"] == 3
    assert set(report["models"]) == set(EXPECTED)
    rows = report["rows"]
    manifest = json.loads((ROOT / "evals/p5_p123_seven_stack_12x3.json").read_text())
    assert len(rows) == 252
    assert len({(r["model"], r["case_id"], r["trial"]) for r in rows}) == 252
    assert {(r["model"], r["case_id"], r["trial"]) for r in rows} == {
        (model, cid, trial)
        for model in EXPECTED
        for cid in manifest["case_ids"]
        for trial in (1, 2, 3)
    }
    assert (
        report["source_revision"]
        == hashlib.sha256((ROOT / manifest["source_file"]).read_bytes()).hexdigest()
    )
    assert all(re.fullmatch(r"[a-f0-9]{64}", r["raw_events_sha256"]) for r in rows)
    assert all(r["status"] != "not_observed" for r in rows)


def test_quality_table_does_not_fabricate_any_improvement_or_safe_version() -> None:
    m = json.loads(JSON.read_text())["models"]
    for name, observed in EXPECTED.items():
        stat = m[name]
        actual = (
            stat["positive_exact_source_structural"],
            stat["negative_nonactivation_observed"],
            stat["detected_boundary_violations"],
            stat["P3_buffered_delivery_permitted"],
            stat["positive_selected_evidence_actually_read"],
        )
        assert actual == observed
        assert stat["observed"] == 36
        assert (
            0
            <= stat["positive_source_with_actual_new_skill_read"]
            <= stat["positive_exact_source_structural"]
        )
    assert m["qwen"]["old_positive_exact_source_structural"] == 2
    assert m["gemma31"]["old_positive_exact_source_structural"] == 3
    assert m["gpt-oss"]["old_positive_exact_source_structural"] == 0
    assert m["mistral"]["old_positive_exact_source_structural"] == 0
    assert m["heretic"]["old_positive_exact_source_structural"] == 0
    assert m["codex_no_web"]["old_positive_exact_source_structural"] == 12
    assert m["codex"]["old_positive_exact_source_structural"] == 11
    assert m["codex_no_web"]["positive_source_with_actual_new_skill_read"] == 5
    assert m["codex"]["positive_source_with_actual_new_skill_read"] == 8


def test_resource_and_production_limitations_honestly_recorded() -> None:
    r = json.loads(JSON.read_text())
    resources = r["resources"]
    assert resources["windows_verified"] == 30
    assert resources["local_native_attempts"] == 180
    assert resources["original_service_state_preserved"] is True
    assert resources["temporary_model_stopped_per_window"] is True
    assert resources["original_model_port_closed_per_window"] is True
    assert len(resources["windows"]) == 30
    assert len({(w["model"], w["trial"], w["part"]) for w in resources["windows"]}) == 30
    assert r["production_mod_semantics_verified"] is False
    assert r["chatgpt_chat_mode_skill_activation_verified"] is False
    assert r["target_native_cli_test_2_1_296_completed"] is False
    assert r["P3_delivery_gate_available_in_all_hosts"] is False
    assert r["strict_skill_automation_not_fine_tuning"] is True
    assert r["model_parameters_unchanged"] is True
    assert r["original_model_text_private"] is True
    assert all(
        row["private_model_text_released"] is False and row["P3_semantic_code_approval"] is False
        for row in r["rows"]
    )


def test_codex_isolation_and_incomplete_model_are_not_faked_as_complete() -> None:
    r = json.loads(JSON.read_text())
    rows = [x for x in r["rows"] if x["model"] == "codex"]
    assert len(rows) == 36
    assert sum(x["native_completed"] is False for x in rows) == 2
    assert all(x["P3_buffered_delivery_permitted"] is False for x in rows)
    assert all(x["registered_isolated_skill"] is True for x in rows)
    disabled = [x for x in r["rows"] if x["model"] == "codex_no_web"]
    assert len(disabled) == 36
    assert sum(x["native_web_search_count"] for x in disabled) == 0


def test_public_report_excludes_private_model_text_and_host_identifiers() -> None:
    combined = JSON.read_text() + "\n" + MD.read_text()
    assert "not implemented on" in combined.lower() or "not a" in combined.lower()
    assert "selected-evidence" in combined
    assert "0/12" in MD.read_text()
    assert not re.search(r"/Users/[^/\s]+|/home/grammy-jiang/|/tmp/", combined)
    assert not re.search(r"sk-[A-Za-z0-9]{20,}", combined)
    assert not re.search(r"Bearer\s+[A-Za-z0-9._-]{20,}", combined)
    assert not re.search(r"chatgpt\.com/c/[0-9a-f-]{36}", combined, re.I)


def test_missing_or_forged_original_evidence_causes_fail_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(scorer, "PRIVATE", tmp_path)
    with pytest.raises((ValueError, OSError)):
        scorer.complete_report()
    monkeypatch.setattr(
        publisher,
        "complete_report",
        lambda: {
            "actual_native_attempts": 251,
            "resources": {"windows_verified": 30},
            "rows": [{}] * 252,
            "models": {name: {} for name in EXPECTED},
        },
    )
    with pytest.raises(ValueError):
        publisher.build()
