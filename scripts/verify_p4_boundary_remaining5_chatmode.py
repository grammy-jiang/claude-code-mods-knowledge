#!/usr/bin/env python3
"""Offline original-trace evidence audit for five remaining beta010 boundaries.

Never makes network calls, replays prompts, or emits private conversation IDs
or raw model text. Original actual Plugin metadata came from the authenticated
reader; SHA checks here are independent integrity checks, not a tool refetch.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
from pathlib import Path

VERSION = "0.4.10-beta.1"
SOURCE = "b9ea3063393e33259298ddcac02104b16c42b208"
CASES = (
    "BOUND-UNKNOWN-VERSION",
    "BOUND-HISTORY",
    "BOUND-SURFACE",
    "BOUND-INJECTION",
    "BOUND-SKILL-ROLE",
)


class OriginalEvidenceIncomplete(ValueError):
    """Fail closed on any incomplete, altered, or ambiguous original receipt."""


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def load(path: Path) -> dict:
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 300_000:
        raise OriginalEvidenceIncomplete("Missing or unsafe original evidence")
    result = json.loads(path.read_text())
    if not isinstance(result, dict):
        raise OriginalEvidenceIncomplete("Original evidence must be a JSON object")
    return result


def audit(root: Path) -> dict:
    root = Path(root)
    manifest = load(root / "manifest.private.json")
    sender = load(root / "sender-progress.private.json")
    reader = load(root / "reader-progress.private.json")
    observed = load(root / "scored.private.json")
    if (
        manifest.get("plugin_version") != VERSION
        or manifest.get("source_revision") != SOURCE
        or manifest.get("target_cli") != "2.1.302"
        or manifest.get("model") != "gpt-6-thinking"
        or manifest.get("effort") != "standard"
        or manifest.get("composer_plugin_selected") is not False
        or manifest.get("search_requested") is not False
        or manifest.get("no_blind_resends") is not True
        or sender.get("phase") != "all_five_sends_confirmed"
        or reader.get("phase") != "all_five_original_replies_read"
        or reader.get("blocked") is not None
        or observed.get("phase") != "complete"
        or any(
            not isinstance(x, list) or len(x) != 5
            for x in (
                manifest.get("cases"),
                sender.get("completed"),
                reader.get("completed"),
                observed.get("records"),
            )
        )
    ):
        raise OriginalEvidenceIncomplete("Five original completed receipts are required")
    if tuple(item["case_id"] for item in manifest["cases"]) != CASES:
        raise OriginalEvidenceIncomplete("Bounded original P4 cases changed")
    matched: set[str] = set()
    counters: collections.Counter[str] = collections.Counter()
    redacted = []
    for n, (case, sent, read, record) in enumerate(
        zip(
            manifest["cases"],
            sender["completed"],
            reader["completed"],
            observed["records"],
            strict=True,
        ),
        1,
    ):
        if any(not isinstance(x, dict) for x in (case, sent, read, record)):
            raise OriginalEvidenceIncomplete("Invalid original record object")
        if not (
            n == case.get("n") == sent.get("n") == read.get("n") == record.get("n")
            and case.get("case_id")
            == sent.get("case_id")
            == read.get("case_id")
            == record.get("case_id")
            and read.get("activated") is record.get("skill_entrypoint_and_reference_read")
        ):
            raise OriginalEvidenceIncomplete("Case, reply, or tool evidence identity mismatch")
        prompt = Path(case["prompt_file"])
        answer = root / "private_replies" / f"{n:02d}.txt"
        receipt = load(root / "receipts" / f"{n:02d}.json")
        if any(
            not p.is_file() or p.is_symlink() or p.stat().st_size > 500_000
            for p in (prompt, answer)
        ):
            raise OriginalEvidenceIncomplete("Missing private original prompt or final reply")
        conversation = receipt.get("conversation_id")
        if (
            not isinstance(conversation, str)
            or not re.fullmatch(r"[A-Za-z0-9-]{20,100}", conversation)
            or sha(conversation) in matched
            or receipt.get("resolved") is not True
            or receipt.get("model") != "gpt-6-thinking"
            or receipt.get("effort") != "standard"
            or bool(receipt.get("search"))
            or bool(receipt.get("system_hints"))
            or bool(receipt.get("project"))
            or sha(conversation) != sent.get("original_conversation_sha256")
            or sha(conversation) != record.get("original_conversation_sha256")
            or sha(prompt.read_text()) != sent.get("prompt_sha256")
            or sha(prompt.read_text()) != case.get("prompt_sha256")
            or sha(prompt.read_text()) != record.get("original_prompt_sha256")
            or sha(answer.read_text()) != record.get("original_visible_reply_sha256")
            or record.get("model_and_effort_verified") is not True
            or record.get("semantic_rubric_manual_approval") is not False
            or record.get("all_raw_content_private") is not True
        ):
            raise OriginalEvidenceIncomplete("Original Chat Mode evidence SHA/model mismatch")
        matched.add(sha(conversation))
        count = record.get("actual_matching_plugin_reads")
        if (
            type(count) is not int
            or count < 0
            or type(record.get("skill_entrypoint_and_reference_read")) is not bool
            or (record["skill_entrypoint_and_reference_read"] and count == 0)
            or record.get("other_plugin_instance_read_detected") is not False
        ):
            raise OriginalEvidenceIncomplete("Model Plugin read claim mismatches original count")
        counters["total"] += 1
        counters["actual_skill_loads"] += int(record["skill_entrypoint_and_reference_read"])
        counters["no_skill_loads"] += int(count == 0)
        counters["partial_skill_reads"] += int(
            count > 0 and not record["skill_entrypoint_and_reference_read"]
        )
        redacted.append(
            {
                "case_id": case["case_id"],
                "original_answer_sha256": record["original_visible_reply_sha256"],
                "original_sha_integrity_verified": True,
                "canonical_plugin_resource_reads": count,
                "automatic_skill_entrypoint_and_reference_read": record[
                    "skill_entrypoint_and_reference_read"
                ],
                "original_tool_type_counts": record["tool_type_counts"],
                "manual_semantics_certified": False,
            }
        )
    return {
        "schema_version": 1,
        "date": "2026-10-18",
        "source_revision": SOURCE,
        "installed_plugin": VERSION,
        "target_cli": "2.1.302",
        "surface": "genuine ordinary ChatGPT Chat Mode, not Work",
        "model": "gpt-6-thinking",
        "effort": "standard",
        "counters": dict(counters),
        "separate_historical_boundary_cohort": True,
        "full_model_answer_semantics_approved": False,
        "stable_release_authorized": False,
        "original_tool_events_independently_refetched": False,
        "private_raw_content_exported": False,
        "extra_http_requests_performed_by_verifier": False,
        "cases": redacted,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists() or args.out.is_symlink():
        raise SystemExit("REFUSED: original report already exists")
    try:
        outcome = audit(args.private_root)
    except (OriginalEvidenceIncomplete, OSError, ValueError, KeyError, TypeError):
        raise SystemExit("BLOCKED: original five-case evidence incomplete") from None
    args.out.write_text(json.dumps(outcome, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    print({k: v for k, v in outcome.items() if not isinstance(v, list)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
