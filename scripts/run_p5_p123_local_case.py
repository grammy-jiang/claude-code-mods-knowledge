#!/usr/bin/env python3
"""One genuine Pi Agent Mod QA turn against isolated new Skill + task evidence.

Original P4 user prompt bytes are unchanged. Case-selected SSOT evidence is
placed only in a disposable Skill copy, without any model/weight/system
changes. Raw responses and events stay private and delivery-gated.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

import run_p5_big_three_case as native

from mods_knowledge.claims import load_claims
from mods_knowledge.registry import load_registry
from mods_knowledge.task_evidence import (
    render_evidence_pack,
    select_task_evidence,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "dist/common/claude-code-mods-development"
PRIVATE = Path.home() / "Models.noindex/benchmarks/p5-p123-seven-stack-20261017"
PLAN = ROOT / "evals/p5_p123_seven_stack_12x3.json"
MODELS = {
    "qwen": ("p5-new-qwen", "qwen36-35b-a3b-mtp", "http://127.0.0.1:8011/v1", "off", 32768, 8192),
    "gemma31": ("p5-new-gemma", "gemma4-31b-mtp", "http://127.0.0.1:8011/v1", "off", 32768, 8192),
    "gpt-oss": ("p5-big", "gpt-oss-120b", "http://127.0.0.1:8011/v1", "medium", 16384, 6144),
    "mistral": ("p5-big", "mistral-small-4-119b", "http://127.0.0.1:8011/v1", "off", 16384, 6144),
    "heretic": ("p5-big", "qwen35-122b-heretic", "http://127.0.0.1:8011/v1", "off", 16384, 6144),
}


def approved_plan() -> dict:
    data = json.loads(PLAN.read_text())
    original = (ROOT / data["source_file"]).read_bytes()
    assert hashlib.sha256(original).hexdigest() == data["source_sha256"]
    assert data["expected_total_local_trials"] == 180
    assert data["repetitions"] == 3
    assert {row["id"] for row in data["models"]} == {x[1] for x in MODELS.values()}
    return data


def run(case_id: str, trial: int, candidate: str) -> dict:
    plan = approved_plan()
    if trial not in (1, 2, 3) or candidate not in MODELS or case_id not in plan["case_ids"]:
        raise ValueError("Model/case/trial outside immutable frozen QA plan")
    if not SOURCE.is_dir():
        raise RuntimeError("Missing reviewed candidate Skill package")
    source_main = SOURCE / "SKILL.md"
    expected_sha = plan["candidate_skill_sha256"]
    if hashlib.sha256(source_main.read_bytes()).hexdigest() != expected_sha:
        raise RuntimeError("Candidate package changed after cohort freeze")
    chosen = MODELS[candidate]
    root = PRIVATE / "paired" / candidate / case_id / f"trial-{trial}"
    if root.exists():
        raise RuntimeError("Original native trial directory already exists: do not replay")
    # Source/Claim lookup is deterministic and pre-inference, without
    # using frozen 'expected_claim_ids' as a query-time selection oracle.
    rows = {x["id"]: x for x in json.loads((ROOT / plan["source_file"]).read_text())["cases"]}
    metadata = rows[case_id]
    claims = load_claims(
        ROOT / "claims",
        load_registry(ROOT / "sources/registry.json"),
        ROOT / "sources/snapshots",
        ROOT / "decisions",
    )
    selection = select_task_evidence(metadata["prompt"], claims, version="2.1.296")
    if metadata["category"] == "positive" and not selection["ready"]:
        raise RuntimeError("No verified task-specific evidence for positive Mod case")
    if metadata["category"] == "negative" and selection["intent"] != "unrelated":
        raise RuntimeError("Expected unrelated task selected unsafe Mod evidence")
    if metadata["category"] == "boundary" and selection["intent"] != "blocked":
        raise RuntimeError("Unsupported boundary was not preflight blocked")
    # Copy the approved bundle only within this specific owner-only trial.
    root.mkdir(parents=True, mode=0o700)
    agent = root / "agent"
    agent.mkdir(mode=0o700)
    skill = agent / "skills/claude-code-mods-development"
    skill.parent.mkdir(mode=0o700)
    shutil.copytree(SOURCE, skill)
    selected_digest = None
    if selection["ready"]:
        source = render_evidence_pack(selection).encode("utf-8")
        target = skill / "references/selected-evidence.md"
        target.write_bytes(source)
        target.chmod(0o600)
        selected_digest = hashlib.sha256(source).hexdigest()
    if hashlib.sha256((skill / "SKILL.md").read_bytes()).hexdigest() != expected_sha:
        raise RuntimeError("Private Skill source digest was modified")

    # Configure only this disposable Pi Agent directory, not the global
    # Pi models.json/settings.json nor the original online Qwen service.
    native.PRIVATE = PRIVATE
    native.SKILL = skill
    native.DIGEST = expected_sha
    native.MODEL_CANDIDATES = {k: v[:3] for k, v in MODELS.items()}
    native.THINKING = {k: v[3] for k, v in MODELS.items()}
    native.PAIRING_MANIFEST = PLAN
    original_agent_factory = native.make_isolated_agent

    def bounded_agent(home: Path, **kwargs) -> Path:
        directory = original_agent_factory(home, **kwargs)
        config = directory / "models.json"
        content = json.loads(config.read_text())
        entry = content["providers"][chosen[0]]["models"][0]
        entry["contextWindow"] = chosen[4]
        entry["maxTokens"] = chosen[5]
        entry["reasoning"] = chosen[3] == "medium"
        content["providers"][chosen[0]]["compat"]["supportsReasoningEffort"] = chosen[3] == "medium"
        native.write_json(config, content)
        native.write_json(
            directory / "settings.json",
            {
                "defaultProvider": chosen[0],
                "defaultModel": chosen[1],
                "defaultThinkingLevel": chosen[3],
            },
        )
        return directory

    native.make_isolated_agent = bounded_agent
    baseline_postflight = native.postflight_mods_case

    def source_gate(*args, **kw):
        return baseline_postflight(*args, **kw, enforce_task_evidence=True)

    native.postflight_mods_case = source_gate
    result = native.runner(
        case_id,
        "auto",
        95,
        candidate=candidate,
        trial=trial,
        research_boundary=metadata["category"] == "boundary",
    )
    result["P123_selection_intent"] = selection["intent"]
    result["P123_selected_claim_ids"] = [c["claim_id"] for c in selection["claims"]]
    result["P123_selected_evidence_sha256"] = selected_digest
    result["P123_skill_bundled_sha256"] = expected_sha
    result["P123_effective_context_window"] = chosen[4]
    result["P123_effective_max_output_tokens"] = chosen[5]
    result["P123_effective_thinking"] = chosen[3]
    result["P123_true_model_calls"] = result.get("model_calls")
    result["P123_raw_reply_exposed"] = False
    path = root / "report.json"
    native.write_json(path, result)
    return result


def main() -> int:
    plan = approved_plan()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", choices=sorted(MODELS), required=True)
    parser.add_argument("--case", choices=sorted(plan["case_ids"]), required=True)
    parser.add_argument("--trial", choices=(1, 2, 3), required=True, type=int)
    args = parser.parse_args()
    result = run(args.case, args.trial, args.candidate)
    print(
        json.dumps(
            {
                "candidate": args.candidate,
                "case": args.case,
                "trial": args.trial,
                "model_calls": result.get("model_calls"),
                "structural_source_verdict": result.get("gate", {}).get("source_verdict"),
                "deliverable": result.get("gate", {}).get("allow_raw_candidate_delivery"),
                "raw_answer_exposed": False,
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
