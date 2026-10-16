"""Bounded native negative control for factory-assigned register declarations.

This intentionally invalid, assistant-authored Mod uses no personal data and
cannot be treated as a real model-origin executable validation. Only the
exact installed Claude Code CLI2.1.296 can establish the expected failure.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent / "fixtures/mods-const-register-rejected"


def test_factory_assigned_const_register_fails_exact_native_target() -> None:
    executable = shutil.which("claude")
    if not executable:
        pytest.skip("Claude Code executable absent: cannot claim native failure")
    version = subprocess.run(  # noqa: S603 -- fixed executable + read-only argument
        [executable, "--version"], capture_output=True, text=True, timeout=15, check=False
    )
    if version.returncode or "2.1.296" not in version.stdout:
        pytest.skip("Native Claude CLI must exactly match approved 2.1.296")

    result = subprocess.run(  # noqa: S603 -- fixed in-repository negative fixture
        [executable, "plugin", "validate", "--strict", str(ROOT)],
        capture_output=True,
        text=True,
        timeout=35,
        check=False,
    )
    assert result.returncode == 1
    assert "register is exported as something other than a function" in (
        result.stdout + result.stderr
    )

    mocked = subprocess.run(  # noqa: S603 -- fake tool only, no network
        [executable, "plugin", "test", str(ROOT)],
        capture_output=True,
        text=True,
        timeout=35,
        check=False,
    )
    assert mocked.returncode == 1
    assert "hooks module did not load" in (mocked.stdout + mocked.stderr)
    assert "1 fail" in (mocked.stdout + mocked.stderr)
