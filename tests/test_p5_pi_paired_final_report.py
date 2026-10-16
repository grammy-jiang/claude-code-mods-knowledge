"""The published 12x3 comparison is evidence-complete, privacy-safe and
does not turn a claim/source structural check into semantic code acceptance.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL_REPORT = ROOT / "docs/reports/2026-10-17-p5-pi-qwen-gemma31-12x3.json"
HUMAN_REPORT = ROOT / "docs/reports/2026-10-17-p5-pi-qwen-gemma31-12x3.md"
FROZEN = ROOT / "evals/p5_pi_auto_12x3.json"


def test_published_comparison_has_exact_36_model_attempts_each() -> None:
    plan = json.loads(FROZEN.read_text())
    report = json.loads(MODEL_REPORT.read_text())
    assert report["observed_calls"] == 72
    assert report["model_count"] == 2
    assert report["cases_per_model"] == 12
    assert report["repetitions_per_case"] == 3
    assert (
        report["source_sha256"]
        == hashlib.sha256((ROOT / plan["source_file"]).read_bytes()).hexdigest()
    )
    assert report["no_gpt_oss_120b_inference"]
    assert report["model_level_full_semantic_acceptance"] is False
    assert report["version_and_code_manual_validation_still_required"]
    observed = report["rows"]
    assert len(observed) == 72
    assert len({(x["model"], x["case_id"], x["trial"]) for x in observed}) == 72
    assert Counter(x["model"] for x in observed) == {"qwen": 36, "gemma31": 36}
    assert all(
        set(x["case_id"] for x in observed if x["model"] == model and x["trial"] == round_no)
        == set(plan["case_ids"])
        for model in ("qwen", "gemma31")
        for round_no in (1, 2, 3)
    )
    assert all(re.fullmatch(r"[0-9a-f]{64}", x["event_sha256"]) for x in observed)
    assert all(x["status"] != "not_observed" for x in observed)


def test_all_six_maintenance_windows_verified_original_service_health() -> None:
    report = json.loads(MODEL_REPORT.read_text())
    rollback = report["original_services"]
    assert rollback["observed_windows"] == 6
    assert rollback["fully_restored_windows"] == 6
    assert rollback["unverified_windows"] == 0
    assert rollback["all_restorations_verified"] is True
    assert rollback["per_round_window_count"] == {"1": 2, "2": 2, "3": 2}


def test_completed_turns_not_confused_with_semantic_mod_passes() -> None:
    report = json.loads(MODEL_REPORT.read_text())
    stats = {x["model"]: x for x in report["models"]}
    assert stats["qwen"]["observed"] == stats["gemma31"]["observed"] == 36
    assert stats["qwen"]["native_completed"] == 33
    assert stats["gemma31"]["native_completed"] == 34
    assert stats["qwen"]["positive_exact_source_structural"] == 2
    assert stats["gemma31"]["positive_exact_source_structural"] == 3
    assert stats["qwen"]["negative_nonactivation_observed"] == 6
    assert stats["gemma31"]["negative_nonactivation_observed"] == 10
    assert stats["qwen"]["boundary_scope_violations"] == 3
    assert stats["gemma31"]["boundary_scope_violations"] == 3
    assert stats["qwen"]["incomplete_or_loop"] == 3
    assert stats["gemma31"]["incomplete_or_loop"] == 2
    assert stats["qwen"]["median_seconds_completed"] < stats["gemma31"]["median_seconds_completed"]


def test_public_report_contains_no_raw_private_paths_or_tokens() -> None:
    body = MODEL_REPORT.read_text() + "\n" + HUMAN_REPORT.read_text()
    assert "Neither model is approved" in body
    assert "GPT-OSS 120B deferred" in body
    assert "2.1.296" in body
    assert not re.search(r"/Users/[^/\s]+|/home/grammy-jiang/|/tmp/mods-", body)
    assert not re.search(r"https?://[^\s]+/oauth/", body)
    assert not re.search(r"sk-[A-Za-z0-9]{20,}", body)
    assert not re.search(r"Bearer\s+[A-Za-z0-9_.-]{20,}", body)
