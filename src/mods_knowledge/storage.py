"""Immutable official-document observation metadata; no HTML or page text is stored."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .collector import ALLOWED_CONTENT_TYPES, FetchResult
from .errors import CollectionError
from .registry import OFFICIAL_LAYERS, _is_official_url

_ID_RE = re.compile(r"^M[0-9]{3,}$")
_SHA_RE = re.compile(r"^[a-f0-9]{64}$")
INDEX_VERSION = 1


@dataclass(frozen=True)
class ChangeResult:
    source_id: str
    status: str
    sha256: str
    previous_sha256: str | None


def _json_bytes(value: dict) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


@contextmanager
def _locked(root: Path) -> Iterator[None]:
    root.mkdir(parents=True, exist_ok=True)
    with (root / ".lock").open("a+b") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def _atomic_replace(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".pending-", delete=False) as file:
            temp_path = Path(file.name)
            file.write(payload)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def _atomic_create(path: Path, payload: bytes) -> bool:
    """Publish a new immutable metadata file without overwriting a prior version."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".pending-", delete=False) as file:
            temp_path = Path(file.name)
            file.write(payload)
            file.flush()
            os.fsync(file.fileno())
        try:
            os.link(temp_path, path)
        except FileExistsError:
            if path.read_bytes() != payload:
                raise CollectionError(
                    "Immutable observation file conflicts with new content"
                ) from None
            return False
        return True
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def _read_index(root: Path) -> dict:
    path = root / "index.json"
    if not path.exists():
        return {"schema_version": INDEX_VERSION, "sources": {}}
    try:
        index = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CollectionError(f"Cannot parse snapshot index: {exc}") from exc
    if not isinstance(index, dict) or index.get("schema_version") != INDEX_VERSION:
        raise CollectionError("Unsupported snapshot index format")
    if not isinstance(index.get("sources"), dict):
        raise CollectionError("Snapshot index sources must be an object")
    return index


def _metadata_path(root: Path, source_id: str, sha256: str) -> Path:
    if not _ID_RE.fullmatch(source_id) or not _SHA_RE.fullmatch(sha256):
        raise CollectionError("Invalid source ID or content hash in snapshot record")
    return root / "metadata" / source_id / f"{sha256}.json"


def _validate_input(source: dict, fetched: FetchResult, at: datetime) -> None:
    identifier = source.get("source_id", "")
    if not _ID_RE.fullmatch(identifier):
        raise CollectionError("Invalid source identity")
    layer_types = {"L0": "official-mods", "L1": "official-dependency", "L2": "official-secondary"}
    if source.get("trust_layer") not in OFFICIAL_LAYERS or source.get(
        "source_type"
    ) != layer_types.get(source.get("trust_layer")):
        raise CollectionError("Only L0/L1/L2 official documents may be fingerprinted")
    if not _is_official_url(source.get("url", "")) or fetched.url != source["url"]:
        raise CollectionError("Untrusted or mismatched official-document URL")
    if not _SHA_RE.fullmatch(fetched.sha256) or fetched.byte_length <= 0:
        raise CollectionError("Invalid downloaded content fingerprint")
    if fetched.content_type not in ALLOWED_CONTENT_TYPES:
        raise CollectionError("Unsupported captured document type")
    if at.tzinfo is None or at.utcoffset() is None:
        raise CollectionError("Observation time must include a time zone")


def _verify_index(root: Path, index: dict) -> list[str]:
    errors: list[str] = []
    expected: set[Path] = set()
    for source_id, entry in index.get("sources", {}).items():
        if not _ID_RE.fullmatch(source_id) or not isinstance(entry, dict):
            errors.append(f"Invalid source entry {source_id!r}")
            continue
        revisions = entry.get("revisions")
        if not isinstance(revisions, dict) or entry.get("current") not in revisions:
            errors.append(f"Missing current revision for {source_id}")
            continue
        for sha, version in revisions.items():
            if not _SHA_RE.fullmatch(sha) or not isinstance(version, dict):
                errors.append(f"Invalid revision key for {source_id}")
                continue
            path = _metadata_path(root, source_id, sha)
            expected.add(path)
            if not path.is_file() or path.is_symlink():
                errors.append(f"Missing or unsafe metadata file for {source_id}/{sha}")
                continue
            try:
                payload = path.read_bytes()
                declared = version.get("metadata_sha256")
                if not isinstance(declared, str) or hashlib.sha256(payload).hexdigest() != declared:
                    errors.append(f"Metadata hash mismatch for {source_id}/{sha}")
                    continue
                metadata = json.loads(payload)
                if (metadata.get("source_id"), metadata.get("content_sha256")) != (source_id, sha):
                    errors.append(f"Metadata identity mismatch for {source_id}/{sha}")
            except (OSError, ValueError, AttributeError) as exc:
                errors.append(f"Invalid metadata for {source_id}/{sha}: {exc}")
    for path in (root / "metadata").glob("*/*.json"):
        if path not in expected:
            errors.append(f"Unindexed observation metadata: {path.relative_to(root)}")
    return errors


def verify_snapshot_store(root: Path) -> list[str]:
    """Check all index-referenced metadata hashes and detect orphan observations.

    This verifies metadata integrity, NOT the source HTML, whose bytes are not stored.
    """
    if not root.exists():
        return []
    try:
        lock = root / ".lock"
        if not lock.exists():
            return _verify_index(root, _read_index(root))
        with lock.open("rb") as handle:
            fcntl.flock(handle, fcntl.LOCK_SH)
            try:
                return _verify_index(root, _read_index(root))
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)
    except (OSError, CollectionError) as exc:
        return [str(exc)]


def record_observation(
    root: Path, source: dict, fetched: FetchResult, at: datetime
) -> ChangeResult:
    """Record one bounded document fingerprint without promoting source authority."""
    _validate_input(source, fetched, at)
    source_id = source["source_id"]
    observed_at = at.astimezone(UTC).isoformat().replace("+00:00", "Z")
    with _locked(root):
        index = _read_index(root)
        failures = _verify_index(root, index)
        if failures:
            raise CollectionError("Snapshot store is not coherent: " + "; ".join(failures))
        history = index["sources"].setdefault(source_id, {"current": None, "revisions": {}})
        previous_sha = history["current"]
        if fetched.sha256 == previous_sha:
            return ChangeResult(source_id, "unchanged", fetched.sha256, previous_sha)

        metadata_path = _metadata_path(root, source_id, fetched.sha256)
        published = False
        if fetched.sha256 not in history["revisions"]:
            metadata = {
                "schema_version": INDEX_VERSION,
                "source_id": source_id,
                "trust_layer": source["trust_layer"],
                "url": source["url"],
                "content_sha256": fetched.sha256,
                "byte_length": fetched.byte_length,
                "content_type": fetched.content_type,
                "etag": fetched.etag,
                "last_modified": fetched.last_modified,
                "observed_at": observed_at,
                "hash_basis": "raw-http-response-bytes",
                "semantic_status": "not-assessed",
                "approval_status": "not-approved",
            }
            payload = _json_bytes(metadata)
            published = _atomic_create(metadata_path, payload)
            history["revisions"][fetched.sha256] = {
                "metadata_sha256": hashlib.sha256(payload).hexdigest()
            }
        history["current"] = fetched.sha256
        try:
            _atomic_replace(root / "index.json", _json_bytes(index))
        except OSError:
            if published:
                metadata_path.unlink(missing_ok=True)
            raise
    return ChangeResult(
        source_id,
        "new" if previous_sha is None else "changed",
        fetched.sha256,
        previous_sha,
    )
