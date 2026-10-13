"""CLI integration tests: no network except an injected synthetic result."""

from __future__ import annotations

import json
import shutil
from hashlib import sha256
from pathlib import Path

import pytest

from mods_knowledge import cli
from mods_knowledge.collector import FetchResult

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def project(tmp_path: Path) -> Path:
    folder = tmp_path / "sources"
    folder.mkdir()
    shutil.copy2(ROOT / "sources/registry.json", folder / "registry.json")
    return tmp_path


def test_validate_reports_counts_and_keeps_registry_unverified(project, capsys) -> None:
    assert cli.main(["--root", str(project), "validate"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["sources"] == 91
    assert payload["layers"] == {"L0": 10, "L1": 19, "L2": 14, "R": 17, "C": 28, "H": 3}
    assert payload["eligible_official_documents"] == 43
    assert payload["approved_claims"] == 0
    assert not (project / "sources/snapshots").exists()


def test_list_history_only(project, capsys) -> None:
    assert cli.main(["--root", str(project), "list", "--layer", "H"]) == 0
    lines = capsys.readouterr().out.strip().splitlines()
    assert len(lines) == 3
    assert all("\tH\t" in line for line in lines)


@pytest.mark.parametrize("source_id", ["M035", "M036", "M046", "M999"])
def test_collect_rejects_untrusted_or_unknown_sources_without_network(
    project, capsys, monkeypatch, source_id
) -> None:
    monkeypatch.setattr(
        cli, "fetch_document", lambda *args, **kwargs: pytest.fail("untrusted fetch attempted")
    )
    assert cli.main(["--root", str(project), "collect", "--source", source_id]) == 2
    assert not (project / "sources/snapshots/index.json").exists()
    assert capsys.readouterr().err


def test_explicit_collection_records_metadata_with_no_page_body(
    project, capsys, monkeypatch
) -> None:
    content = b"<html>synthetic fixture, should never appear in files</html>"
    calls: list[str] = []

    def fake_fetch(url: str, **kwargs) -> FetchResult:
        calls.append(url)
        return FetchResult(
            url=url,
            sha256=sha256(content).hexdigest(),
            byte_length=len(content),
            content_type="text/html",
            etag=None,
            last_modified=None,
        )

    monkeypatch.setattr(cli, "fetch_document", fake_fetch)
    assert cli.main(["--root", str(project), "collect", "--source", "M001"]) == 0
    response = json.loads(capsys.readouterr().out)
    assert response["collected"][0]["source_id"] == "M001"
    assert response["collected"][0]["status"] == "new"
    assert calls == ["https://code.claude.com/docs/en/plugins/mods/overview"]
    assert content not in b"".join(
        p.read_bytes() for p in (project / "sources/snapshots").rglob("*.json")
    )
    assert cli.main(["--root", str(project), "verify"]) == 0


def test_verify_empty_store_is_read_only(project, capsys) -> None:
    assert cli.main(["--root", str(project), "verify"]) == 0
    assert not (project / "sources/snapshots").exists()
    assert "verified" in capsys.readouterr().out


def test_collect_requires_explicit_source_or_all_flag(project) -> None:
    with pytest.raises(SystemExit) as exc:
        cli.main(["--root", str(project), "collect"])
    assert exc.value.code == 2


def test_collect_all_requires_explicit_all_official_flag_and_can_be_limited(
    project, capsys, monkeypatch
) -> None:
    calls: list[str] = []

    def fake_fetch(url: str, **_kwargs) -> FetchResult:
        calls.append(url)
        return FetchResult(
            url=url,
            sha256=sha256(url.encode()).hexdigest(),
            byte_length=len(url),
            content_type="text/html",
            etag=None,
            last_modified=None,
        )

    monkeypatch.setattr(cli, "fetch_document", fake_fetch)
    assert cli.main(["--root", str(project), "collect", "--all-official", "--limit", "2"]) == 0
    captured = json.loads(capsys.readouterr().out)
    assert len(captured["collected"]) == 2
    assert len(calls) == 2
    assert cli.main(["--root", str(project), "verify"]) == 0
