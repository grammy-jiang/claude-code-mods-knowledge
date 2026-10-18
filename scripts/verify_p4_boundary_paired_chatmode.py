#!/usr/bin/env python3
"""Offline audit of six real natural-vs-explicit Chat Mode boundary prompts.

No account access, browser, model calls, prompt replay, or credential export.
Tool-use classifications come from original authenticated read traces and are
checked against the saved original answer/receipt SHA256 identity, not
independently re-observed. Model semantics require separate manual review.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
from pathlib import Path

SOURCE_REVISION = "b9ea3063393e33259298ddcac02104b16c42b208"
EXPECTED_PAIRS = (
    ("BOUND-VERSION-OLD", "natural"),
    ("BOUND-VERSION-OLD", "explicit"),
    ("BOUND-VERSION-NEW", "natural"),
    ("BOUND-VERSION-NEW", "explicit"),
    ("BOUND-PLUGIN-PRIV", "natural"),
    ("BOUND-PLUGIN-PRIV", "explicit"),
)


class PairedEvidenceBlocked(ValueError):
    """Original boundary test material is incomplete, invalid, or mismatched."""


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _load(path: Path) -> dict | list:
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 300_000:
        raise PairedEvidenceBlocked("Missing or untrusted original evidence file")
    return json.loads(path.read_text(encoding="utf-8"))


def audit(root: Path) -> dict:
    root = Path(root)
    matrix = _load(root / "manifest.private.json")
    sender = _load(root / "sender-progress.private.json")
    reader = _load(root / "reader-progress.private.json")
    results = _load(root / "scored.private.json")
    if any(not isinstance(v, dict) for v in (matrix, sender, reader, results)):
        raise PairedEvidenceBlocked("Original matrix/ledger must be objects")
    if (
        matrix.get("installed_plugin_version") != "0.4.10-beta.1"
        or matrix.get("source_revision") != SOURCE_REVISION
        or matrix.get("target_cli") != "2.1.302"
        or matrix.get("model") != "gpt-6-thinking"
        or matrix.get("effort") != "standard"
        or matrix.get("no_search_requested") is not True
        or matrix.get("no_system_hints") is not True
        or matrix.get("no_resends") is not True
        or sender.get("phase") != "all_six_original_sends_confirmed"
        or reader.get("phase") != "all_six_original_replies_read"
        or reader.get("blocked") is not None
        or results.get("phase") != "complete"
        or not isinstance(matrix.get("cases"), list)
        or not isinstance(sender.get("completed"), list)
        or not isinstance(reader.get("completed"), list)
        or not isinstance(results.get("records"), list)
        or any(
            len(x) != 6
            for x in (matrix["cases"], sender["completed"], reader["completed"], results["records"])
        )
    ):
        raise PairedEvidenceBlocked("Exactly six fully completed Chat Mode originals are required")
    if tuple((r.get("case_id"), r.get("condition")) for r in matrix["cases"]) != EXPECTED_PAIRS:
        raise PairedEvidenceBlocked("Paired case order/labels must match predeclared design")

    counters: collections.Counter[str] = collections.Counter()
    seen_ids: set[str] = set()
    rows = []
    for index, (case, sent, read, observed) in enumerate(
        zip(
            matrix["cases"],
            sender["completed"],
            reader["completed"],
            results["records"],
            strict=True,
        ),
        1,
    ):
        if any(not isinstance(x, dict) for x in (case, sent, read, observed)):
            raise PairedEvidenceBlocked("Malformed original paired case")
        if not (
            case.get("n") == sent.get("n") == read.get("n") == observed.get("n") == index
            and case.get("case_id")
            == sent.get("case_id")
            == read.get("case_id")
            == observed.get("case_id")
            and case.get("condition")
            == sent.get("condition")
            == read.get("condition")
            == observed.get("condition")
        ):
            raise PairedEvidenceBlocked("Original case and receipt identity mismatch")
        prompt = Path(case["prompt_file"])
        original = root / "private_replies" / f"{index:02d}.txt"
        receipt = _load(root / "receipts" / f"{index:02d}.json")
        if not isinstance(receipt, dict) or any(
            not p.is_file() or p.is_symlink() or p.stat().st_size > 500_000
            for p in (prompt, original)
        ):
            raise PairedEvidenceBlocked("Original prompt/answer or receipt absent")
        cid = receipt.get("conversation_id")
        if (
            not isinstance(cid, str)
            or not re.fullmatch(r"[A-Za-z0-9-]{20,100}", cid)
            or receipt.get("resolved") is not True
            or receipt.get("model") != "gpt-6-thinking"
            or receipt.get("effort") != "standard"
            or bool(receipt.get("project"))
            or bool(receipt.get("search"))
            or bool(receipt.get("system_hints"))
            or _sha(prompt.read_text()) != case.get("prompt_sha256")
            or _sha(prompt.read_text()) != sent.get("prompt_sha256")
            or _sha(original.read_text()) != observed.get("original_visible_reply_sha256")
            or _sha(cid) != observed.get("original_conversation_sha256")
            or _sha(cid) != sent.get("original_conversation_sha256")
            or observed.get("original_prompt_sha256") != case.get("prompt_sha256")
            or observed.get("model_and_effort_verified") is not True
        ):
            raise PairedEvidenceBlocked("Original send/read/hash/model provenance is inconsistent")
        if _sha(cid) in seen_ids:
            raise PairedEvidenceBlocked("Duplicate original conversation detected")
        seen_ids.add(_sha(cid))
        if (
            not isinstance(observed.get("canonical_plugin_resource_reads"), int)
            or observed["canonical_plugin_resource_reads"] < 0
            or (observed["canonical_plugin_resource_reads"] > 0)
            != (observed.get("real_plugin_read") is True)
            or read.get("plugin_read") is not observed.get("real_plugin_read")
            or observed.get("other_plugin_instance_read_detected") is True
            or observed.get("independent_generated_code_semantics_approved") is not False
            or observed.get("all_raw_account_material_private") is not True
        ):
            raise PairedEvidenceBlocked("Impossible Plugin activation or unreviewed semantic claim")
        condition = case["condition"]
        counters[f"{condition}_cases"] += 1
        counters[f"{condition}_actual_skill_reads"] += int(observed["real_plugin_read"])
        counters[f"{condition}_skill_and_reference_reads"] += int(
            bool(observed.get("skill_entrypoint_read") and observed.get("reference_read"))
        )
        rows.append(
            {
                "case_id": case["case_id"],
                "condition": condition,
                "original_visible_answer_sha256": observed["original_visible_reply_sha256"],
                "original_identity_verified": True,
                "actual_plugin_resource_reads_in_original_trace": observed[
                    "canonical_plugin_resource_reads"
                ],
                "actual_plugin_skill_read": observed["real_plugin_read"],
                "skill_entrypoint_read": observed["skill_entrypoint_read"],
                "reference_read": observed["reference_read"],
                "tool_type_counts": observed["tool_event_counts"],
                "generated_code_and_safety_semantics_pass": False,
            }
        )
    body_sha = matrix["cases"][0]["original_body_sha256"]
    if not all(
        pair[0]["original_body_sha256"] == pair[1]["original_body_sha256"]
        for pair in zip(matrix["cases"][::2], matrix["cases"][1::2], strict=True)
    ):
        raise PairedEvidenceBlocked("Original paired question bodies changed")
    if not re.fullmatch(r"[a-f0-9]{64}", body_sha):
        raise PairedEvidenceBlocked("Invalid canonical question fingerprint")
    return {
        "schema_version": 1,
        "target_cli": "2.1.302",
        "plugin_version": "0.4.10-beta.1",
        "source_revision": SOURCE_REVISION,
        "surface": "genuine ordinary ChatGPT Chat Mode, not Work",
        "model": "gpt-6-thinking",
        "effort": "standard",
        "total_distinct_sent_and_read_originals": 6,
        "observed_counts": dict(counters),
        "has_full_boundary_qualification": False,
        "genuine_model_code_semantics_certified": False,
        "stable_release_authorized": False,
        "tool_metadata_independently_refetched": False,
        "private_raw_content_exported": False,
        "new_browser_requests_by_verifier": False,
        "paired_cases": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-root", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    arguments = parser.parse_args()
    if arguments.out.exists() or arguments.out.is_symlink():
        raise SystemExit("REFUSED: prior original report must not be overwritten")
    try:
        result = audit(arguments.private_root)
    except (PairedEvidenceBlocked, OSError, ValueError, KeyError, TypeError):
        raise SystemExit("BLOCKED: incomplete or inconsistent original paired evidence") from None
    arguments.out.write_text(
        json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    )
    print({k: v for k, v in result.items() if not isinstance(v, list)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
