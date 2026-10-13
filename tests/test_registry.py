from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from mods_knowledge.errors import RegistryError
from mods_knowledge.registry import eligible_official_sources, load_registry, validate_registry

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "docs/design/mods_ssot_design_v0_1/schemas/source.schema.json"
SEED = ROOT / "docs/design/mods_ssot_design_v0_1/registry_seed_UNVERIFIED.json"


@pytest.fixture
def data() -> dict:
    return json.loads(SEED.read_text(encoding="utf-8"))


def test_imported_registry_retains_all_original_source_ids_and_statuses(data: dict) -> None:
    loaded = load_registry(ROOT / "sources/registry.json", SCHEMA)
    assert len(loaded) == 91
    assert set(loaded) == {entry["source_id"] for entry in data["sources"]}
    assert [loaded[entry["source_id"]] for entry in data["sources"]] == data["sources"]
    assert all(source["snapshot"]["state"] == "unpinned" for source in loaded.values())
    assert all(source["review_state"] != "pinned" for source in loaded.values())


def test_official_docs_eligibility_excludes_examples_history_community(data: dict) -> None:
    registry = validate_registry(data, SCHEMA)
    sources = eligible_official_sources(registry)
    assert len(sources) == 43
    assert [entry["source_id"] for entry in sources[:3]] == ["M001", "M002", "M003"]
    assert {source["trust_layer"] for source in sources} == {"L0", "L1", "L2"}
    assert all(
        source["url"].startswith("https://code.claude.com/docs/en/")
        or source["url"] == "https://code.claude.com/docs/llms.txt"
        for source in sources
    )


@pytest.mark.parametrize(
    "mutation",
    [
        lambda data: data["sources"].append(copy.deepcopy(data["sources"][0])),
        lambda data: data["sources"][1].update(url=data["sources"][0]["url"]),
        lambda data: data["sources"][1].update(canonical_url=data["sources"][0]["url"]),
        lambda data: data["sources"][0].update(trust_layer="C"),
        lambda data: data["sources"][0].update(url="http://code.claude.com/docs/en/test"),
        lambda data: data["sources"][0].update(superseded_by="M999"),
        lambda data: data["sources"][0].update(superseded_by="M001"),
        lambda data: data["sources"][0]["areas"]["secondary"].append("E"),
        lambda data: data["sources"][0]["snapshot"].update(state="unpinned", sha256="a" * 64),
        lambda data: data["sources"][0].update(review_state="pinned"),
        lambda data: next(x for x in data["sources"] if x["trust_layer"] == "H").update(
            historical_reason=None
        ),
    ],
)
def test_invalid_registry_is_rejected(data: dict, mutation) -> None:
    mutation(data)
    with pytest.raises(RegistryError):
        validate_registry(data, SCHEMA)


def test_schema_rejects_invalid_field_and_type(data: dict) -> None:
    data["sources"][0]["undocumented_flag"] = True
    with pytest.raises(RegistryError):
        validate_registry(data, SCHEMA)


def test_rejects_duplicate_alias_with_different_fragment(data: dict) -> None:
    # Fragment changes a browser position, not the actual document identity.
    data["sources"][1]["url"] = data["sources"][0]["url"] + "#test"
    with pytest.raises(RegistryError):
        validate_registry(data, SCHEMA)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda data: data["sources"].__setitem__(0, "not a source record"),
        lambda data: data["sources"][0].update(
            canonical_url="https://evil.example/docs/en/overview"
        ),
        lambda data: data.update(approved_claims=999),
    ],
)
def test_malformed_or_untrusted_registry_metadata_raises_registry_error(
    data: dict, mutation
) -> None:
    mutation(data)
    with pytest.raises(RegistryError):
        validate_registry(data, SCHEMA)
