"""Managed native PreToolUse denies when either local or MAC authority fails."""

from __future__ import annotations

import importlib.util
import json
import sys
from io import BytesIO
from pathlib import Path

import pytest

from mods_knowledge.cli304_coordinator_grant import GrantBlocked
from mods_knowledge.cli304_supervised_lease import SupervisorBlocked

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
SOURCE = SCRIPTS / "cli304_coordinator_pretool.py"
_spec = importlib.util.spec_from_file_location("native_mac_coordinator_pretool", SOURCE)
assert _spec and _spec.loader
m = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(m)


@pytest.fixture
def resources(tmp_path: Path):
    return dict(
        lease=tmp_path / "lease.private.json",
        workspace=tmp_path,
        request=tmp_path / "request.private.json",
        grant=tmp_path / "grant.private.json",
        public=tmp_path / "public.pem",
        receipt=tmp_path / "receipt.private.json",
        openssl=Path(sys.executable).resolve(),
    )


def test_valid_qa_event_requires_two_independent_checks(resources, monkeypatch):
    observed = []
    monkeypatch.setattr(m, "check_supervisor", lambda *args, **kwargs: observed.append("local"))
    monkeypatch.setattr(m, "authorized", lambda *args, **kwargs: observed.append("mac"))
    assert m.check({"hook_event_name": "PreToolUse"}, **resources) is None
    assert observed == ["local", "mac"]


def test_local_frozen_state_refuses_without_treating_valid_mac_grant_as_enough(
    resources, monkeypatch
):
    monkeypatch.setattr(
        m,
        "check_supervisor",
        lambda *args, **kwargs: (_ for _ in ()).throw(SupervisorBlocked("FROZEN")),
    )
    mac_called = []
    monkeypatch.setattr(m, "authorized", lambda *args, **kwargs: mac_called.append(True))
    with pytest.raises(SupervisorBlocked, match="FROZEN"):
        m.check({"hook_event_name": "PreToolUse"}, **resources)
    assert mac_called == []


def test_mac_expiry_blocks_even_if_local_supervisor_would_allow(resources, monkeypatch):
    monkeypatch.setattr(m, "check_supervisor", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        m,
        "authorized",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            GrantBlocked("MAC_AUTHORITY_MONOTONIC_LEASE_EXPIRED")
        ),
    )
    with pytest.raises(GrantBlocked, match="MONOTONIC_LEASE_EXPIRED"):
        m.check({"hook_event_name": "PreToolUse"}, **resources)


def test_malformed_event_returns_blocking_exit_code_without_fallback(
    resources, monkeypatch, capsys
):
    class BadStdin:
        buffer = BytesIO(b"malformed{")

    monkeypatch.setattr(m.sys, "stdin", BadStdin())
    argv = [str(SOURCE)]
    for key, path in resources.items():
        argv.extend([f"--{key}", str(path)])
    monkeypatch.setattr(m.sys, "argv", argv)
    assert m.main() == 2
    assert "MAC_AUTHORITY_QA_DENIED" in capsys.readouterr().err


def test_grant_verification_failure_returns_blocking_exit_code(resources, monkeypatch, capsys):
    class Input:
        buffer = BytesIO(json.dumps({"hook_event_name": "PreToolUse"}).encode())

    monkeypatch.setattr(m.sys, "stdin", Input())
    argv = [str(SOURCE)]
    for key, path in resources.items():
        argv.extend([f"--{key}", str(path)])
    monkeypatch.setattr(m.sys, "argv", argv)
    monkeypatch.setattr(m, "check_supervisor", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        m,
        "authorized",
        lambda *args, **kwargs: (_ for _ in ()).throw(GrantBlocked("REPLAYED_OLD_GRANT")),
    )
    assert m.main() == 2
    assert "MAC_AUTHORITY_QA_DENIED" in capsys.readouterr().err
