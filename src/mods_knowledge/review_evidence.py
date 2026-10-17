"""Conservative, offline checking of human/agent-reviewed official Markdown anchors.

The attestation certifies a recorded review of an official Markdown rendition.
It cannot prove that its author actually read a page and is not a signature.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from .errors import ClaimError
from .registry import OFFICIAL_LAYERS

_SHA = re.compile(r"[a-f0-9]{64}\Z")
_ANCHOR = re.compile(r"[a-z0-9][a-z0-9-]*\Z")


def _time(value: str) -> datetime:
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise ClaimError("Invalid official review timestamp") from exc
    if result.tzinfo is None or result.utcoffset() is None:
        raise ClaimError("Official review timestamp must carry a timezone")
    return result


def validate_official_review(
    source: dict,
    sha: str,
    anchor: str,
    review_dir: Path,
    snapshot_root: Path,
    *,
    revision_review_file: Path | None = None,
) -> bool:
    """Check source-reviewed digest, approved section, and observational metadata."""
    source_id = source["source_id"]
    if source.get("trust_layer") not in OFFICIAL_LAYERS:
        raise ClaimError(f"{source_id}: source review must be current first-party docs")
    if not isinstance(sha, str) or not _SHA.fullmatch(sha):
        raise ClaimError(f"{source_id}: invalid source review HTML digest")
    if not isinstance(anchor, str) or not _ANCHOR.fullmatch(anchor):
        raise ClaimError(f"{source_id}: invalid source review anchor")
    pin = source["snapshot"]
    if (
        source["review_state"] != "pinned"
        or pin["state"] != "pinned"
        or pin["sha256"] != sha
        or not pin.get("checked_at")
    ):
        raise ClaimError(f"{source_id}: source review lacks a consistent pinned source")
    if revision_review_file is None:
        file = review_dir / f"{source_id}.json"
    else:
        expected_revision = review_dir / "revisions" / source_id / f"{sha}.json"
        if revision_review_file != expected_revision:
            raise ClaimError(f"{source_id}: unexpected revision review path")
        if expected_revision.parent.is_symlink():
            raise ClaimError(f"{source_id}: unsafe revision review directory")
        file = expected_revision
    if file.is_symlink() or not file.is_file():
        raise ClaimError(f"{source_id}: source review attestation file missing or unsafe")
    try:
        record = json.loads(file.read_text(encoding="utf-8"))
        metadata = json.loads(
            (snapshot_root / "metadata" / source_id / f"{sha}.json").read_text(encoding="utf-8")
        )
    except (OSError, ValueError) as exc:
        raise ClaimError(f"{source_id}: corrupt review or source metadata: {exc}") from exc
    expected = {
        "schema_version",
        "source_id",
        "html_url",
        "html_sha256",
        "markdown_url",
        "markdown_sha256",
        "reviewed_at",
        "reviewer",
        "scope",
        "sections",
    }
    if not isinstance(record, dict) or set(record) != expected:
        raise ClaimError(f"{source_id}: review attestation has invalid fields")
    if (
        record["schema_version"] != 1
        or record["source_id"] != source_id
        or record["html_url"] != source["url"]
        or record["html_sha256"] != sha
        or record["markdown_url"] != source["url"] + ".md"
        or not isinstance(record["markdown_sha256"], str)
        or not _SHA.fullmatch(record["markdown_sha256"])
        or not isinstance(record["reviewer"], str)
        or not record["reviewer"].strip()
        or not isinstance(record["scope"], str)
        or not record["scope"].strip()
    ):
        raise ClaimError(f"{source_id}: invalid/mismatched official review identity")
    if (
        metadata.get("url") != source["url"]
        or metadata.get("source_id") != source_id
        or metadata.get("content_sha256") != sha
        or metadata.get("trust_layer") != source["trust_layer"]
    ):
        raise ClaimError(f"{source_id}: pinned HTML metadata does not match official review")
    reviewed_at = _time(record["reviewed_at"])
    checked_at = _time(pin["checked_at"])
    observed_at = _time(metadata["observed_at"])
    if reviewed_at < observed_at or checked_at < observed_at or reviewed_at != checked_at:
        raise ClaimError(f"{source_id}: source review predates the observed/checked snapshot")
    sections = record["sections"]
    if not isinstance(sections, list) or not sections:
        raise ClaimError(f"{source_id}: no reviewed Markdown headings")
    seen: set[str] = set()
    for section in sections:
        required = {"anchor", "heading", "line_start", "line_end", "section_sha256"}
        if not isinstance(section, dict) or set(section) != required:
            raise ClaimError(f"{source_id}: malformed reviewed section")
        section_anchor = section["anchor"]
        if (
            not isinstance(section_anchor, str)
            or not _ANCHOR.fullmatch(section_anchor)
            or section_anchor in seen
            or not isinstance(section["heading"], str)
            or not section["heading"].strip()
            or not isinstance(section["line_start"], int)
            or isinstance(section["line_start"], bool)
            or not isinstance(section["line_end"], int)
            or isinstance(section["line_end"], bool)
            or section["line_start"] < 1
            or section["line_end"] < section["line_start"]
            or not isinstance(section["section_sha256"], str)
            or not _SHA.fullmatch(section["section_sha256"])
        ):
            raise ClaimError(f"{source_id}: invalid review heading/anchor/digest")
        seen.add(section_anchor)
    if anchor not in seen:
        raise ClaimError(f"{source_id}: anchor {anchor} absent from reviewed official source")
    return True
