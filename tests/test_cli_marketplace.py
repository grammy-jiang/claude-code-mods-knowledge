"""Package-local CLI marketplace staging does not consume model tokens."""

from __future__ import annotations

import json
from pathlib import Path

from mods_knowledge import cli
from mods_knowledge.compiler import build_artifacts

ROOT = Path(__file__).resolve().parents[1]


def test_cli_marketplace_stage_defaults_to_no_side_effects(tmp_path: Path, capsys) -> None:
    build_artifacts(ROOT, tmp_path / "dist", api_version="2.1.296", surface="cli")
    home = tmp_path / "home"
    rc = cli.main(
        [
            "marketplace-stage",
            "--dist",
            str(tmp_path / "dist"),
            "--home",
            str(home),
        ]
    )
    assert rc == 0
    assert json.loads(capsys.readouterr().out)["status"] == "dry_run"
    assert not home.exists()


def test_cli_marketplace_stage_apply_creates_source_only_not_claimed_host_install(
    tmp_path: Path, capsys
) -> None:
    build_artifacts(ROOT, tmp_path / "dist", api_version="2.1.296", surface="cli")
    home = tmp_path / "home"
    rc = cli.main(
        [
            "marketplace-stage",
            "--dist",
            str(tmp_path / "dist"),
            "--home",
            str(home),
            "--apply",
        ]
    )
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert data["status"] == "marketplace_prepared_not_host_verified"
    assert data["chatgpt_runtime_verified"] is False
    assert (home / ".agents/plugins/marketplace.json").is_file()
