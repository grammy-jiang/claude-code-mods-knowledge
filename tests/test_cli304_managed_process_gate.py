"""Real POSIX subprocess gate: opt-in managed work is frozen and drained."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from mods_knowledge.guarded_rollout import (
    GuardedRollout,
    UpdateBlocked,
    fixture_verifier_for_tests_only,
)

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts/guard_cli304_managed_run.py"


@pytest.fixture
def running(tmp_path: Path):
    gate = GuardedRollout(tmp_path / "gate", ttl=120)
    gate.create(["agent-one"], good_version="0.0.1", good_tree="a" * 64)
    secret = gate.enroll("agent-one")
    challenge = gate.challenge("agent-one", secret)
    file = tmp_path / "synthetic-private-baseline.json"
    file.write_text(
        json.dumps(
            {
                "TEST_ONLY": True,
                "session": challenge["session"],
                "challenge": challenge["challenge"],
                "tree": challenge["tree_sha"],
                "epoch": challenge["epoch"],
            }
        )
    )
    gate.attest("agent-one", secret, file, verifier=fixture_verifier_for_tests_only)
    gate.ready()
    token = tmp_path / "secret"
    token.write_text(secret)
    token.chmod(0o600)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    return gate, token, env


def argv(gate, secret_file, *tool_command, timeout=5):
    return [
        sys.executable,
        str(CLI),
        "--state-root",
        str(gate.directory),
        "run",
        "--session-id",
        "agent-one",
        "--secret-file",
        str(secret_file),
        "--timeout-seconds",
        str(timeout),
        "--",
        *tool_command,
    ]


def test_mediated_process_exit_and_status_redact_auth(running):
    gate, token, env = running
    s = subprocess.run(  # noqa: S603 - explicit local QA argv
        argv(gate, token, sys.executable, "-c", "raise SystemExit(3)"),
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert s.returncode == 3
    assert gate.status()["outstanding_permits"] == 0
    r = subprocess.run(  # noqa: S603 - explicit local QA argv
        [sys.executable, str(CLI), "--state-root", str(gate.directory), "status"],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(r.stdout)["phase"] == "ready"
    assert token.read_text() not in r.stdout
    assert "production_wide_guarantee" in r.stdout


def test_real_subprocess_inflight_permit_blocks_update_until_exit(running, tmp_path):
    gate, token, env = running
    marker = tmp_path / "started"
    source = f"from pathlib import Path; import time; Path({str(marker)!r}).write_text('ok'); time.sleep(0.8)"
    process = subprocess.Popen(  # noqa: S603 - explicit local QA argv
        argv(gate, token, sys.executable, "-c", source),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        until = time.monotonic() + 4
        while not marker.exists() and time.monotonic() < until:
            time.sleep(0.015)
        assert marker.exists()
        assert gate.status()["outstanding_permits"] == 1
        gate.begin(transaction_id="test-001", new_version="0.0.2", new_tree="b" * 64)
        with pytest.raises(UpdateBlocked, match="INFLIGHT_PROTECTED_OP"):
            gate.acknowledge("agent-one", token.read_text())
        assert process.wait(timeout=5) == 0
        gate.acknowledge("agent-one", token.read_text())
        assert gate.status()["outstanding_permits"] == 0
        assert gate.status()["acknowledged"] == 1
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=3)


def test_unknown_token_never_launches_child_and_bad_permissions_block(running, tmp_path):
    gate, token, env = running
    marker = tmp_path / "SHOULD_NOT_EXIST"
    token.write_text("X" * 64)
    result = subprocess.run(  # noqa: S603 - explicit local QA argv
        argv(gate, token, sys.executable, "-c", f"open({str(marker)!r},'w').write('x')"),
        env=env,
        capture_output=True,
        text=True,
        timeout=6,
    )
    assert result.returncode == 77
    assert not marker.exists()
    token.chmod(0o644)
    result = subprocess.run(  # noqa: S603 - explicit local QA argv
        argv(gate, token, sys.executable, "-c", "print('UNEXPECTED')"),
        env=env,
        capture_output=True,
        text=True,
        timeout=6,
    )
    assert result.returncode == 77
    assert "UNEXPECTED" not in result.stdout


def test_expired_command_closes_cohort_and_cannot_be_used_to_resume(running):
    gate, token, env = running
    result = subprocess.run(  # noqa: S603 - explicit local QA argv
        argv(gate, token, sys.executable, "-c", "import time; time.sleep(5)", timeout=1),
        env=env,
        capture_output=True,
        text=True,
        timeout=8,
    )
    assert result.returncode == 77
    assert gate.status()["phase"] == "blocked"
    with pytest.raises(UpdateBlocked, match="PROTECTED_ACTION_FROZEN"):
        gate.enter("agent-one", token.read_text())
