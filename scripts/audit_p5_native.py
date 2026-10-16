#!/usr/bin/env python3
"""Review private real Agent JSONL and produce ONLY sanitized P5 evidence.

Model inference is deliberately not performed by this script.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from mods_knowledge.claims import load_claims
from mods_knowledge.p5_native_evidence import (
    aggregate_native_matrix,
    summarize_codex_native_trace,
    summarize_pi_native_trace,
)
from mods_knowledge.registry import load_registry

ROOT = Path(__file__).resolve().parents[1]
BASE = "6cbdc9ad6ed9f958072f9cbf4a34c4bbc2d5ef3e"
SHA = "03053cc81e43ca215621db048eb435d675a2685205953019744a5df1bc13530e"


def _read_jsonl(path: Path) -> list[dict]:
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 50_000_000:
        raise ValueError("Private native event trace missing, unsafe or unbounded")
    records = []
    with path.open(encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue
            event = json.loads(line)
            if not isinstance(event, dict):
                raise ValueError("Invalid JSONL event type")
            records.append(event)
            if len(records) > 100_000:
                raise ValueError("Excessive native trace events")
    return records


def _safe_write(out: Path, report: dict) -> None:
    if not out.is_absolute() or out.is_symlink() or not out.parent.is_dir():
        raise ValueError("Explicit absolute report path in an existing directory required")
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    descriptor = out.open("x", encoding="utf-8")
    try:
        out.chmod(0o600)
        descriptor.write(payload)
    finally:
        descriptor.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="operation", required=True)
    audit = sub.add_parser("audit")
    audit.add_argument("--agent", choices=["codex", "pi"], required=True)
    audit.add_argument("--host", choices=["macbook-pro", "raspberry-pi", "sextant"], required=True)
    audit.add_argument("--case", required=True)
    audit.add_argument("--trace", type=Path, required=True)
    audit.add_argument("--cli-version", required=True)
    audit.add_argument("--source-revision", default=BASE)
    audit.add_argument("--skill-root", type=Path, required=True)
    audit.add_argument("--skill-sha256", default=SHA)
    audit.add_argument("--expected-provider", default="mac-qwen")
    audit.add_argument("--expected-model", default="qwen36-35b-a3b-mtp")
    audit.add_argument("--model-was-pinned", action="store_true")
    audit.add_argument("--out", required=True, type=Path)
    matrix = sub.add_parser("matrix")
    matrix.add_argument("--source-revision", default=BASE)
    matrix.add_argument("--reports", nargs="+", type=Path, required=True)
    matrix.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    if args.operation == "matrix":
        reports = [json.loads(p.read_text(encoding="utf-8")) for p in args.reports]
        result = aggregate_native_matrix(reports, source_revision=args.source_revision)
    else:
        skill = args.skill_root / "SKILL.md"
        if (
            not skill.is_file()
            or skill.is_symlink()
            or hashlib.sha256(skill.read_bytes()).hexdigest() != args.skill_sha256
        ):
            raise ValueError("Skill source SHA cannot be verified")
        case_data = json.loads((ROOT / "evals/p4_cases.json").read_text())["cases"]
        matched = [c for c in case_data if c["id"] == args.case]
        if len(matched) != 1:
            raise ValueError("Exact frozen case ID not found")
        registry = load_registry(ROOT / "sources/registry.json")
        claims = load_claims(
            ROOT / "claims", registry, ROOT / "sources/snapshots", ROOT / "decisions"
        )
        records = _read_jsonl(args.trace)
        options = {
            "source_revision": args.source_revision,
            "host": args.host,
            "cli_version": args.cli_version,
            "skill_root": str(args.skill_root),
            "claims": claims,
        }
        if args.agent == "codex":
            result = summarize_codex_native_trace(matched[0], records, **options)
        else:
            result = summarize_pi_native_trace(
                matched[0],
                records,
                **options,
                expected_provider=args.expected_provider,
                expected_model=args.expected_model,
                model_was_pinned=args.model_was_pinned,
            )
    _safe_write(args.out, result)
    print(
        json.dumps(
            {
                "operation": args.operation,
                "case_id": result.get("case_id"),
                "host": result.get("host"),
                "agent": result.get("agent"),
                "verdict": result.get("verdict"),
                "observed": result.get("observed"),
                "missing": result.get("missing"),
                "semantic_review_complete": result.get("semantic_review_complete", False),
                "full_p5_acceptance": result.get("full_p5_acceptance", False),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
