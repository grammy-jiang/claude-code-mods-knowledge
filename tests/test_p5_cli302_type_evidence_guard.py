"""Prove the new compiled Skill warning derives from genuine SSOT evidence."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from mods_knowledge.compiler import CompilerError, _verified_cli302_hook_type_note

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "evidence/cli302/hook_observer_typed_logging.json"
REPORT = ROOT / "docs/reports/2026-10-19-p5-cli302-original-code-core-type-audit.json"
NOTE_SHA = "9f04bd160de12b2d6ad6118f5ba11b3e043875677c3b39b80b45ca629d44177f"


def _staged_files(root: Path) -> tuple[Path, Path]:
    p = root / "evidence/cli302/hook_observer_typed_logging.json"
    q = root / "docs/reports/2026-10-19-p5-cli302-original-code-core-type-audit.json"
    p.parent.mkdir(parents=True)
    q.parent.mkdir(parents=True)
    shutil.copyfile(SOURCE, p)
    shutil.copyfile(REPORT, q)
    return p, q


def test_verified_advisory_is_pinned_to_original_model_type_failures():
    row = json.loads(SOURCE.read_text())
    report = json.loads(REPORT.read_text())
    assert row["advisory_note_sha256"] == NOTE_SHA
    assert hashlib.sha256(row["advisory_skill_markdown"].encode()).hexdigest() == NOTE_SHA
    assert row["reviewed_native_core_sha256"] == report["core_declarations_sha256"]
    assert row["original_model_type_failures"] == report["original_fail"] == 3
    assert row["test_only_proposed_fix_typecheck_passes"] == 5
    assert row["not_an_approved_api_claim"] is True


@pytest.mark.parametrize(
    "tamper",
    (
        "missing_report",
        "fake_core",
        "fake_failures",
        "fake_type_fix",
        "edited_note",
        "fake_schema_completeness",
    ),
)
def test_compiler_refuses_unreviewed_cli302_type_evidence(tmp_path: Path, tamper: str):
    p, q = _staged_files(tmp_path)
    row = json.loads(p.read_text())
    if tamper == "missing_report":
        q.unlink()
    elif tamper == "fake_core":
        row["reviewed_native_core_sha256"] = "0" * 64
    elif tamper == "fake_failures":
        row["original_model_type_failures"] = 0
    elif tamper == "fake_type_fix":
        row["test_only_proposed_fix_typecheck_passes"] = 4
    elif tamper == "edited_note":
        row["advisory_skill_markdown"] = row["advisory_skill_markdown"].replace(
            "Typecheck against target", "Never typecheck against target"
        )
    elif tamper == "fake_schema_completeness":
        row["complete_runtime_generated_builtin_tool_schema_verified"] = True
    p.write_text(json.dumps(row))
    with pytest.raises(CompilerError):
        _verified_cli302_hook_type_note(tmp_path, version="2.1.302", surface="cli")


def test_unreviewed_303_and_historical_296_never_reuse_cli302_type_note(tmp_path: Path):
    assert _verified_cli302_hook_type_note(tmp_path, version="2.1.303", surface="cli") is None
    assert _verified_cli302_hook_type_note(tmp_path, version="2.1.296", surface="cli") is None
