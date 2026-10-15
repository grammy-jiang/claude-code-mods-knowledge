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
