"""Offline isolation and fail-closed checks for sequential Gemma maintenance."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import orchestrate_p5_gemma_paired as orchestrator  # noqa: E402


def test_no_gemma_observations_are_inferred_from_missing_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(orchestrator, "PRIVATE", tmp_path)
    cases = orchestrator.pending(3)
    assert len(cases) == 12
    case = cases[0]
    f = tmp_path / "paired/gemma31" / case / "trial-3/report.json"
    f.parent.mkdir(parents=True)
    f.write_text(json.dumps({"case_id": case}))
    assert case not in orchestrator.pending(3)
    assert len(orchestrator.pending(3)) == 11


def test_never_begin_if_previous_owner_failed_to_restore(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(orchestrator, "PRIVATE", tmp_path)
    assert orchestrator.previous_window_safe()
    root = tmp_path / "gemma-windows/round-1"
    root.mkdir(parents=True)
    prior = root / "window-failed.json"
    prior.write_text(
        json.dumps({"phase": "complete_with_blocker", "qwen_restored": False, "complete": True})
    )
    assert not orchestrator.previous_window_safe()
    prior.write_text(json.dumps({"phase": "complete", "qwen_restored": True, "complete": True}))
    assert orchestrator.previous_window_safe()


def test_readiness_requires_original_services_safe_ram_no_qwen_clients(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot = {
        "service_states": {"original-qwen": True, "other": True},
        "qwen_healthy": True,
        "test_port_clear": True,
        "active_qwen_clients": 0,
        "memory_pressure": 70,
        "swap_mib": 5,
    }
    monkeypatch.setattr(orchestrator, "snapshot", lambda: snapshot)
    assert orchestrator.healthy_to_switch()
    for key, value in (
        ("active_qwen_clients", 1),
        ("memory_pressure", 40),
        ("swap_mib", 600),
        ("qwen_healthy", False),
        ("test_port_clear", False),
    ):
        candidate = {**snapshot, key: value}
        monkeypatch.setattr(orchestrator, "snapshot", lambda v=candidate: v)
        assert orchestrator.healthy_to_switch() is False


def test_window_needs_explicit_verified_rollback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data = {
        "phase": "complete",
        "qwen_restored": True,
        "all_original_services_running": True,
        "default_qwen_api_healthy": True,
    }
    monkeypatch.setattr(
        orchestrator.subprocess,
        "run",
        lambda *args, **kw: SimpleNamespace(returncode=0, stdout=json.dumps(data)),
    )
    assert orchestrator.run_window(2, 3, 540)["qwen_restored"]
    monkeypatch.setattr(
        orchestrator.subprocess,
        "run",
        lambda *args, **kw: SimpleNamespace(
            returncode=0, stdout=json.dumps(data | {"qwen_restored": False})
        ),
    )
    with pytest.raises(orchestrator.MaintenanceError):
        orchestrator.run_window(2, 3, 540)
