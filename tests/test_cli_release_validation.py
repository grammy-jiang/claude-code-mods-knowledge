"""Model-free package verification command for P5 and P6 across ARM64 hosts."""

from __future__ import annotations

import json
from pathlib import Path

from mods_knowledge import cli
from mods_knowledge.compiler import build_artifacts

ROOT = Path(__file__).resolve().parents[1]


def test_package_check_success_without_chatgpt_model(tmp_path: Path, capsys) -> None:
    build_artifacts(ROOT, tmp_path / "dist", api_version="2.1.296", surface="cli")
    assert cli.main(["package-check", "--dist", str(tmp_path / "dist")]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["artifacts_verified"] == 53
    assert result["status"] == "package_verified_host_not_tested"
    assert result["approved_claims"] == 31


def test_package_check_detects_tampering(tmp_path: Path, capsys) -> None:
    build_artifacts(ROOT, tmp_path / "dist", api_version="2.1.296", surface="cli")
    skill = tmp_path / "dist/common/claude-code-mods-development/SKILL.md"
    skill.write_bytes(skill.read_bytes() + b"tampered\n")
    assert cli.main(["package-check", "--dist", str(tmp_path / "dist")]) == 2
    assert "SHA" in capsys.readouterr().err or "hash" in capsys.readouterr().err
