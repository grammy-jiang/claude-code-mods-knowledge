"""Even official URL mentions elsewhere cannot excuse omitted Evidence IDs."""

from pathlib import Path

import pytest

from mods_knowledge.claim_source_link_coverage import (
    ClaimSourceLinkError,
    audit_claim_evidence_section,
    audit_claim_source_links,
)
from mods_knowledge.claims import load_claims
from mods_knowledge.registry import load_registry

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def approved() -> dict:
    return load_claims(
        ROOT / "claims",
        load_registry(ROOT / "sources/registry.json"),
        ROOT / "sources/snapshots",
        ROOT / "decisions",
    )


def source(approved: dict, cid: str) -> str:
    return next(
        entry["locator"]
        for entry in approved[cid]["evidence"]
        if entry.get("kind") == "official-doc" and entry.get("source_id", "").startswith("M")
    )


def test_two_approved_claims_every_line_in_opening_evidence_pass(approved):
    a, b = (source(approved, cid) for cid in ("K-0040", "K-0041"))
    answer = (
        "## Evidence\n"
        f"- K-0040 — {a}\n"
        f"- K-0041 — {b}\n\n"
        "## Scope\nCLI 2.1.302.\n\n"
        "## Answer\nUse K-0040; do not mutate K-0041 inputs.\n"
    )
    r = audit_claim_evidence_section(
        answer,
        approved,
        version="2.1.302",
        surface="cli",
        required_claim_ids=("K-0040", "K-0041"),
    )
    assert r["structural_verdict"] == "pass"
    assert r["has_ordered_opening_evidence_scope_answer"] is True
    assert r["evidence_claim_ids_with_exact_approved_locator"] == ["K-0040", "K-0041"]
    assert r["cited_claim_ids_missing_exact_evidence_line"] == []
    assert r["is_answer_semantics_or_runtime_verified"] is False


def test_realistic_302_case_body_only_k0041_is_missed_by_older_link_checker(approved):
    a, b = (source(approved, cid) for cid in ("K-0040", "K-0041"))
    answer = (
        "## Evidence\n"
        f"- K-0040: {a}\n\n"
        "## Scope\nCLI 2.1.302.\n\n"
        "## Answer\n"
        f"K-0041: do not mutate e. {b}\n"
    )
    old = audit_claim_source_links(answer, approved, version="2.1.302", surface="cli")
    assert old["structural_verdict"] == "pass"
    audit = audit_claim_evidence_section(answer, approved, version="2.1.302", surface="cli")
    assert audit["structural_verdict"] == "fail"
    assert audit["overall_exact_source_link_verdict"] == "pass"
    assert audit["cited_claim_ids_missing_exact_evidence_line"] == ["K-0041"]


def test_url_for_wrong_claim_same_page_anchor_fails(approved):
    wrong = source(approved, "K-0041")
    answer = f"## Evidence\n- K-0040 — {wrong}\n## Scope\n302 only\n## Answer\nK-0040 observer\n"
    result = audit_claim_evidence_section(answer, approved, version="2.1.302", surface="cli")
    assert result["structural_verdict"] == "fail"
    assert result["cited_claim_ids_missing_exact_evidence_line"] == ["K-0040"]
    assert result["malformed_or_wrong_locator_evidence_claim_ids"] == ["K-0040"]


@pytest.mark.parametrize("intro", ["Preamble\n", "## Scope\nHere\n"])
def test_intro_or_wrong_heading_order_fails(approved, intro):
    url = source(approved, "K-0040")
    answer = intro + f"## Evidence\n- K-0040 — {url}\n## Scope\nOnly 302\n## Answer\nK-0040\n"
    r = audit_claim_evidence_section(answer, approved, version="2.1.302", surface="cli")
    assert r["structural_verdict"] == "fail"
    assert r["has_ordered_opening_evidence_scope_answer"] is False


def test_evidence_multiple_claim_ids_on_single_url_line_fails(approved):
    url = source(approved, "K-0040")
    answer = f"## Evidence\n- K-0040 K-0041 — {url}\n## Scope\n302\n## Answer\nObserver\n"
    r = audit_claim_evidence_section(answer, approved, version="2.1.302", surface="cli")
    assert r["structural_verdict"] == "fail"
    assert r["malformed_or_wrong_locator_evidence_claim_ids"] == ["K-0040", "K-0041"]


def test_309_unsupported_target_fail_even_with_302_links(approved):
    url = source(approved, "K-0040")
    answer = f"## Evidence\n- K-0040 — {url}\n## Scope\n309\n## Answer\nMaybe K-0040\n"
    r = audit_claim_evidence_section(answer, approved, version="2.1.309", surface="cli")
    assert r["structural_verdict"] == "fail"
    assert r["unsupported_claim_ids"] == ["K-0040"]


def test_missing_or_giant_answer_fails_closed(approved):
    with pytest.raises(ClaimSourceLinkError):
        audit_claim_evidence_section("", approved, version="2.1.302", surface="cli")
    with pytest.raises(ClaimSourceLinkError):
        audit_claim_evidence_section("x" * 500001, approved, version="2.1.302", surface="cli")
