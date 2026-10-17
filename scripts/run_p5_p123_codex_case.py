#!/usr/bin/env python3
"""One real native Codex Sol/medium turn, new Skill isolated from global user.

Original P4 prompt, actual same-thread App Server model and Skill read,
owner-only transcript and safe source verdict. Never fabricate availability
or turn an unsupported-version research response into deliverable code.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import time
from pathlib import Path

import run_p5_p123_codex_native as codex

from mods_knowledge.claims import load_claims
from mods_knowledge.registry import load_registry
from mods_knowledge.task_evidence import render_evidence_pack, select_task_evidence

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "dist/common/claude-code-mods-development"
PRIVATE = Path.home() / "Models.noindex/benchmarks/p5-p123-seven-stack-20261017"
PLAN = ROOT / "evals/p5_p123_seven_stack_12x3.json"


def run(case_id: str, trial: int, *, no_web: bool) -> dict:
    manifest = json.loads(PLAN.read_text())
    if (
        case_id not in manifest["case_ids"]
        or trial not in (1, 2, 3)
        or hashlib.sha256((ROOT / manifest["source_file"]).read_bytes()).hexdigest()
        != manifest["source_sha256"]
    ):
        raise ValueError("Frozen original candidate case/trial identity invalid")
    code = "codex_no_web" if no_web else "codex"
    workspace = PRIVATE / "codex-v2" / code / case_id / f"trial-{trial}"
    if workspace.exists():
        raise ValueError("Original Codex model trial cannot be overwritten/replayed")
    if (
        not SOURCE.is_dir()
        or hashlib.sha256((SOURCE / "SKILL.md").read_bytes()).hexdigest()
        != manifest["candidate_skill_sha256"]
    ):
        raise ValueError("Candidate local Skill bytes changed")
    catalog = {
        x["id"]: x for x in json.loads((ROOT / manifest["source_file"]).read_text())["cases"]
    }
    case = catalog[case_id]
    claims = load_claims(
        ROOT / "claims",
        load_registry(ROOT / "sources/registry.json"),
        ROOT / "sources/snapshots",
        ROOT / "decisions",
    )
    evidence = select_task_evidence(case["prompt"], claims)
    if (
        case["category"] == "positive"
        and not evidence["ready"]
        or case["category"] == "negative"
        and evidence["intent"] != "unrelated"
        or case["category"] == "boundary"
        and evidence["intent"] != "blocked"
    ):
        raise ValueError("Deterministic Task Evidence mode is inconsistent with frozen case")
    workspace.mkdir(parents=True, mode=0o700)
    workspace.chmod(0o700)
    skill = workspace / ".agents/skills/claude-code-mods-development"
    skill.parent.mkdir(parents=True, mode=0o700)
    shutil.copytree(SOURCE, skill)
    pack_sha = None
    if evidence["ready"]:
        content = render_evidence_pack(evidence).encode("utf-8")
        file = skill / "references/selected-evidence.md"
        file.write_bytes(content)
        file.chmod(0o600)
        pack_sha = hashlib.sha256(content).hexdigest()
    from run_p5_codex_paired import prepare_fixture

    prepare_fixture(case_id, workspace)
    started = time.monotonic()
    home, result = codex.run_native_case(
        case_id,
        "macbook-pro",
        105,
        private_workspace=workspace,
        approved_case_ids=set(manifest["case_ids"]),
        disable_web_search=no_web,
    )
    wire = home / "native-wire.jsonl"
    if not wire.is_file():
        raise ValueError("Missing native model transcript; no completion claimed")
    native_sha = hashlib.sha256(wire.read_bytes()).hexdigest()
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
    if no_web and web_count:
        raise ValueError("Web-search-disabled native Codex still used web search")
    report = {
        "case_id": case_id,
        "candidate": code,
        "trial": trial,
        "original_source_sha256": manifest["source_sha256"],
        "candidate_skill_sha256": manifest["candidate_skill_sha256"],
        "selected_claim_ids": [x["claim_id"] for x in evidence["claims"]],
        "selected_evidence_sha256": pack_sha,
        "model_requested": "gpt-6.1-sol",
        "effort_requested": "medium",
        "model_server_resolved": result.get("model_server_resolved"),
        "effort_server_resolved": result.get("effort_server_resolved"),
        "native_model_provenance": result.get("model_provenance"),
        "native_case_completed": result.get("agent_completed") is True
        and result.get("state") == "native_turn_recorded",
        "actual_candidate_skill_read": result.get("skill_loaded"),
        "source_verdict": result.get("source_verdict"),
        "native_scorer_verdict": result.get("verdict"),
        "web_search_disabled": no_web,
        "native_web_search_count": web_count,
        "elapsed_s": round(time.monotonic() - started, 2),
        "registered_isolated_skill": result.get("registered_candidate_skill_before_model"),
        "private_wire_sha256": native_sha,
        "raw_reply_exposed": False,
        "semantic_mods_correctness_verified": False,
        "production_delivery": False,
        "boundary_preflight_would_block": case["category"] == "boundary",
    }
    dest = workspace / "report.json"
    if dest.exists():
        raise ValueError("Original Codex trial evidence already exists")
    dest.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    dest.chmod(0o600)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    p = json.loads(PLAN.read_text())
    parser.add_argument("--case", choices=p["case_ids"], required=True)
    parser.add_argument("--trial", type=int, choices=(1, 2, 3), required=True)
    parser.add_argument("--no-web", action="store_true")
    args = parser.parse_args()
    row = run(args.case, args.trial, no_web=args.no_web)
    print(
        json.dumps(
            {
                "candidate": row["candidate"],
                "case_id": row["case_id"],
                "trial": row["trial"],
                "native_completed": row["native_case_completed"],
                "model": row["model_server_resolved"],
                "skill_read": row["actual_candidate_skill_read"],
                "source": row["source_verdict"],
                "raw_reply_exposed": False,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
