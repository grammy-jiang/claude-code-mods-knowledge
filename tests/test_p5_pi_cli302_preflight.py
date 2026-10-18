"""Native 2.1.302 Pi preflight is model-free and revision bound."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

from mods_knowledge.compiler import compile_knowledge

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_p5_pi_cli302_preflight.py"


def mod():
    spec = importlib.util.spec_from_file_location("pi_p5_preflight_302", SCRIPT)
    assert spec and spec.loader
    script = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(script)
    return script


@pytest.fixture(scope="module")
def skill() -> bytes:
    return compile_knowledge(
        ROOT,
        api_version="2.1.302",
        surface="cli",
        knowledge_version="0.4.11",
        package_version="0.4.11-beta.1",
        source_revision="a37d96e7e018e14e27562c366ead0d3e36c2c377",
    )["common/claude-code-mods-development/SKILL.md"]


def case(case_id: str):
    return next(
        x
        for x in json.loads((ROOT / "evals/p4_cases_cli_2_1_302.json").read_text())["cases"]
        if x["id"] == case_id
    )


def test_302_unsafe_boundary_never_performs_model_call(skill: bytes) -> None:
    script = mod()
    result = script.plan(
        case("BOUND-VERSION-NEW"),
        skill_bytes=skill,
        reviewed_skill_sha256=hashlib.sha256(skill).hexdigest(),
        reviewed_source_revision="a37d96e7e018e14e27562c366ead0d3e36c2c377",
        observed_claude_version="2.1.302 (Claude Code)",
        observed_pi_version="1.3.0",
    )
    assert result["action"] == "abstain_before_model"
    assert result["model_requests_authorized_by_gate"] == 0
    assert result["model_requests_performed"] == 0
    assert result["native_model_inference_completed"] is False
    assert result["safe_refusal_sha256"]
    assert result["stable_release_authorized"] is False


@pytest.mark.parametrize("case_id", ["POS-E-01", "POS-Q-01", "NEG-TYPESCRIPT"])
def test_302_positive_and_unrelated_are_only_backend_pending(skill: bytes, case_id: str) -> None:
    script = mod()
    outcome = script.plan(
        case(case_id),
        skill_bytes=skill,
        reviewed_skill_sha256=hashlib.sha256(skill).hexdigest(),
        reviewed_source_revision="a37d96e7e018e14e27562c366ead0d3e36c2c377",
        observed_claude_version="2.1.302 (Claude Code)",
        observed_pi_version="1.3.0",
    )
    assert outcome["action"] == "model_backend_required_after_preflight"
    assert outcome["model_requests_authorized_by_gate"] == 1
    assert outcome["model_requests_performed"] == 0
    assert outcome["native_model_inference_completed"] is False


def test_version_or_skill_drift_never_allows_zero_check_shortcut(skill: bytes) -> None:
    script = mod()
    case_data = case("BOUND-VERSION-NEW")
    for bad in [
        {"skill_bytes": skill + b"\n"},
        {"observed_claude_version": "2.1.310 (Claude Code)"},
        {"observed_pi_version": "0.9.0"},
    ]:
        options = {
            "skill_bytes": skill,
            "reviewed_skill_sha256": hashlib.sha256(skill).hexdigest(),
            "reviewed_source_revision": "a37d96e7e018e14e27562c366ead0d3e36c2c377",
            "observed_claude_version": "2.1.302 (Claude Code)",
            "observed_pi_version": "1.3.0",
        }
        options.update(bad)
        with pytest.raises(script.NativePreflight302Error):
            script.plan(case_data, **options)
