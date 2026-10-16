"""No-web Codex cohort must independently prove the web tool was absent."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import run_p5_codex_paired as runner  # noqa: E402
import score_p5_codex_no_web as no_web  # noqa: E402


def fixture_report(tmp_path: Path, *, actual_web_search: bool = False) -> None:
    root = tmp_path / "no-web/paired/gpt-6.1-sol/POS-E-01/trial-1"
    root.mkdir(parents=True)
    event = {
        "method": "item/completed",
        "params": {
            "item": {
                "type": "webSearch" if actual_web_search else "commandExecution",
            }
        },
    }
    text = json.dumps(event) + "\n"
    (root / "native-wire.jsonl").write_text(text)
    report = {
        "case_id": "POS-E-01",
        "trial": 1,
        "candidate": "codex",
        "model_requested": "gpt-6.1-sol",
        "effort_requested": "medium",
        "source_revision": runner.SOURCE,
        "original_case_file_sha256": runner.frozen()["source_sha256"],
        "raw_output_exposed": False,
        "raw_transcript_private": True,
        "semantic_review_complete": False,
        "native_mod_runtime_verified": False,
        "web_search_disabled_requested": True,
        "native_web_search_count": 0,
        "native_wire_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "elapsed_s": 14.0,
        "evidence": {
            "state": "native_turn_recorded",
            "model_server_resolved": "gpt-6.1-sol",
            "effort_server_resolved": "medium",
            "model_provider_server_resolved": "openai",
            "model_provenance": "same-thread-app-server-response+thread-read",
            "prompt_matched": True,
            "agent_completed": True,
            "answer_present": True,
            "skill_loaded": True,
            "reference_read": True,
            "source_verdict": "pass",
            "risk_flags": [],
            "manual_review_flags": [],
        },
    }
    (root / "report.json").write_text(json.dumps(report))


def test_missing_no_web_cases_still_count_as_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(no_web, "PRIVATE", tmp_path)
    report = no_web.summarize()
    assert report["codex_observed"] == 0 and report["codex_unobserved"] == 36
    assert report["web_search_disabled"] is True
    assert report["all_observed_trials_web_search_count"] == 0


def test_legitimate_tool_only_offline_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture_report(tmp_path)
    monkeypatch.setattr(no_web, "PRIVATE", tmp_path)
    s = no_web.summarize()
    assert s["codex_observed"] == 1
    assert s["stat"]["positive_exact_source_structural"] == 1
    assert s["rows"][0]["model"] == "codex_no_web"
    assert s["rows"][0]["native_web_search_calls"] == 0


def test_fake_web_disabled_metadata_does_not_hide_actual_web_search(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture_report(tmp_path, actual_web_search=True)
    monkeypatch.setattr(no_web, "PRIVATE", tmp_path)
    with pytest.raises(ValueError):
        no_web.summarize()


def test_no_web_runner_requires_explicit_offline_parameter_in_new_trial() -> None:
    # Changing the model config to read-only does NOT disable webSearch.
    # Test the actual separate web_search disabled app-server switch.
    text = (ROOT / "scripts/run_p5_codex_native.py").read_text()
    assert 'web_search="disabled"' in text
    text = (ROOT / "scripts/run_p5_codex_paired.py").read_text()
    assert '"web_search_disabled_requested": no_web' in text
