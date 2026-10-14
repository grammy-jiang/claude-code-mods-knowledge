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


def test_cli_binds_normalized_download_to_account_report_without_waiving_chat_gates(
    tmp_path: Path,
) -> None:
    import io
    import stat
    import zipfile

    from mods_knowledge.account_archive import _expected_server_sidecar, verify_account_download

    dist = tmp_path / "dist"
    build_artifacts(
        ROOT,
        dist,
        api_version="2.1.296",
        surface="cli",
        package_version="0.3.0",
        source_revision="1" * 40,
    )
    original = (dist / "packages/claude-code-mods-knowledge-0.3.0.zip").read_bytes()
    with zipfile.ZipFile(io.BytesIO(original)) as archive:
        prefix = "claude-code-mods-knowledge/"
        files = {
            member.filename[len(prefix) :]: archive.read(member) for member in archive.infolist()
        }
    files[".codex-plugin/plugin.json"] = json.dumps(
        _expected_server_sidecar(json.loads(files["plugin.json"]))
    ).encode()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, content in sorted(files.items()):
            item = zipfile.ZipInfo(name, date_time=(2026, 10, 14, 16, 0, 0))
            item.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(item, content)
    downloaded = tmp_path / "account.zip"
    downloaded.write_bytes(buffer.getvalue())
    audit = verify_account_download(original, downloaded.read_bytes())
    account = {
        "schema_version": 1,
        "installed_plugin_version": "0.3.0",
        "installed_enabled": True,
        "skill_enabled": True,
        "chat_surface": "chat",
        "installed_bundle_sha256": audit["downloaded_zip_sha256"],
        "source_bundle_sha256": audit["uploaded_zip_sha256"],
        "canonical_content_sha256": audit["canonical_content_sha256"],
        "server_sidecar_sha256": audit["server_sidecar_sha256"],
        "rollback_verified": True,
        "evidence_sha256": "f" * 64,
    }
    account_path = tmp_path / "account-report.json"
    account_path.write_text(json.dumps(account))
    output = tmp_path / "report.json"
    code = cli.main(
        [
            "--root",
            str(ROOT),
            "stable-readiness",
            "--dist",
            str(dist),
            "--account-download-zip",
            str(downloaded),
            "--account-report",
            str(account_path),
            "--out",
            str(output),
            "--require-ready",
        ]
    )
    result = json.loads(output.read_text())
    assert code == 3  # synthetic account data cannot replace real P4/P5 acceptance
    assert result["checks"]["account_archive_content"] == "pass"
    assert result["checks"]["account_install_rollback"] == "pass"
    assert result["checks"]["chat_46_case_quality"] == "fail"
    assert result["checks"]["three_agent_model_validation"] == "fail"
    assert "Cookie" not in output.read_text()


def test_cli_rejects_oversized_account_download_without_creating_report(
    tmp_path: Path,
) -> None:
    from mods_knowledge.release_validation import MAX_ARCHIVE_SIZE

    archive = tmp_path / "oversized.zip"
    with archive.open("wb") as out:
        out.seek(MAX_ARCHIVE_SIZE)
        out.write(b"x")
    report = tmp_path / "report.json"
    code = cli.main(
        [
            "--root",
            str(ROOT),
            "stable-readiness",
            "--dist",
            str(tmp_path),
            "--account-download-zip",
            str(archive),
            "--out",
            str(report),
        ]
    )
    assert code == 2
    assert not report.exists()
