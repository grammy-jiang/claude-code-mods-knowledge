"""End-to-end Claim CLI behavior; only explicit transitions can modify Claims."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from mods_knowledge import cli

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def project(tmp_path: Path) -> Path:
    (tmp_path / "sources").mkdir()
    shutil.copy2(ROOT / "sources/registry.json", tmp_path / "sources/registry.json")
    shutil.copytree(ROOT / "sources/snapshots", tmp_path / "sources/snapshots")
    shutil.copytree(ROOT / "claims", tmp_path / "claims")
    return tmp_path


def test_claims_validate_sees_six_candidates_without_promoting_them(project: Path, capsys) -> None:
    assert cli.main(["--root", str(project), "claims", "validate"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["total"] == 6
    assert data["lifecycles"] == {"candidate": 6}
    assert data["approved"] == 0
    assert data["areas"] == {"E": 1, "S": 1, "T": 1, "Q": 1, "P": 1, "U": 1}
    assert not (project / "decisions").exists()


def test_read_only_claims_list_show_query(project: Path, capsys) -> None:
    assert cli.main(["--root", str(project), "claims", "list"]) == 0
    lines = capsys.readouterr().out.strip().splitlines()
    assert len(lines) == 6
    assert all("\tcandidate\t" in line for line in lines)
    assert cli.main(["--root", str(project), "claims", "show", "K-0001"]) == 0
    record = json.loads(capsys.readouterr().out)
    assert record["lifecycle"] == "candidate"
    assert (
        cli.main(
            ["--root", str(project), "claims", "query", "--version", "2.1.296", "--surface", "cli"]
        )
        == 0
    )
    response = json.loads(capsys.readouterr().out)
    assert response["claims"] == []
    assert response["count"] == 0
    assert not (project / "decisions").exists()


def test_cli_rejects_invalid_review_and_preserves_candidates(
    project: Path, capsys, monkeypatch
) -> None:
    monkeypatch.setattr(cli, "fetch_document", lambda *_args, **_kwargs: pytest.fail("network"))
    before = (project / "claims/K-0001.json").read_bytes()
    assert (
        cli.main(
            [
                "--root",
                str(project),
                "claims",
                "transition",
                "K-0001",
                "--to",
                "approved",
                "--actor",
                "chatgpt",
                "--reason",
                "Cannot approve an unreviewed candidate",
            ]
        )
        == 2
    )
    assert (project / "claims/K-0001.json").read_bytes() == before
    assert not (project / "decisions/K-0001.json").exists()
    assert capsys.readouterr().err


def test_untrusted_claim_disk_edit_causes_validate_failure(project: Path, capsys) -> None:
    target = project / "claims/K-0002.json"
    claim = json.loads(target.read_text())
    claim["evidence"][0]["source_id"] = "M999"
    target.write_text(json.dumps(claim))
    assert cli.main(["--root", str(project), "claims", "validate"]) == 2
    assert "M999" in capsys.readouterr().err


def test_unknown_claim_and_invalid_query_version_are_fail_closed(project: Path) -> None:
    assert cli.main(["--root", str(project), "claims", "show", "K-9999"]) == 2
    assert (
        cli.main(
            ["--root", str(project), "claims", "query", "--version", "latest", "--surface", "cli"]
        )
        == 2
    )


def test_main_validate_and_verify_also_check_claim_integrity(project: Path, capsys) -> None:
    assert cli.main(["--root", str(project), "validate"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["claims"] == 6
    assert result["approved_claims"] == 0
    assert cli.main(["--root", str(project), "verify"]) == 0
    target = project / "claims/K-0001.json"
    claim = json.loads(target.read_text())
    claim["claim_id"] = "K-9999"
    target.write_text(json.dumps(claim))
    assert cli.main(["--root", str(project), "verify"]) == 2
