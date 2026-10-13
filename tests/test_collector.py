"""Offline contract tests: no actual network operations are required."""

from __future__ import annotations

import hashlib
from email.message import Message
from urllib.request import Request

import pytest

from mods_knowledge import collector
from mods_knowledge.errors import CollectionError

OFFICIAL = "https://code.claude.com/docs/en/plugins/mods/overview"


class FakeResponse:
    def __init__(
        self,
        body: bytes = b"<html>safe official document</html>",
        status: int = 200,
        content_type: str = "text/html",
        final_url: str = OFFICIAL,
    ) -> None:
        self.body = body
        self.status = status
        self.url = final_url
        self.headers = Message()
        self.headers["Content-Type"] = content_type
        self.headers["ETag"] = '"revision-1"'
        self.headers["Last-Modified"] = "Tue, 13 Oct 2026 03:00:00 GMT"

    def geturl(self) -> str:
        return self.url

    def read(self, max_bytes: int) -> bytes:
        return self.body[:max_bytes]

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        return None


def test_fetch_fingerprints_bytes_without_returning_original_content(monkeypatch) -> None:
    body = b"<html>official docs without locally saved raw content</html>"
    requests: list[tuple[Request, float]] = []

    def opener(request: Request, timeout: float):
        requests.append((request, timeout))
        return FakeResponse(body=body)

    monkeypatch.setattr(collector, "_open_response", opener)
    result = collector.fetch_document(OFFICIAL)
    assert result.sha256 == hashlib.sha256(body).hexdigest()
    assert result.byte_length == len(body)
    assert result.content_type == "text/html"
    assert result.etag == '"revision-1"'
    assert result.last_modified == "Tue, 13 Oct 2026 03:00:00 GMT"
    assert result.url == OFFICIAL
    assert not hasattr(result, "body")
    assert len(requests) == 1
    assert requests[0][0].full_url == OFFICIAL


@pytest.mark.parametrize(
    "url",
    [
        "http://code.claude.com/docs/en/plugins/mods/overview",
        "https://attacker.example/docs/en/plugins/mods/overview",
        "https://code.claude.com.evil.example/docs/en/plugins/mods/overview",
        "https://code.claude.com@localhost/docs/en/plugins/mods/overview",
        "https://code.claude.com:1234/docs/en/plugins/mods/overview",
        "https://code.claude.com/docs/en/plugins/mods/overview?token=x",
        "https://code.claude.com/private",
        "https://127.0.0.1/docs/en/plugins/mods/overview",
        "https://github.com/anthropics/claude-code",
        "https://claude.com/resources/articles/claude-code-mods",
    ],
)
def test_fetch_rejects_disallowed_urls_without_network(monkeypatch, url: str) -> None:
    def must_not_fetch(*_args, **_kwargs):
        raise AssertionError("network used for untrusted URL")

    monkeypatch.setattr(collector, "_open_response", must_not_fetch)
    with pytest.raises(CollectionError):
        collector.fetch_document(url)


@pytest.mark.parametrize(
    ("response", "max_bytes"),
    [
        (FakeResponse(status=404), 2_000_000),
        (FakeResponse(content_type="application/octet-stream"), 2_000_000),
        (FakeResponse(body=b""), 2_000_000),
        (FakeResponse(body=b"abcdefghijk"), 10),
        (FakeResponse(final_url="https://localhost/internal"), 2_000_000),
    ],
)
def test_fetch_rejects_invalid_status_content_length_or_final_url(
    monkeypatch, response: FakeResponse, max_bytes: int
) -> None:
    monkeypatch.setattr(collector, "_open_response", lambda *_args, **_kwargs: response)
    with pytest.raises(CollectionError):
        collector.fetch_document(OFFICIAL, max_bytes=max_bytes)


def test_index_plain_text_source_is_explicit_allowlisted(monkeypatch) -> None:
    url = "https://code.claude.com/docs/llms.txt"
    monkeypatch.setattr(
        collector,
        "_open_response",
        lambda *_args, **_kwargs: FakeResponse(
            body=b"# index\n", content_type="text/plain", final_url=url
        ),
    )
    assert collector.fetch_document(url).byte_length == len(b"# index\n")


def test_redirect_handler_does_not_follow_redirects() -> None:
    redirect = collector.NoRedirect()
    with pytest.raises(CollectionError, match="redirect"):
        redirect.redirect_request(Request(OFFICIAL), None, 302, "Found", {}, OFFICIAL)


@pytest.mark.parametrize("timeout,max_bytes", [(0, 100), (60, 100), (5, 0), (5, 8_000_001)])
def test_fetch_validates_resource_limits_before_network(monkeypatch, timeout, max_bytes) -> None:
    monkeypatch.setattr(
        collector,
        "_open_response",
        lambda *_args, **_kwargs: pytest.fail("network attempted"),
    )
    with pytest.raises(CollectionError):
        collector.fetch_document(OFFICIAL, timeout=timeout, max_bytes=max_bytes)


def test_explicit_large_cap_supports_changelog_without_changing_default(monkeypatch) -> None:
    monkeypatch.setattr(collector, "_open_response", lambda *_args, **_kwargs: FakeResponse())
    assert collector.fetch_document(OFFICIAL, max_bytes=6_000_000).byte_length > 0
