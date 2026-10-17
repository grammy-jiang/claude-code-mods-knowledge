#!/usr/bin/env python3
"""Verify twelve already completed CLI302 beta049 Chat Mode follow-up turns.

No authenticated account access, network request, send, retry, or model code
execution occurs here. This is a limited 12-case discovery metadata A/B
check, not a complete 46-case release acceptance or semantic certification.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
from pathlib import Path

SOURCE_SHA = "e00f395509030382398df41ae14ef389490bea51"
CASE_INDICES = (1, 4, 31, 32, 39, 40, 41, 42, 43, 44, 45, 46)


class TargetedEvidenceBlocked(ValueError):
    """The original twelve targeted sends/replies are not fully verifiable."""


def hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def load(path: Path) -> dict | list:
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 260_000:
        raise TargetedEvidenceBlocked("Missing or untrusted evidence file")
    return json.loads(path.read_text(encoding="utf-8"))


def audit(root: Path) -> dict:
    root = Path(root)
    manifest = load(root / "manifest.private.json")
    send = load(root / "progress.private.json")
    read = load(root / "read-progress.private.json")
    rows = load(root / "46-redacted.private.json")
    if any(not isinstance(item, dict) for item in (manifest, send, read)):
        raise TargetedEvidenceBlocked("Missing valid source or progress ledger")
    if (
        manifest.get("target_cli") != "2.1.302"
        or manifest.get("source_revision") != SOURCE_SHA
        or manifest.get("installed_version") != "0.4.9-beta.1"
        or manifest.get("model") != "gpt-6-thinking"
        or manifest.get("effort") != "standard"
        or manifest.get("no_composer_plugin_hint") is not True
        or manifest.get("web_search_requested") is not False
        or send.get("phase") != "all_12_sent_confirmed"
        or read.get("phase") != "all_12_original_answers_read"
        or read.get("blocked") is not None
        or not isinstance(rows, list)
        or len(manifest.get("cases", [])) != 12
        or len(send.get("sent_confirmed", [])) != 12
        or len(read.get("completed", [])) != 12
        or len(rows) != 12
    ):
        raise TargetedEvidenceBlocked("Twelve original finished targeted cases required")
    if tuple(x.get("n") for x in manifest["cases"]) != CASE_INDICES:
        raise TargetedEvidenceBlocked("Original targeted case identity/order changed")
    cats = collections.Counter()
    verdicts = collections.Counter()
    activated = collections.Counter()
    qualified = collections.Counter()
    fingerprints: set[str] = set()
    output: list[dict] = []
    for entry, sender, reader, row in zip(
        manifest["cases"], send["sent_confirmed"], read["completed"], rows, strict=True
    ):
        if not all(isinstance(v, dict) for v in (entry, sender, reader, row)):
            raise TargetedEvidenceBlocked("Invalid targeted case ledger")
        n = entry["n"]
        if not (
            sender.get("n") == reader.get("n") == row.get("n") == n
            and entry.get("id") == sender.get("id") == reader.get("case_id") == row.get("case_id")
            and entry.get("category") == row.get("category")
            and reader.get("result") == row.get("result")
        ):
            raise TargetedEvidenceBlocked("Original targeted case identity mismatch")
        prompt = Path(entry["prompt_file"])
        response = root / "private_replies" / f"{n:02d}.txt"
        receipt = load(root / "receipts" / f"{n:02d}.json")
        if (
            not isinstance(receipt, dict)
            or not prompt.is_file()
            or prompt.is_symlink()
            or not response.is_file()
            or response.is_symlink()
            or response.stat().st_size > 500_000
        ):
            raise TargetedEvidenceBlocked("Original targeted receipts/replies absent")
        prompt_hash = hash_text(prompt.read_text())
        conversation = receipt.get("conversation_id")
        if (
            not isinstance(conversation, str)
            or not conversation
            or prompt_hash != entry.get("prompt_sha256")
            or prompt_hash != sender.get("prompt_sha256")
            or receipt.get("resolved") is not True
            or receipt.get("model") != "gpt-6-thinking"
            or receipt.get("effort") != "standard"
            or receipt.get("system_hints")
            or receipt.get("search") is True
            or hash_text(conversation) != sender.get("conversation_id_sha256")
            or hash_text(conversation) != reader.get("conversation_sha256")
            or hash_text(conversation) != row.get("conversation_sha256")
            or hash_text(response.read_text()) != row.get("reply_sha256")
            or row.get("model_and_effort_verified") is not True
            or row.get("manual_generated_code_semantics_pass") is not False
        ):
            raise TargetedEvidenceBlocked("Original targeted metadata or digest mismatch")
        finger = hash_text(conversation)
        if finger in fingerprints:
            raise TargetedEvidenceBlocked("Duplicate original target conversation")
        fingerprints.add(finger)
        category = entry["category"]
        if category not in ("positive", "negative", "boundary"):
            raise TargetedEvidenceBlocked("Unknown targeted category")
        valid_results = {
            "positive": ("structural_pass_semantic_pending", "structural_fail"),
            "negative": ("negative_nonactivation_pass", "negative_activation_fail"),
            "boundary": ("boundary_manual_semantic_review", "boundary_activation_fail"),
        }[category]
        if row.get("result") not in valid_results:
            raise TargetedEvidenceBlocked("Unexpected original targeted model outcome")
        cats[category] += 1
        verdicts[row["result"]] += 1
        activated[category] += int(row.get("activated_right_plugin") is True)
        qualified[category] += int(row["result"] == valid_results[0])
        output.append(
            {
                "case_id": row["case_id"],
                "category": category,
                "original_answer_sha256": row["reply_sha256"],
                "original_receipt_and_answer_sha256_verified": True,
                "actual_plugin_read_count_from_collector": row.get("actual_matching_plugin_reads"),
                "automatic_skill_activation_from_collector": row.get("activated_right_plugin"),
                "required_claim_ids": row.get("required_claim_ids"),
                "missing_claim_ids": row.get("missing_required_claims"),
                "missing_exact_official_sources": row.get("missing_exact_source_claims"),
                "unsupported_claim_ids": row.get("cited_wrong_scope_claims"),
                "structural_result": row["result"],
                "whole_answer_native_semantic_pass": False,
            }
        )
    if cats != collections.Counter({"positive": 2, "negative": 2, "boundary": 8}):
        raise TargetedEvidenceBlocked("Targeted category distribution changed")
    return {
        "schema_version": 1,
        "date": "2026-10-18",
        "target_cli": "2.1.302",
        "plugin_candidate": "0.4.9-beta.1",
        "source_revision": SOURCE_SHA,
        "surface": "genuine ChatGPT ordinary Chat Mode, not Work Mode",
        "model": "gpt-6-thinking",
        "effort": "standard",
        "purpose": "12 new targeted Plugin metadata discovery cases; not full 46 release suite",
        "new_distinct_sends_verified": 12,
        "canonical_final_replies_verified": 12,
        "family_counts": dict(cats),
        "structural_results": dict(verdicts),
        "actual_skill_activation_by_category": dict(activated),
        "structural_successes_by_category": dict(qualified),
        "full_46_case_plugin_qualification": False,
        "stable_release_approved": False,
        "model_generated_code_semantics_verified": False,
        "original_tool_calls_independently_refetched": False,
        "raw_private_prompts_answers_or_account_identifiers_exported": False,
        "new_account_requests_issued_by_this_verifier": False,
        "per_case_metadata": output,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-root", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    if args.out.exists() or args.out.is_symlink():
        raise SystemExit("REFUSED: original report file exists; no overwrite")
    try:
        report = audit(args.private_root)
    except (TargetedEvidenceBlocked, OSError, ValueError, KeyError, TypeError):
        raise SystemExit("BLOCKED: original targeted Chat Mode evidence is incomplete") from None
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    print({k: v for k, v in report.items() if not isinstance(v, list)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
