"""Fail-closed Claim policy and source-to-evidence cross-reference tests."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from mods_knowledge.claims import approved_claims, load_claims, validate_claims
from mods_knowledge.errors import ClaimError
from mods_knowledge.registry import load_registry

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "docs/design/mods_ssot_design_v0_1/schemas/claim.schema.json"
EXAMPLE = ROOT / "docs/design/mods_ssot_design_v0_1/EXAMPLE_CANDIDATE_CLAIM.json"
SOURCE = load_registry(ROOT / "sources/registry.json")
SNAPSHOTS = ROOT / "sources/snapshots"


@pytest.fixture
def claim() -> dict:
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


def validate(claims: dict[str, dict], registry=None, decision_dir=None) -> None:
    validate_claims(
        claims,
        SOURCE if registry is None else registry,
        SNAPSHOTS,
        Path("/nonexistent-decisions") if decision_dir is None else decision_dir,
        SCHEMA,
    )


def test_original_candidate_is_admissible_without_false_approval(claim: dict) -> None:
    validate({"K-0001": claim})
    assert approved_claims({"K-0001": claim}, "2.1.296", "cli") == []


def test_empty_claims_are_valid_and_do_not_publish_anything() -> None:
    validate({})
    assert approved_claims({}, "2.1.296", "cli") == []


@pytest.mark.parametrize(
    "mutation",
    [
        lambda x: x.update(claim_id="K-9999"),
        lambda x: x.update(undocumented_field=True),
        lambda x: x["areas"]["secondary"].append("T"),
        lambda x: x["applies_to"]["claude_code"].update(
            min_inclusive="2.1.400", max_exclusive="2.1.300"
        ),
        lambda x: x["evidence"][0].update(source_id="M999"),
        lambda x: x["evidence"][0].update(source_id="M035"),
        lambda x: x["evidence"][0].update(kind="community"),
        lambda x: x["evidence"][0].update(snapshot_sha256="a" * 64),
        lambda x: x["related_claims"].append("K-9999"),
        lambda x: x["related_claims"].append("K-0001"),
        lambda x: x["supersedes"].append("K-0001"),
        lambda x: x["verification"].update(
            runtime="incompatible", runtime_profiles=["nonexistent"]
        ),
    ],
)
def test_invalid_candidate_metadata_is_blocked(claim: dict, mutation) -> None:
    mutation(claim)
    with pytest.raises(ClaimError):
        validate({"K-0001": claim})


@pytest.mark.parametrize(
    "source_id,kind",
    [
        ("M035", "history"),
        ("M046", "community"),
        ("M036", "official-example"),
    ],
)
def test_historical_or_non_normative_sources_allowed_only_as_candidate_context(
    claim: dict, source_id: str, kind: str
) -> None:
    claim["evidence"][0].update(source_id=source_id, kind=kind, role="context")
    validate({"K-0001": claim})


def test_historical_claim_cannot_be_published_as_current(claim: dict) -> None:
    claim.update(authority="historical", kind="history")
    claim["evidence"][0].update(source_id="M035", kind="history", role="context")
    validate({"K-0001": claim})
    assert approved_claims({"K-0001": claim}, "2.1.296", "cli") == []


def test_claim_references_must_resolve_and_have_no_cycles(claim: dict) -> None:
    second = copy.deepcopy(claim)
    second["claim_id"] = "K-0002"
    second["related_claims"] = ["K-0001"]
    claim["related_claims"] = ["K-0002"]
    with pytest.raises(ClaimError, match="cycle"):
        validate({"K-0001": claim, "K-0002": second})


def test_unsupported_version_comparisons_raise_without_guessing() -> None:
    with pytest.raises(ClaimError):
        approved_claims({}, "latest", "cli")


def test_duplicate_identifiers_rejected_during_disk_load(tmp_path: Path, claim: dict) -> None:
    path = tmp_path / "claims"
    path.mkdir()
    (path / "K-0001.json").write_text(json.dumps(claim))
    (path / "K-0002.json").write_text(json.dumps(claim))
    with pytest.raises(ClaimError, match="ID"):
        load_claims(path, SOURCE, SNAPSHOTS, tmp_path / "decisions")


def test_reject_invalid_filename_or_symlink(tmp_path: Path, claim: dict) -> None:
    path = tmp_path / "claims"
    path.mkdir()
    (path / "evil.json").write_text(json.dumps(claim))
    with pytest.raises(ClaimError):
        load_claims(path, SOURCE, SNAPSHOTS, tmp_path / "decisions")
    (path / "evil.json").unlink()
    target = tmp_path / "link-target.json"
    target.write_text(json.dumps(claim))
    (path / "K-0001.json").symlink_to(target)
    with pytest.raises(ClaimError):
        load_claims(path, SOURCE, SNAPSHOTS, tmp_path / "decisions")


def test_explicit_normative_approval_without_decision_is_rejected(claim: dict) -> None:
    claim.update(authority="normative", kind="api", lifecycle="approved")
    claim["applies_to"]["claude_code"].update(min_inclusive="2.1.296", max_exclusive="2.1.297")
    claim["applies_to"]["surfaces"] = ["cli"]
    claim["evidence"][0].update(
        role="supports",
        snapshot_sha256=json.loads((SNAPSHOTS / "index.json").read_text())["sources"]["M003"][
            "current"
        ],
    )
    claim["verification"].update(
        source="reviewed",
        runtime="integration-pass",
        runtime_profiles=["macbook-20261013"],
        test_evidence=["tests/fixtures/test-mods-api.md"],
    )
    with pytest.raises(ClaimError, match="decision"):
        validate({"K-0001": claim})


def test_normative_approval_disallows_community_only_and_conflict(claim: dict) -> None:
    claim.update(authority="normative", kind="api", lifecycle="approved")
    claim["applies_to"]["claude_code"].update(min_inclusive="2.1.296", max_exclusive="2.1.297")
    claim["applies_to"]["surfaces"] = ["cli"]
    claim["evidence"][0].update(source_id="M046", kind="community", role="supports")
    claim["verification"].update(
        source="reviewed",
        runtime="smoke-pass",
        runtime_profiles=["macbook-20261013"],
        test_evidence=["tests/fixtures/proof.md"],
    )
    with pytest.raises(ClaimError):
        validate({"K-0001": claim})


def test_reviewed_claim_without_decision_is_invalid(claim: dict) -> None:
    claim["lifecycle"] = "reviewed"
    claim["verification"]["source"] = "reviewed"
    with pytest.raises(ClaimError, match="pinned"):
        validate({"K-0001": claim})
