"""Host discovery checks are source/package read-only and consume zero model tokens."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/verify_host_skill_discovery.py"


def _script():
    spec = importlib.util.spec_from_file_location("host_discovery_test_module", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_declares_missing_agents_unavailable_not_a_faked_pass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _script()
    monkeypatch.setattr(module.shutil, "which", lambda _name: None)
    dist = tmp_path / "dist"
    work = tmp_path / "work"
    dist.mkdir()
    work.mkdir()
    assert module._pi_skill_lookup(dist, work)["status"] == "unavailable"
    assert module._codex_skill_lookup(dist, work)["status"] == "unavailable"
    assert module._claude_manifest_check(dist, work)["status"] == "unavailable"


def test_host_report_does_not_claim_inference_or_real_cli_skill_invocation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from mods_knowledge.compiler import build_artifacts

    module = _script()
    dist = tmp_path / "dist"
    build_artifacts(ROOT, dist, api_version="2.1.296", surface="cli")
    monkeypatch.setattr(module.shutil, "which", lambda _name: None)
    report = tmp_path / "host-report.json"
    monkeypatch.setattr(
        "sys.argv",
        ["host_discovery", "--dist", str(dist), "--report", str(report)],
    )
    assert module.main() == 0
    data = json.loads(report.read_text())
    assert data["status"] == "native_discovery_only_model_turns_not_run"
    assert all(
        data[host + "_model_invocation"] == "not_run"
        for host in ("claude_code", "codex", "pi_agent")
    )
    assert all(
        data["host_checks"][host]["status"] == "unavailable"
        for host in ("claude_code", "codex", "pi_agent")
    )
    assert "skills://plugins" not in report.read_text()
    assert "access_token" not in report.read_text()


def test_native_pi_loader_and_codex_server_are_considered_separate_from_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _script()
    # No subprocess calls in this test; ensure missing host binaries cannot
    # claim success in an integration report.
    monkeypatch.setattr(module.shutil, "which", lambda _n: None)
    no_pi = module._pi_skill_lookup(tmp_path, tmp_path)
    no_codex = module._codex_skill_lookup(tmp_path, tmp_path)
    assert no_pi["status"] == "unavailable"
    assert no_codex["status"] == "unavailable"
    assert "model" not in no_pi
    assert "model" not in no_codex
