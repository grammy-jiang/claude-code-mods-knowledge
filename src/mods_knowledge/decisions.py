"""Explicit Claim review decisions with a SHA-linked on-disk audit trail."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path

from .errors import ClaimError
from .registry import load_registry
from .storage import _atomic_replace, _locked

STATES = {
    "candidate": frozenset(("reviewed", "rejected")),
    "reviewed": frozenset(("approved", "rejected")),
    "approved": frozenset(("deprecated",)),
}
_HASH = re.compile(r"[a-f0-9]{64}\Z")
_ID = re.compile(r"K-[0-9]{4,}\Z")
_EVENT_KEYS = frozenset(
    (
        "from_state",
        "to_state",
        "actor",
        "rationale",
        "at",
        "claim_before_sha256",
        "claim_after_sha256",
        "previous_event_sha256",
        "event_sha256",
    )
)


def _canonical(value: dict) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


def _hash(value: dict) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _file_bytes(value: dict) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def _parse_time(value: str) -> datetime:
    if not isinstance(value, str):
        raise ClaimError("Audit timestamp must be a timestamp string")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ClaimError("Invalid audit timestamp") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ClaimError("Audit timestamp must have UTC offset")
    return dt


def validate_ledger(claim: dict, ledger: dict) -> None:
    """Verify immutable event hashes, chain continuity, claim binding, and legal state changes."""
    cid = claim["claim_id"]
    if not isinstance(ledger, dict) or set(ledger) != {"schema_version", "claim_id", "events"}:
        raise ClaimError(f"{cid}: malformed decision ledger")
    if ledger["schema_version"] != 1 or ledger["claim_id"] != cid:
        raise ClaimError(f"{cid}: decision ledger identity mismatch")
    events = ledger["events"]
    if not isinstance(events, list) or not events:
        raise ClaimError(f"{cid}: decision ledger must have at least one event")
    expected_from = "candidate"
    last_hash = None
    last_claim_hash = None
    last_timestamp = None
    for i, event in enumerate(events):
        if not isinstance(event, dict) or set(event) != _EVENT_KEYS:
            raise ClaimError(f"{cid}: malformed event #{i + 1}")
        if event["from_state"] != expected_from or event["to_state"] not in STATES.get(
            expected_from, frozenset()
        ):
            raise ClaimError(f"{cid}: illegal state transition in decision ledger")
        if (
            not isinstance(event["actor"], str)
            or not event["actor"].strip()
            or not isinstance(event["rationale"], str)
            or not event["rationale"].strip()
        ):
            raise ClaimError(f"{cid}: event requires a reviewer attribution and rationale")
        timestamp = _parse_time(event["at"])
        if last_timestamp is not None and timestamp < last_timestamp:
            raise ClaimError(f"{cid}: non-monotonic review timestamp")
        last_timestamp = timestamp
        if event["previous_event_sha256"] != last_hash:
            raise ClaimError(f"{cid}: previous event hash mismatch")
        if last_claim_hash is not None and event["claim_before_sha256"] != last_claim_hash:
            raise ClaimError(f"{cid}: prior Claim hash chain mismatch")
        if not all(
            isinstance(event[key], str) and _HASH.fullmatch(event[key])
            for key in ("claim_before_sha256", "claim_after_sha256", "event_sha256")
        ):
            raise ClaimError(f"{cid}: missing or invalid Claim/event SHA")
        calculated = _hash({key: value for key, value in event.items() if key != "event_sha256"})
        if calculated != event["event_sha256"]:
            raise ClaimError(f"{cid}: event hash mismatch")
        last_hash = event["event_sha256"]
        last_claim_hash = event["claim_after_sha256"]
        expected_from = event["to_state"]
    if expected_from != claim["lifecycle"] or last_claim_hash != _hash(claim):
        raise ClaimError(f"{cid}: current Claim content hash does not match its decision ledger")


def _event(
    old: dict, new: dict, actor: str, rationale: str, at: datetime, prev_sha: str | None
) -> dict:
    event = {
        "from_state": old["lifecycle"],
        "to_state": new["lifecycle"],
        "actor": actor.strip(),
        "rationale": rationale.strip(),
        "at": at.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "claim_before_sha256": _hash(old),
        "claim_after_sha256": _hash(new),
        "previous_event_sha256": prev_sha,
    }
    event["event_sha256"] = _hash(event)
    return event


def transition_claim(
    root: Path,
    claim_id: str,
    action: str,
    actor: str,
    rationale: str,
    at: datetime,
) -> dict:
    """Audit a deliberate lifecycle transition after enforcing all policy gates.

    Reviewer attribution is a declared label, NOT verified user authentication.
    One-file writes are atomic; a power loss between the two writes is detected
    by the ledger/Claim hash validation and must be recovered from Git.
    """
    if not _ID.fullmatch(claim_id):
        raise ClaimError("Invalid Claim ID")
    if not isinstance(actor, str) or not actor.strip() or len(actor) > 128:
        raise ClaimError("A nonempty reviewer/agent attribution is required")
    if not isinstance(rationale, str) or len(rationale.strip()) < 12:
        raise ClaimError("Provide an explicit review rationale of at least 12 characters")
    if not isinstance(at, datetime) or at.tzinfo is None or at.utcoffset() is None:
        raise ClaimError("Transition time must be timezone-aware")
    if at > datetime.now(UTC):
        raise ClaimError("Cannot record future review decisions")
    claim_path = root / "claims" / f"{claim_id}.json"
    ledger_path = root / "decisions" / f"{claim_id}.json"
    with _locked(root / "decisions"):
        from .claims import load_claims, validate_claims

        registry = load_registry(root / "sources/registry.json")
        claims = load_claims(
            root / "claims", registry, root / "sources/snapshots", root / "decisions"
        )
        old = claims.get(claim_id)
        if old is None:
            raise ClaimError(f"Unknown Claim {claim_id}")
        if action not in STATES.get(old["lifecycle"], frozenset()):
            raise ClaimError(f"{claim_id}: transition {old['lifecycle']} -> {action} not permitted")
        if ledger_path.is_symlink():
            raise ClaimError("Unsafe decision ledger path")
        existing = {"schema_version": 1, "claim_id": claim_id, "events": []}
        if ledger_path.exists():
            try:
                existing = json.loads(ledger_path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                raise ClaimError(f"Cannot read decision history: {exc}") from exc
        new_claim = copy.deepcopy(old)
        new_claim["lifecycle"] = action
        new_claim["decision_record"] = f"decisions/{claim_id}.json"
        prev_event = existing["events"][-1]["event_sha256"] if existing["events"] else None
        event = _event(old, new_claim, actor, rationale, at, prev_event)
        updated_ledger = copy.deepcopy(existing)
        updated_ledger["events"].append(event)
        updated_claims = dict(claims)
        updated_claims[claim_id] = new_claim
        validate_claims(
            updated_claims,
            registry,
            root / "sources/snapshots",
            root / "decisions",
            _decision_overrides={claim_id: updated_ledger},
        )
        # Guard valid pre-state; rollback ordinary I/O failures without corrupting
        # the existing audit. Unexpected OS power-loss requires manual Git recovery.
        old_claim_bytes = claim_path.read_bytes()
        old_ledger_bytes = ledger_path.read_bytes() if ledger_path.exists() else None
        try:
            _atomic_replace(ledger_path, _file_bytes(updated_ledger))
            _atomic_replace(claim_path, _file_bytes(new_claim))
        except OSError:
            _atomic_replace(claim_path, old_claim_bytes)
            if old_ledger_bytes is None:
                ledger_path.unlink(missing_ok=True)
            else:
                _atomic_replace(ledger_path, old_ledger_bytes)
            raise
        return new_claim
