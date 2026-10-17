"""Privacy-safe static model-origin snippets: never execute them."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import audit_p5_generated_code_static as audit  # noqa: E402


def fenced(language: str, content: str) -> str:
    fence = chr(96) * 3
    return f"User-facing context\n{fence}{language}\n{content}\n{fence}\n"


def test_extract_bounded_fences_with_case_insensitive_languages() -> None:
    spans = audit.code_blocks(fenced("JS", "const x = 1;") + fenced("sh", "echo safe"))
    assert spans == [("js", "const x = 1;\n"), ("sh", "echo safe\n")]


def test_malformed_or_oversize_content_fails_closed() -> None:
    with pytest.raises(audit.StaticAuditBlocked):
        audit.code_blocks("")
    with pytest.raises(audit.StaticAuditBlocked):
        audit.code_blocks("x" * 200_001)
    with pytest.raises(audit.StaticAuditBlocked):
        audit.code_blocks(fenced("js", "x" * 65_537))


def test_javascript_check_is_not_execution_and_cannot_leak_code(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    exe = tmp_path / "node"
    exe.write_text("")
    seen = {}

    def pretend_run(args: list[str], **kw: object) -> SimpleNamespace:
        seen["args"] = args
        seen["kwargs"] = kw
        return SimpleNamespace(returncode=0, stderr="secret echoed in stderr")

    monkeypatch.setattr(audit.subprocess, "run", pretend_run)
    sample_code = "const user_secret_never_publish = 999;"
    assert audit.javascript_syntax_ok(sample_code, node=str(exe))
    assert seen["args"] == [str(exe), "--check", "--input-type=module"]
    kw = seen["kwargs"]
    assert kw["input"] == sample_code
    assert kw["capture_output"] is True
    assert kw["cwd"] == kw["env"]["HOME"]
    assert kw["env"]["NODE_OPTIONS"] == ""
    assert kw["timeout"] == 8
    assert "secret" not in json.dumps(audit.code_blocks(fenced("js", "const x = 1;")))


def test_syntax_failure_is_not_semantic_approval(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    exe = tmp_path / "node"
    exe.write_text("")
    monkeypatch.setattr(audit.subprocess, "run", lambda *_a, **_kw: SimpleNamespace(returncode=1))
    assert audit.javascript_syntax_ok("const =", node=str(exe)) is False


def test_no_raw_private_content_in_script_or_public_report() -> None:
    script = (ROOT / "scripts/audit_p5_generated_code_static.py").read_text()
    assert "exec(" not in script
    assert "eval(" not in script
    assert "shell=True" not in script
    assert "subprocess.run" in script


def test_published_report_contains_only_anonymized_static_metadata() -> None:
    report_path = ROOT / "docs/reports/2026-10-17-p5-codex-generated-code-static-audit.json"
    raw = report_path.read_text()
    report = json.loads(raw)
    assert report["observed_verified_native_answers"] == 12
    assert report["original_answer_sha256_verified"] == 12
    assert report["answers_with_fences"] == 6
    assert report["javascript_code_blocks"] == 6
    assert report["javascript_syntax_pass"] == 6
    assert report["javascript_syntax_fail"] == 0
    assert report["shell_code_blocks_not_executed"] == 3
    assert report["P3_blocked_code_reason"] == 6
    assert report["all_model_origin_code_executed"] is False
    assert report["native_mod_semantics_verified"] is False
    assert report["promote_production_skill_or_gate"] is False
    assert report["model_text_or_private_path_exported"] is False
    assert len(report["per_case_metadata"]) == 12
    for entry in report["per_case_metadata"]:
        assert set(entry) == {
            "case_id",
            "trial",
            "answer_sha256_verified",
            "code_fence_count",
            "javascript_fence_count",
            "javascript_syntax_pass",
            "javascript_syntax_fail",
            "shell_fence_count",
            "postflight_code_reason_present",
        }
    for forbidden in (
        "/Users/",
        "Models.noindex",
        ".codex/",
        "native-wire.jsonl",
        "threadId",
        "raw_answer",
        "original_prompt",
        "NODE_OPTIONS=",
    ):
        assert forbidden not in raw
