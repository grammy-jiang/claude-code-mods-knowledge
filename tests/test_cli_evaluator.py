"""CLI for the P4 static-only evaluation suite."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from mods_knowledge import cli

ROOT = Path(__file__).resolve().parents[1]


def test_cli_eval_runs_p4_offline_without_claiming_runtime_pass(tmp_path: Path) -> None:
    for folder in ("claims", "decisions", "sources", "targets", "evidence", "evals"):
        shutil.copytree(ROOT / folder, tmp_path / folder)
    result = tmp_path / "p4-static-report.json"
    status = cli.main(
        [
            "--root",
            str(tmp_path),
            "eval",
            "--suite",
            "evals/p4_cases.json",
            "--report",
            str(result),
        ]
    )
    assert status == 0
    report = json.loads(result.read_text())
    assert report["cases_total"] == 46
    assert report["resource_checks_passed"] == 46
    assert report["host_runtime_cases_passed"] == 0
    assert report["host_runtime_cases_pending"] == 46
    assert report["status"] == "STATIC_PASS_HOST_NOT_TESTED"


def test_cli_eval_fails_closed_for_wrong_version(tmp_path: Path, capsys) -> None:
    for folder in ("claims", "decisions", "sources", "targets", "evidence", "evals"):
        shutil.copytree(ROOT / folder, tmp_path / folder)
    suite_path = tmp_path / "evals/p4_cases.json"
    data = json.loads(suite_path.read_text())
    data["target"]["claude_code_version"] = "2.1.310"
    suite_path.write_text(json.dumps(data))
    assert cli.main(["--root", str(tmp_path), "eval"]) == 2
    assert (
        "approved" in capsys.readouterr().err.lower() or "scope" in capsys.readouterr().err.lower()
    )
