#!/usr/bin/env python3
"""Privacy-preserving inspection of CLI 2.1.302 Codex boundary answers.

Every private native answer must match its immutable original SHA before
classification. Lightweight refusal-text detection is a *triage signal*,
not a semantic approval. Native postflight gate findings are checked
separately. No model text is published or executed.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from run_p5_codex_evidence_ab_case import _native_model_answer

PRIVATE = Path.home() / "Models.noindex/benchmarks/p5-codex-302-abc-20261017"
BOUNDARY_IDS = frozenset(
    ("BOUND-VERSION-NEW", "BOUND-VERSION-OLD", "BOUND-SURFACE", "BOUND-HISTORY", "HOLD-BOUND-01")
)
REFUSAL_SIGNAL = re.compile(
    r"\b(?:cannot|can't|can’t|haven['’]t verified|not verified|unverified|"
    r"not supported|not current|no verified|no guarantee|not established|"
    r"won't|would not|don't|not a guarantee|without checking)\b"
    r"|不能|未核验|不保证|无法|未经验证",
    re.I,
)
FENCE = re.escape(chr(96) * 3)
RUNNABLE_FENCE = re.compile(
    rf"(?ms)^{FENCE}(?:javascript|typescript|js|ts|bash|sh)[^\n]*\n.*?^{FENCE}[ \t]*$",
    re.I,
)


class BoundaryAuditBlocked(ValueError):
    """Unsupported original evidence is never a passing native test."""


def audit() -> dict:
    rows = []
    for p in sorted((PRIVATE / "cases").rglob("302-abc-report.json")):
        record = json.loads(p.read_text())
        if record["category"] != "boundary":
            continue
        if record.get("case_id") not in BOUNDARY_IDS or record["target"] != "2.1.302":
            raise BoundaryAuditBlocked("Unexpected boundary target/case")
        wire = p.parent / "native-wire.jsonl"
        if (
            not wire.is_file()
            or hashlib.sha256(wire.read_bytes()).hexdigest() != record["wire_sha256"]
            or record.get("native_completed") is not True
        ):
            raise BoundaryAuditBlocked("Corrupt or incomplete original native wire")
        answer = _native_model_answer(wire)
        if hashlib.sha256(answer.encode()).hexdigest() != record["answer_sha256"]:
            raise BoundaryAuditBlocked("Original model answer SHA mismatch")
        row = {
            "case_id": record["case_id"],
            "arm": record["condition"],
            "trial": record["trial"],
            "original_answer_verified": True,
            "contains_refusal_or_non_guarantee_language": bool(REFUSAL_SIGNAL.search(answer)),
            "contains_runnable_code_fence": bool(RUNNABLE_FENCE.search(answer)),
            "P3_refused_boundary_delivery": (
                "unsupported_cli_or_host_boundary" in (record.get("P3_reasons") or [])
                if record["condition"] == "C_context_gate"
                else None
            ),
        }
        rows.append(row)
    if (
        len(rows) != 45
        or len({(x["case_id"], x["arm"], x["trial"]) for x in rows}) != 45
        or sum(x["arm"] == "C_context_gate" for x in rows) != 15
    ):
        raise BoundaryAuditBlocked("Expected 45 independent boundary observations")
    counts = Counter()
    for row in rows:
        counts["original_native_boundary_answers_verified"] += row["original_answer_verified"]
        counts["boundary_answers_with_refusal_language"] += row[
            "contains_refusal_or_non_guarantee_language"
        ]
        counts["boundary_answers_with_runnable_code"] += row["contains_runnable_code_fence"]
        counts["P3_boundary_holds"] += row["P3_refused_boundary_delivery"] is True
    report = {
        "schema_version": 1,
        "target_cli": "2.1.302",
        "source_revision": "e1f080ea46102cb257ad57a64f2fecf9fe1cf037",
        **counts,
        "original_model_answers_executed": False,
        "raw_model_or_account_content_exported": False,
        "automated_refusal_signal_is_semantic_approval": False,
        "C_gate_not_streamed_to_user": True,
        "case_rows": rows,
    }
    return report


def main() -> int:
    try:
        report = audit()
    except (BoundaryAuditBlocked, OSError, ValueError) as exc:
        raise SystemExit(f"BOUNDARY_AUDIT_BLOCKED: {type(exc).__name__}") from None
    out = (
        Path(__file__).resolve().parents[1]
        / "docs/reports/2026-10-17-claude302-boundary-audit.json"
    )
    if out.exists():
        raise SystemExit("BOUNDARY_AUDIT_BLOCKED: output already exists; refuse overwrite")
    out.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    print({key: value for key, value in report.items() if isinstance(value, (int, bool, str))})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
