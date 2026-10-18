#!/usr/bin/env python3
"""Offline two-axis diagnostic report. Never modifies frozen QA or release gates."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from mods_knowledge.boundary_diagnostics import (
    BoundaryDiagnosticError,
    diagnose_boundary_cohort,
)

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--original",
        type=Path,
        default=ROOT / "docs/reports/2026-10-18-cli302-beta010-all-eight-boundary-natural.json",
    )
    parser.add_argument(
        "--diagnostic-contract",
        type=Path,
        default=ROOT / "evals/p4_boundary_two_axis_diagnostic_302.json",
    )
    parser.add_argument(
        "--strict-rubric",
        type=Path,
        default=ROOT / "evals/p4_boundary_semantic_rubric_cli_2_1_302.json",
    )
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    if args.out.exists() or args.out.is_symlink():
        raise SystemExit("REFUSED: existing report is immutable")
    try:
        original, contract, strict = (
            json.loads(x.read_text(encoding="utf-8"))
            for x in (args.original, args.diagnostic_contract, args.strict_rubric)
        )
        result = diagnose_boundary_cohort(original, contract, strict)
    except (OSError, ValueError, KeyError, TypeError, BoundaryDiagnosticError):
        raise SystemExit(
            "BLOCKED: invalid frozen P4 boundary evidence or diagnostic contract"
        ) from None
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    print(json.dumps({k: v for k, v in result.items() if not isinstance(v, list)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
