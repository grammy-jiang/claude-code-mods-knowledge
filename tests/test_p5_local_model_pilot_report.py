"""Preserve the observed local Pi model QA failure and privacy boundaries."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/reports/2026-10-16-p5-pi-local-model-pilot.md"
DATA = ROOT / "docs/reports/2026-10-16-p5-pi-local-model-pilot.json"
CASES = {"POS-E-01", "POS-Q-01", "NEG-TYPESCRIPT", "BOUND-VERSION-NEW"}


def test_real_pilot_rows_cannot_be_mistaken_for_full_host_acceptance() -> None:
    data = json.loads(DATA.read_text())
    assert data["target_knowledge"] == "Claude Code CLI 2.1.296 only"
    assert data["source"] == "6cbdc9ad6ed9f958072f9cbf4a34c4bbc2d5ef3e"
    assert data["gpt_oss"]["native_pi_inference_attempted"] is False
    rows = data["rows"]
    assert len(rows) == 12
    assert Counter(row["model"] for row in rows) == {
        "gemma4-31b-mtp": 4,
        "gemma4-26b-a4b": 4,
        "qwen36-35b-a3b-mtp": 4,
    }
    assert all(
        {r["case_id"] for r in rows if r["model"] == model} == CASES
        for model in {"gemma4-31b-mtp", "gemma4-26b-a4b", "qwen36-35b-a3b-mtp"}
    )
    assert sum(x["source_verdict"] == "pass" for x in rows) == 0
    assert (
        next(
            x
            for x in rows
            if x["model"] == "qwen36-35b-a3b-mtp" and x["case_id"] == "NEG-TYPESCRIPT"
        )["timed_out"]
        is True
    )
    assert (
        next(
            x
            for x in rows
            if x["model"] == "qwen36-35b-a3b-mtp" and x["case_id"] == "BOUND-VERSION-NEW"
        )["status"]
        == "boundary_scope_violated"
    )
    assert (
        next(
            x
            for x in rows
            if x["model"] == "gemma4-31b-mtp" and x["case_id"] == "BOUND-VERSION-NEW"
        )["skill_read"]
        is False
    )


def test_public_report_is_sanitized_and_documents_restoration() -> None:
    text = REPORT.read_text() + "\n" + DATA.read_text()
    assert "all five original AI services" in text
    assert "120B" in text and "NOT OBSERVED" in text
    assert not re.search(r"/Users/[^/\s]+|/home/grammy-jiang/|/tmp/mods-local-model", text)
    assert not re.search(r"https?://[^\s]+/oauth/", text)
    assert not re.search(r"chatgpt.com/c/[a-f0-9-]{36}", text, re.I)
