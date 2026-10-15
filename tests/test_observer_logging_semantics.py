"""Native Node, network-free control-flow contract for transparent observers.

No actual model-origin code is imported, no user files/credentials are opened,
and a real Mods host runtime has not been claimed. Native CLI strict loading
is reviewed on Mac separately and not replaced by this JS fixture.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent / "fixtures/observer_logging_safety"


def test_synthetic_node_observer_cannot_replace_next_success_or_original_error() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js unavailable: native JS microcontract not verified on this host")
    # noqa: S603 -- fixed in-repository, assistant-authored, network-free fixture.
    result = subprocess.run(  # noqa: S603
        [node, "--test", str(ROOT / "contract.test.mjs")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=12,
        check=False,
    )
    assert result.returncode == 0, result.stdout[-500:] + result.stderr[-500:]
    assert "pass 7" in result.stdout or "pass 7" in result.stderr
    assert "fail 0" in result.stdout or "fail 0" in result.stderr
