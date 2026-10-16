"""Frozen 120B native evidence must never inflate completion into Mod approval."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "docs/reports/2026-10-17-p5-big-three-completion.json"
REPORT = ROOT / "docs/reports/2026-10-17-p5-big-three-completion.md"
EXPECTED = ("POS-E-01", "POS-Q-01", "NEG-TYPESCRIPT", "BOUND-VERSION-NEW")


def test_exact_original_trials_are_not_silently_retried_as_passes() -> None:
    data = json.loads(PUBLIC.read_text())
    assert data["schema_version"] == 1
    assert data["native_primary_attempts"] == 12
    assert data["complete_primary_answers"] == 11
    assert data["separate_heretic_attempts"] == 3
    assert data["separate_heretic_complete"] == 1
    assert data["not_a_single_configuration_12_of_12_pass"] is True
    assert len(data["models"]) == 3
    assert [x["primary_complete"] for x in data["models"]] == [4, 4, 3]
    assert all(
        [x["context_window"] == 16384 and x["max_output_tokens"] == 6144 for x in data["models"]]
    )
    assert all({x["id"] for x in m["cases"]} == set(EXPECTED) for m in data["models"])
    assert all(len(m["cases"]) == 4 for m in data["models"])
    assert Counter(t["complete_answer"] for t in data["heretic_retest"]) == {False: 2, True: 1}
    assert Counter(t["repeat_tool_abort"] for t in data["heretic_retest"]) == {True: 2, False: 1}
    assert all(x["context_window"] == 8192 for x in data["heretic_retest"])


def test_source_and_version_boundary_are_not_misrepresented_as_safe() -> None:
    d = json.loads(PUBLIC.read_text())
    assert d["positive_exact_source_passes"] == 0
    assert d["version_boundary_implementation_flags"] == 3
    assert d["production_mods_approved"] is False
    assert d["full_semantic_code_validation"] is False
    assert all(c["code_semantic_approval"] is False for m in d["models"] for c in m["cases"])
    assert all(
        re.fullmatch(r"[0-9a-f]{64}", c["native_events_sha256"])
        for m in d["models"]
        for c in m["cases"]
    )
    assert all(
        re.fullmatch(r"[0-9a-f]{64}", c["native_events_sha256"]) for c in d["heretic_retest"]
    )


def test_original_ai_services_restored_and_private_model_text_not_published() -> None:
    d = json.loads(PUBLIC.read_text())
    material = PUBLIC.read_text() + "\n" + REPORT.read_text()
    assert d["original_five_ai_services_restored"] is True
    assert d["custom_50_percent_abort_disabled"] is True
    assert d["macos_memory_management_unchanged"] is True
    assert d["global_pi_defaults_unchanged"] is True
    assert d["raw_native_transcripts_private"] is True
    assert "Strata-native" in material
    assert not re.search(r"/Users/[^/\s]+|/home/grammy-jiang/|/tmp/mods-", material)
    assert not re.search(r"chatgpt.com/c/[0-9a-f-]{36}", material, re.I)
    assert not re.search(r"Bearer\s+[A-Za-z0-9._-]{20,}", material)
