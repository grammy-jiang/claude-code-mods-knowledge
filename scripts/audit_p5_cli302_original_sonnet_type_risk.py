#!/usr/bin/env python3
"""Offline SHA-bound recheck of real Sonnet CLI302 code-block type hazards.

No model/network/account request and never emits original reply contents.
Historical original transcripts remain private. The public original report
furnishes immutable full-wire and final-answer hashes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from mods_knowledge.answer_lint import _code_spans, lint_mods_answer

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs/reports/2026-10-18-claude302-sonnet-beta012-five-native-observations.json"
CASE_COUNTS = {"POS-E-01": 3, "POS-Q-01": 1}
RISK = "mods-cli302-unsupported-console-global"


class NativeTypeReplayBlocked(ValueError):
    """Original transcript, final answer, or current type finding disagrees."""


def checksum(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def read_original(path: Path, expected: dict) -> dict:
    if not path.is_file() or path.is_symlink() or not 1_000 < path.stat().st_size < 300_000:
        raise NativeTypeReplayBlocked("Missing bounded original completed native wire")
    wire = path.read_bytes()
    if checksum(wire) != expected["original_wire_sha256"]:
        raise NativeTypeReplayBlocked("Native original wire altered")
    try:
        events = [json.loads(line) for line in wire.splitlines() if line.strip()]
    except (ValueError, UnicodeError) as exc:
        raise NativeTypeReplayBlocked("Native event JSONL corrupt") from exc
    finals = [x for x in events if x.get("type") == "result"]
    if len(finals) != 1 or finals[0].get("subtype") != "success":
        raise NativeTypeReplayBlocked("Not exactly one real completed native model result")
    terminal = finals[0]
    if set(terminal.get("modelUsage") or {}) != {"claude-sonnet-5-5"}:
        raise NativeTypeReplayBlocked("Wrong real native model")
    text = terminal.get("result")
    if (
        not isinstance(text, str)
        or checksum(text.encode()) != expected["original_final_answer_sha256"]
    ):
        raise NativeTypeReplayBlocked("Wrong original completed answer hash")
    result = lint_mods_answer(text, case_id=expected["case_id"], target_version="2.1.302")
    detected = RISK in result["risk_flags"]
    wanted = expected["case_id"] == "POS-E-01"
    snippets = len(_code_spans(text))
    if detected is not wanted or snippets != CASE_COUNTS[expected["case_id"]]:
        raise NativeTypeReplayBlocked(
            "Current linter missed genuine type error or falsely flagged control"
        )
    return {
        "case_id": expected["case_id"],
        "original_wire_sha256": checksum(wire),
        "original_final_sha256": checksum(text.encode()),
        "actual_markdown_fenced_snippets_detected": snippets,
        "known_cli302_console_type_risk": detected,
        "full_semantic_quality_verified": False,
    }


def audit(positive: Path, control: Path) -> dict:
    previous = json.loads(SOURCE.read_text())
    by_case = {x["case_id"]: x for x in previous["cases"] if x["case_id"] in CASE_COUNTS}
    if set(by_case) != set(CASE_COUNTS):
        raise NativeTypeReplayBlocked("Frozen source report is missing original cases")
    rows = [
        read_original(positive, by_case["POS-E-01"]),
        read_original(control, by_case["POS-Q-01"]),
    ]
    return {
        "schema_version": 1,
        "source_candidate": "0.4.12-beta.1",
        "reviewed_cli": "2.1.302",
        "model": "claude-sonnet-5-5",
        "original_real_native_responses_verified": 2,
        "historical_model_rerun_performed": False,
        "new_model_or_network_requests": 0,
        "real_indented_codeblocks_recovered": 3,
        "real_bad_example_correctly_flagged": True,
        "real_control_not_falsely_flagged": True,
        "old_p4_strict_activation_gate_modified": False,
        "complete_current_p5_host_acceptance": False,
        "stable_release_authorized": False,
        "raw_original_answers_prompts_paths_or_credentials_exported": False,
        "cases": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--positive-wire", type=Path, required=True)
    parser.add_argument("--control-wire", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists() or args.out.is_symlink():
        raise SystemExit("REFUSED: historical native type risk report is immutable")
    try:
        result = audit(args.positive_wire, args.control_wire)
    except (OSError, ValueError, KeyError, TypeError, NativeTypeReplayBlocked):
        raise SystemExit("BLOCKED: genuine Sonnet native type evidence mismatch") from None
    args.out.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    print(
        {
            "real_positive_type_risk_detected": True,
            "real_safe_control_preserved": True,
            "native_model_reruns": 0,
            "stable_release": "HOLD",
        }
    )


if __name__ == "__main__":
    raise SystemExit(main())
