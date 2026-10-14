"""CLI must explain P6 blockers without claiming stable release or leaking chats."""

import json
from pathlib import Path

from mods_knowledge import cli
from mods_knowledge.compiler import build_artifacts

ROOT = Path(__file__).resolve().parents[1]


def test_missing_host_and_chat_evidence_blocks_but_produces_safe_report(
    tmp_path: Path, capsys
) -> None:
    dist = tmp_path / "dist"
    build_artifacts(
        ROOT,
        dist,
        api_version="2.1.296",
        surface="cli",
        package_version="0.3.0",
        source_revision="1" * 40,
    )
    output = tmp_path / "readiness.json"
    code = cli.main(
        [
            "--root",
            str(ROOT),
            "stable-readiness",
            "--dist",
            str(dist),
            "--out",
            str(output),
            "--require-ready",
        ]
    )
    assert code == 3
    record = json.loads(output.read_text())
    assert record["status"] == "STABLE_RELEASE_BLOCKED"
    assert record["checks"]["package_integrity"] == "pass"
    assert record["checks"]["chat_46_case_quality"] == "fail"
    assert record["checks"]["three_agent_model_validation"] == "fail"
    assert record["checks"]["account_install_rollback"] == "fail"
    assert "STABLE_RELEASE_BLOCKED" in capsys.readouterr().out
    assert "raw_reply" not in output.read_text()


def test_without_require_ready_blocked_report_is_still_a_valid_inspection(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    build_artifacts(
        ROOT,
        dist,
        api_version="2.1.296",
        surface="cli",
        package_version="0.3.0",
        source_revision="1" * 40,
    )
    output = tmp_path / "inspection.json"
    code = cli.main(
        ["--root", str(ROOT), "stable-readiness", "--dist", str(dist), "--out", str(output)]
    )
    assert code == 0
    assert json.loads(output.read_text())["eligible_for_stable_release"] is False


def test_invalid_dist_returns_error_and_does_not_create_report(tmp_path: Path) -> None:
    out = tmp_path / "none.json"
    assert (
        cli.main(
            [
                "--root",
                str(ROOT),
                "stable-readiness",
                "--dist",
                str(tmp_path / "missing"),
                "--out",
                str(out),
            ]
        )
        == 2
    )
    assert not out.exists()
