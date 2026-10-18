"""CLI302 embedded official type proof: exact model code and honest failures.

CI does not contain the closed-source CLI binary, never reconstructs
or publishes proprietary .d.ts, and never runs model-generated JS.
The true native typecheck is separately verified on Raspberry Pi.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from audit_p5_cli302_native_code_types import (  # noqa: E402
    EXPECTED_TYPE_ERRORS,
    CoreTypeAuditBlocked,
    _stage,
    parse_diagnostics,
)
from extract_reviewed_cli302_core_types import (  # noqa: E402
    DECLARATION_SHA256,
    OFFICIAL_NATIVE_BINARIES,
    CliTypesBlocked,
    verify_core,
)


def test_official_native_core_decl_requires_exact_arch_independent_sha() -> None:
    assert DECLARATION_SHA256 == "8afa71883ecfa52901eb7a04cf31fef700d8ba565eaad244f4884cc620f8d56e"
    assert OFFICIAL_NATIVE_BINARIES == {
        "5262ce9de86243fed0d21edc39b271555d56780d0112e2b194439fe1c6662d37",
        "2bd4f4e5ed5cb09955b490098f745321cb5491e7ea8c752ba1e3bb010cdadb10",
    }
    with pytest.raises(CliTypesBlocked):
        verify_core(b"declare module 'claude-code' { export type Register = any }")


def test_type_stage_preserves_five_original_model_sha_and_two_wrappers(tmp_path: Path) -> None:
    original = _stage(
        tmp_path / "original", declarations=b"synthetic-non-authoritative", repair=False
    )
    fixed = _stage(tmp_path / "suggested", declarations=b"synthetic-non-authoritative", repair=True)
    assert len(original["files"]) == len(fixed["files"]) == 5
    assert sum(x["fragment_wrapped_for_test_only"] for x in original["files"]) == 2
    assert not any(x["proposed_diagnostic_uses_ui_log"] for x in original["files"])
    assert sum(x["proposed_diagnostic_uses_ui_log"] for x in fixed["files"]) == 3
    for a, b in zip(original["files"], fixed["files"], strict=True):
        assert a["source_name"] == b["source_name"]
        assert a["original_model_code_sha256"] == b["original_model_code_sha256"]
        assert (
            a["original_model_code_sha256"]
            == hashlib.sha256(
                (ROOT / "evals/fixtures/p5-native-model-code-302" / a["source_name"]).read_bytes()
            ).hexdigest()
        )
    config = json.loads((tmp_path / "original/tsconfig.json").read_text())
    assert config["compilerOptions"]["noEmit"] is True
    assert config["compilerOptions"]["checkJs"] is True
    assert config["compilerOptions"]["types"] == []
    assert config["compilerOptions"]["lib"] == ["es2023"]
    assert "dom" not in config["compilerOptions"]["lib"]


def test_original_three_console_diagnostics_are_not_falsely_accepted() -> None:
    lines = [
        f"hooks/{name}(7,31): error TS2584: Cannot find name 'console'. "
        "Do you need to change your target library?"
        for name in EXPECTED_TYPE_ERRORS
    ]
    rows = parse_diagnostics("\n".join(lines))
    assert len(rows) == 3
    assert {x["file"]: x["code"] for x in rows} == EXPECTED_TYPE_ERRORS
    assert all(x["description_signal"] == "unknown_console_global" for x in rows)


@pytest.mark.parametrize(
    "bad",
    (
        "some arbitrary success message",
        "hooks/codex-02.mjs(1,2): error TS2322: Wrong type\nSome extra line",
        "ERR: no TypeScript compiler here",
    ),
)
def test_unrecognized_compiler_output_never_becomes_source_pass(bad: str) -> None:
    with pytest.raises(CoreTypeAuditBlocked):
        parse_diagnostics(bad)


def test_type_auditor_must_not_claim_live_host_or_unsafe_execution() -> None:
    body = (ROOT / "scripts/audit_p5_cli302_native_code_types.py").read_text()
    for marker in (
        "noEmit",
        "checkJs",
        "runtime_generated_builtin_tool_type_merge_verified",
        "stable_release_authorized",
        "original_model_code_executed_during_typecheck",
        "console.log",
        "$.ui.log",
        "2.1.277",
    ):
        assert marker in body
