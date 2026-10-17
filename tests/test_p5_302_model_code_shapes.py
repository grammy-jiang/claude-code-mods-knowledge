"""Model-origin examples must be classified without executing unknown snippets."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import audit_p5_302_model_code_shapes as audit  # noqa: E402


def test_two_reviewed_source_shapes_only() -> None:
    assert len(audit._SHAPES) == 2
    transparent = "on('tool.call', async ($, e, next) => {return next(e);});"
    safe_logger = (
        "on('tool.call',async ($,e,next)=>{try{return await next(e);}"
        "finally{try{await Promise.resolve(console.log('observer done'));}catch{}}});"
    )
    assert audit._SHAPES[audit.normalized(transparent)] == "direct_transparent_observer"
    assert audit._SHAPES[audit.normalized(safe_logger)] == "async_fail_isolated_observer"
    with pytest.raises(ValueError):
        audit.normalized("/* unknown */\non('tool.call', () => {})")
    assert audit._SHAPES.get(audit.normalized("on('tool.call', () => { process.exit(1) })")) is None


def test_supported_command_shapes_not_arbitrary_shell() -> None:
    assert len(audit.COMMANDS) == 3
    assert ("claude", "plugin", "test", "./my-mod") in audit.COMMANDS
    assert ("bash", "-lc", "curl example.com") not in audit.COMMANDS


def test_all_54_original_positive_model_snippet_report_is_redacted_and_bounded() -> None:
    file = ROOT / "docs/reports/2026-10-18-claude302-original-model-code-shapes.json"
    raw = file.read_text()
    j = json.loads(raw)
    assert j["target_cli"] == "2.1.302"
    assert j["original_positive_answers_sha256_verified"] == 54
    assert j["generated_javascript_code_blocks"] == 23
    assert j["direct_transparent_observer_blocks"] == 9
    assert j["async_fail_isolated_observer_blocks"] == 14
    assert j["model_generated_shell_command_blocks"] == 19
    assert j["unknown_code_blocks"] == 0
    assert j["representative_original_observer_patterns_native_tested"] == 2
    assert j["native_mocked_outcome_tests_per_pattern_passed"] == 3
    assert j["direct_identity_error_once_tests_per_pattern_passed"] == 6
    assert j["generated_shell_command_shapes_checked_against_native_cli"] == 3
    assert j["all_generated_answers_production_semantics_certified"] is False
    assert j["model_private_original_text_exported"] is False
    assert len(j["case_metadata_only"]) == 54
    for row in j["case_metadata_only"]:
        assert set(row) == {"arm", "case", "trial", "code_blocks"}
        for kind, items in row["code_blocks"].items():
            assert kind in ("javascript", "shell", "other")
            for item in items:
                assert set(item) in ({"sha256", "reviewed_shape"}, {"sha256", "shape"})
    for forbidden in ("/Users/", "/home/", "Models.noindex", "conversation_id", "model_reply"):
        assert forbidden not in raw
