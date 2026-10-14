"""Compare two distinct, real Chat-mode test runs without claiming semantic QA pass.

Only structural evidence is compared. Original conversation IDs/prompts/replies
never enter the report. Full-suite acceptance is evaluated separately.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from .chat_mode_report import ChatReportError, _check_record


class ComparisonError(ValueError):
    """Mismatched or untrusted Chat-mode A/B records."""


def _case_identity(row: dict) -> dict:
    if not isinstance(row, dict):
        raise ComparisonError("Each Chat-mode observation must be a record")
    cid = row.get("case_id")
    cat = row.get("category")
    if not isinstance(cid, str) or not re.fullmatch(r"[A-Z][A-Z0-9_-]{3,60}", cid):
        raise ComparisonError(f"Unsafe/unknown Chat-mode case ID: {cid!r}")
    if cat not in ("positive", "negative", "boundary"):
        raise ComparisonError(f"{cid}: unsupported Chat-mode case category")
    expect = cat != "negative"
    if row.get("expected_activation") is not expect:
        raise ComparisonError(f"{cid}: mismatch in activation expectation")
    return {"id": cid, "category": cat, "expected_activation": expect}


def _load_records(rows: Sequence[dict], version: str) -> dict[str, dict]:
    if not isinstance(rows, (list, tuple)):
        raise ComparisonError("Expected a list of Chat-mode observations")
    out = {}
    seen_conversation_hashes: set[str] = set()
    plugin_instance_hashes: set[str] = set()
    for entry in rows:
        ident = _case_identity(entry)
        cid = ident["id"]
        if cid in out:
            raise ComparisonError(f"Duplicate Chat-mode case {cid}")
        try:
            _check_record(entry, ident, version)
        except ChatReportError as exc:
            raise ComparisonError(str(exc)) from exc
        digest = entry["conversation_sha256"]
        if digest in seen_conversation_hashes:
            raise ComparisonError(f"Duplicate Chat-mode conversation evidence for {cid}")
        seen_conversation_hashes.add(digest)
        if entry["skill_loaded"]:
            plugin_instance_hashes.add(entry["plugin_id_sha256"])
        out[cid] = entry
    if len(plugin_instance_hashes) > 1:
        raise ComparisonError("Run refers to multiple installed Plugin instances")
    return out


def compare_chat_versions(
    before: Sequence[dict],
    after: Sequence[dict],
    *,
    before_version: str,
    after_version: str,
) -> dict:
    """Describe changed structural/activation verdicts on *matched* cases only."""
    version = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.-]+)?\Z")
    if (
        not isinstance(before_version, str)
        or not version.fullmatch(before_version)
        or not isinstance(after_version, str)
        or not version.fullmatch(after_version)
        or before_version == after_version
    ):
        raise ComparisonError("A/B requires distinct explicit plugin versions")
    old = _load_records(before, before_version)
    new = _load_records(after, after_version)
    common = sorted(set(old) & set(new))
    if any(old[cid]["category"] != new[cid]["category"] for cid in common):
        raise ComparisonError("Case categories changed across version runs")
    if any(old[cid]["conversation_sha256"] == new[cid]["conversation_sha256"] for cid in common):
        raise ComparisonError("A/B reused one Chat conversation as two version tests")

    def select(predicate) -> list[str]:
        return [cid for cid in common if predicate(old[cid], new[cid])]

    result = {
        "schema_version": 1,
        "mode": "chat",
        "before_version": before_version,
        "after_version": after_version,
        "cases_both_observed": len(common),
        "cases_before_only": sorted(set(old) - set(new)),
        "cases_after_only": sorted(set(new) - set(old)),
        "before_structural_pass": sum(old[cid]["answer_quality"] == "pass" for cid in common),
        "after_structural_pass": sum(new[cid]["answer_quality"] == "pass" for cid in common),
        "structurally_recovered": select(
            lambda a, b: a["answer_quality"] == "fail" and b["answer_quality"] == "pass"
        ),
        "structurally_regressed": select(
            lambda a, b: a["answer_quality"] == "pass" and b["answer_quality"] == "fail"
        ),
        "persistently_failed": select(
            lambda a, b: a["answer_quality"] == "fail" and b["answer_quality"] == "fail"
        ),
        "both_passed": select(
            lambda a, b: a["answer_quality"] == "pass" and b["answer_quality"] == "pass"
        ),
        "gained_skill_activation": select(lambda a, b: not a["skill_loaded"] and b["skill_loaded"]),
        "lost_skill_activation": select(lambda a, b: a["skill_loaded"] and not b["skill_loaded"]),
        "answer_semantics_verified": False,
        "full_suite_qa_pass": False,
        "caveat": (
            "Only matching case IDs in actual Chat-mode records are compared. "
            "Static PASS and activation are not semantic correctness. "
            "Cases missing a retest must not be inferred to have improved."
        ),
    }
    return result
