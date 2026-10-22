"""Native wire verifier rejects stale, forged-shaped, and wrong-session QA proofs."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mods_knowledge.guarded_host_probe import verify_native_qa_probe
from mods_knowledge.guarded_rollout import UpdateBlocked

SESSION = "11111111-2222-4333-8444-555555555555"
CHALLENGE = "a" * 40
TREE = "b" * 64


@pytest.fixture
def proof(tmp_path: Path) -> Path:
    wire = tmp_path / "private-wire.jsonl"
    debug = tmp_path / "private-debug.log"
    events = [
        {
            "type": "system",
            "subtype": "init",
            "session_id": SESSION,
            "claude_code_version": "2.1.304",
        },
        {
            "type": "result",
            "subtype": "success",
            "is_error": False,
            "num_turns": 0,
            "session_id": SESSION,
            "result": f"Prompt dropped by a hook: P1D_GUARD_DENIED_{CHALLENGE}",
        },
    ]
    wire.write_text("\n".join(json.dumps(x) for x in events) + "\n")
    debug.write_text(
        "hooks module qa-cohort304-host@inline loaded\n"
        "plugin.register: qa-cohort304-host (user) admitted\n"
        f"[qa-cohort304-host] P1D_GUARD_ACTIVE_{CHALLENGE}\n"
        "hooks module qa-cohort304-host@inline prompt.submit settled\n"
    )
    manifest = tmp_path / "private-manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema": 1,
                "session_id": SESSION,
                "epoch": 1,
                "tree_sha": TREE,
                "wire": str(wire),
                "debug": str(debug),
            }
        )
    )
    return manifest


def verify(manifest: Path, *, session=SESSION, challenge=CHALLENGE, tree=TREE, epoch=1):
    return verify_native_qa_probe(manifest, session, challenge, tree, epoch)


def test_matching_native_shape_and_challenge_attested_without_model_turn(proof):
    assert len(verify(proof)) == 64
    assert verify(proof) == verify(proof)


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"session": "00000000-0000-4000-8000-000000000009"}, "COHORT"),
        ({"challenge": "c" * 40}, "REFUSAL"),
        ({"tree": "d" * 64}, "COHORT"),
        ({"epoch": 5}, "COHORT"),
    ],
)
def test_wrong_session_challenge_epoch_or_tree_refused(proof, overrides, message):
    with pytest.raises(UpdateBlocked, match=message):
        verify(proof, **overrides)


def test_false_model_turn_or_extra_result_refused(proof):
    manifest = json.loads(proof.read_text())
    wire = Path(manifest["wire"])
    lines = [json.loads(s) for s in wire.read_text().splitlines()]
    lines[-1]["num_turns"] = 1
    wire.write_text("\n".join(json.dumps(x) for x in lines))
    with pytest.raises(UpdateBlocked, match="NO_REAL_HOST_PROBE_REFUSAL"):
        verify(proof)
    lines[-1]["num_turns"] = 0
    wire.write_text("\n".join(json.dumps(x) for x in lines + [lines[-1]]))
    with pytest.raises(UpdateBlocked, match="NO_REAL_HOST_PROBE_REFUSAL"):
        verify(proof)


def test_absent_actual_hook_marker_refused(proof):
    manifest = json.loads(proof.read_text())
    debug = Path(manifest["debug"])
    debug.write_text(debug.read_text().replace("P1D_GUARD_ACTIVE_", "UNTRUSTED_"))
    with pytest.raises(UpdateBlocked, match="NO_REAL_QA_GUARD_INVOCATION"):
        verify(proof)


def test_wrong_native_version_and_session_refused(proof):
    manifest = json.loads(proof.read_text())
    wire = Path(manifest["wire"])
    lines = [json.loads(s) for s in wire.read_text().splitlines()]
    lines[0]["claude_code_version"] = "2.1.302"
    wire.write_text("\n".join(json.dumps(x) for x in lines) + "\n")
    with pytest.raises(UpdateBlocked, match="WRONG_NATIVE_PROBE_VERSION"):
        verify(proof)
    lines[0]["claude_code_version"] = "2.1.304"
    lines[-1]["session_id"] = "00000000-0000-4000-8000-000000000010"
    wire.write_text("\n".join(json.dumps(x) for x in lines) + "\n")
    with pytest.raises(UpdateBlocked, match="WRONG_NATIVE_SESSION"):
        verify(proof)


def test_private_source_symlink_and_malformed_proof_refused(proof):
    raw = json.loads(proof.read_text())
    real_wire = Path(raw["wire"])
    link = proof.parent / "fake-wire"
    link.symlink_to(real_wire)
    raw["wire"] = str(link)
    proof.write_text(json.dumps(raw))
    with pytest.raises(UpdateBlocked, match="INVALID_PRIVATE_HOST_EVIDENCE_FILE"):
        verify(proof)
    proof.write_text("{")
    with pytest.raises(UpdateBlocked, match="INVALID_NATIVE_PROOF_MANIFEST"):
        verify(proof)
