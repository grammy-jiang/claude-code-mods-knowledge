"""Fail-closed, bounded HTTPS fingerprinting of the official Mods documentation."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .errors import CollectionError
from .registry import _is_official_url

ALLOWED_CONTENT_TYPES = frozenset(("text/html", "text/plain", "text/markdown"))


@dataclass(frozen=True)
class FetchResult:
    """HTTP evidence metadata only; deliberately omits page content."""

    url: str
    sha256: str
    byte_length: int
    content_type: str
    etag: str | None
    last_modified: str | None


class NoRedirect(HTTPRedirectHandler):
    """Never follow an HTTP redirect, including cross-host or downgraded redirects."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise CollectionError("HTTP redirect refused; update reviewed canonical URL first")


def _open_response(request: Request, timeout: float):
    opener = build_opener(NoRedirect())
    return opener.open(request, timeout=timeout)


def fetch_document(url: str, timeout: float = 12.0, max_bytes: int = 2_000_000) -> FetchResult:
    """GET one explicitly allowlisted official URL and hash its raw response bytes.

    No page text is persisted. Byte changes are NOT classified as API changes.
    """
    if not _is_official_url(url):
        raise CollectionError("Only first-party code.claude.com Docs URLs may be fetched")
    if isinstance(timeout, bool) or not 1 <= timeout <= 30:
        raise CollectionError("Timeout must be between 1 and 30 seconds")
    if isinstance(max_bytes, bool) or not 1 <= max_bytes <= 8_000_000:
        raise CollectionError("Response cap must be between 1 and 8,000,000 bytes")
    # The scheme, exact host, and path were validated by _is_official_url above.
    request = Request(  # noqa: S310
        url,
        headers={
            "User-Agent": "claude-code-mods-knowledge/0.1 (documentation-fingerprint-only)",
            "Accept": "text/html,text/markdown;q=0.9,text/plain;q=0.8",
            "Accept-Encoding": "identity",
        },
        method="GET",
    )
    try:
        with _open_response(request, timeout) as response:
            if response.status != 200:
                raise CollectionError(f"Expected HTTP 200, received {response.status}")
            if response.geturl() != url:
                raise CollectionError("Final URL changed unexpectedly")
            content_type = response.headers.get_content_type().lower()
            if content_type not in ALLOWED_CONTENT_TYPES:
                raise CollectionError(f"Unsafe or unsupported MIME type: {content_type}")
            encoding = response.headers.get("Content-Encoding", "identity").lower()
            if encoding != "identity":
                raise CollectionError(f"Unexpected Content-Encoding: {encoding}")
            length = response.headers.get("Content-Length")
            if length:
                try:
                    parsed_length = int(length)
                except ValueError as exc:
                    raise CollectionError("Invalid Content-Length") from exc
                if parsed_length < 0 or parsed_length > max_bytes:
                    raise CollectionError("Content-Length exceeds the bounded response size")
            data = response.read(max_bytes + 1)
            if not data or len(data) > max_bytes:
                raise CollectionError("Empty or oversized documentation response")
            return FetchResult(
                url=url,
                sha256=hashlib.sha256(data).hexdigest(),
                byte_length=len(data),
                content_type=content_type,
                etag=response.headers.get("ETag"),
                last_modified=response.headers.get("Last-Modified"),
            )
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise CollectionError(f"Unable to fetch official documentation: {exc}") from exc
