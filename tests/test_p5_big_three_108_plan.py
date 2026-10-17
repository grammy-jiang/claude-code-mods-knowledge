"""Freeze 108 real local Pi research turns and reject unsafe window scores."""

from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import orchestrate_p5_big_three_108 as orchestrator  # noqa: E402
from run_p5_big_three_case import MODEL_CANDIDATES, PAIRING_MANIFEST, THINKING  # noqa: E402


def test_native_large_model_frozen_cases_exact_108() -> None:
    m = json.loads(PAIRING_MANIFEST.read_text())
    src = ROOT / m["source_file"]
    assert hashlib.sha256(src.read_bytes()).hexdigest() == m["source_sha256"]
    original = {row["id"]: row for row in json.loads(src.read_text())["cases"]}
    assert len(m["case_ids"]) == len(set(m["case_ids"])) == 12
    assert Counter(original[cid]["category"] for cid in m["case_ids"]) == {
        "positive": 4,
        "negative": 4,
        "boundary": 4,
    }
    assert m["repetitions"] == 3
    assert m["expected_total_model_trials"] == 108
    assert m["context_window"] == 16384
    assert m["max_output_tokens"] == 6144
    assert {v[1] for v in MODEL_CANDIDATES.values()} == {row["id"] for row in m["models"]}
    assert THINKING == {"gpt-oss": "medium", "mistral": "off", "heretic": "off"}


def test_windows_are_non_overlapping_exact_original_case_triples() -> None:
    chunks = orchestrator.windows()
    assert len(chunks) == 18
    assert all(len(c["case_ids"]) == 6 for c in chunks)
    assert len({(w["candidate"], w["trial"], w["part"]) for w in chunks}) == 18
    assert Counter((w["candidate"], w["trial"], cid) for w in chunks for cid in w["case_ids"]) == {
        (name, trial, cid): 1
        for name in orchestrator.MODELS
        for trial in (1, 2, 3)
        for cid in json.loads(PAIRING_MANIFEST.read_text())["case_ids"]
    }
    assert all(
        w["source_sha256"] == json.loads(PAIRING_MANIFEST.read_text())["source_sha256"]
        for w in chunks
    )


def test_no_window_resumes_if_prior_restoration_is_unverified(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(orchestrator, "PRIVATE", tmp_path)
    row = orchestrator.windows()[0]
    assert orchestrator.safe_prior_state(row) is None
    folder = orchestrator.window_dir(row)
    folder.mkdir(parents=True)
    with pytest.raises(orchestrator.BigModelWindowError):
        orchestrator.safe_prior_state(row)
    state = {
        "candidate": row["candidate"],
        "trial": row["trial"],
        "window_part": row["part"],
        "phase": "complete",
        "restore_confirmed": False,
        "restore": {"all_five_running": False, "qwen_api_healthy": False},
        "models": [
            {
                "model": orchestrator.MODEL_IDS[row["candidate"]],
                "ready": True,
                "stop_success": True,
                "cases": [{} for _ in range(6)],
            }
        ],
    }
    (folder / "live_state.json").write_text(json.dumps(state))
    with pytest.raises(orchestrator.BigModelWindowError):
        orchestrator.safe_prior_state(row)
    state["restore_confirmed"] = True
    state["restore"] = {"all_five_running": True, "qwen_api_healthy": True}
    (folder / "live_state.json").write_text(json.dumps(state))
    assert orchestrator.safe_prior_state(row) is not None


def test_user_original_services_are_never_implicitly_assumed_healthy() -> None:
    assert len(orchestrator.SERVICES) == 5
    assert orchestrator.SERVICES[0] == "com.grammy.qwen36-omlx"
    assert all("127.0.0.1" in v[2] for v in MODEL_CANDIDATES.values())
    source = (ROOT / "scripts/p5_big_three_window_controller.py").read_text()
    assert "memory_pressure_pct" in source
    assert 'memory_pressure_pct"] < 50' not in source
    assert '"--memory-guard",' in source
    assert '"off"' in source
    assert "4096" in source


def test_research_output_buffers_native_text_in_private_files() -> None:
    source = (ROOT / "scripts/run_p5_big_three_case.py").read_text()
    assert "response_stream_buffered" in source
    assert "raw_output_exposed" in source
    assert "NativeRepeatGuard" in source
    assert "signal.signal(signal.SIGTERM, _stop_native_child)" in source
    assert "substantive_completed_answer" in source
