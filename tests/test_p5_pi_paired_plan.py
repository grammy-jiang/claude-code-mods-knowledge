"""Freeze the reproducible 12×3 two-model native Pi campaign scope."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
# Scripts are intentionally not shipped as an importable installed package.
sys.path.insert(0, str(ROOT))
from scripts.run_p5_pi_gated import MODEL_CANDIDATES  # noqa: E402
from scripts.run_p5_pi_paired_batch import _cases_for_round, _preflight  # noqa: E402


def test_paired_suite_is_12_unique_existing_cases_three_times() -> None:
    plan = json.loads((ROOT / "evals/p5_pi_auto_12x3.json").read_text())
    source = ROOT / plan["source_file"]
    assert hashlib.sha256(source.read_bytes()).hexdigest() == plan["source_sha256"]
    catalog = {row["id"]: row for row in json.loads(source.read_text())["cases"]}
    assert set(plan["case_ids"]) <= set(catalog)
    assert len(plan["case_ids"]) == len(set(plan["case_ids"])) == 12
    categories = Counter(catalog[cid]["category"] for cid in plan["case_ids"])
    assert categories == {"positive": 4, "negative": 4, "boundary": 4}
    assert plan["repetitions"] == 3
    assert plan["expected_total_model_trials"] == 72
    assert len(plan["models"]) == 2
    assert all("gpt-oss" not in v["id"].lower() for v in plan["models"])
    assert set(plan["tools"]) == {"read", "ls", "find", "grep"}
    _preflight("qwen", plan)
    _preflight("gemma31", plan)


def test_model_sources_are_literal_allowed_local_endpoints() -> None:
    plan = json.loads((ROOT / "evals/p5_pi_auto_12x3.json").read_text())
    expected = {(m["id"], m["provider"], m["backend"]) for m in plan["models"]}
    actual = {(m[1], m[0], m[2]) for m in MODEL_CANDIDATES.values()}
    assert expected == actual
    assert all(x[2].startswith("http://127.0.0.1:") for x in actual)


def test_three_rounds_use_separate_independent_orders() -> None:
    ids = json.loads((ROOT / "evals/p5_pi_auto_12x3.json").read_text())["case_ids"]
    rounds = [_cases_for_round(ids, i) for i in (1, 2, 3)]
    assert all(len(x) == 12 and set(x) == set(ids) for x in rounds)
    assert len({tuple(x) for x in rounds}) == 3


def test_only_approved_read_only_tools_and_extension_may_be_used() -> None:
    plan = json.loads((ROOT / "evals/p5_pi_auto_12x3.json").read_text())
    assert plan["identical_tool_repeat_abort"] == 6
    assert plan["restricted_tool_cap"] == 48
    assert plan["max_per_turn_seconds"] == 90
    assert plan["delivery_policy"] == "research-only-buffered-no-model-text-user-delivery"


@pytest.mark.skipif(shutil.which("node") is None, reason="Native Node test runtime not installed")
def test_native_opt_in_scope_extension_blocks_path_traversal() -> None:
    node = shutil.which("node")
    assert node
    proc = subprocess.run(  # noqa: S603 - local test file and resolved node executable
        [node, "--test", str(ROOT / "tests/test_pi_scope_guard.mjs")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert proc.returncode == 0, "Isolated native file-scope regression must pass"
