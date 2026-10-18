"""Exact native Codex/Sonnet model snippets are SHA-verified and sandbox-only.

Never import/execute model-origin modules in pytest. Real behavioral
execution is limited to a separately invoked Bubblewrap OS sandbox on Pi,
with network unshared. Ordinary CI verifies provenance and staging only.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from audit_p5_original_model_code import (  # noqa: E402
    CANDIDATE_FILENAMES,
    CODE_FILES,
    EXPECTED,
    FIXTURES,
    ModelCodeEvidenceBlocked,
    stage,
    validate_manifest,
)
from run_p5_model_code_sandbox import (  # noqa: E402
    ModelCodeSandboxBlocked,
    _test_counts,
    sandbox_argv,
)


def _copy_source(root: Path) -> None:
    shutil.copytree(FIXTURES, root)


def test_five_real_model_blocks_exact_hash_and_model_identity() -> None:
    original = validate_manifest()
    assert original["reviewed_claude_cli"] == "2.1.302"
    assert original["tests_do_not_grant_actual_claude_mods_host_acceptance"] is True
    assert set(CANDIDATE_FILENAMES) == CODE_FILES
    assert len(EXPECTED) == 5
    for path, expected in EXPECTED.items():
        assert hashlib.sha256((FIXTURES / path).read_bytes()).hexdigest() == expected
    c, e, q = original["model_candidate_sources"]
    assert c["native_agent"] == "codex-cli 0.163.0"
    assert c["requested_model"] == "gpt-6.1-sol"
    assert c["requested_effort"] == "medium"
    assert c["model_identity_in_wire_independently_attested"] is False
    assert e["case_id"] == "POS-E-01"
    assert len(e["source"]["blocks"]) == 3
    assert q["case_id"] == "POS-Q-01"
    assert q["source"]["blocks"][0]["is_shell_command_not_mod_code"] is True
    assert q["source"]["blocks"][0]["fixture_path"] is None


def test_staged_five_candidates_wrap_only_two_noninstallable_fragments(
    tmp_path: Path,
) -> None:
    dest = tmp_path / "sandbox-only"
    report = stage(FIXTURES, dest)
    assert report["original_reviewed_source_files"] == 5
    assert report["full_module_candidates"] == 3
    assert report["synthetic_fragment_wrapper_candidates"] == 2
    assert report["shell_documentation_examples_not_executed"] == 1
    assert report["actual_claude_mod_host_runtime_tested"] is False
    assert report["model_code_run_on_host_without_sandbox"] is False
    rows = report["per_case"]
    assert len(rows) == 5
    for item in rows:
        source = (FIXTURES / item["model_code_fixture"]).read_bytes()
        staged = (dest / "candidates" / item["sandbox_module_name"]).read_bytes()
        assert item["source_code_sha256"] == hashlib.sha256(source).hexdigest()
        assert item["sandbox_module_sha256"] == hashlib.sha256(staged).hexdigest()
        assert staged.decode().lstrip().startswith("export function register(on)")
        assert item["syntax_checked_only_not_type_or_production_certified"] is True
    assert {x["model_code_fixture"] for x in rows if x["requires_test_only_register_wrapper"]} == {
        "sonnet/01-fragment.js",
        "sonnet/02-fragment.js",
    }
    with pytest.raises(ModelCodeEvidenceBlocked, match="replace"):
        stage(FIXTURES, dest)


def test_modification_of_any_real_model_block_invalidates_original_sha(
    tmp_path: Path,
) -> None:
    fixture = tmp_path / "fixture"
    _copy_source(fixture)
    file = fixture / "codex/01.mjs"
    file.write_text(file.read_text().replace("return next(e)", "return { changed: true }"))
    with pytest.raises(ModelCodeEvidenceBlocked, match="mutated"):
        validate_manifest(fixture)


def test_injected_fs_network_process_api_never_reaches_sandbox(
    tmp_path: Path,
) -> None:
    fixture = tmp_path / "fixture"
    _copy_source(fixture)
    file = fixture / "sonnet/03-module.js"
    file.write_text(file.read_text() + "\nprocess.env.SECRET;\n")
    manifest_file = fixture / "manifest.json"
    manifest = json.loads(manifest_file.read_text())
    wrong = hashlib.sha256(file.read_bytes()).hexdigest()
    for item in manifest["model_candidate_sources"][1]["source"]["blocks"]:
        if item["fixture_path"] == "sonnet/03-module.js":
            item["code_sha256"] = wrong
    manifest_file.write_text(json.dumps(manifest))
    # The fixed, reviewed source hash is separate from the mutable manifest.
    with pytest.raises(ModelCodeEvidenceBlocked):
        validate_manifest(fixture)


@pytest.mark.parametrize(
    "tap",
    (
        "TAP version 13\n# tests 50\n# pass 49\n# fail 1\n",
        "TAP version 13\n# tests 50\n# pass 50\n",
        "TAP version 13\n# tests 50\n# tests 50\n# pass 50\n# fail 0\n",
        "TAP version 13\n# tests fifty\n# pass 50\n# fail 0\n",
    ),
)
def test_incomplete_or_ambiguous_tap_cannot_be_reported_as_success(tap: str) -> None:
    if tap.count("# tests 50") == 1 and "# pass 49" in tap:
        assert _test_counts(tap) == (50, 49, 1)
    else:
        with pytest.raises(ModelCodeSandboxBlocked):
            _test_counts(tap)


def test_bwrap_argv_never_mounts_host_home_or_shares_network(tmp_path: Path) -> None:
    fake_node = tmp_path / "node-v24.19.0"
    fake_node.mkdir()
    work = tmp_path / "work"
    work.mkdir()
    cmd = sandbox_argv(
        Path("/usr/bin/bwrap"),
        fake_node,
        work,
        ["/runtime/bin/node", "--test", "/tests/observer-contract.test.mjs"],
    )
    assert cmd[0] == "/usr/bin/bwrap"
    assert "--unshare-all" in cmd
    assert "--share-net" not in cmd
    assert "--clearenv" in cmd
    assert "--die-with-parent" in cmd
    assert "--proc" in cmd and "--dev" in cmd
    assert "--tmpfs" in cmd
    assert cmd[cmd.index("--chdir") + 1] == "/work"
    pairs = [
        (cmd[i + 1], cmd[i + 2]) for i, token in enumerate(cmd) if token in ("--ro-bind", "--bind")
    ]
    assert ("/usr", "/usr") in pairs
    assert (str(fake_node.resolve()), "/runtime") in pairs
    assert (str(FIXTURES.resolve()), "/tests") in pairs
    assert (str(work.resolve()), "/work") in pairs
    assert not any(host in ("/", "/home", "/root", "/etc", "/mnt") for host, _ in pairs)
    assert cmd[-3:] == [
        "/runtime/bin/node",
        "--test",
        "/tests/observer-contract.test.mjs",
    ]


def test_missing_bwrap_never_falls_back_to_host_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import run_p5_model_code_sandbox as isolated

    monkeypatch.setattr(isolated.shutil, "which", lambda name: None)
    with pytest.raises(ModelCodeSandboxBlocked, match="Bubblewrap missing"):
        isolated.audit(timeout=20)


def test_original_provenance_is_not_synthetically_a_real_host_code_pass() -> None:
    report = validate_manifest()
    assert report["no_generated_code_has_been_run_on_production_host"] is True
    assert report["tests_do_not_grant_actual_claude_mods_host_acceptance"] is True


def test_model_code_behavior_requires_pinned_tap_and_negative_control() -> None:
    import inspect

    import run_p5_model_code_sandbox as runner

    implementation = inspect.getsource(runner.audit)
    assert "--test-reporter=tap" in implementation
    assert "tested != 48" in implementation
    assert "synthetic_corrupt_downstream_observer_detected" in implementation
    assert "on('tool.call', async ($,e,next)=>({fake:true}))" in implementation
    assert _test_counts("# tests 48\n# pass 48\n# fail 0\n") == (48, 48, 0)
    # Earlier Node 24 default "spec" output is intentionally NOT accepted
    # unless the child process is explicitly forced to TAP.
    with pytest.raises(ModelCodeSandboxBlocked):
        _test_counts("ℹ tests 48\nℹ pass 48\nℹ fail 0\n")


def test_test_harness_is_checked_and_not_a_sonnet_or_codex_model_block() -> None:
    from run_p5_model_code_sandbox import HARNESS

    text = HARNESS.read_text()
    assert HARNESS.name == "observer-contract.test.mjs"
    assert "file:///work/candidates/" in text
    assert "original downstream" in text
    assert "asynchronous logger rejection" in text
    assert "synchronous diagnostic throw" in text
    assert "node:assert/strict" in text
    assert "node:test" in text
    assert "child_process" not in text
    assert "globalThis" not in text
    assert "fetch(" not in text
