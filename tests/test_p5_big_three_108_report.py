"""108 frozen model turns need original SHA evidence and 18 verified rollbacks."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_p5_big_three_108_report as publish  # noqa: E402
import score_p5_big_three_108 as scorer  # noqa: E402


def test_private_cohort_never_fabricates_a_missing_trial(tmp_path: Path) -> None:
    observed = scorer.summarize(tmp_path)
    assert observed["planned_model_turns"] == 108
    assert observed["observed"] == 0
    assert observed["unobserved"] == 108
    assert all(r["status"] == "not_observed" for r in observed["rows"])
    assert observed["full_p5_acceptance"] is False


def test_publisher_refuses_partial_evidence(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        publish,
        "summarize",
        lambda: {
            "observed": 107,
            "unobserved": 1,
            "rows": [{}] * 108,
            "source_sha256": "a" * 64,
        },
    )
    with pytest.raises(ValueError):
        publish.report()


def test_pub_refuses_fake_native_sha_even_if_claimed_observed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    previous = json.loads(publish.PREVIOUS.read_text())
    fake = {
        "observed": 108,
        "unobserved": 0,
        "source_sha256": previous["frozen_cases_source_sha256"],
        "rows": [
            {"status": "positive_source_structure_only", "event_sha256": None} for _ in range(108)
        ],
    }
    monkeypatch.setattr(publish, "summarize", lambda: fake)
    with pytest.raises(ValueError):
        publish.report()


def test_window_validator_blocks_unverified_service_rollback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    row = {"candidate": "gpt-oss", "trial": 1, "part": 1, "source_sha256": "a" * 64}
    folder = tmp_path / "window"
    folder.mkdir()
    j = {
        "phase": "complete",
        "restore_confirmed": False,
        "candidate": row["candidate"],
        "trial": row["trial"],
        "window_part": row["part"],
        "source_sha256": row["source_sha256"],
        "restore": {"all_five_running": False, "qwen_api_healthy": False},
        "models": [
            {
                "model": "gpt-oss-120b",
                "ready": True,
                "stop_success": True,
                "cases": [{} for _ in range(6)],
            }
        ],
    }
    (folder / "live_state.json").write_text(json.dumps(j))
    monkeypatch.setattr(publish, "windows", lambda: [row])
    monkeypatch.setattr(publish, "window_dir", lambda ignored: folder)
    with pytest.raises(ValueError):
        publish.verified_resources()
    j["restore_confirmed"] = True
    j["restore"] = {"all_five_running": True, "qwen_api_healthy": True}
    (folder / "live_state.json").write_text(json.dumps(j))
    assert len(publish.verified_resources()) == 1


def test_sources_frozen_exactly_same_as_previous_cohorts() -> None:
    earlier = json.loads(publish.PREVIOUS.read_text())
    plan = json.loads((ROOT / "evals/p5_big_three_auto_12x3.json").read_text())
    assert plan["source_sha256"] == earlier["frozen_cases_source_sha256"]
    assert (
        hashlib.sha256((ROOT / plan["source_file"]).read_bytes()).hexdigest()
        == plan["source_sha256"]
    )
