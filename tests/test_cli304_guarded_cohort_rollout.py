"""P1-D1..D4: deterministic cross-process, fail-closed *managed-only* QA controls."""

from __future__ import annotations

import json
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from mods_knowledge.guarded_rollout import (
    GuardedRollout,
    UpdateBlocked,
    fixture_verifier_for_tests_only,
    installed_tree,
    run_isolated_qa_update,
    verified_candidate,
)

ROOT = Path(__file__).resolve().parents[1]
GOOD = ROOT / "evals/fixtures/cli304-p1a-installed-20261021/market/plugins/qa-guard304-host"


@pytest.fixture
def fixture(tmp_path: Path, monkeypatch):
    good = tmp_path / "v001"
    shutil.copytree(GOOD, good)
    newer = tmp_path / "v002"
    shutil.copytree(good, newer)
    manifest = newer / ".claude-plugin/plugin.json"
    d = json.loads(manifest.read_text())
    d["version"] = "0.0.2"
    manifest.write_text(json.dumps(d) + "\n")
    source = newer / "hooks/register.js"
    source.write_text(source.read_text().replace("QA304_GUARD_ENTRY", "QA304_GUARD_V002"))
    installed = tmp_path / "installed"
    shutil.copytree(good, installed)
    native = tmp_path / "official-test-double"
    native.write_bytes(b"fake official binary for deterministic CI only")

    def fake_validator(args, **kwargs):
        assert args[1:4] == ["plugin", "validate", "--strict"]
        assert installed_tree(Path(args[-1]))["sha"] == installed_tree(newer)["sha"]
        return subprocess.CompletedProcess(args, 0, "Validation passed", "")

    monkeypatch.setattr("mods_knowledge.guarded_rollout.subprocess.run", fake_validator)
    import hashlib

    native_sha = hashlib.sha256(native.read_bytes()).hexdigest()
    clock = [1000.0]
    gate = GuardedRollout(tmp_path / "gate", clock=lambda: clock[0], ttl=120)
    gate.create(["s-a", "s-b"], good_version="0.0.1", good_tree=installed_tree(good)["sha"])
    secrets = {session: gate.enroll(session) for session in ("s-a", "s-b")}

    def prove(session, challenge):
        path = tmp_path / f"qa-proof-{session}-{challenge['epoch']}-{challenge['challenge']}.json"
        path.write_text(
            json.dumps(
                {
                    "session": session,
                    "challenge": challenge["challenge"],
                    "tree": challenge["tree_sha"],
                    "epoch": challenge["epoch"],
                    "TEST_ONLY": True,
                }
            )
        )
        return path

    for session, secret in secrets.items():
        gate.attest(
            session,
            secret,
            prove(session, gate.challenge(session, secret)),
            verifier=fixture_verifier_for_tests_only,
        )
    gate.ready()
    return {
        "gate": gate,
        "secrets": secrets,
        "prove": prove,
        "good": good,
        "new": newer,
        "installed": installed,
        "native": native,
        "native_sha": native_sha,
        "clock": clock,
        "tmp": tmp_path,
    }


def copy_plugin(source: Path, installed: Path):
    shutil.rmtree(installed)
    shutil.copytree(source, installed)


def begin_quiescence(f):
    gate = f["gate"]
    gate.begin(
        transaction_id="test-txn-123",
        new_version="0.0.2",
        new_tree=installed_tree(f["new"])["sha"],
    )
    for session, secret in f["secrets"].items():
        gate.acknowledge(session, secret)


def run(f, **kw):
    return run_isolated_qa_update(
        f["gate"],
        participant_secrets=f["secrets"],
        candidate=f["new"],
        old_source=f["good"],
        installed=f["installed"],
        native_binary=f["native"],
        plugin_name="qa-guard304-host",
        expected_binary_sha=f["native_sha"],
        apply=copy_plugin,
        restore=copy_plugin,
        request_health=lambda s, c: f["prove"](s, c),
        verify_health=fixture_verifier_for_tests_only,
        **kw,
    )


def test_not_enrolled_invalid_token_and_replayed_challenge_denied(fixture):
    f = fixture
    gate = f["gate"]
    with pytest.raises(UpdateBlocked, match="UNREGISTERED_OR_UNAUTHORIZED"):
        gate.enter("s-a", "made-up-secret")
    with pytest.raises(UpdateBlocked, match="UNREGISTERED_OR_UNAUTHORIZED"):
        gate.enter("unknown", f["secrets"]["s-a"])
    challenge = gate.challenge("s-a", f["secrets"]["s-a"])
    # The verified bootstrap challenge must be single-use.
    assert challenge["challenge"] == ""
    with pytest.raises(UpdateBlocked, match="NOT_ATTESTING"):
        gate.attest(
            "s-a",
            f["secrets"]["s-a"],
            f["prove"]("s-a", challenge),
            verifier=fixture_verifier_for_tests_only,
        )


def test_exact_inventory_and_active_operation_drain_before_any_apply(fixture):
    f = fixture
    gate = f["gate"]
    permit = gate.enter("s-a", f["secrets"]["s-a"])
    gate.begin(
        transaction_id="t1",
        new_version="0.0.2",
        new_tree=installed_tree(f["new"])["sha"],
    )
    with pytest.raises(UpdateBlocked, match="PROTECTED_ACTION_FROZEN"):
        gate.enter("s-b", f["secrets"]["s-b"])
    with pytest.raises(UpdateBlocked, match="INFLIGHT_PROTECTED_OP"):
        gate.acknowledge("s-a", f["secrets"]["s-a"])
    gate.acknowledge("s-b", f["secrets"]["s-b"])
    with pytest.raises(UpdateBlocked, match="NOT_ALL_SESSIONS_QUIESCED"):
        gate.start_apply(
            candidate=f["new"],
            native_binary=f["native"],
            plugin_name="qa-guard304-host",
            expected_native_sha=f["native_sha"],
        )
    gate.leave("s-a", f["secrets"]["s-a"], permit)
    gate.acknowledge("s-a", f["secrets"]["s-a"])
    receipt = gate.start_apply(
        candidate=f["new"],
        native_binary=f["native"],
        plugin_name="qa-guard304-host",
        expected_native_sha=f["native_sha"],
    )
    assert receipt["version"] == "0.0.2"
    assert gate.status()["phase"] == "applying"
    assert gate.status()["outstanding_permits"] == 0


def test_guarded_two_participant_happy_path_never_unfreezes_early(fixture):
    f = fixture
    begin_quiescence(f)
    gate = f["gate"]
    attempted = []

    def updater(src, dst):
        for session in f["secrets"]:
            with pytest.raises(UpdateBlocked, match="PROTECTED_ACTION_FROZEN"):
                gate.enter(session, f["secrets"][session])
        attempted.append("all_session_actions_fenced")
        copy_plugin(src, dst)

    result = run_isolated_qa_update(
        gate,
        participant_secrets=f["secrets"],
        candidate=f["new"],
        old_source=f["good"],
        installed=f["installed"],
        native_binary=f["native"],
        plugin_name="qa-guard304-host",
        expected_binary_sha=f["native_sha"],
        apply=updater,
        restore=copy_plugin,
        request_health=lambda s, c: f["prove"](s, c),
        verify_health=fixture_verifier_for_tests_only,
    )
    assert result["outcome"] == "candidate_healthy_in_managed_cohort_only"
    assert attempted == ["all_session_actions_fenced"]
    assert gate.status()["phase"] == "ready"
    for session, secret in f["secrets"].items():
        permit = gate.enter(session, secret)
        gate.leave(session, secret, permit)
    assert installed_tree(f["installed"]) == installed_tree(f["new"])
    assert result["non_cooperative_sessions_protected"] is False


def test_failed_candidate_health_rolls_back_then_requires_all_old_health(fixture):
    f = fixture
    begin_quiescence(f)
    candidate_sha = installed_tree(f["new"])["sha"]

    def probe(s, challenge):
        if challenge["tree_sha"] == candidate_sha and s == "s-b":
            raise UpdateBlocked("SIMULATED_HOST_DROPPED_HOOK")
        return f["prove"](s, challenge)

    result = run_isolated_qa_update(
        f["gate"],
        participant_secrets=f["secrets"],
        candidate=f["new"],
        old_source=f["good"],
        installed=f["installed"],
        native_binary=f["native"],
        plugin_name="qa-guard304-host",
        expected_binary_sha=f["native_sha"],
        apply=copy_plugin,
        restore=copy_plugin,
        request_health=probe,
        verify_health=fixture_verifier_for_tests_only,
    )
    assert result["outcome"] == "candidate_rejected_old_version_recovered_in_managed_cohort"
    assert installed_tree(f["installed"]) == installed_tree(f["good"])
    assert f["gate"].status()["phase"] == "ready"
    assert f["gate"].status()["verified"] == 2


def test_partial_session_failure_and_rollback_failure_permanently_block(fixture):
    f = fixture
    begin_quiescence(f)

    def failed_rollback(_old, _dest):
        raise OSError("simulated disk failure restoring old bytes")

    result = run_isolated_qa_update(
        f["gate"],
        participant_secrets=f["secrets"],
        candidate=f["new"],
        old_source=f["good"],
        installed=f["installed"],
        native_binary=f["native"],
        plugin_name="qa-guard304-host",
        expected_binary_sha=f["native_sha"],
        apply=copy_plugin,
        restore=failed_rollback,
        request_health=lambda *_: (_ for _ in ()).throw(UpdateBlocked("host offline")),
        verify_health=fixture_verifier_for_tests_only,
    )
    assert result["outcome"] == "blocked_requires_manual_recovery"
    assert f["gate"].status()["phase"] == "blocked"
    with pytest.raises(UpdateBlocked, match="PROTECTED_ACTION_FROZEN"):
        f["gate"].enter("s-a", f["secrets"]["s-a"])
    with pytest.raises(UpdateBlocked, match="FAILED_COHORT_REQUIRES"):
        f["gate"].ready()


def test_crash_after_candidate_apply_is_durable_blocked_across_new_process(fixture):
    f = fixture
    begin_quiescence(f)
    f["gate"].start_apply(
        candidate=f["new"],
        native_binary=f["native"],
        plugin_name="qa-guard304-host",
        expected_native_sha=f["native_sha"],
    )
    copy_plugin(f["new"], f["installed"])
    f["gate"].candidate_applied(installed=f["installed"])
    # Simulate controller process dying: reopen state from a separate object.
    recovering = GuardedRollout(f["gate"].directory, clock=lambda: f["clock"][0])
    assert recovering.status()["phase"] == "verifying"
    for session, secret in f["secrets"].items():
        with pytest.raises(UpdateBlocked, match="PROTECTED_ACTION_FROZEN"):
            recovering.enter(session, secret)
    recovering.fail_closed("CRASH_UNKNOWN_SESSION_STATE")
    assert recovering.status()["phase"] == "blocked"


def test_expired_session_refuses_tool_and_update(fixture):
    f = fixture
    f["clock"][0] += 121
    with pytest.raises(UpdateBlocked, match="SESSION_LEASE_EXPIRED"):
        f["gate"].enter("s-a", f["secrets"]["s-a"])
    with pytest.raises(UpdateBlocked, match="SESSION_LEASE_EXPIRED"):
        f["gate"].begin(
            transaction_id="t1", new_version="0.0.2", new_tree=installed_tree(f["new"])["sha"]
        )
    # One refreshed session does not imply all sessions have recovered.
    f["gate"].heartbeat("s-a", f["secrets"]["s-a"])
    with pytest.raises(UpdateBlocked, match="SESSION_LEASE_EXPIRED"):
        f["gate"].enter("s-a", f["secrets"]["s-a"])


def test_rejects_source_symlinks_and_preflight_binary_mismatch(fixture):
    f = fixture
    (f["new"] / "hooks/unsafe.js").symlink_to(f["new"] / "hooks/register.js")
    with pytest.raises(UpdateBlocked, match="PLUGIN_SYMLINK_FORBIDDEN"):
        installed_tree(f["new"])
    (f["new"] / "hooks/unsafe.js").unlink()
    with pytest.raises(UpdateBlocked, match="OFFICIAL_NATIVE_BINARY_MISMATCH"):
        verified_candidate(
            f["new"],
            f["native"],
            expected_tree=installed_tree(f["new"])["sha"],
            expected_version="0.0.2",
            expected_name="qa-guard304-host",
        )


@pytest.mark.parametrize(
    ("exit", "stdout", "stderr"),
    [
        (1, "Validation failed", "Unexpected token"),
        (0, "Validation passed\ngating hook without .catch", ""),
        (0, "Validation passed\nWarning: unsafe", ""),
        (0, "No checks performed", ""),
    ],
)
def test_native_validator_rejects_invalid_source_even_on_exit_zero(
    fixture, monkeypatch, exit, stdout, stderr
):
    f = fixture
    monkeypatch.setattr(
        "mods_knowledge.guarded_rollout.subprocess.run",
        lambda args, **kw: subprocess.CompletedProcess(args, exit, stdout, stderr),
    )
    with pytest.raises(UpdateBlocked, match="NATIVE_STRICT_CANDIDATE_REJECTED"):
        verified_candidate(
            f["new"],
            f["native"],
            expected_tree=installed_tree(f["new"])["sha"],
            expected_name="qa-guard304-host",
            expected_version="0.0.2",
            expected_binary_sha=f["native_sha"],
        )


def test_wrong_installed_bytes_or_changed_after_attestation_never_ready(fixture):
    f = fixture
    begin_quiescence(f)
    f["gate"].start_apply(
        candidate=f["new"],
        native_binary=f["native"],
        plugin_name="qa-guard304-host",
        expected_native_sha=f["native_sha"],
    )
    with pytest.raises(UpdateBlocked, match="INSTALLED_BYTES_MISMATCH"):
        f["gate"].candidate_applied(installed=f["installed"])
    copy_plugin(f["new"], f["installed"])
    f["gate"].candidate_applied(installed=f["installed"])
    for session, secret in f["secrets"].items():
        challenge = f["gate"].challenge(session, secret)
        f["gate"].attest(
            session,
            secret,
            f["prove"](session, challenge),
            verifier=fixture_verifier_for_tests_only,
        )
    (f["installed"] / "hooks/register.js").write_text("bad runtime change")
    with pytest.raises(UpdateBlocked, match="INSTALLED_CHANGED_AFTER_ATTESTATION"):
        f["gate"].ready(installed=f["installed"])
    assert f["gate"].status()["phase"] == "verifying"


def test_rollback_bytes_never_release_without_real_guard_attestation(fixture):
    f = fixture
    begin_quiescence(f)
    f["gate"].begin_rollback(reason="CANDIDATE_PREFLIGHT_FAILED")
    with pytest.raises(UpdateBlocked, match="ROLLBACK_BYTES_NOT_CONFIRMED"):
        f["gate"].ready(installed=f["installed"])
    f["gate"].rollback_bytes_restored(installed=f["installed"])
    with pytest.raises(UpdateBlocked, match="UNVERIFIED_OR_BUSY_PARTICIPANT"):
        f["gate"].ready(installed=f["installed"])
    for session, secret in f["secrets"].items():
        challenge = f["gate"].challenge(session, secret)
        f["gate"].attest(
            session,
            secret,
            f["prove"](session, challenge),
            verifier=fixture_verifier_for_tests_only,
        )
    f["gate"].ready(installed=f["installed"])
    assert f["gate"].status()["phase"] == "ready"


def test_disk_permissions_corruption_and_secret_redaction(fixture):
    f = fixture
    state = f["gate"].directory / "state.json"
    text = state.read_text()
    for secret in f["secrets"].values():
        assert secret not in text
    assert f["gate"].status()["production_wide_guarantee"] is False
    state.chmod(0o644)
    with pytest.raises(UpdateBlocked, match="UNSAFE_STATE_FILE"):
        f["gate"].enter("s-a", f["secrets"]["s-a"])
    state.chmod(0o600)
    state.write_text("{invalid json")
    with pytest.raises(UpdateBlocked, match="CORRUPTED_STATE"):
        f["gate"].status()


def test_simultaneous_file_locking_mediated_actions_across_instances(fixture):
    f = fixture
    root = f["gate"].directory

    def one(index):
        session = ("s-a", "s-b")[index % 2]
        second = GuardedRollout(root, clock=lambda: f["clock"][0])
        permit = second.enter(session, f["secrets"][session])
        second.leave(session, f["secrets"][session], permit)
        return index

    with ThreadPoolExecutor(max_workers=8) as pool:
        assert sorted(pool.map(one, range(40))) == list(range(40))
    assert f["gate"].status()["outstanding_permits"] == 0
    assert f["gate"].status()["phase"] == "ready"
