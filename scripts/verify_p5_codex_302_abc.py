#!/usr/bin/env python3
"""Read-only audit of the original private CLI 2.1.302 native Codex campaign.

One wire, one completed native turn and one SHA-bound answer per cell.
Print and optionally publish only aggregate statistics; never export prompts,
raw replies, conversation/account identities, or native wire events.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_p5_codex_302_abc import cells, folder, load, observed  # noqa: E402
from run_p5_codex_evidence_ab_case import _native_model_answer  # noqa: E402

from mods_knowledge.claim_source_link_coverage import audit_claim_source_links  # noqa: E402


def verify() -> dict:
    plan, cases, _skill, _home, claims = load()
    matrix = cells(plan)
    rows = []
    wire_hashes = set()
    answer_hashes = set()
    groups: dict[tuple[str, str, str], Counter] = {}
    missing = 0
    for cell in matrix:
        report = observed(cell, plan)  # Fails closed on corrupt or partial originals.
        if report is None:
            missing += 1
            continue
        home = folder(cell)
        raw = (home / "native-wire.jsonl").read_bytes()
        lines = [json.loads(line) for line in raw.splitlines()]
        started = [x for x in lines if x.get("method") == "turn/started"]
        completed = [x for x in lines if x.get("method") == "turn/completed"]
        if (
            len(started) != 1
            or len(completed) != 1
            or (started[0].get("params", {}).get("turn") or {}).get("status") != "inProgress"
            or (completed[0].get("params", {}).get("turn") or {}).get("status") != "completed"
            or (completed[0].get("params", {}).get("turn") or {}).get("error")
            or (started[0].get("params", {}).get("turn") or {}).get("id")
            != (completed[0].get("params", {}).get("turn") or {}).get("id")
            or report["model"] != plan["model"]
            or report["effort"] != plan["thinking"]
            or report["target"] != plan["target_cli"]
            or not report["no_web"]
            or not report["native_completed"]
            or report["raw_private_content_exported"] is not False
            or report["model_internal_evidence_consumption_proven"] is not False
            or report["native_mod_semantics_verified"] is not False
        ):
            raise ValueError("Native turn provenance/completion mismatch")
        answer = _native_model_answer(home / "native-wire.jsonl")
        if (
            not answer.strip()
            or hashlib.sha256(answer.encode()).hexdigest() != report["answer_sha256"]
        ):
            raise ValueError("Answer digest mismatch with original native wire")
        if report["wire_sha256"] in wire_hashes or report["answer_sha256"] in answer_hashes:
            raise ValueError("Duplicate native wire or answer across distinct original cells")
        wire_hashes.add(report["wire_sha256"])
        answer_hashes.add(report["answer_sha256"])
        installed = home / ".agents/skills/claude-code-mods-development/SKILL.md"
        if hashlib.sha256(installed.read_bytes()).hexdigest() != plan["skill_sha256"]:
            raise ValueError("Isolated per-cell Skill digest mismatch")
        if report["category"] == "positive":
            audit = audit_claim_source_links(
                answer,
                claims,
                version="2.1.302",
                surface="cli",
                required_claim_ids=cases[report["case_id"]]["expected_claim_ids"],
            )
            if (audit["structural_verdict"] == "pass") != report["positive_raw_exact_source"]:
                raise ValueError("Independent case-required exact-source rescore mismatch")
        rows.append(report)
        key = (report["cohort"], report["condition"], report["category"])
        stats = groups.setdefault(key, Counter())
        stats["observed"] += 1
        stats["native_completed"] += int(report["native_completed"])
        stats["skill_read"] += int(report["actual_skill_read"])
        stats["positive_exact_source"] += int(report["positive_raw_exact_source"])
        stats["negative_no_skill"] += int(report["negative_no_skill"])
        stats["gate_candidate"] += int(report["P3_structural_candidate"] is True)
        stats["gate_needs_review"] += int(bool(report["P3_reasons"]))
    if len(rows) != 144 or missing:
        raise ValueError(f"Incomplete original campaign: observed={len(rows)} missing={missing}")
    canonical = json.dumps(
        sorted(
            (r["case_id"], r["condition"], r["trial"], r["wire_sha256"], r["answer_sha256"])
            for r in rows
        ),
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return {
        "schema_version": 1,
        "target_cli": plan["target_cli"],
        "source_revision": plan["source_revision"],
        "source_sha256": plan["source_sha256"],
        "skill_sha256": plan["skill_sha256"],
        "model": plan["model"],
        "effort": plan["thinking"],
        "web_search": plan["web_search"],
        "planned_original_native_turns": len(matrix),
        "verified_original_native_turns": len(rows),
        "unique_native_wire_sha256": len(wire_hashes),
        "unique_native_answer_sha256": len(answer_hashes),
        "per_cell_sha256_and_single_completed_turn_verified": True,
        "private_cell_ledger_sha256": hashlib.sha256(canonical.encode()).hexdigest(),
        "group_results": [
            {
                "cohort": cohort,
                "condition": arm,
                "category": category,
                **dict(groups[(cohort, arm, category)]),
            }
            for cohort, arm, category in sorted(groups)
        ],
        "raw_prompts_or_transcripts_exported": False,
        "model_internal_evidence_consumption_proven": False,
        "native_mod_semantics_verified": False,
        "limitations": [
            "Sources and activation are structural; no Mod code has been semantically certified by this campaign.",
            "C P3 gate candidates are not execution-tested, and boundaries still require case-by-case technical review.",
            "Historical benchmark was isolated; its prior files were not modified by this read-only audit.",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, help="Optional redacted, aggregate JSON")
    args = ap.parse_args()
    result = verify()
    serial = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        if args.out.exists():
            raise FileExistsError("Refusing to overwrite an existing QA publication")
        args.out.write_text(serial)
    print(
        json.dumps(
            {
                "verified_original_native_turns": result["verified_original_native_turns"],
                "private_cell_ledger_sha256": result["private_cell_ledger_sha256"],
                "native_mod_semantics_verified": result["native_mod_semantics_verified"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
