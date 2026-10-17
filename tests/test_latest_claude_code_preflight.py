"""Latest-only release preflight guards without network access in test."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import check_latest_claude_code as check  # noqa: E402


class Response:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    def __enter__(self) -> Response:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self, size: int = -1) -> bytes:
        return self.payload[:size]


def test_latest_valid_fixed_official_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(request: object, *, timeout: int) -> Response:
        assert request.full_url == check.REGISTRY_DIST_TAGS_URL
        assert timeout == 12
        return Response(b'{"stable":"2.1.292","latest":"2.1.302"}')

    monkeypatch.setattr(check.urllib.request, "urlopen", fake_urlopen)
    assert check.official_latest() == "2.1.302"


@pytest.mark.parametrize(
    "payload",
    (b"", b"not json", b"{}", b'{"latest":"foo"}', b"x" * 16385),
)
def test_official_latest_fails_closed(monkeypatch: pytest.MonkeyPatch, payload: bytes) -> None:
    monkeypatch.setattr(check.urllib.request, "urlopen", lambda *_a, **_kw: Response(payload))
    with pytest.raises(check.LatestVersionGateError):
        check.official_latest()


def test_rejects_both_old_target_and_old_host() -> None:
    with pytest.raises(check.LatestVersionGateError, match="Stale"):
        check.checked_target("2.1.296", "2.1.302")
    with pytest.raises(check.LatestVersionGateError, match="Local"):
        check.checked_target("2.1.302", "2.1.302", "2.1.301")
    check.checked_target("2.1.302", "2.1.302", "2.1.302")


def test_installed_cli_version(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(check.shutil, "which", lambda _name: "/usr/local/bin/claude")
    monkeypatch.setattr(
        check.subprocess,
        "run",
        lambda args, **kwargs: SimpleNamespace(
            returncode=0, stdout="2.1.302 (Claude Code)", stderr=""
        ),
    )
    assert check.local_cli_version() == "2.1.302"


def test_old_claims_cannot_authorize_new_release(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(check, "official_latest", lambda: "2.1.302")
    monkeypatch.setattr(check, "local_cli_version", lambda: "2.1.302")
    monkeypatch.setattr(check, "approved_current_claims", lambda *_a: 0)
    assert (
        check.main(["--target-version", "2.1.302", "--require-installed", "--require-approved"])
        == 2
    )
    output = capsys.readouterr().out
    assert "BLOCKED" in output and "No approved exact-version" in output


def test_verified_current_claims_only_pass_preflight(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(check, "official_latest", lambda: "2.1.302")
    monkeypatch.setattr(check, "local_cli_version", lambda: "2.1.302")
    monkeypatch.setattr(check, "approved_current_claims", lambda *_a: 31)
    assert (
        check.main(["--target-version", "2.1.302", "--require-installed", "--require-approved"])
        == 0
    )
    result = capsys.readouterr().out
    assert '"publication_authorized": false' in result
    assert '"approved_exact_version_claims": 31' in result


def test_preflight_is_not_version_alias() -> None:
    with pytest.raises(check.LatestVersionGateError):
        check.checked_target("latest", "2.1.302")
