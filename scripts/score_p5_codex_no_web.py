#!/usr/bin/env python3
"""Score native Codex Sol/medium with web_search disabled and proven unused.

This is a distinct 36-turn cohort, never mixed with the existing 36-turn
web-enabled Codex cohort. Codex default user-global settings unchanged.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import score_p5_codex_paired as scorer
from run_p5_codex_paired import MODEL, PRIVATE, frozen


def summarize() -> dict:
    original_private = scorer.PRIVATE
    scorer.PRIVATE = PRIVATE / "no-web"
    try:
        base = scorer.summarize()
    finally:
        scorer.PRIVATE = original_private
    ids = set(frozen()["case_ids"])
    for x in base["rows"]:
        if x["status"] == "not_observed":
            continue
        cid, trial = x["case_id"], x["trial"]
        if cid not in ids or trial not in (1, 2, 3):
            raise ValueError("Outside frozen no-web test cohort")
        folder = PRIVATE / "no-web/paired" / MODEL / cid / f"trial-{trial}"
        wire = folder / "native-wire.jsonl"
        report = json.loads((folder / "report.json").read_text())
        if (
            report.get("web_search_disabled_requested") is not True
            or report.get("native_web_search_count") != 0
            or report.get("model_requested") != MODEL
            or report.get("effort_requested") != "medium"
        ):
            raise ValueError("Native Codex no-web run was not actually configured offline")
        web_count = 0
        for line in wire.read_text(errors="replace").splitlines():
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if event.get("method") == "item/completed":
                item = event.get("params", {}).get("item")
                if isinstance(item, dict) and item.get("type") == "webSearch":
                    web_count += 1
        if web_count:
            raise ValueError("Found actual webSearch call despite disabled configuration")
        if hashlib.sha256(wire.read_bytes()).hexdigest() != x["wire_sha256"]:
            raise ValueError("Immutable no-web native event hash mismatch")
        x["native_web_search_calls"] = 0
        x["model"] = "codex_no_web"
    base["stat"]["model"] = "codex_no_web"
    base["web_search_disabled"] = True
    base["all_observed_trials_web_search_count"] = 0
    base["cohort"] = "Codex Sol medium, web_search disabled through CLI configuration"
    base["complete_timing_observations"] = sum(
        x["status"] != "not_observed" and isinstance(x.get("elapsed_s"), (int, float))
        for x in base["rows"]
    )
    base["runtime_caveat"] = (
        "The same frozen prompts and Skill are used, but native Codex "
        "read-only command tools, available user plugin resources and hosted "
        "model behavior still differ from Pi Agent's local read/ls/find/grep."
    )
    return base


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    report = summarize()
    if args.dry_run:
        print(
            json.dumps(
                {
                    "observed": report["codex_observed"],
                    "unobserved": report["codex_unobserved"],
                    "all_native_web_search_calls": 0,
                    "stat": report["stat"],
                }
            )
        )
        return 0
    if args.out.exists():
        p.error("Immutable private offline report already exists")
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    args.out.chmod(0o600)
    print(
        json.dumps(
            {
                "observed": report["codex_observed"],
                "unobserved": report["codex_unobserved"],
                "all_native_web_search_calls": 0,
                "stat": report["stat"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
