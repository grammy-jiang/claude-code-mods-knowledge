"""Atomic Knowledge Claim validation and conservative evidence/compatibility policy.

A raw HTTP fingerprint only proves an observation; it is never an API approval.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from .errors import ClaimError
from .storage import verify_snapshot_store

SCHEMA_PATH = (
    Path(__file__).resolve().parents[2]
    / "docs/design/mods_ssot_design_v0_1/schemas/claim.schema.json"
)
CLAIM_ID = re.compile(r"K-[0-9]{4,}\Z")
AREA = ("E", "S", "T", "Q", "P", "U")
MATCH_KIND = {
    "L0": frozenset(("official-doc",)),
    "L1": frozenset(("official-doc",)),
    "L2": frozenset(("official-doc",)),
    "R": frozenset(("official-example", "official-source")),
    "C": frozenset(("community",)),
    "H": frozenset(("history",)),
}
AUTHORITATIVE = frozenset(("L0", "L1"))


def parse_version(text: str) -> tuple[int, int, int]:
    if not isinstance(text, str) or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", text):
        raise ClaimError(f"Expected explicit three-part version, got {text!r}")
    return tuple(int(part) for part in text.split("."))  # type: ignore[return-value]


def _interval(claim: dict) -> tuple[tuple[int, ...] | None, tuple[int, ...] | None]:
    scope = claim["applies_to"]["claude_code"]
    lo = parse_version(scope["min_inclusive"]) if scope["min_inclusive"] else None
    hi = parse_version(scope["max_exclusive"]) if scope["max_exclusive"] else None
    if lo is not None and hi is not None and lo >= hi:
        raise ClaimError(f"{claim['claim_id']}: empty or reversed version interval")
    return lo, hi


def _overlap(a: dict, b: dict) -> bool:
    low_a, high_a = _interval(a)
    low_b, high_b = _interval(b)
    if high_a is not None and low_b is not None and high_a <= low_b:
        return False
    if high_b is not None and low_a is not None and high_b <= low_a:
        return False
    return bool(set(a["applies_to"]["surfaces"]) & set(b["applies_to"]["surfaces"]))


def _known_observations(snapshot_root: Path) -> dict:
    index = snapshot_root / "index.json"
    if not index.is_file() or index.is_symlink():
        return {}
    try:
        data = json.loads(index.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ClaimError(f"Unusable observed-snapshot index: {exc}") from exc
    if data.get("schema_version") != 1 or not isinstance(data.get("sources"), dict):
        raise ClaimError("Unsupported observed-snapshot index format")
    problems = verify_snapshot_store(snapshot_root)
    if problems:
        raise ClaimError("Observed evidence metadata is not intact: " + "; ".join(problems))
    return data["sources"]


def _is_pinned_official_support(
    evidence: dict,
    source: dict,
    snapshot_root: Path,
    observations: Mapping[str, dict],
    *,
    required_version: str | None = None,
) -> bool:
    """Validate historical or later independently reviewed source revisions.

    Never modify the original Registry pin: previous 2.1.296 Claim evidence
    and decision ledgers must remain valid when 2.1.302 is reviewed.
    """
    pin = source["snapshot"]
    sha = evidence.get("snapshot_sha256")
    source_id = source["source_id"]
    if (
        source["review_state"] != "pinned"
        or pin["state"] != "pinned"
        or not isinstance(sha, str)
        or sha not in observations.get(source_id, {}).get("revisions", {})
    ):
        return False
    locator = evidence["locator"]
    if not locator.startswith(source["url"] + "#") or not locator[len(source["url"]) + 1 :].strip():
        return False
    metadata_file = snapshot_root / "metadata" / source_id / f"{sha}.json"
    try:
        metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
        if (
            metadata["source_id"] != source_id
            or metadata["trust_layer"] != source["trust_layer"]
            or metadata["url"] != source["url"]
            or metadata["content_sha256"] != sha
        ):
            return False
        from datetime import datetime

        observed = datetime.fromisoformat(metadata["observed_at"].replace("Z", "+00:00"))
        if observed.tzinfo is None:
            return False
        from .review_evidence import validate_official_review

        if sha == pin["sha256"]:
            checked = datetime.fromisoformat(pin["checked_at"].replace("Z", "+00:00"))
            return (
                checked.tzinfo is not None
                and checked >= observed
                and validate_official_review(
                    source,
                    sha,
                    locator.partition("#")[2],
                    snapshot_root.parent / "reviews",
                    snapshot_root,
                )
            )

        # A later revision is not approved by a changed HTTP digest alone.
        # Require a new SHA-addressed official Markdown section review whose
        # declared scope explicitly identifies the target version.
        review_dir = snapshot_root.parent / "reviews"
        file = review_dir / "revisions" / source_id / f"{sha}.json"
        if (
            not required_version
            or file.is_symlink()
            or not file.is_file()
            or file.stat().st_size > 120_000
        ):
            return False
        record = json.loads(file.read_text(encoding="utf-8"))
        if not isinstance(record, dict) or f"CLI {required_version}" not in record.get("scope", ""):
            return False
        reviewed = datetime.fromisoformat(record["reviewed_at"].replace("Z", "+00:00"))
        if reviewed.tzinfo is None or reviewed < observed:
            return False
        revised_source = dict(source)
        revised_source["snapshot"] = {
            **pin,
            "sha256": sha,
            "checked_at": record["reviewed_at"],
        }
        return validate_official_review(
            revised_source,
            sha,
            locator.partition("#")[2],
            review_dir,
            snapshot_root,
            revision_review_file=file,
        )
    except (OSError, ValueError, KeyError, TypeError):
        return False


def _is_pinned_official_example(evidence: dict, source: dict) -> bool:
    """Only a reviewed Anthropic Git commit pin can support official examples.

    The Git object itself must be independently checked before a publisher
    treats the pin as an implemented API contract (examples are guidance).
    """
    pin = source["snapshot"]
    return bool(
        source["source_type"] == "official-example"
        and source["url"].startswith("https://github.com/anthropics/")
        and source["review_state"] == "pinned"
        and pin["state"] == "pinned"
        and pin.get("commit_sha")
        and pin["commit_sha"] == evidence.get("commit_sha")
        and pin.get("checked_at")
        and evidence["locator"].startswith(source["url"])
    )


def _check_refs(claims: Mapping[str, dict]) -> None:
    for cid, claim in claims.items():
        for name in ("related_claims", "supersedes"):
            for other in claim.get(name, []):
                if other not in claims:
                    raise ClaimError(f"{cid}: unknown {name} reference {other}")
                if other == cid:
                    raise ClaimError(f"{cid}: self-referential {name}")
    for field in ("related_claims", "supersedes"):
        _check_cycles(claims, field)


def _check_cycles(claims: Mapping[str, dict], field: str) -> None:
    visited: set[str] = set()
    stack: set[str] = set()

    def visit(cid: str) -> None:
        if cid in stack:
            raise ClaimError(f"Cross-claim {field} cycle at {cid}")
        if cid in visited:
            return
        stack.add(cid)
        for other in claims[cid].get(field, []):
            visit(other)
        stack.remove(cid)
        visited.add(cid)

    for cid in claims:
        visit(cid)


def validate_claims(
    claims: Mapping[str, dict],
    source_registry: Mapping[str, dict],
    snapshot_root: Path,
    decision_dir: Path,
    schema_path: Path = SCHEMA_PATH,
    *,
    _decision_overrides: Mapping[str, dict] | None = None,
) -> None:
    """Validate every claim and its references, approval policy, and audit ledger.

    No network or mutation. Candidate entries may lack pins but may not invent
    a verified digest or refer to unknown official materials.
    """
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
    except (OSError, ValueError) as exc:
        raise ClaimError(f"Cannot use claim schema: {exc}") from exc
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    observations = None
    for cid, claim in claims.items():
        if not isinstance(claim, dict):
            raise ClaimError(f"{cid}: expected a JSON claim record")
        violations = sorted(validator.iter_errors(claim), key=lambda err: str(err.path))
        if violations:
            raise ClaimError(f"{cid}: claim schema violation: {violations[0].message}")
        if cid != claim["claim_id"] or not CLAIM_ID.fullmatch(cid):
            raise ClaimError(f"{cid}: claim ID does not match its record")
        if set(claim["areas"]["primary"]) & set(claim["areas"]["secondary"]):
            raise ClaimError(f"{cid}: duplicated engineering area")
        lo, hi = _interval(claim)
        verification = claim["verification"]
        if verification["runtime"] == "not-run" and (
            verification.get("runtime_profiles") or verification.get("test_evidence")
        ):
            raise ClaimError(f"{cid}: cannot have runtime evidence with status not-run")
        if verification["runtime"] != "not-run" and (
            not verification.get("runtime_profiles") or not verification.get("test_evidence")
        ):
            raise ClaimError(f"{cid}: runtime status requires profiles and test evidence")
        for evidence in claim["evidence"]:
            source_id = evidence["source_id"]
            source = source_registry.get(source_id)
            if source is None:
                raise ClaimError(f"{cid}: unknown evidence source {source_id}")
            layer = source["trust_layer"]
            if evidence["kind"] not in MATCH_KIND[layer]:
                raise ClaimError(f"{cid}: evidence kind does not match layer {layer}")
            if claim["authority"] == "historical" and layer != "H":
                raise ClaimError(f"{cid}: historical authority must cite only H sources")
            if layer == "H" and claim["authority"] != "historical":
                if evidence["role"] != "context":
                    raise ClaimError(f"{cid}: historical source may only supply context")
            sha = evidence.get("snapshot_sha256")
            if sha:
                if layer not in ("L0", "L1", "L2"):
                    raise ClaimError(f"{cid}: only captured official docs have HTTP SHA pins")
                if observations is None:
                    observations = _known_observations(snapshot_root)
                captured = observations.get(source_id)
                if not captured or sha not in captured.get("revisions", {}):
                    raise ClaimError(f"{cid}: evidence SHA is not an observed source revision")
        if claim["lifecycle"] == "reviewed":
            if verification["source"] != "reviewed":
                raise ClaimError(f"{cid}: cannot review a claim before source review")
            if any(e["role"] == "contradicts" for e in claim["evidence"]):
                raise ClaimError(f"{cid}: contradictory evidence cannot enter review")
            reviewable = False
            if claim["authority"] == "historical":
                reviewable = bool(
                    claim["evidence"]
                    and all(
                        source_registry[e["source_id"]]["trust_layer"] == "H"
                        for e in claim["evidence"]
                    )
                )
            else:
                for e in claim["evidence"]:
                    if e["role"] != "supports" or "to pin" in e["locator"].lower():
                        continue
                    src = source_registry[e["source_id"]]
                    if src["trust_layer"] in ("L0", "L1", "L2"):
                        if observations is None:
                            observations = _known_observations(snapshot_root)
                        reviewable |= _is_pinned_official_support(
                            e,
                            src,
                            snapshot_root,
                            observations,
                            required_version=claim["applies_to"]["claude_code"]["min_inclusive"],
                        )
                    elif src["trust_layer"] == "R":
                        reviewable |= _is_pinned_official_example(e, src)
            if not reviewable:
                raise ClaimError(
                    f"{cid}: reviewed claim requires pinned official supporting evidence"
                )
        if claim["lifecycle"] in ("reviewed", "approved", "deprecated", "rejected"):
            path = claim.get("decision_record")
            if path != f"decisions/{cid}.json":
                raise ClaimError(f"{cid}: missing or unsafe decision record path")
            # Delayed import avoids circular dependencies with transition helper.
            from .decisions import validate_ledger

            ledger_file = decision_dir / f"{cid}.json"
            if _decision_overrides and cid in _decision_overrides:
                ledger = _decision_overrides[cid]
            else:
                if not ledger_file.is_file() or ledger_file.is_symlink():
                    raise ClaimError(f"{cid}: missing decision ledger")
                try:
                    ledger = json.loads(ledger_file.read_text(encoding="utf-8"))
                except (OSError, ValueError) as exc:
                    raise ClaimError(f"{cid}: invalid decision ledger: {exc}") from exc
            validate_ledger(claim, ledger)
        elif claim.get("decision_record"):
            raise ClaimError(f"{cid}: candidate must not declare decision record")
        if claim["lifecycle"] != "approved":
            continue

        if claim["authority"] == "normative":
            if lo is None or hi is None or not claim["applies_to"]["surfaces"]:
                raise ClaimError(
                    f"{cid}: approved normative API needs bounded target versions and surfaces"
                )
            if verification["source"] != "reviewed":
                raise ClaimError(f"{cid}: official evidence must be reviewed")
            if verification["runtime"] not in ("smoke-pass", "integration-pass"):
                raise ClaimError(
                    f"{cid}: normative publication requires successful runtime evidence"
                )
            from .runtime_evidence import validate_runtime_reports

            validate_runtime_reports(claim, snapshot_root)
            supports = []
            for evidence in claim["evidence"]:
                if evidence["role"] == "contradicts":
                    raise ClaimError(f"{cid}: unresolved contradicting evidence blocks approval")
                source = source_registry[evidence["source_id"]]
                if evidence["role"] == "supports" and source["trust_layer"] in AUTHORITATIVE:
                    if observations is None:
                        observations = _known_observations(snapshot_root)
                    if not _is_pinned_official_support(
                        evidence,
                        source,
                        snapshot_root,
                        observations,
                        required_version=claim["applies_to"]["claude_code"]["min_inclusive"],
                    ):
                        raise ClaimError(
                            f"{cid}: official source is not pinned to reviewed metadata/locator"
                        )
                    supports.append(evidence)
            if not supports:
                raise ClaimError(
                    f"{cid}: normative approval requires pinned L0/L1 supporting evidence"
                )
        elif claim["authority"] == "guidance":
            if verification["source"] != "reviewed":
                raise ClaimError(f"{cid}: approved guidance requires reviewed sources")
            valid = False
            for evidence in claim["evidence"]:
                if evidence["role"] == "contradicts":
                    raise ClaimError(f"{cid}: contradicting evidence blocks guidance approval")
                source = source_registry[evidence["source_id"]]
                if evidence["role"] != "supports":
                    continue
                if source["trust_layer"] in ("L0", "L1", "L2"):
                    if observations is None:
                        observations = _known_observations(snapshot_root)
                    valid |= _is_pinned_official_support(
                        evidence,
                        source,
                        snapshot_root,
                        observations,
                        required_version=claim["applies_to"]["claude_code"]["min_inclusive"],
                    )
                elif source["trust_layer"] == "R":
                    valid |= _is_pinned_official_example(evidence, source)
            if not valid:
                raise ClaimError(
                    f"{cid}: approved guidance needs pinned official documentation/example"
                )
        elif claim["authority"] == "historical":
            # Historical knowledge is never returned by the current API query.
            if not claim["evidence"] or verification["source"] != "reviewed":
                raise ClaimError(f"{cid}: approved history needs reviewed historical source")
    _check_refs(claims)
    approved_normative = sorted(
        (
            claim
            for claim in claims.values()
            if claim["lifecycle"] == "approved" and claim["authority"] == "normative"
        ),
        key=lambda item: item["claim_id"],
    )
    for i, claim in enumerate(approved_normative):
        for other in approved_normative[i + 1 :]:
            if claim["subject"] == other["subject"] and _overlap(claim, other):
                raise ClaimError(
                    f"{claim['claim_id']} conflicts with {other['claim_id']}: "
                    "overlapping normative claims for the same subject/target"
                )


def load_claims(
    claim_dir: Path,
    source_registry: Mapping[str, dict],
    snapshot_root: Path,
    decision_dir: Path,
    schema_path: Path = SCHEMA_PATH,
) -> dict[str, dict]:
    """Load stable-ID JSON claim records, reject symlinks/invalid names, then validate."""
    claims: dict[str, dict] = {}
    if claim_dir.exists():
        if not claim_dir.is_dir() or claim_dir.is_symlink():
            raise ClaimError("Claims root must be a directory")
        for path in sorted(claim_dir.iterdir()):
            if path.name.startswith("."):
                continue
            if path.suffix != ".json" or not CLAIM_ID.fullmatch(path.stem):
                raise ClaimError(f"Unexpected entry in claims directory: {path.name}")
            if path.is_symlink() or not path.is_file():
                raise ClaimError(f"Unsafe claim path: {path.name}")
            try:
                claim = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                raise ClaimError(f"Cannot read claim {path.name}: {exc}") from exc
            if path.stem in claims:
                raise ClaimError(f"Duplicate claim ID: {path.stem}")
            if not isinstance(claim, dict) or claim.get("claim_id") != path.stem:
                raise ClaimError(f"Claim ID/path mismatch: {path.name}")
            claims[path.stem] = claim
    validate_claims(claims, source_registry, snapshot_root, decision_dir, schema_path)
    return claims


def approved_claims(claims: Mapping[str, dict], version: str, surface: str) -> list[dict]:
    """Filter previously validated claims; never return H/history or unapproved entries."""
    version_tuple = parse_version(version)
    if surface not in ("cli", "desktop", "vscode", "headless"):
        raise ClaimError(f"Unsupported target surface: {surface}")
    selected = []
    for _cid, claim in sorted(claims.items()):
        if claim["lifecycle"] != "approved" or claim["authority"] == "historical":
            continue
        if surface not in claim["applies_to"]["surfaces"]:
            continue
        lo, hi = _interval(claim)
        if lo is None or hi is None:
            continue
        if lo <= version_tuple < hi:
            selected.append(claim)
    return selected
