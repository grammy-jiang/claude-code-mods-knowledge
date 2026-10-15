"""Source-level Chat Mode QA: one direct approved URL per cited Claim.

This is intentionally weaker than native code QA and stronger than a single
"any official docs URL" Boolean. No Chat account/network is involved.
"""

from pathlib import Path

import pytest

from mods_knowledge.claim_source_link_coverage import (
    ClaimSourceLinkError,
    audit_claim_source_links,
)
from mods_knowledge.claims import load_claims
from mods_knowledge.registry import load_registry

ROOT = Path(__file__).resolve().parents[1]
GOOD = (
    "https://code.claude.com/docs/en/plugins/mods/create#check-what-claude-code-reads-from-your-mod"
)
WRONG = "https://code.claude.com/docs/en/plugins/mods/create#get-the-types-for-your-build"
UI = "https://code.claude.com/docs/en/plugins/mods/interface#pick-where-to-draw"


@pytest.fixture(scope="module")
def approved() -> dict:
    sources = load_registry(ROOT / "sources/registry.json")
    return load_claims(ROOT / "claims", sources, ROOT / "sources/snapshots", ROOT / "decisions")


def test_real_ui_case_k0035_is_missing_its_exact_official_source_even_with_other_official_urls(
    approved: dict,
) -> None:
    # In the real 2026-10-16 Chat Mode candidate, K-0035 was cited, but its
    # approved M002 #check-what... locator was absent. The model gave the
    # same first-party PAGE with another anchor instead. No private answer.
    answer = f"K-0035. K-0027. {WRONG} {UI}"
    report = audit_claim_source_links(answer, approved, version="2.1.296", surface="cli")
    assert report["structural_verdict"] == "fail"
    assert report["cited_claim_ids"] == ["K-0027", "K-0035"]
    assert report["missing_exact_source_claim_ids"] == ["K-0035"]
    assert report["uncited_required_claim_ids"] == []
    assert "K-0035" not in report["unsupported_claim_ids"]


def test_exact_approved_source_anchor_passes_even_in_markdown_link(approved: dict) -> None:
    report = audit_claim_source_links(
        f"Use K-0035 with [official K-0035 source]({GOOD}).",
        approved,
        version="2.1.296",
        surface="cli",
        required_claim_ids=("K-0035",),
    )
    assert report["structural_verdict"] == "pass"
    assert report["matched_exact_source_claim_ids"] == ["K-0035"]
    assert not report["missing_exact_source_claim_ids"]
    assert not report["unsupported_claim_ids"]
    assert not report["uncited_required_claim_ids"]
    assert report["is_native_code_validated"] is False
    assert "response" not in str(report).lower()


def test_same_page_wrong_anchor_and_domain_spoof_do_not_count(approved: dict) -> None:
    for link in (
        WRONG,
        GOOD + "-made-up",
        GOOD.replace("code.claude.com", "code.claude.com.attacker.invalid"),
        GOOD.replace("https://", "http://"),
        GOOD + "?tracking=1",
    ):
        result = audit_claim_source_links(
            f"K-0035 link: {link}", approved, version="2.1.296", surface="cli"
        )
        assert result["missing_exact_source_claim_ids"] == ["K-0035"]
        assert result["structural_verdict"] == "fail"


def test_all_three_independently_approved_ui_sources_pass(approved: dict) -> None:
    claim_ids = ("K-0015", "K-0027", "K-0028")
    links = [approved[cid]["evidence"][0]["locator"] for cid in claim_ids]
    answer = "\n".join((cid + " " + link for cid, link in zip(claim_ids, links, strict=True)))
    result = audit_claim_source_links(
        answer, approved, version="2.1.296", surface="cli", required_claim_ids=claim_ids
    )
    assert result["structural_verdict"] == "pass"
    assert result["matched_exact_source_claim_ids"] == sorted(claim_ids)


def test_uncited_required_or_unapproved_claims_fail_closed(approved: dict) -> None:
    missing = audit_claim_source_links(
        f"K-0035 {GOOD}",
        approved,
        version="2.1.296",
        surface="cli",
        required_claim_ids=("K-0035", "K-0027"),
    )
    assert missing["uncited_required_claim_ids"] == ["K-0027"]
    assert missing["structural_verdict"] == "fail"
    unapproved = audit_claim_source_links(
        f"K-0001 K-0035 {GOOD}", approved, version="2.1.296", surface="cli"
    )
    assert unapproved["unsupported_claim_ids"] == ["K-0001"]
    assert unapproved["structural_verdict"] == "fail"


def test_version_outside_scoped_approval_fails_even_with_exact_source(approved: dict) -> None:
    report = audit_claim_source_links(f"K-0035 {GOOD}", approved, version="2.1.310", surface="cli")
    assert report["unsupported_claim_ids"] == ["K-0035"]
    assert report["structural_verdict"] == "fail"


def test_missing_claims_cannot_pass_with_generic_official_link(approved: dict) -> None:
    result = audit_claim_source_links(f"See {GOOD}", approved, version="2.1.296", surface="cli")
    assert result["cited_claim_ids"] == []
    assert result["structural_verdict"] == "fail"


def test_bad_arguments_are_rejected_not_guessed(approved: dict) -> None:
    for version, surface in (("latest", "cli"), ("2.1.296", "unknown")):
        with pytest.raises(ClaimSourceLinkError):
            audit_claim_source_links("K-0035", approved, version=version, surface=surface)
    with pytest.raises(ClaimSourceLinkError):
        audit_claim_source_links("x" * 500_001, approved, version="2.1.296", surface="cli")
