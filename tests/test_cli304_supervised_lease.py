"""Fail closed if the managed QA host supervisor is frozen, expired, or dead."""

from __future__ import annotations

import json
import os
import stat
import time
from pathlib import Path

import pytest

from mods_knowledge import cli304_supervised_lease as m


@pytest.fixture
def live(tmp_path: Path, monkeypatch):
    root = tmp_path / "private"
    root.mkdir(mode=0o700)
    root.chmod(0o700)
    monkeypatch.setattr(m, "boot_id", lambda: "11111111-2222-4333-8444-555555555555")
    monkeypatch.setattr(m, "start_ticks", lambda pid: 999)
    lease = m.PrivateLease(root / "lease.json", session="session-A-0123456789", ttl=2.0)
    lease.refresh("ready")
    return lease


def test_ready_private_lease_requires_same_parent_and_short_fresh_deadline(live):
    data = m.read_lease(live.path)
    assert data["session"] == live.session
    assert data["phase"] == "ready"
    assert data["generation"] == live.generation
    assert stat.S_IMODE(live.path.stat().st_mode) == 0o600


def test_external_freeze_blocks_future_tool_and_cannot_be_reopened(live):
    live.refresh("frozen")
    with pytest.raises(m.SupervisorBlocked, match="SUPERVISED_HOST_FROZEN"):
        m.read_lease(live.path)
    with pytest.raises(m.SupervisorBlocked, match="BLOCKED_SUPERVISOR_CANNOT_REOPEN"):
        live.refresh("ready")


def test_missing_or_stale_supervisor_deadline_fails_closed(live):
    original = json.loads(live.path.read_text())
    expired = dict(original, deadline_monotonic=time.monotonic() - 0.1)
    m.atomic_lease(live.path, expired)
    with pytest.raises(m.SupervisorBlocked, match="EXPIRED_OR_FUTURE"):
        m.read_lease(live.path)


def test_stale_boot_and_wrong_pid_or_reuse_refused(live, monkeypatch):
    record = json.loads(live.path.read_text())
    m.atomic_lease(live.path, {**record, "boot_id": "alien-boot"})
    with pytest.raises(m.SupervisorBlocked, match="STALE_LINUX_BOOT"):
        m.read_lease(live.path)
    m.atomic_lease(live.path, record)
    monkeypatch.setattr(m, "start_ticks", lambda pid: 1001)
    with pytest.raises(m.SupervisorBlocked, match="SUPERVISOR_PID_REUSED_OR_GONE"):
        m.read_lease(live.path)


def test_missing_lease_symlink_and_insecure_file_refused(live):
    path = live.path
    original = path.read_bytes()
    path.chmod(0o644)
    with pytest.raises(m.SupervisorBlocked, match="INVALID_LEASE_FILE_PERMISSIONS"):
        m.read_lease(path)
    path.chmod(0o600)
    path.unlink()
    with pytest.raises(m.SupervisorBlocked, match="MISSING_PRIVATE_LEASE"):
        m.read_lease(path)
    sibling = path.with_name("actual.private.json")
    sibling.write_bytes(original)
    sibling.chmod(0o600)
    path.symlink_to(sibling)
    with pytest.raises(m.SupervisorBlocked, match="MISSING_PRIVATE_LEASE"):
        m.read_lease(path)


def test_corrupted_session_and_unsafe_directory_refused(live):
    record = json.loads(live.path.read_text())
    m.atomic_lease(live.path, {**record, "session": "<script>"})
    with pytest.raises(m.SupervisorBlocked, match="INVALID_LEASE_SESSION"):
        m.read_lease(live.path)
    live.path.parent.chmod(0o755)
    with pytest.raises(m.SupervisorBlocked, match="INVALID_LEASE_DIRECTORY_PERMISSIONS"):
        m.read_lease(live.path)


def test_atomic_state_never_changes_group_or_world_perms(live):
    for _ in range(20):
        live.refresh()
        assert stat.S_IMODE(live.path.stat().st_mode) == 0o600
    assert live.path.parent.stat().st_uid == os.getuid()
