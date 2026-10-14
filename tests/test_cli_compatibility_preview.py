"""Opt-in two-Skill builds never install to user accounts or release automatically."""

from __future__ import annotations

import json
from pathlib import Path

from mods_knowledge import cli

ROOT = Path(__file__).resolve().parents[1]


def test_preview_cli_build_and_verify_are_explicit_and_read_only(tmp_path: Path, capsys) -> None:
    output = tmp_path / "preview"
    result = cli.main(
        [
            "--root",
            str(ROOT),
            "preview-compat-build",
            "--api-version",
            "2.1.296",
            "--surface",
            "cli",
            "--package-version",
            "0.2.0-preview.1",
            "--source-revision",
            "exact-source-for-tests",
            "--out",
            str(output),
        ]
    )
    assert result == 0
    status = json.loads(capsys.readouterr().out)
    assert status["publishable"] is False
    assert status["approved_claims"] == 29
    assert status["preview_extension"]["canonical_skill_unchanged"] is True
    assert (
        output / "chatgpt/claude-code-mods-knowledge/skills/claude-mods-compatibility/SKILL.md"
    ).is_file()
    assert cli.main(["--root", str(ROOT), "preview-compat-verify", "--dist", str(output)]) == 0
    validated = json.loads(capsys.readouterr().out)
    assert validated["status"] == "experimental_preview_validated_no_host_claim"
    assert validated["publishable"] is False


def test_preview_cli_rejects_unsupported_version_without_writing(tmp_path: Path, capsys) -> None:
    out = tmp_path / "preview"
    assert (
        cli.main(
            [
                "--root",
                str(ROOT),
                "preview-compat-build",
                "--api-version",
                "2.1.310",
                "--surface",
                "cli",
                "--out",
                str(out),
            ]
        )
        == 2
    )
    assert not out.exists()
    assert (
        "unverified" in capsys.readouterr().err.lower()
        or "approved" in capsys.readouterr().err.lower()
    )


def test_preview_cli_does_not_silently_overwrite_an_existing_directory(tmp_path: Path) -> None:
    out = tmp_path / "preview"
    out.mkdir()
    marker = out / "keep"
    marker.write_text("do-not-overwrite")
    assert (
        cli.main(
            [
                "--root",
                str(ROOT),
                "preview-compat-build",
                "--api-version",
                "2.1.296",
                "--surface",
                "cli",
                "--out",
                str(out),
            ]
        )
        == 2
    )
    assert marker.read_text() == "do-not-overwrite"
