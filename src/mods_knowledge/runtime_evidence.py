"""Version-bound and content-addressed runtime evidence for normative knowledge claims.

This validates a recorded run artifact, not the truthfulness of the actor who
produced it. Git code review remains required before shipping an approval.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

from .errors import ClaimError

_RECORD_REF = re.compile(r"^(evidence/runtime/[A-Za-z0-9._/-]+\.json)#sha256=([a-f0-9]{64})$")
_SHA = re.compile(r"^[a-f0-9]{64}$")
_REQUIRED = frozenset(
    (
        "schema_version",
        "claim_id",
        "profile_id",
        "claude_code_version",
        "surface",
        "command",
        "exit_code",
        "result",
        "log_path",
        "log_sha256",
        "observed_at",
    )
)


def _safe_relative_path(root: Path, text: str) -> Path:
    if not isinstance(text, str):
        raise ClaimError("Evidence path must be a string")
    path = Path(text)
    if (
        path.is_absolute()
        or ".." in path.parts
        or "." in path.parts
        or "\\" in text
        or not text.startswith("evidence/runtime/")
    ):
        raise ClaimError("Unsafe runtime evidence path")
    resolved = root / path
    if not resolved.resolve().is_relative_to((root / "evidence/runtime").resolve()):
        raise ClaimError("Runtime evidence path escapes the allowed directory")
    if resolved.is_symlink() or not resolved.is_file():
        raise ClaimError("Runtime evidence file is missing or unsafe")
    return resolved


def validate_runtime_reports(claim: dict, snapshot_root: Path) -> None:
    """Require source/version/surface-specific PASS reports pinned by SHA-256."""
    from .claims import parse_version

    cid = claim["claim_id"]
    root = snapshot_root.parents[1]
    versions = claim["applies_to"]["claude_code"]
    lo = parse_version(versions["min_inclusive"])
    hi = parse_version(versions["max_exclusive"])
    try:
        targets = json.loads((root / "targets/profiles.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ClaimError(f"{cid}: missing or invalid target profiles") from exc
    if not isinstance(targets, list):
        raise ClaimError(f"{cid}: target profiles must form an array")
    from jsonschema import Draft202012Validator, FormatChecker

    schema_file = (
        Path(__file__).resolve().parents[2]
        / "docs/design/mods_ssot_design_v0_1/schemas/target.schema.json"
    )
    try:
        schema = json.loads(schema_file.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
    except (OSError, ValueError) as exc:
        raise ClaimError(f"{cid}: unusable target profile schema") from exc
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    for profile in targets:
        if not isinstance(profile, dict):
            raise ClaimError(f"{cid}: malformed target profile")
        issues = list(validator.iter_errors(profile))
        if issues:
            raise ClaimError(f"{cid}: target profile validation failed: {issues[0].message}")
    profiles = {profile["profile_id"]: profile for profile in targets}
    if len(profiles) != len(targets):
        raise ClaimError(f"{cid}: duplicate target profile IDs")
    claimed_profiles = claim["verification"].get("runtime_profiles", [])
    report_refs = claim["verification"].get("test_evidence", [])
    if len(set(claimed_profiles)) != len(claimed_profiles):
        raise ClaimError(f"{cid}: duplicate runtime profiles")
    seen: set[str] = set()
    for record_ref in report_refs:
        match = _RECORD_REF.fullmatch(record_ref)
        if not match:
            raise ClaimError(f"{cid}: runtime report must have a hash-pinned relative JSON path")
        path = _safe_relative_path(root, match.group(1))
        if path.stat().st_size > 100_000:
            raise ClaimError(f"{cid}: oversized evidence report")
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != match.group(2):
            raise ClaimError(f"{cid}: runtime report SHA-256 mismatch")
        try:
            record = json.loads(raw)
        except ValueError as exc:
            raise ClaimError(f"{cid}: invalid runtime report JSON") from exc
        if not isinstance(record, dict) or not _REQUIRED.issubset(record):
            raise ClaimError(f"{cid}: malformed runtime report")
        pid = record["profile_id"]
        if record["claim_id"] != cid or pid not in claimed_profiles or pid in seen:
            raise ClaimError(f"{cid}: runtime record Claim/profile mismatch or duplicate")
        profile = profiles.get(pid)
        if not profile or record["claude_code_version"] != profile["claude_code_version"]:
            raise ClaimError(
                f"{cid}: runtime profile missing or has mismatched Claude Code version"
            )
        version = parse_version(record["claude_code_version"])
        if not lo <= version < hi:
            raise ClaimError(f"{cid}: runtime profile is outside the applicable version interval")
        if record["surface"] not in claim["applies_to"]["surfaces"]:
            raise ClaimError(f"{cid}: runtime report surface outside the approved scope")
        if (
            record["schema_version"] != 1
            or record["result"] != "pass"
            or type(record["exit_code"]) is not int
            or record["exit_code"] != 0
            or not isinstance(record["command"], str)
            or not record["command"].strip()
        ):
            raise ClaimError(f"{cid}: runtime report is not a successful, named command")
        try:
            dt = datetime.fromisoformat(record["observed_at"].replace("Z", "+00:00"))
        except (AttributeError, ValueError) as exc:
            raise ClaimError(f"{cid}: invalid runtime observation timestamp") from exc
        if dt.tzinfo is None or dt.utcoffset() is None:
            raise ClaimError(f"{cid}: runtime timestamp lacks a timezone")
        log_path = _safe_relative_path(root, record["log_path"])
        if log_path.suffix != ".log" or log_path.stat().st_size > 2_000_000:
            raise ClaimError(f"{cid}: runtime log is not a bounded .log file")
        log_sha = record["log_sha256"]
        if not isinstance(log_sha, str) or not _SHA.fullmatch(log_sha):
            raise ClaimError(f"{cid}: invalid runtime log checksum")
        if hashlib.sha256(log_path.read_bytes()).hexdigest() != log_sha:
            raise ClaimError(f"{cid}: runtime log SHA-256 mismatch")
        seen.add(pid)
    if seen != set(claimed_profiles):
        raise ClaimError(f"{cid}: runtime evidence does not cover all claimed profiles")
