#!/usr/bin/env python3
"""Native Codex 2.1.302 A/B/C turns, immutable private original evidence."""

import argparse
import hashlib
import json
import re
import shutil
import time
from pathlib import Path

from run_p5_codex_ab_native import run_native_case
from run_p5_codex_evidence_ab_case import _native_model_answer
from run_p5_codex_paired import prepare_fixture

from mods_knowledge.claims import load_claims
from mods_knowledge.evidence_delivery import make_verified_task_context
from mods_knowledge.registry import load_registry
from mods_knowledge.task_evidence import select_task_evidence

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "evals/p5_codex_302_abc_plan_20261017.json"
PRIVATE = Path.home() / "Models.noindex/benchmarks/p5-codex-302-abc-20261017"
CODE = re.compile(
    r"\x60{3}(?:javascript|js|typescript|ts|bash|sh)\b|"
    r"\bexport\s+(?:function|const)\s+register\b|"
    r"\bon\s*\(\s*['\"]tool\.call['\"]",
    re.I,
)


def load():
    plan = json.loads(PLAN.read_text())
    path = ROOT / plan["source_file"]
    if (
        plan["target_cli"] != "2.1.302"
        or plan["model"] != "gpt-6.1-sol"
        or plan["thinking"] != "medium"
        or plan["web_search"] != "disabled"
        or plan["source_revision"] != "e1f080ea46102cb257ad57a64f2fecf9fe1cf037"
        or plan["turns_planned"] != 144
        or hashlib.sha256(path.read_bytes()).hexdigest() != plan["source_sha256"]
    ):
        raise ValueError("Frozen 2.1.302 manifest does not match")
    cases = {x["id"]: x for x in json.loads(path.read_text())["cases"]}
    if set(cases) != set(plan["frozen_case_ids"] + plan["heldout_case_ids"]):
        raise ValueError("Current-version case set differs")
    skill = (ROOT / plan["skill_file_source"]).resolve()
    if (
        not skill.is_dir()
        or hashlib.sha256((skill / "SKILL.md").read_bytes()).hexdigest() != plan["skill_sha256"]
    ):
        raise ValueError("Current-version immutable Skill digest mismatch")
    home = PRIVATE / "codex-home"
    auth = Path.home() / ".codex/auth.json"
    if not home.exists():
        home.mkdir(mode=0o700, parents=True)
        (home / "auth.json").symlink_to(auth)
    if (
        home.is_symlink()
        or home.stat().st_mode & 0o077
        or not (home / "auth.json").is_symlink()
        or (home / "auth.json").resolve() != auth.resolve()
    ):
        raise ValueError("Private Codex auth HOME is not isolated")
    claims = load_claims(
        ROOT / "claims",
        load_registry(ROOT / "sources/registry.json"),
        ROOT / "sources/snapshots",
        ROOT / "decisions",
    )
    return plan, cases, skill, home, claims


def cells(plan):
    matrix = []
    for cohort in ("frozen_case_ids", "heldout_case_ids"):
        ids = plan[cohort]
        for trial in (1, 2, 3):
            seq = ids if trial == 1 else list(reversed(ids)) if trial == 2 else ids[1:] + ids[:1]
            conditions = plan["conditions"]
            order = conditions[trial - 1 :] + conditions[: trial - 1]
            for case_id in seq:
                for condition in order:
                    matrix.append((condition, trial, case_id))
    if len(matrix) != 144 or len(set(matrix)) != 144:
        raise ValueError("Unverified original 144 native cell layout")
    return matrix


def folder(cell):
    condition, trial, cid = cell
    return PRIVATE / "cases" / condition / cid / f"trial-{trial}"


def observed(cell, plan):
    root = folder(cell)
    file = root / "302-abc-report.json"
    if not file.is_file():
        if root.exists():
            raise ValueError("Partial immutable model turn exists; no auto retry")
        return None
    record = json.loads(file.read_text())
    wire = root / "native-wire.jsonl"
    if (
        not wire.is_file()
        or record["condition"] != cell[0]
        or record["trial"] != cell[1]
        or record["case_id"] != cell[2]
        or record["case_sha256"] != plan["source_sha256"]
        or record["skill_sha256"] != plan["skill_sha256"]
        or hashlib.sha256(wire.read_bytes()).hexdigest() != record["wire_sha256"]
    ):
        raise ValueError("Corrupt original native evidence; fail closed")
    return record


def one(cell, plan, cases, skill, home, claims):
    condition, trial, cid = cell
    case = cases[cid]
    selected = select_task_evidence(case["prompt"], claims, version="2.1.302")
    if (
        (case["category"] == "positive" and not selected["ready"])
        or (case["category"] == "boundary" and selected["ready"])
        or (case["category"] == "negative" and selected["intent"] != "unrelated")
    ):
        raise ValueError("Current exact-version routing disagrees with case category")
    context = (
        make_verified_task_context(selected)
        if condition != "A_v3" and case["category"] == "positive"
        else None
    )
    root = folder(cell)
    if root.exists():
        raise ValueError("Original A/B/C cell already exists")
    root.mkdir(mode=0o700, parents=True)
    dest = root / ".agents/skills/claude-code-mods-development"
    dest.parent.mkdir(mode=0o700, parents=True)
    shutil.copytree(skill, dest)
    prepare_fixture(cid, root)
    start = time.monotonic()
    _, result = run_native_case(
        cid,
        "macbook-pro",
        120,
        private_workspace=root,
        approved_case_ids={cid},
        disable_web_search=True,
        developer_instructions=context,
        case_source=ROOT / plan["source_file"],
        frozen_skill_sha=plan["skill_sha256"],
        private_auth_root=home,
        target_cli_version="2.1.302",
        source_revision=plan["source_revision"],
    )
    wire = root / "native-wire.jsonl"
    if not wire.is_file():
        raise ValueError("Actual native App Server transcript missing")
    answer = _native_model_answer(wire)
    completed = (
        result.get("state") == "native_turn_recorded"
        and result.get("model_server_resolved") == "gpt-6.1-sol"
        and result.get("effort_server_resolved") == "medium"
        and result.get("prompt_matched") is True
        and result.get("agent_completed") is True
        and result.get("registered_candidate_skill_before_model") is True
        and bool(answer.strip())
    )
    skill_read = result.get("skill_loaded") is True
    exact = (
        case["category"] == "positive"
        and completed
        and skill_read
        and result.get("source_verdict") == "pass"
    )
    reasons = []
    if condition == "C_context_gate":
        if case["category"] == "boundary":
            reasons.append("unsupported_cli_or_host_boundary")
        elif case["category"] == "positive":
            if not exact:
                reasons.append("missing_exact_approved_claim_or_url")
            if CODE.search(answer):
                reasons.append("runnable_code_needs_native_semantic_test")
            if result.get("risk_flags") or result.get("manual_review_flags"):
                reasons.append("manual_code_or_source_review")
        elif skill_read:
            reasons.append("unrelated_task_activated_mods_skill")
        if not completed:
            reasons.append("native_original_turn_incomplete")
    record = {
        "case_id": cid,
        "category": case["category"],
        "cohort": case["source_cohort"],
        "condition": condition,
        "trial": trial,
        "model": "gpt-6.1-sol",
        "effort": "medium",
        "target": "2.1.302",
        "source_revision": plan["source_revision"],
        "case_sha256": plan["source_sha256"],
        "skill_sha256": plan["skill_sha256"],
        "no_web": True,
        "native_completed": bool(completed),
        "actual_skill_read": skill_read,
        "source_verdict": result.get("source_verdict"),
        "native_verdict": result.get("verdict"),
        "positive_raw_exact_source": bool(exact),
        "negative_no_skill": case["category"] == "negative" and completed and not skill_read,
        "boundary_requires_manual_review": case["category"] == "boundary",
        "context_submitted": context is not None,
        "context_sha256": hashlib.sha256(context.encode()).hexdigest() if context else None,
        "selected_claim_ids": [x["claim_id"] for x in selected["claims"]],
        "P3_reasons": sorted(set(reasons)) if condition == "C_context_gate" else None,
        "P3_structural_candidate": not reasons if condition == "C_context_gate" else None,
        "model_internal_evidence_consumption_proven": False,
        "native_mod_semantics_verified": False,
        "raw_private_content_exported": False,
        "wire_sha256": hashlib.sha256(wire.read_bytes()).hexdigest(),
        "answer_sha256": hashlib.sha256(answer.encode()).hexdigest(),
        "duration_seconds": round(time.monotonic() - start, 2),
    }
    report = root / "302-abc-report.json"
    with report.open("x") as fd:
        fd.write(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    report.chmod(0o600)
    return record


def run(limit):
    plan, cases, skill, home, claims = load()
    matrix = cells(plan)
    count = 0
    for cell in matrix:
        if observed(cell, plan) is not None:
            continue
        if count >= limit:
            break
        r = one(cell, plan, cases, skill, home, claims)
        count += 1
        print(
            json.dumps(
                {
                    "case": r["case_id"],
                    "arm": r["condition"],
                    "trial": r["trial"],
                    "completed": r["native_completed"],
                    "skill": r["actual_skill_read"],
                    "source": r["positive_raw_exact_source"],
                    "seconds": r["duration_seconds"],
                }
            ),
            flush=True,
        )
        if not r["native_completed"]:
            raise ValueError("Native turn failed, no automatic retry")
    rows = [observed(cell, plan) for cell in matrix]
    completed = [x for x in rows if x is not None]
    counts = {
        arm: {
            "observed": sum(r["condition"] == arm for r in completed),
            "positive_exact_source": sum(
                r["condition"] == arm and r["positive_raw_exact_source"] for r in completed
            ),
            "negative_no_skill": sum(
                r["condition"] == arm and r["negative_no_skill"] for r in completed
            ),
        }
        for arm in plan["conditions"]
    }
    summary = {
        "target": "2.1.302",
        "model": "gpt-6.1-sol",
        "effort": "medium",
        "web_search": "disabled",
        "planned": len(matrix),
        "observed": len(completed),
        "missing": len(matrix) - len(completed),
        "fully_completed": len(completed) == len(matrix),
        "source_revision": plan["source_revision"],
        "old_original_evidence_unchanged": True,
        "semantic_mod_runtime_verified": False,
        "private_model_content_exported": False,
        "scores": counts,
    }
    (PRIVATE / "302-campaign-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
    )
    print("SUMMARY " + json.dumps(summary, ensure_ascii=False), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=144)
    args = parser.parse_args()
    if not 1 <= args.limit <= 144:
        parser.error("Invalid bounded limit")
    try:
        run(args.limit)
    except (OSError, ValueError) as exc:
        print("BLOCKED: " + type(exc).__name__ + ": " + str(exc)[:220], flush=True)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
