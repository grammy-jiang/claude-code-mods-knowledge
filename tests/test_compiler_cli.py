"""First-party P3 builder CLI tests, isolated from user runtime settings."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from mods_knowledge import cli

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    for name in ("claims", "decisions", "sources", "targets", "evidence"):
        shutil.copytree(ROOT / name, tmp_path / name)
    return tmp_path


def test_cli_build_emits_all_four_packages_without_network(repo: Path, capsys, monkeypatch) -> None:
    monkeypatch.setattr(
        cli, "fetch_document", lambda *_a, **_kw: pytest.fail("network attempt during build")
    )
    rc = cli.main(
        [
            "--root",
            str(repo),
            "build",
            "--api-version",
            "2.1.296",
            "--surface",
            "cli",
            "--source-revision",
            "synthetic-test-revision",
        ]
    )
    assert rc == 0
    result = json.loads(capsys.readouterr().out)
    assert result["approved_claims"] == 30
    assert result["target"]["api_version"] == "2.1.296"
    assert result["source_revision"] == "synthetic-test-revision"
    assert (repo / "dist/chatgpt/claude-code-mods-knowledge/plugin.json").is_file()
    assert (repo / "dist/codex/.agents/skills/claude-code-mods-development/SKILL.md").is_file()
    assert (
        repo / "dist/claude-code/.claude/skills/claude-code-mods-development/SKILL.md"
    ).is_file()
    assert (repo / "dist/pi/.agents/skills/claude-code-mods-development/SKILL.md").is_file()
    assert (repo / "dist/manifests/build-manifest.json").is_file()


def test_cli_build_refuses_unknown_version_without_overwriting_existing_dist(
    repo: Path, capsys
) -> None:
    (repo / "dist").mkdir()
    (repo / "dist/keep.txt").write_text("keep this")
    assert (
        cli.main(["--root", str(repo), "build", "--api-version", "2.1.297", "--surface", "cli"])
        == 2
    )
    assert (repo / "dist/keep.txt").read_text() == "keep this"
    assert "no approved" in capsys.readouterr().err.lower()


def test_cli_build_requires_explicit_version() -> None:
    with pytest.raises(SystemExit) as exc:
        cli.main(["build", "--surface", "cli"])
    assert exc.value.code == 2
