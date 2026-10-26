"""Scoped, account-free prompt preparation; never claim native auto-selection."""

from pathlib import Path

import pytest

from mods_knowledge.claims import approved_claims, load_claims
from mods_knowledge.registry import load_registry

ROOT = Path(__file__).resolve().parents[1]


def _implementation():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "p4_controlled_prompt", ROOT / "scripts/prepare_p4_explicit_mods_request.py"
    )
    assert spec and spec.loader
    script = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(script)
    return script


def test_scope_matched_original_approved_302_and_text_directed_output(tmp_path):
    app = _implementation()
    input_file = tmp_path / "task.private.txt"
    question = "How should a Claude Code Mod tool.call observer preserve next(e)?\n"
    input_file.write_text(question)
    out = tmp_path / "selected-plugin.private.txt"
    report = app.create_private_request(input_file, out, target="2.1.302", root=ROOT)
    result = out.read_text()
    assert result == app.TESTED_PREFIX + question
    assert result.endswith(question)
    assert out.stat().st_mode & 0o777 == 0o600
    assert report["source_target_cli"] == "2.1.302"
    assert report["adds_explicit_plugin_use_request"] is True
    assert report["composer_system_hint_added"] is False
    assert report["counts_as_native_model_auto_routing"] is False
    assert report["actually_sent_to_chatgpt"] is False
    assert report["stable_release_authorized"] is False


@pytest.mark.parametrize("version", ["latest", "2.1.309", "2.1.310", "2.1.296"])
def test_wrong_cli_target_never_inherits_302_approved_package(version):
    script = _implementation()
    with pytest.raises(script.ScopeRequestBlocked, match="NO_APPROVED_TARGET"):
        script.compose("Claude Code Mod hook", target_version=version, approved_count=31)


def test_no_content_unknown_approval_or_binary_rejected():
    s = _implementation()
    with pytest.raises(s.ScopeRequestBlocked, match="APPROVED_TARGET"):
        s.compose("mod", target_version="2.1.302", approved_count=0)
    for text in ("", "  ", "x" * 13000, "alpha\x00beta"):
        with pytest.raises(s.ScopeRequestBlocked, match="INVALID_OR_UNBOUNDED"):
            s.compose(text, target_version="2.1.302", approved_count=31)


def test_existing_target_file_never_overwritten(tmp_path):
    script = _implementation()
    task = tmp_path / "input.private.txt"
    task.write_text("Claude Code Mods")
    out = tmp_path / "output.private.txt"
    out.write_text("MUST_PRESERVE")
    with pytest.raises(script.ScopeRequestBlocked, match="OUTPUT_ALREADY_EXISTS"):
        script.create_private_request(task, out, target="2.1.302", root=ROOT)
    assert out.read_text() == "MUST_PRESERVE"


def test_preparer_matches_exact_previous_real_successful_text_only_prompt_sha():
    import hashlib
    import json

    script = _implementation()
    suite = json.loads((ROOT / "evals/p4_cases_cli_2_1_302.json").read_text())
    original = next(case["prompt"] for case in suite["cases"] if case["id"] == "POS-E-01")
    prepared = script.compose(original, target_version="2.1.302", approved_count=31)
    assert hashlib.sha256(prepared.encode()).hexdigest() == (
        "111860da7401d14d63f56b6c3af679bab6e5e15e4c96d6ae76066a4848e9c78a"
    )
    assert prepared.endswith(original)


def test_approved_claims_do_exist_on_302_but_not_latest():
    root = ROOT
    registry = load_registry(root / "sources/registry.json")
    claims = load_claims(root / "claims", registry, root / "sources/snapshots", root / "decisions")
    assert len(approved_claims(claims, "2.1.302", "cli")) == 31
    assert not approved_claims(claims, "2.1.310", "cli")


def test_symlink_target_is_not_overwritten(tmp_path):
    script = _implementation()
    p = tmp_path / "input.private.txt"
    p.write_text("Claude Code Mods tool.call")
    actual = tmp_path / "secret.txt"
    actual.write_text("ORIGINAL")
    link = tmp_path / "output.private.txt"
    link.symlink_to(actual)
    with pytest.raises(script.ScopeRequestBlocked):
        script.create_private_request(p, link, target="2.1.302", root=ROOT)
    assert actual.read_text() == "ORIGINAL"


def test_export_to_git_project_root_is_blocked(tmp_path):
    script = _implementation()
    task = tmp_path / "input.private.txt"
    task.write_text("Claude Code Mods")
    out = ROOT / "uncommitted-user-question.private.txt"
    assert not out.exists()
    with pytest.raises(script.ScopeRequestBlocked, match="REFUSE_STORING"):
        script.create_private_request(task, out, target="2.1.302", root=ROOT)
    assert not out.exists()
