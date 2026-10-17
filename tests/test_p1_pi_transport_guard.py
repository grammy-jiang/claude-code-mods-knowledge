"""Pi native adapter never accepts arbitrary evidence without scoped approval."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run_p5_big_three_case as native  # noqa: E402


def test_pi_runner_rejects_path_without_matching_delivery(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="path/envelope"):
        native.runner(
            "POS-E-01", "auto", 95, candidate="gpt-oss",
            evidence_preload_path=tmp_path / "approved-task-evidence.txt",
        )


def test_pi_runner_rejects_forged_delivery_before_any_inference(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Unverified Pi evidence envelope"):
        native.runner(
            "POS-E-01", "auto", 95, candidate="gpt-oss",
            evidence_preload_path=tmp_path / "approved-task-evidence.txt",
            evidence_delivery="arbitrary content",  # type: ignore[arg-type]
        )
