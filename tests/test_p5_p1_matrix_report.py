"""Regression: P1 public evidence cannot silently infer missing runtime cases."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "docs/reports/2026-10-16-p5-local-p1-matrix.json"
REPORT = ROOT / "docs/reports/2026-10-16-p5-local-p1-acceptance.md"


def test_matrix_records_real_cohort_and_missing_cells() -> None:
    data = json.loads(MATRIX.read_text())
    assert data["schema_version"] == 1
    assert data["source_revision"] == "6cbdc9ad6ed9f958072f9cbf4a34c4bbc2d5ef3e"
    assert data["observed"] == 10
    assert data["missing"] == 14
    assert data["full_p5_acceptance"] is False
    cells = data["cells"]
    assert len(cells) == 24
    assert len({(c["host"], c["agent"], c["case_id"]) for c in cells}) == 24
    assert Counter(c["status"] for c in cells)["not_observed"] == 14
    assert sum(c["agent"] == "codex" and c["real_model_trace"] for c in cells) == 6
    assert sum(c["agent"] == "pi" and c["real_model_trace"] for c in cells) == 4
    for cell in cells:
        assert cell["native_mod_runtime_verified"] is False
        if cell["real_model_trace"]:
            assert re.fullmatch(r"[a-f0-9]{64}", cell["evidence_sha256"])
            assert cell["model_provenance"] in (
                "same-thread-app-server-response+thread-read",
                "native-message_end",
            )
            assert cell["skill_loaded"] in (True, False)
        else:
            assert cell["evidence_sha256"] is None
            assert cell["skill_loaded"] is None


def test_no_private_identifiers_leak_from_public_p1_report() -> None:
    content = MATRIX.read_text() + "\n" + REPORT.read_text()
    assert not re.search(r"chatgpt\.com/c/[a-f0-9-]{36}", content, re.I)
    assert not re.search(r"/Users/[^/\s]+|/home/grammy-jiang/|/tmp/mods-p5-", content)
    assert "full_p5_acceptance" in content
    assert "boundary_scope_violated" in content
    assert "2.1.296" in content and "2.1.301" in content
