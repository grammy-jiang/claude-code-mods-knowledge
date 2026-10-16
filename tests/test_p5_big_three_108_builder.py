"""Do not publish a seven-stack comparison with missing model turns or unsafe Mac recovery."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_p5_big_three_108_report as pub  # noqa: E402


def _sample_stats() -> dict:
    return {
        "model": "sample",
        "observed": 36,
        "not_observed": 0,
        "native_completed": 35,
        "strict_substantive_completed": 34,
        "positive_exact_source_structural": 3,
        "negative_nonactivation_observed": 9,
        "boundary_scope_violations": 2,
        "incomplete_or_loop": 2,
        "median_seconds_completed": 33.5,
        "p95_seconds_completed_nearest_rank": 55.5,
        "states": {"positive_exact_claim_or_source_missing": 9},
    }


def test_incomplete_model_evidence_never_published(monkeypatch: pytest.MonkeyPatch) -> None:
    previous = json.loads(pub.PREVIOUS.read_text())
    data = {
        "observed": 107,
        "unobserved": 1,
        "source_sha256": previous["frozen_cases_source_sha256"],
        "rows": [{} for _ in range(108)],
    }
    monkeypatch.setattr(pub, "summarize", lambda: data)
    with pytest.raises(ValueError):
        pub.report()


def test_missing_original_sha_or_exposed_candidate_never_accepted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    previous = json.loads(pub.PREVIOUS.read_text())
    data = {
        "observed": 108,
        "unobserved": 0,
        "source_sha256": previous["frozen_cases_source_sha256"],
        "rows": [
            {
                "event_sha256": None,
                "status": "positive_source_structure_only",
                "raw_model_output_exposed": False,
            }
            for _ in range(108)
        ],
    }
    monkeypatch.setattr(pub, "summarize", lambda: data)
    with pytest.raises(ValueError):
        pub.report()
    data["rows"][0]["event_sha256"] = "e" * 64
    data["rows"][0]["raw_model_output_exposed"] = True
    with pytest.raises(ValueError):
        pub.report()


def test_model_window_must_end_with_original_service_restoration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    row = {"candidate": "gpt-oss", "trial": 1, "part": 1, "source_sha256": "a" * 64}
    folder = tmp_path / "sample-window"
    folder.mkdir()
    state = {
        "phase": "complete",
        "restore_confirmed": False,
        "fatal_error": None,
        "candidate": row["candidate"],
        "trial": row["trial"],
        "window_part": row["part"],
        "source_sha256": row["source_sha256"],
        "restore": {"all_five_running": True, "qwen_api_healthy": True},
        "models": [
            {
                "model": "gpt-oss-120b",
                "ready": True,
                "stop_success": True,
                "cases": [{} for _ in range(6)],
            }
        ],
    }
    (folder / "live_state.json").write_text(json.dumps(state))
    monkeypatch.setattr(pub, "windows", lambda: [row])
    monkeypatch.setattr(pub, "window_dir", lambda ignored: folder)
    with pytest.raises(ValueError):
        pub.verified_resources()
    state["restore_confirmed"] = True
    (folder / "live_state.json").write_text(json.dumps(state))
    assert pub.verified_resources()[0]["all_original_services_restored"] is True


def test_same_original_frozen_12_cases_as_codex_and_local_qwen() -> None:
    earlier = json.loads(pub.PREVIOUS.read_text())
    this_suite = json.loads((ROOT / "evals/p5_big_three_auto_12x3.json").read_text())
    assert earlier["frozen_cases_source_sha256"] == this_suite["source_sha256"]
    assert earlier["case_count_per_stack"] == 12
    assert this_suite["expected_total_model_trials"] == 108
