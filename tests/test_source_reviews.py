"""Versioned official-doc evidence review attestation boundaries."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from mods_knowledge.errors import ClaimError
from mods_knowledge.registry import load_registry
from mods_knowledge.review_evidence import validate_official_review

ROOT = Path(__file__).resolve().parents[1]
SOURCES = load_registry(ROOT / "sources/registry.json")


def fixture(tmp_path: Path):
    src = copy.deepcopy(SOURCES["M004"])
    # Append-only observations can advance the latest pointer without changing
    # the historically reviewed pinned HTML digest or its review timestamp.
    digest = src["snapshot"]["sha256"]
    src["snapshot"].update(state="pinned", sha256=digest, checked_at="2026-10-13T15:00:00Z")
    src["review_state"] = "pinned"
    fake_md = b"# reviewed official markdown\n## Observe an event\nrelevant text"
    section = b"## Observe an event\nrelevant text"
    record = {
        "schema_version": 1,
        "source_id": "M004",
        "html_url": src["url"],
        "html_sha256": digest,
        "markdown_url": src["url"] + ".md",
        "markdown_sha256": hashlib.sha256(fake_md).hexdigest(),
        "reviewed_at": "2026-10-13T15:00:00Z",
        "reviewer": "test-curator",
        "scope": "CLI 2.1.296 documentation cross-check, no runtime implied",
        "sections": [
            {
                "anchor": "observe-an-event",
                "heading": "Observe an event",
                "line_start": 2,
                "line_end": 3,
                "section_sha256": hashlib.sha256(section).hexdigest(),
            }
        ],
    }
    review = tmp_path / "reviews"
    review.mkdir()
    (review / "M004.json").write_text(json.dumps(record))
    return src, digest, review, record


def test_source_review_accepts_exact_doc_identity_hash_and_heading(tmp_path: Path) -> None:
    src, sha, reviews, _ = fixture(tmp_path)
    assert validate_official_review(
        src, sha, "observe-an-event", reviews, ROOT / "sources/snapshots"
    )


@pytest.mark.parametrize(
    "mutation",
    [
        lambda x: x.update(source_id="M999"),
        lambda x: x.update(html_url="https://evil.invalid/doc"),
        lambda x: x.update(html_sha256="e" * 64),
        lambda x: x.update(markdown_url="https://evil.invalid/doc.md"),
        lambda x: x.update(markdown_sha256="bogus"),
        lambda x: x.update(reviewer=""),
        lambda x: x.update(reviewed_at="2026-10-13T14:00:00Z"),
        lambda x: x["sections"][0].update(section_sha256="bad"),
        lambda x: x["sections"][0].update(anchor="../../hack"),
        lambda x: x["sections"][0].update(line_start=10, line_end=1),
    ],
)
def test_review_attestation_tampering_is_rejected(tmp_path: Path, mutation) -> None:
    src, sha, reviews, record = fixture(tmp_path)
    mutation(record)
    (reviews / "M004.json").write_text(json.dumps(record))
    with pytest.raises(ClaimError):
        validate_official_review(src, sha, "observe-an-event", reviews, ROOT / "sources/snapshots")


def test_missing_heading_cannot_support_claim(tmp_path: Path) -> None:
    src, sha, reviews, _ = fixture(tmp_path)
    with pytest.raises(ClaimError, match="anchor"):
        validate_official_review(src, sha, "different-heading", reviews, ROOT / "sources/snapshots")


def test_wrong_source_snapshot_does_not_pass(tmp_path: Path) -> None:
    src, _, reviews, _ = fixture(tmp_path)
    with pytest.raises(ClaimError):
        validate_official_review(
            src, "b" * 64, "observe-an-event", reviews, ROOT / "sources/snapshots"
        )


def test_symlinked_review_file_rejected(tmp_path: Path) -> None:
    src, sha, reviews, _ = fixture(tmp_path)
    original = reviews / "M004.json"
    text = original.read_text()
    original.unlink()
    (tmp_path / "source.json").write_text(text)
    original.symlink_to(tmp_path / "source.json")
    with pytest.raises(ClaimError):
        validate_official_review(src, sha, "observe-an-event", reviews, ROOT / "sources/snapshots")
