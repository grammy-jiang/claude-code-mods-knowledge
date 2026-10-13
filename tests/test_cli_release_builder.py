"""P6 release commands must not silently publish to a public directory."""

from __future__ import annotations

import json
from pathlib import Path

from mods_knowledge import cli
from mods_knowledge.compiler import build_artifacts

ROOT = Path(__file__).resolve().parents[1]
SHA = "b" * 40


def matrix_file(path: Path) -> None:
    data = {
        "schema_version": 1,
        "platforms": {
            name: {"static_tests": "pass", "token_based_agent_test": "not_run"}
            for name in ("macbook", "raspberrypi", "sextant")
        },
        "chatgpt": {
            "marketplace_source": "prepared",
            "local_package_cache": "not_verified",
            "chat_skill_activation": "not_run",
            "chat_answer_evaluation": "not_run",
        },
    }
    path.write_text(json.dumps(data, indent=2) + "\n")


def test_release_cli_assembles_and_verifies_prerelease(tmp_path: Path, capsys) -> None:
    dist = tmp_path / "dist"
    build_artifacts(
        ROOT,
        dist,
        api_version="2.1.296",
        surface="cli",
        package_version="0.1.0-rc.1",
        source_revision=SHA,
    )
    matrix = tmp_path / "p5.json"
    matrix_file(matrix)
    folder = tmp_path / "release"
    rc = cli.main(
        [
            "--root",
            str(ROOT),
            "release",
            "--dist",
            str(dist),
            "--out",
            str(folder),
            "--source-revision",
            SHA,
            "--tag",
            "v0.1.0-rc.1",
            "--host-matrix",
            str(matrix),
        ]
    )
    assert rc == 0
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "prerelease_host_runtime_unverified"
    assert cli.main(["release-verify", "--dir", str(folder)]) == 0
    assert json.loads(capsys.readouterr().out)["tag"] == "v0.1.0-rc.1"


def test_release_cli_requires_a_real_sha_and_matrix(tmp_path: Path, capsys) -> None:
    folder = tmp_path / "missing-dist"
    matrix = tmp_path / "missing.json"
    assert (
        cli.main(
            [
                "release",
                "--dist",
                str(folder),
                "--out",
                str(tmp_path / "release"),
                "--source-revision",
                SHA,
                "--tag",
                "v0.1.0-rc.1",
                "--host-matrix",
                str(matrix),
            ]
        )
        == 2
    )
    assert not (tmp_path / "release").exists()
    assert capsys.readouterr().err
