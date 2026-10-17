#!/usr/bin/env python3
"""Produce a private-data-free report from already captured Chat Mode evidence.

Read-only and offline: does not connect to ChatGPT or execute model-origin code.
This verifier independently hashes original private receipts, prompts and
visible answers, but cannot independently re-observe tool-call provenance:
that metadata was captured by the original read-only collector. Never equate
a successful HTTP reply with Plugin activation or semantic correctness.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
from pathlib import Path


class ChatEvidenceBlocked(ValueError):
    """The original full Chat Mode evidence does not qualify for an audit."""


def sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _load(path: Path) -> dict | list:
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 250_000:
        raise ChatEvidenceBlocked("Missing, symlinked or oversized private source")
    return json.loads(path.read_text(encoding="utf-8"))


def audit(root: Path) -> dict:
    """Never mutate the original 46 case files or reconstruct deleted chats."""
    root = Path(root)
    suite = _load(root / "manifest.private.json")
    sender = _load(root / "progress.private.json")
    reader = _load(root / "read-progress.private.json")
    results = _load(root / "46-redacted.private.json")
    if any(not isinstance(item, dict) for item in (suite, sender, reader)):
        raise ChatEvidenceBlocked("Original QA ledgers are invalid")
    if not isinstance(results, list) or not all(isinstance(x, dict) for x in results):
        raise ChatEvidenceBlocked("Original QA results are not a bounded array")
    if (
        suite.get("target_cli") != "2.1.302"
        or suite.get("installed_version") != "0.4.8-beta.1"
        or suite.get("model") != "gpt-6-thinking"
        or suite.get("effort") != "standard"
        or suite.get("no_composer_plugin_hint") is not True
        or suite.get("web_search_requested") is not False
        or sender.get("phase") != "all_46_sent_confirmed"
        or reader.get("phase") != "all_46_original_answers_read"
        or reader.get("blocked") is not None
        or len(suite.get("cases", [])) != 46
        or len(sender.get("sent_confirmed", [])) != 46
        or len(reader.get("completed", [])) != 46
        or len(results) != 46
    ):
        raise ChatEvidenceBlocked("46 distinct fully read native Chat Mode cases are required")
    categories = collections.Counter()
    verdicts = collections.Counter()
    activation = collections.Counter()
    qualified = collections.Counter()
    seen_hashes: set[str] = set()
    per_case = []
    for n, (case, send, original, row) in enumerate(
        zip(
            suite["cases"],
            sender["sent_confirmed"],
            reader["completed"],
            results,
            strict=True,
        ),
        1,
    ):
        if not all(isinstance(item, dict) for item in (case, send, original, row)):
            raise ChatEvidenceBlocked("Malformed original case evidence")
        if not (
            case.get("n") == send.get("n") == original.get("n") == row.get("n") == n
            and case.get("id") == send.get("id") == original.get("case_id") == row.get("case_id")
            and case.get("category") == row.get("category")
            and original.get("result") == row.get("result")
            and case.get("category") in ("positive", "negative", "boundary")
        ):
            raise ChatEvidenceBlocked(f"Original case identity mismatch at position {n}")
        prompt = Path(case["prompt_file"])
        receipt = _load(root / "receipts" / f"{n:02d}.json")
        visible = root / "private_replies" / f"{n:02d}.txt"
        if (
            not prompt.is_file()
            or prompt.is_symlink()
            or not visible.is_file()
            or visible.is_symlink()
            or visible.stat().st_size > 500_000
            or not isinstance(receipt, dict)
        ):
            raise ChatEvidenceBlocked(f"Original bounded private files missing for case {n}")
        if sha(prompt.read_text()) != case.get("prompt_sha256") or (
            sha(prompt.read_text()) != send.get("prompt_sha256")
        ):
            raise ChatEvidenceBlocked(f"Original immutable prompt digest changed at case {n}")
        cid = receipt.get("conversation_id")
        if (
            not isinstance(cid, str)
            or not cid
            or receipt.get("resolved") is not True
            or receipt.get("model") != "gpt-6-thinking"
            or receipt.get("effort") != "standard"
            or bool(receipt.get("system_hints"))
            or receipt.get("search") is True
            or sha(cid) != original.get("conversation_sha256")
            or sha(cid) != row.get("conversation_sha256")
            or sha(cid) != send.get("conversation_id_sha256")
            or sha(visible.read_text()) != row.get("reply_sha256")
        ):
            raise ChatEvidenceBlocked(f"Original sent/final reply integrity mismatch at case {n}")
        if sha(cid) in seen_hashes:
            raise ChatEvidenceBlocked("Duplicate conversation in full Chat Mode suite")
        seen_hashes.add(sha(cid))
        if row.get("model_and_effort_verified") is not True:
            raise ChatEvidenceBlocked("Model and effort not verified by original reader")
        if row.get("manual_generated_code_semantics_pass") is not False:
            raise ChatEvidenceBlocked("Do not rewrite unreviewed code as semantically passed")
        expected = {
            "positive": ("structural_pass_semantic_pending", "structural_fail"),
            "negative": ("negative_nonactivation_pass", "negative_activation_fail"),
            "boundary": ("boundary_manual_semantic_review", "boundary_activation_fail"),
        }[row["category"]]
        if row["result"] not in expected:
            raise ChatEvidenceBlocked("Unknown case verdict in private original")
        cats = row["category"]
        categories[cats] += 1
        verdicts[row["result"]] += 1
        if row.get("activated_right_plugin") is True:
            activation[cats] += 1
        if row["result"] == expected[0]:
            qualified[cats] += 1
        per_case.append(
            {
                "case_id": row["case_id"],
                "category": cats,
                "original_visible_reply_sha256": row["reply_sha256"],
                "original_evidence_integrity_verified": True,
                "read_resource_count_from_original_collector": row.get(
                    "actual_matching_plugin_reads"
                ),
                "plugin_activated_in_original_collector": row.get("activated_right_plugin"),
                "required_approved_claim_ids": row.get("required_claim_ids"),
                "missing_required_claim_ids": row.get("missing_required_claims"),
                "missing_exact_official_source_ids": row.get("missing_exact_source_claims"),
                "unsupported_claim_ids": row.get("cited_wrong_scope_claims"),
                "source_structure": row.get("source_structural_verdict"),
                "result": row["result"],
                "generated_code_semantics_verified": False,
            }
        )
    if categories != collections.Counter({"positive": 30, "negative": 8, "boundary": 8}):
        raise ChatEvidenceBlocked("The original 46-case cohort distribution changed")
    return {
        "schema_version": 1,
        "date": "2026-10-18",
        "target_cli": "2.1.302",
        "plugin_version": "0.4.8-beta.1",
        "source_revision": suite["source_revision"],
        "scope": "Real ChatGPT ordinary Chat Mode; not Work Mode",
        "model": "gpt-6-thinking",
        "effort": "standard",
        "original_unique_sends_with_receipts": 46,
        "original_completed_final_replies_sha256_verified": 46,
        "categories": dict(categories),
        "structural_verdicts": dict(verdicts),
        "actual_plugin_activation_counts_from_original_collector": dict(activation),
        "per_category_structural_success_counts": dict(qualified),
        "all_original_responses_semantically_approved": False,
        "stable_release_authorized": False,
        "original_private_model_answers_or_conversation_ids_exported": False,
        "tool_metadata_independently_refetched": False,
        "full_report_verified_without_new_http_requests": True,
        "per_case_redacted_metadata": per_case,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-root", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    if args.out.exists() or args.out.is_symlink():
        raise SystemExit("REFUSED: report file already exists; no overwrite")
    try:
        result = audit(args.private_root)
    except (ChatEvidenceBlocked, OSError, KeyError, TypeError, ValueError):
        raise SystemExit("BLOCKED: original 46-case evidence incomplete or inconsistent") from None
    args.out.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    print({k: v for k, v in result.items() if not isinstance(v, list)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
