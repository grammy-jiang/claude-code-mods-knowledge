"""Model maintenance helper cannot casually stop services or disable guards."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import run_p5_gemma_window as job  # noqa: E402


def good() -> dict:
    return {
        "service_states": {name: True for name in job.SERVICES},
        "memory_pressure": 78,
        "swap_mib": 2.0,
        "qwen_healthy": True,
        "test_port_clear": True,
        "active_qwen_clients": 0,
    }


def test_dry_run_never_bootouts_daemons(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(job, "snapshot", good)
    calls = []
    monkeypatch.setattr(
        job,
        "cmd",
        lambda a, **kw: calls.append(a) or type("Result", (), {"returncode": 0, "stdout": ""})(),
    )
    data = job.run(1, max_cases=4, window_seconds=420, execute=False)
    assert data["phase"] == "dry_run_safe"
    assert data["model_calls"] == 0
    assert calls == [["sudo", "-n", "true"]]


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("memory_pressure", 50),
        ("swap_mib", 600.0),
        ("qwen_healthy", False),
        ("test_port_clear", False),
        ("active_qwen_clients", 1),
    ],
)
def test_bad_service_or_resource_snapshot_refuses_change(
    monkeypatch: pytest.MonkeyPatch, key: str, value
) -> None:
    s = good()
    s[key] = value
    monkeypatch.setattr(job, "snapshot", lambda: s)
    monkeypatch.setattr(job, "cmd", lambda *x, **kw: pytest.fail("must not touch system"))
    with pytest.raises(job.MaintenanceError):
        job.run(1, max_cases=4, window_seconds=420, execute=True)


def test_server_source_stays_original_in_prepared_copy(tmp_path: Path) -> None:
    if not job.SERVER_ORIGINAL.is_file():
        pytest.skip("Mac lab supervisor not installed on CI")
    before = job.SERVER_ORIGINAL.read_bytes()
    copy = job.prepared_supervisor(tmp_path)
    assert (
        hashlib.sha256(job.SERVER_ORIGINAL.read_bytes()).digest() == hashlib.sha256(before).digest()
    )
    assert "p5-gemma-supervisor.py" in copy.read_text()
    assert "gemma4-31b-mtp" in copy.read_text()
    assert copy.stat().st_size > 6000


def test_invalid_window_rejected_before_any_operation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(job, "snapshot", lambda: pytest.fail("Invalid task should not preflight"))
    with pytest.raises(job.MaintenanceError):
        job.run(1, max_cases=9, window_seconds=420, execute=True)
