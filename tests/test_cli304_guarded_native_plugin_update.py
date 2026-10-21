"""Deterministic CLI304 candidate guard and QA-only same-host receipt boundaries."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scripts/guard_cli304_native_plugin.py"
FIXTURE = ROOT / "evals/fixtures/cli304-p1a-installed-20261021/market/plugins/qa-guard304-host"
_spec = importlib.util.spec_from_file_location("cli304_guarded_plugin_update", SOURCE)
assert _spec and _spec.loader
_gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_gate)


@pytest.fixture
def reviewed_qa(tmp_path: Path) -> tuple[Path, Path, str]:
    candidate = tmp_path / "qa-guard"
    shutil.copytree(FIXTURE, candidate)
    binary = tmp_path / "frozen-official-stub"
    binary.write_bytes(b"offline-validator-test-double-only")
    return candidate, binary, hashlib.sha256(binary.read_bytes()).hexdigest()


def test_preflight_requires_exact_tree_and_never_approves_running_host(monkeypatch, reviewed_qa):
    candidate, binary, binary_sha = reviewed_qa
    expected = _gate.inspect_tree(candidate)["content_tree_sha256"]
    commands: list[list[str]] = []

    def fake_validator(args, **kwargs):
        commands.append(args)
        assert args[1:4] == ["plugin", "validate", "--strict"]
        assert _gate.inspect_tree(Path(args[-1]))["content_tree_sha256"] == expected
        return subprocess.CompletedProcess(args, 0, "Validation passed", "")

    monkeypatch.setattr(_gate.subprocess, "run", fake_validator)
    result = _gate.preflight(
        candidate,
        binary,
        expected_tree_sha256=expected,
        expected_plugin_name="qa-guard304-host",
        expected_plugin_version="0.0.1",
        expected_native_sha256=binary_sha,
    )
    assert len(commands) == 1
    assert result["native_strict_validator_pass"] is True
    assert result["content_tree_sha256"] == expected
    assert result["active_host_guard_attested"] is False
    assert result["protected_session_ready"] is False
    assert result["stable_release_authorized"] is False


def test_preflight_rejects_unreviewed_tree_wrong_native_and_wrong_version(reviewed_qa):
    candidate, binary, binary_sha = reviewed_qa
    sha = _gate.inspect_tree(candidate)["content_tree_sha256"]
    options = dict(
        root=candidate,
        binary=binary,
        expected_tree_sha256=sha,
        expected_plugin_name="qa-guard304-host",
        expected_plugin_version="0.0.1",
        expected_native_sha256=binary_sha,
    )
    with pytest.raises(_gate.BlockedUpdate, match="OFFICIAL_NATIVE_BINARY_MISMATCH"):
        _gate.preflight(**(options | {"expected_native_sha256": "0" * 64}))
    with pytest.raises(_gate.BlockedUpdate, match="WRONG_PLUGIN_IDENTITY_OR_VERSION"):
        _gate.preflight(**(options | {"expected_plugin_version": "0.0.2"}))
    candidate.joinpath("hooks/register.js").write_text("export function wrong() {")
    with pytest.raises(_gate.BlockedUpdate, match="UNREVIEWED_PACKAGE_BYTES"):
        _gate.preflight(**options)


@pytest.mark.parametrize(
    ("return_code", "stdout", "stderr"),
    (
        (1, "Validation failed", "Unexpected token"),
        (0, "Validation passed\ngating hook without .catch", ""),
        (0, "Validation passed\nWarning: guard unprotected", ""),
        (0, "Nothing to validate", ""),
    ),
)
def test_preflight_rejects_native_validation_and_warning_even_with_zero_exit(
    monkeypatch, reviewed_qa, return_code, stdout, stderr
):
    candidate, binary, binary_sha = reviewed_qa

    def fake_validator(args, **kwargs):
        return subprocess.CompletedProcess(args, return_code, stdout, stderr)

    monkeypatch.setattr(_gate.subprocess, "run", fake_validator)
    with pytest.raises(_gate.BlockedUpdate, match="NATIVE_STRICT_PLUGIN_VALIDATION_FAILED"):
        _gate.preflight(
            candidate,
            binary,
            expected_tree_sha256=_gate.inspect_tree(candidate)["content_tree_sha256"],
            expected_plugin_name="qa-guard304-host",
            expected_plugin_version="0.0.1",
            expected_native_sha256=binary_sha,
        )


def test_host_orphan_cache_metadata_is_not_part_of_reviewed_candidate(reviewed_qa):
    candidate, _, _ = reviewed_qa
    source_sha = _gate.inspect_tree(candidate)["content_tree_sha256"]
    (candidate / ".orphaned_at").write_text("host-generated-state")
    with pytest.raises(_gate.BlockedUpdate, match="RUNTIME_CACHE_METADATA_IN_CANDIDATE"):
        _gate.inspect_tree(candidate)
    (candidate / ".orphaned_at").unlink()
    assert _gate.inspect_tree(candidate)["content_tree_sha256"] == source_sha


def test_preflight_rejects_symlink_and_toctou_mutations(monkeypatch, reviewed_qa):
    candidate, binary, binary_sha = reviewed_qa
    bad = candidate / "hooks/unsafe-link.js"
    bad.symlink_to(candidate / "hooks/register.js")
    with pytest.raises(_gate.BlockedUpdate, match="SYMLINK_IN_PLUGIN"):
        _gate.inspect_tree(candidate)
    bad.unlink()
    expected = _gate.inspect_tree(candidate)["content_tree_sha256"]

    def mutate_original_during_validation(args, **kwargs):
        (candidate / "hooks/register.js").write_text("export function changed() {}")
        return subprocess.CompletedProcess(args, 0, "Validation passed", "")

    monkeypatch.setattr(_gate.subprocess, "run", mutate_original_during_validation)
    with pytest.raises(_gate.BlockedUpdate, match="ORIGINAL_PACKAGE_CHANGED_DURING_VALIDATION"):
        _gate.preflight(
            candidate,
            binary,
            expected_tree_sha256=expected,
            expected_plugin_name="qa-guard304-host",
            expected_plugin_version="0.0.1",
            expected_native_sha256=binary_sha,
        )


def _synthetic_private_host(tmp_path: Path) -> tuple[dict, Path, Path, Path]:
    """Shape-only test fixture. NOT a real host record or release evidence."""
    installed = tmp_path / "installed"
    shutil.copytree(FIXTURE, installed)
    observed = _gate.inspect_tree(installed)
    reviewed = {
        "schema_version": 1,
        "target_cli": "2.1.304",
        "native_strict_validator_pass": True,
        **observed,
    }
    session = "00000000-0000-4000-8000-000000000001"
    events = [
        {
            "type": "system",
            "subtype": "init",
            "session_id": session,
            "claude_code_version": "2.1.304",
        },
        {
            "type": "result",
            "subtype": "success",
            "is_error": False,
            "num_turns": 0,
            "result": f"Prompt dropped by a hook: {_gate.QA_GUARD_MESSAGE}",
            "session_id": session,
        },
        {
            "type": "result",
            "subtype": "success",
            "is_error": False,
            "num_turns": 0,
            "result": "Reloaded: 1 plugin · 0 hooks",
            "session_id": session,
        },
        {
            "type": "assistant",
            "message": {"model": "claude-sonnet-5-5", "content": []},
            "session_id": session,
        },
        {
            "type": "result",
            "subtype": "success",
            "is_error": False,
            "num_turns": 1,
            "result": _gate.QA_MODEL_RESULT,
            "session_id": session,
        },
        {
            "type": "result",
            "subtype": "success",
            "is_error": False,
            "num_turns": 0,
            "result": "Reloaded: 1 plugin · 0 hooks",
            "session_id": session,
        },
        {
            "type": "result",
            "subtype": "success",
            "is_error": False,
            "num_turns": 0,
            "result": f"Prompt dropped by a hook: {_gate.QA_GUARD_MESSAGE}",
            "session_id": session,
        },
    ]
    wire = tmp_path / "synthetic-wire.jsonl"
    wire.write_text("\n".join(json.dumps(e) for e in events) + "\n")
    tag = f"hooks module {_gate.QA_PLUGIN_ID} loaded"
    debug = tmp_path / "synthetic-debug.log"
    debug.write_text(
        "\n".join(
            [
                tag,
                _gate.QA_HOOK_MARKER,
                "does not parse: Unexpected token; the version loaded before is unloaded",
                tag,
                f"plugin.register: {_gate.QA_PLUGIN_NAME} admitted",
                _gate.QA_HOOK_MARKER,
            ]
        )
        + "\n"
    )
    return reviewed, installed, wire, debug


def test_postflight_requires_same_host_sequence_and_fresh_registered_guard(tmp_path):
    receipt, installed, wire, debug = _synthetic_private_host(tmp_path)
    result = _gate.postflight(
        receipt, current_installed=installed, native_wire=wire, native_debug=debug
    )
    assert result["qa_recovery_guard_attested_in_this_session"] is True
    assert result["other_session_or_production_host_protected"] is False
    assert result["stable_release_authorized"] is False
    assert result["actual_native_result_turns"] == [0, 0, 1, 0, 0]


def test_postflight_rejects_wrong_session_wrong_order_missing_guard(tmp_path):
    receipt, installed, wire, debug = _synthetic_private_host(tmp_path)
    lines = [json.loads(x) for x in wire.read_text().splitlines()]
    lines[-1]["session_id"] = "00000000-0000-4000-8000-000000000002"
    wire.write_text("\n".join(json.dumps(x) for x in lines) + "\n")
    with pytest.raises(_gate.BlockedUpdate, match="NOT_ONE_NATIVE_SESSION"):
        _gate.postflight(receipt, current_installed=installed, native_wire=wire, native_debug=debug)
    lines[-1]["session_id"] = lines[0]["session_id"]
    lines[-1]["num_turns"] = 1
    wire.write_text("\n".join(json.dumps(x) for x in lines) + "\n")
    with pytest.raises(
        _gate.BlockedUpdate, match="ACTUAL_GUARD_LOSS_AND_RECOVERY_SEQUENCE_UNPROVEN"
    ):
        _gate.postflight(receipt, current_installed=installed, native_wire=wire, native_debug=debug)
    lines[-1]["num_turns"] = 0
    wire.write_text("\n".join(json.dumps(x) for x in lines) + "\n")
    debug.write_text(debug.read_text().replace("plugin.register:", "plugin.ignored:"))
    with pytest.raises(_gate.BlockedUpdate, match="RECOVERED_MOD_NOT_REGISTERED"):
        _gate.postflight(receipt, current_installed=installed, native_wire=wire, native_debug=debug)


def test_postflight_rejects_modified_installed_package_and_forged_preflight(tmp_path):
    receipt, installed, wire, debug = _synthetic_private_host(tmp_path)
    bogus = dict(receipt, native_strict_validator_pass=False)
    with pytest.raises(_gate.BlockedUpdate, match="REVIEWED_PREFLIGHT_RECEIPT_REQUIRED"):
        _gate.postflight(bogus, current_installed=installed, native_wire=wire, native_debug=debug)
    (installed / "hooks/register.js").write_text("export function wrong() {}")
    with pytest.raises(
        _gate.BlockedUpdate, match="ACTIVE_INSTALLED_PACKAGE_DOES_NOT_MATCH_PREFLIGHT"
    ):
        _gate.postflight(receipt, current_installed=installed, native_wire=wire, native_debug=debug)


def test_result_writer_does_not_overwrite_existing_receipts(tmp_path):
    out = tmp_path / "redacted.json"
    _gate._save_new(out, {"status": "blocked", "release": False})
    with pytest.raises(_gate.BlockedUpdate, match="EVIDENCE_OUTPUT_ALREADY_EXISTS"):
        _gate._save_new(out, {"status": "unsafe-override"})
