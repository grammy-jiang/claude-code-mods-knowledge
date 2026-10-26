"""Deterministic per-Claim first-party source URL audit for Chat Mode QA.

Only a structure checker over an already-received complete visible answer.
Never authenticates a ChatGPT conversation, asserts an actual Skill read,
runs model-origin code or promotes a source reference into API correctness.
A single URL pointing to the same page at the WRONG section is insufficient.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from urllib.parse import urlsplit

from .claims import approved_claims
from .errors import ClaimError

_CLAIM_PATTERN = re.compile(r"(?<![A-Za-z0-9_-])K-[0-9]{4,}\b")
_URL_PATTERN = re.compile(r"https?://[^\s<>()\[\]{}'\"`]+", re.I)


class ClaimSourceLinkError(ValueError):
    """The QA source-link evaluation could not safely proceed."""


def _urls(answer: str) -> set[str]:
    urls: set[str] = set()
    for match in _URL_PATTERN.finditer(answer):
        url = match.group(0).rstrip(".,;:!?")
        try:
            parsed = urlsplit(url)
            if (
                parsed.scheme == "https"
                and parsed.netloc == "code.claude.com"
                and parsed.path.startswith("/docs/en/plugins/mods/")
                and parsed.fragment
                and not parsed.username
                and not parsed.password
            ):
                urls.add(url)
        except ValueError:
            continue
    return urls


def audit_claim_source_links(
    answer: str,
    claims: Mapping[str, dict],
    *,
    version: str,
    surface: str,
    required_claim_ids: Iterable[str] = (),
) -> dict:
    """Compare every cited K-Claim with its EXACT approved official locator.

    Caller must independently load/validate the SSOT claims and inspect the
    full user-visible assistant turn (not only the last assistant segment).
    Output deliberately excludes any answer text or private identifier.
    `structural_verdict="pass"` does NOT mean runtime/semantic pass.
    """
    if not isinstance(answer, str) or not answer.strip() or len(answer) > 500_000:
        raise ClaimSourceLinkError("Invalid or unbounded complete Chat answer")
    if not isinstance(claims, Mapping):
        raise ClaimSourceLinkError("Validated SSOT Claim mapping required")
    try:
        in_scope = {claim["claim_id"]: claim for claim in approved_claims(claims, version, surface)}
    except (ClaimError, KeyError, TypeError, ValueError) as exc:
        raise ClaimSourceLinkError("Invalid version/surface or claim map") from exc
    if not isinstance(required_claim_ids, (tuple, list, set, frozenset)):
        raise ClaimSourceLinkError("Required Claim IDs must be a finite collection")
    required = set(required_claim_ids)
    if len(required) > 100 or any(
        not isinstance(cid, str) or not _CLAIM_PATTERN.fullmatch(cid) for cid in required
    ):
        raise ClaimSourceLinkError("Invalid required Claim IDs")
    observed = set(_CLAIM_PATTERN.findall(answer))
    if len(observed) > 100:
        raise ClaimSourceLinkError("Unbounded number of cited Claims")
    recognized = observed & set(in_scope)
    urls = _urls(answer)
    matched: set[str] = set()
    missing: set[str] = set()
    for cid in recognized:
        refs = [
            entry["locator"]
            for entry in in_scope[cid].get("evidence") or []
            if entry.get("kind") == "official-doc"
            and entry.get("source_id", "").startswith("M")
            and isinstance(entry.get("locator"), str)
            and entry["locator"].startswith("https://code.claude.com/docs/en/plugins/mods/")
            and "#" in entry["locator"]
        ]
        if refs and any(ref in urls for ref in refs):
            matched.add(cid)
        else:
            missing.add(cid)
    unsupported = observed - recognized
    uncited_required = required - observed
    pass_structure = bool(observed) and not (missing or unsupported or uncited_required)
    return {
        "structural_verdict": "pass" if pass_structure else "fail",
        "version": version,
        "surface": surface,
        "cited_claim_ids": sorted(observed),
        "matched_exact_source_claim_ids": sorted(matched),
        "missing_exact_source_claim_ids": sorted(missing),
        "unsupported_claim_ids": sorted(unsupported),
        "uncited_required_claim_ids": sorted(uncited_required),
        "official_source_links_observed": len(urls),
        "is_native_code_validated": False,
        "notes": "Source/Claim structural check only; real Skill read and code semantics are separate",
    }


# Stronger, opt-in form of Claim provenance checking for generated Mods
# Skills that explicitly require an opening Evidence / Scope / Answer layout.
# An exact official link appearing somewhere in prose is weaker than listing
# that Claim's own exact source URL in the designated Evidence section.
_EVIDENCE_HEADINGS = re.compile(
    r"(?m)^[ ]{0,3}(#{1,4})[ \t]+(?P<name>Evidence|Scope|Answer)[ \t]*:?[ \t]*$",
    re.IGNORECASE,
)
_ANY_MD_HEADING = re.compile(r"(?m)^[ ]{0,3}#{1,6}[ \t]+[^\n]+$")


def audit_claim_evidence_section(
    answer: str,
    claims: Mapping[str, dict],
    *,
    version: str,
    surface: str,
    required_claim_ids: Iterable[str] = (),
) -> dict:
    """Ensure EVERY cited Claim has its OWN approved URL in opening Evidence.

    Supplements, never replaces, audit_claim_source_links. This structural
    guard cannot establish whether the native Skill was loaded, whether
    generated code typechecks, or whether the model's prose is true.
    A failed result is a QA signal, not an automatic edit to approval state.
    """
    base = audit_claim_source_links(
        answer,
        claims,
        version=version,
        surface=surface,
        required_claim_ids=required_claim_ids,
    )
    try:
        active = {c["claim_id"]: c for c in approved_claims(claims, version, surface)}
    except (ClaimError, KeyError, TypeError, ValueError) as exc:
        raise ClaimSourceLinkError("Invalid approved Claim mapping") from exc
    headings = list(_EVIDENCE_HEADINGS.finditer(answer))
    by_name = {
        key: [m for m in headings if m.group("name").lower() == key]
        for key in ("evidence", "scope", "answer")
    }
    has_order = all(len(by_name[k]) == 1 for k in by_name)
    if has_order:
        a, b, c = (by_name[key][0] for key in ("evidence", "scope", "answer"))
        has_order = a.start() < b.start() < c.start() and not answer[: a.start()].strip()
    evidence_lines: list[str] = []
    if has_order:
        evidence_header = by_name["evidence"][0]
        subtext = answer[evidence_header.end() :]
        next_heading = _ANY_MD_HEADING.search(subtext)
        evidence_lines = subtext[: next_heading.start() if next_heading else None].splitlines()
    matched: set[str] = set()
    malformed: set[str] = set()
    found: set[str] = set()
    for line in evidence_lines:
        ids = set(_CLAIM_PATTERN.findall(line))
        if not ids:
            continue
        found.update(ids)
        # One Claim per evidence line. Links on a different line or merely
        # near the Claim cannot substitute for an exact direct locator.
        if len(ids) != 1:
            malformed.update(ids)
            continue
        claim_id = next(iter(ids))
        claim = active.get(claim_id)
        if claim is None:
            malformed.add(claim_id)
            continue
        expected = {
            x["locator"]
            for x in claim.get("evidence") or []
            if isinstance(x, dict)
            and x.get("kind") == "official-doc"
            and isinstance(x.get("locator"), str)
            and x["locator"].startswith("https://code.claude.com/docs/en/plugins/mods/")
            and "#" in x["locator"]
        }
        if expected & _urls(line):
            matched.add(claim_id)
        else:
            malformed.add(claim_id)
    cited = set(base["cited_claim_ids"])
    missing = cited - matched
    passed = (
        bool(has_order)
        and bool(cited)
        and base["structural_verdict"] == "pass"
        and not missing
        and not malformed
    )
    return {
        "structural_verdict": "pass" if passed else "fail",
        "version": version,
        "surface": surface,
        "has_ordered_opening_evidence_scope_answer": bool(has_order),
        "all_cited_claim_ids": sorted(cited),
        "evidence_claim_ids_found": sorted(found),
        "evidence_claim_ids_with_exact_approved_locator": sorted(matched),
        "cited_claim_ids_missing_exact_evidence_line": sorted(missing),
        "malformed_or_wrong_locator_evidence_claim_ids": sorted(malformed),
        "overall_exact_source_link_verdict": base["structural_verdict"],
        "unsupported_claim_ids": base["unsupported_claim_ids"],
        "uncited_required_claim_ids": base["uncited_required_claim_ids"],
        "is_native_skill_invocation_verified": False,
        "is_answer_semantics_or_runtime_verified": False,
        "notes": "Exact Claim-linked Evidence section structure only, never a semantic PASS",
    }
