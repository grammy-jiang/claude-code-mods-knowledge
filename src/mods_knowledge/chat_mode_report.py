"""Aggregate sanitized, independently reviewed REAL Chat-mode QA evidence.

Structural checks do not prove semantic correctness. The report distinguishes
not_run, platform_blocked, semantic_review_pending, failures, and real passes.
No model sends, account API, raw chat IDs, prompts, or replies are needed.
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from collections.abc import Mapping, Sequence

from .evaluator import validate_suite

_SHA = re.compile(r"[a-f0-9]{64}\Z")
_REV = re.compile(r"[a-f0-9]{40}\Z")
_SEMVER = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+(?:-[a-zA-Z0-9.-]+)?\Z")
_RESOURCE = "skills://plugins/claude-code-mods-knowledge/claude-code-mods-development"

_FIELDS = frozenset(
    {
        "case_id",
        "category",
        "plugin_version",
        "conversation_sha256",
        "response_sha256",
        "plugin_id_sha256",
        "skill_loaded",
        "resource_uris",
        "expected_activation",
        "observed_claim_ids",
        "official_source_cited",
        "code_callback_signature_correct",
        "answer_quality",
        "quality_flags",
        "notes",
        "invocation_mode",
        "test_instance",
    }
)
VERDICTS = frozenset(("pass", "fail", "inconclusive"))
_CATEGORIES = ("positive", "negative", "boundary")


class ChatReportError(ValueError):
    """Chat-mode QA report cannot safely be derived from the supplied records."""


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _check_record(record: dict, case: dict, version: str) -> None:
    cid = case["id"]
    if not isinstance(record, dict) or set(record) - _FIELDS:
        raise ChatReportError(f"{cid}: unsafe/unknown fields in Chat-mode record")
    if (
        record.get("case_id") != cid
        or record.get("category") != case["category"]
        or record.get("plugin_version") != version
        or record.get("expected_activation") != case["expected_activation"]
    ):
        raise ChatReportError(f"{cid}: Chat-mode evidence identity/version mismatch")
    for key in ("conversation_sha256", "response_sha256"):
        if not isinstance(record.get(key), str) or not _SHA.fullmatch(record[key]):
            raise ChatReportError(f"{cid}: missing content-addressed evidence digest")
    if type(record.get("skill_loaded")) is not bool:
        raise ChatReportError(f"{cid}: missing actual Skill load observation")
    resources = record.get("resource_uris")
    if not isinstance(resources, list) or len(resources) != len(set(resources)):
        raise ChatReportError(f"{cid}: duplicate or invalid skill resource references")
    if any(
        not isinstance(uri, str) or not (uri == _RESOURCE or uri.startswith(_RESOURCE + "/"))
        for uri in resources
    ):
        raise ChatReportError(f"{cid}: a resource does not belong to this plugin")
    pid = record.get("plugin_id_sha256")
    if record["skill_loaded"]:
        if not resources or not isinstance(pid, str) or not _SHA.fullmatch(pid):
            raise ChatReportError(f"{cid}: claimed Skill load is not substantiated")
    elif resources or pid is not None:
        raise ChatReportError(f"{cid}: claimed no-load conflicts with resource trace")
    ids = record.get("observed_claim_ids")
    if not isinstance(ids, list) or not all(
        isinstance(i, str) and re.fullmatch(r"K-[0-9]{4,}", i) for i in ids
    ):
        raise ChatReportError(f"{cid}: malformed observed Claim IDs")
    if record.get("answer_quality") not in ("pass", "fail", "inconclusive"):
        raise ChatReportError(f"{cid}: expected an explicit structural quality verdict")
    flags = record.get("quality_flags")
    if not isinstance(flags, list) or not all(isinstance(x, str) for x in flags):
        raise ChatReportError(f"{cid}: invalid structural flags")
    mode = record.get("invocation_mode", "automatic")
    if mode not in ("automatic", "explicit"):
        raise ChatReportError(f"{cid}: invalid activation mode")
    if record["category"] == "negative" and record["answer_quality"] == "pass":
        if record["skill_loaded"]:
            raise ChatReportError(f"{cid}: negative nonactivation cannot pass after Skill load")
    if record["category"] == "positive" and record["answer_quality"] == "pass":
        if not record["skill_loaded"]:
            raise ChatReportError(f"{cid}: positive passed without resource read")
    if not isinstance(record.get("notes"), str) or len(record["notes"]) > 1400:
        raise ChatReportError(f"{cid}: invalid sanitized observation note")


def _manual_verdicts(manual_reviews: Mapping[str, dict], recorded: set[str]) -> dict[str, dict]:
    result = {}
    for cid, review in manual_reviews.items():
        if cid not in recorded or not isinstance(review, dict):
            raise ChatReportError(f"Manual review cannot attach to an unobserved case: {cid}")
        if set(review) != {"verdict", "rationale"}:
            raise ChatReportError(f"Invalid review fields for {cid}")
        if review["verdict"] not in VERDICTS:
            raise ChatReportError(f"Invalid manual verdict for {cid}")
        rationale = review["rationale"]
        if (
            not isinstance(rationale, str)
            or not 12 <= len(rationale.strip()) <= 500
            or "\n" in rationale
            or "\r" in rationale
        ):
            raise ChatReportError(f"{cid}: manual review needs a bounded rationale")
        # Store a checksum rather than potentially sensitive raw conversation text.
        result[cid] = {
            "verdict": review["verdict"],
            "rationale_sha256": _sha(rationale.strip()),
        }
    return result


def aggregate_chat_mode_results(
    suite: dict,
    records: Sequence[dict],
    *,
    plugin_version: str,
    source_revision: str,
    manual_reviews: Mapping[str, dict] | None = None,
    blocked_case_ids: set[str] | None = None,
) -> dict:
    """Aggregate P4's exact 46 Chat-mode scenarios without inventing success."""
    try:
        validate_suite(suite)
    except Exception as exc:
        raise ChatReportError(f"Invalid original P4 suite: {exc}") from exc
    if not isinstance(plugin_version, str) or not _SEMVER.fullmatch(plugin_version):
        raise ChatReportError("Exact installed plugin version required")
    if not isinstance(source_revision, str) or not _REV.fullmatch(source_revision):
        raise ChatReportError("Exact full Git source revision required")
    if not isinstance(records, (list, tuple)):
        raise ChatReportError("Expected a list of content-addressed records")
    case_map = {c["id"]: c for c in suite["cases"]}
    observed = {}
    for record in records:
        if not isinstance(record, dict):
            raise ChatReportError("Malformed Chat-mode record")
        cid = record.get("case_id")
        if cid not in case_map or cid in observed:
            raise ChatReportError(f"Unknown or duplicate Chat-mode case: {cid}")
        _check_record(record, case_map[cid], plugin_version)
        observed[cid] = record
    blocked = set(blocked_case_ids or ())
    if blocked - set(case_map) or blocked & set(observed):
        raise ChatReportError("Invalid blocked case identities")
    reviewed = _manual_verdicts(manual_reviews or {}, set(observed))
    items = []
    per_category: dict[str, Counter] = {name: Counter() for name in _CATEGORIES}
    counts = Counter()
    for case in suite["cases"]:
        cid, category = case["id"], case["category"]
        item = {
            "id": cid,
            "category": category,
            "expected_activation": case["expected_activation"],
        }
        if cid in observed:
            rec = observed[cid]
            flags = list(rec["quality_flags"])
            semantic = reviewed.get(cid)
            item.update(
                {
                    "received": True,
                    "skill_loaded": rec["skill_loaded"],
                    "invocation_mode": rec.get("invocation_mode", "automatic"),
                    "structural_verdict": rec["answer_quality"],
                    "observed_claim_ids": rec["observed_claim_ids"],
                    "conversation_sha256": rec["conversation_sha256"],
                    "response_sha256": rec["response_sha256"],
                    "plugin_id_sha256": rec["plugin_id_sha256"],
                    "resource_uris": rec["resource_uris"],
                }
            )
            if semantic is not None:
                item["semantic_review"] = semantic
            quality = rec["answer_quality"]
            if quality == "fail":
                verdict = "failed"
            elif category == "negative":
                verdict = "passed" if quality == "pass" else "inconclusive"
            elif quality == "pass" and semantic and semantic["verdict"] == "pass":
                verdict = "passed"
            elif (
                category == "boundary"
                and quality == "inconclusive"
                and rec["skill_loaded"]
                and semantic is not None
                and semantic["verdict"] == "pass"
                and set(flags) <= {"manual-semantic-review-required"}
            ):
                verdict = "passed"
            elif semantic and semantic["verdict"] == "fail":
                verdict = "failed"
            else:
                verdict = "inconclusive"
                if not semantic:
                    flags.append("manual_review_required")
            item["quality_flags"] = sorted(set(flags))
        elif cid in blocked:
            verdict = "blocked"
            item.update({"received": False, "block_reason": "platform_read_rate_limited"})
        else:
            verdict = "not_run"
            item["received"] = False
        item["final_verdict"] = verdict
        counts[verdict] += 1
        if cid in observed:
            counts["observed"] += 1
        per_category[category][verdict] += 1
        items.append(item)
    summary = {
        "total": len(items),
        "observed": counts["observed"],
        "passed": counts["passed"],
        "failed": counts["failed"],
        "inconclusive": counts["inconclusive"],
        "blocked": counts["blocked"],
        "not_run": counts["not_run"],
        "by_category": {
            name: {
                "total": sum(1 for c in suite["cases"] if c["category"] == name),
                **{
                    key: per_category[name][key]
                    for key in ("passed", "failed", "inconclusive", "blocked", "not_run")
                },
            }
            for name in _CATEGORIES
        },
    }
    summary["full_qa_pass"] = summary["passed"] == summary["total"]
    return {
        "schema_version": 1,
        "suite_id": suite["suite_id"],
        "mode": "chat",
        "target": suite["target"],
        "plugin_version": plugin_version,
        "source_revision": source_revision,
        "status": (
            "FULL_SUITE_LIVE_CHAT_MODE_PASS"
            if summary["full_qa_pass"]
            else "PARTIAL_LIVE_CHAT_MODE_EVALUATION"
        ),
        "summary": summary,
        "items": items,
        "scope_limit": (
            "Each pass requires actual Chat resource reads and independent "
            "semantic review except a negative nonactivation check. "
            "No Work mode or other AI Agent model call is inferred."
        ),
    }
