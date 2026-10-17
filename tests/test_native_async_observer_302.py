"""Bounded real CLI2.1.302 offline Plugin-loader smoke for K-0037.

This is NOT a model-inference or production-host test. CI machines without the
exact CLI skip this native acceptance rather than fabricate a success.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent / "fixtures/mods-async-observer"


def test_exact_target_cli_accepts_fail_isolated_async_observer_hook() -> None:
    executable = shutil.which("claude")
    if executable is None:
        pytest.skip("Claude Code CLI is absent; cannot certify native Mod tests")

    # noqa: S603 -- only native installed claude binary and a fixed --version arg.
    version = subprocess.run(  # noqa: S603
        [executable, "--version"], capture_output=True, text=True, timeout=15, check=False
    )
    if version.returncode != 0 or "2.1.302" not in version.stdout:
        pytest.skip("Installed Claude Code version is not reviewed CLI 2.1.302")

    assert (ROOT / "tests/observer.test.ts").is_file()
    assert (ROOT / "hooks/register.js").is_file()
    # Fixed in-repository, assistant-authored, network-free synthetic fixtures.
    strict = subprocess.run(  # noqa: S603
        [executable, "plugin", "validate", "--strict", str(ROOT)],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert strict.returncode == 0, (strict.stdout + strict.stderr)[-600:]

    observed = subprocess.run(  # noqa: S603
        [executable, "plugin", "test", str(ROOT)],
        capture_output=True,
        text=True,
        timeout=35,
        check=False,
    )
    assert observed.returncode == 0, (observed.stdout + observed.stderr)[-650:]
    output = observed.stdout + observed.stderr
    assert "1 pass" in output and "0 fail" in output
    assert "synthetic rejected diagnostic must not alter mocked tool success" in output
