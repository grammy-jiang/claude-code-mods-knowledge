"""Immutable history and current-pointer tests with synthetic fetched hashes."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import pytest

from mods_knowledge.collector import FetchResult
from mods_knowledge.errors import CollectionError
from mods_knowledge.registry import load_registry
from mods_knowledge.storage import record_observation, verify_snapshot_store

ROOT = Path(__file__).resolve().parents[1]
OFFICIAL = load_registry(ROOT / "sources/registry.json")


def observation(source: dict, content: bytes) -> FetchResult:
    from hashlib import sha256

    return FetchResult(
        url=source["url"],
        sha256=sha256(content).hexdigest(),
        byte_length=len(content),
        content_type="text/html",
        etag='"revision"',
        last_modified=None,
    )


def timestamp() -> datetime:
    return datetime(2026, 10, 13, 2, 0, 0, tzinfo=UTC)


def test_first_observation_creates_immutable_metadata_and_index(tmp_path: Path) -> None:
    src = OFFICIAL["M001"]
    snap = observation(src, b"<html>v1</html>")
    result = record_observation(tmp_path, src, snap, timestamp())
    assert result.status == "new"
    assert result.previous_sha256 is None
    index = json.loads((tmp_path / "index.json").read_text())
    history = index["sources"]["M001"]
    assert history["current"] == snap.sha256
    assert set(history["revisions"]) == {snap.sha256}
    meta_path = tmp_path / "metadata/M001" / f"{snap.sha256}.json"
    meta = json.loads(meta_path.read_text())
    assert meta["source_id"] == "M001"
    assert meta["content_sha256"] == snap.sha256
    assert meta["semantic_status"] == "not-assessed"
    assert meta["approval_status"] == "not-approved"
    assert b"<html>v1</html>" not in meta_path.read_bytes()
    assert verify_snapshot_store(tmp_path) == []


def test_repeat_unchanged_does_not_rewrite_files(tmp_path: Path) -> None:
    src = OFFICIAL["M001"]
    snap = observation(src, b"<html>v1</html>")
    first = record_observation(tmp_path, src, snap, timestamp())
    assert first.status == "new"
    index_path = tmp_path / "index.json"
    meta_path = tmp_path / "metadata/M001" / f"{snap.sha256}.json"
    prev_index = index_path.read_bytes()
    prev_meta = meta_path.read_bytes()
    second = record_observation(tmp_path, src, snap, datetime(2026, 10, 14, tzinfo=UTC))
    assert second.status == "unchanged"
    assert second.previous_sha256 == snap.sha256
    assert index_path.read_bytes() == prev_index
    assert meta_path.read_bytes() == prev_meta
    assert verify_snapshot_store(tmp_path) == []


def test_changed_content_preserves_old_metadata_and_tracks_revisions(tmp_path: Path) -> None:
    src = OFFICIAL["M001"]
    old = observation(src, b"old")
    new = observation(src, b"new")
    record_observation(tmp_path, src, old, timestamp())
    result = record_observation(tmp_path, src, new, timestamp())
    assert result.status == "changed"
    assert result.previous_sha256 == old.sha256
    index = json.loads((tmp_path / "index.json").read_text())
    assert index["sources"]["M001"]["current"] == new.sha256
    assert set(index["sources"]["M001"]["revisions"]) == {old.sha256, new.sha256}
    assert (tmp_path / "metadata/M001" / f"{old.sha256}.json").exists()
    assert (tmp_path / "metadata/M001" / f"{new.sha256}.json").exists()
    assert verify_snapshot_store(tmp_path) == []


@pytest.mark.parametrize("source", [OFFICIAL["M035"], OFFICIAL["M046"], OFFICIAL["M036"]])
def test_historical_community_and_official_example_never_enter_active_store(
    tmp_path: Path, source: dict
) -> None:
    with pytest.raises(CollectionError):
        record_observation(tmp_path, source, observation(source, b"data"), timestamp())
    assert not (tmp_path / "index.json").exists()


def test_source_mismatch_fails_without_mutation(tmp_path: Path) -> None:
    src = OFFICIAL["M001"]
    invalid = observation(OFFICIAL["M002"], b"data")
    with pytest.raises(CollectionError):
        record_observation(tmp_path, src, invalid, timestamp())
    assert not (tmp_path / "index.json").exists()


def test_corrupt_index_or_modified_metadata_is_reported(tmp_path: Path) -> None:
    src = OFFICIAL["M001"]
    fetched = observation(src, b"sample")
    record_observation(tmp_path, src, fetched, timestamp())
    meta = tmp_path / "metadata/M001" / f"{fetched.sha256}.json"
    body = json.loads(meta.read_text())
    body["etag"] = '"tampered"'
    meta.write_text(json.dumps(body), encoding="utf-8")
    assert any("hash" in err.lower() for err in verify_snapshot_store(tmp_path))


def test_concurrent_observations_of_different_sources_do_not_lose_updates(
    tmp_path: Path,
) -> None:
    sources = [OFFICIAL[f"M{i:03d}"] for i in range(1, 9)]

    def record(source: dict):
        record_observation(
            tmp_path, source, observation(source, source["source_id"].encode()), timestamp()
        )

    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(record, sources))
    index = json.loads((tmp_path / "index.json").read_text())
    assert set(index["sources"]) == {src["source_id"] for src in sources}
    assert verify_snapshot_store(tmp_path) == []


def test_naive_datetime_rejected_without_writes(tmp_path: Path) -> None:
    source = OFFICIAL["M001"]
    with pytest.raises(CollectionError):
        record_observation(tmp_path, source, observation(source, b"x"), datetime(2026, 10, 13))
    assert not (tmp_path / "index.json").exists()


def test_mismatched_official_layer_and_type_cannot_be_recorded(tmp_path: Path) -> None:
    src = dict(OFFICIAL["M001"], source_type="official-dependency")
    with pytest.raises(CollectionError):
        record_observation(tmp_path, src, observation(src, b"data"), timestamp())
    assert not (tmp_path / "index.json").exists()
