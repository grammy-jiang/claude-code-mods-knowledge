#!/usr/bin/env python3
"""Recompute actual native CLI304 P1-D managed-cohort QA receipts from private bytes.

This is a read-only off-Git audit. Every actual host proof is checked against
the private wire/debug, challenge, version, cohort, and final persisted gate.
The returned JSON deliberately excludes session IDs, secrets, prompts and logs.
It does not attest persistent hosts, unmanaged operations, or production safety.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from collections import Counter
from pathlib import Path

from mods_knowledge.guarded_host_probe import verify_native_qa_probe
from mods_knowledge.guarded_rollout import NATIVE_CLI304_SHA, UpdateBlocked, installed_tree

CASE_EXPECTED = {
    "normal-two-sessions": {"epoch": 1, "good_version": "0.0.2", "proof_epochs": {0: 2, 1: 2}},
    "rollback-two-sessions": {
        "epoch": 2,
        "good_version": "0.0.1",
        "proof_epochs": {0: 2, 2: 2},
    },
}


def required(ok: bool, reason: str) -> None:
    if not ok:
        raise UpdateBlocked(reason)


def digest(file: Path) -> str:
    required(file.is_file() and not file.is_symlink(), "MISSING_PRIVATE_OR_UNSAFE_FILE")
    required(file.stat().st_size <= 8_000_000, "PRIVATE_EVIDENCE_TOO_LARGE")
    with file.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def audit(root: Path, official_binary: Path) -> dict:
    if not official_binary.is_file() or official_binary.is_symlink():
        raise UpdateBlocked("OFFICIAL_NATIVE_CLI_UNAVAILABLE")
    with official_binary.open("rb") as src:
        expected = hashlib.file_digest(src, "sha256").hexdigest()
    required(expected == NATIVE_CLI304_SHA, "OFFICIAL_CLI304_DIGEST_MISMATCH")
    source = installed_tree(root / "plugin")
    required(
        source["name"] == "qa-cohort304-host" and source["version"] == "0.0.1",
        "WRONG_ORIGINAL_QA_FIXTURE",
    )
    plans = json.loads((root / "private/plans.private.json").read_text())
    required(
        len(plans) == 2
        and {x["name"] for x in plans} == {"a", "b"}
        and len({x["session"] for x in plans}) == 2,
        "WRONG_EXPECTED_PRIVATE_TWO_SESSION_INVENTORY",
    )
    inventory = {x["session"] for x in plans}
    sanitized = json.loads((root / "private/cohort-sanitized-qa.json").read_text())
    required(sanitized["official_cli"] == "2.1.304", "WRONG_PRIOR_NATIVE_REPORT")
    required(sanitized["native_sha256"] == NATIVE_CLI304_SHA, "WRONG_PRIOR_NATIVE_BINARY")
    actual_proofs = []
    summaries = []
    for name, expected_case in CASE_EXPECTED.items():
        cohort = root / "private" / name
        state = json.loads((cohort / "gate/state.json").read_text())
        required(state["schema"] == 1 and state["phase"] == "ready", "COHORT_NOT_PERSISTED_READY")
        required(state["epoch"] == expected_case["epoch"], "WRONG_RECOVERY_FENCING_EPOCH")
        required(
            state["good_version"] == expected_case["good_version"], "WRONG_FINAL_COHORT_VERSION"
        )
        required(sorted(state["inventory"]) == sorted(inventory), "DRIFTED_SESSION_INVENTORY")
        required(set(state["sessions"]) == inventory, "PARTICIPANTS_MISSING")
        required(
            state["transaction"] is None and state["block_reason"] is None, "TRANSACTION_STILL_OPEN"
        )
        observed_installed = installed_tree(cohort / "installed")
        required(observed_installed["sha"] == state["good_tree"], "INSTALLED_TREE_MISMATCH")
        if name == "rollback-two-sessions":
            required(state["good_tree"] == source["sha"], "UNSAFE_ROLLBACK_TARGET")
        else:
            required(
                state["good_tree"] == installed_tree(cohort / "candidate")["sha"],
                "UNVERIFIED_NEW_VERSION",
            )
        counts: Counter[int] = Counter()
        latest: dict[str, str] = {}
        cohort_proofs = []
        for proof in sorted(cohort.glob("*-*/proof.private.json")):
            directory = proof.parent
            data = json.loads(proof.read_text())
            session = data["session_id"]
            require_epoch = data["epoch"]
            required(session in inventory, "UNKNOWN_NATIVE_SESSION_IN_PROOF")
            required(directory.name.startswith(session + "-"), "SCOPE_MISMATCHED_PROOF_DIRECTORY")
            challenge = directory.name[len(session) + 1 :]
            required(len(challenge) == 40, "BAD_CHALLENGE_NAME")
            required(
                data["schema"] == 1
                and data["tree_sha"] in (source["sha"], observed_installed["sha"]),
                "UNREVIEWED_PRIVATE_PROBE_SOURCE",
            )
            # Private manifests preserve the original /tmp root. Rebase their
            # pointers for persisted evidence replay, without changing raw logs.
            wire, debug = directory / "wire.private.jsonl", directory / "debug.private.log"
            required(wire.is_file() and debug.is_file(), "MISSING_PERSISTED_NATIVE_WIRE")
            rebased = dict(data, wire=str(wire.absolute()), debug=str(debug.absolute()))
            with tempfile.TemporaryDirectory(prefix="mods-p1d-audit-") as temp:
                repl = Path(temp) / "proof.json"
                repl.write_text(json.dumps(rebased))
                identity = verify_native_qa_probe(
                    repl, session, challenge, data["tree_sha"], require_epoch
                )
            counts[require_epoch] += 1
            cohort_proofs.append(
                {
                    "proof_sha256": identity,
                    "wire_sha256": digest(wire),
                    "debug_sha256": digest(debug),
                    "epoch": require_epoch,
                }
            )
            if require_epoch == state["epoch"]:
                required(session not in latest, "DUPLICATE_FINAL_SESSION_ATTESTATION")
                latest[session] = identity
        required(dict(counts) == expected_case["proof_epochs"], "MISSING_PROOF_OR_REPLAY")
        required(set(latest) == inventory, "MISSING_FINAL_REAL_HOST_PROOF")
        for session, record in state["sessions"].items():
            required(
                record["verified_epoch"] == state["epoch"]
                and record["proof_sha"] == latest[session]
                and record["challenge"] == ""
                and not record["permits"],
                "STATE_NOT_BOUND_TO_TRUE_LAST_SESSION_PROOF",
            )
            required(len(record["secret_sha"]) == 64, "MISSING_PRIVATE_SESSION_AUTH")
        actual_proofs += cohort_proofs
        summaries.append(
            {
                "case": name,
                "final_version": state["good_version"],
                "final_epoch": state["epoch"],
                "managed_session_count": 2,
                "native_probe_count": sum(counts.values()),
                "native_probe_epochs": {str(k): v for k, v in sorted(counts.items())},
                "all_managed_session_health_proofs_matched": True,
                "no_outstanding_protected_permits": True,
                "unmanaged_claude_sessions_not_attested": True,
            }
        )
    required(len(actual_proofs) == 8, "REAL_NATIVE_RECEIPT_COUNT_MISMATCH")
    required(sanitized["private_real_host_proof_count"] == 8, "PRIOR_SCORE_MISMATCH")
    required(
        sanitized["scenario_results"][0]["outcome"] == "candidate_healthy_in_managed_cohort_only"
        and sanitized["scenario_results"][1]["outcome"]
        == "candidate_rejected_old_version_recovered_in_managed_cohort",
        "INCORRECT_PRIOR_GATED_CONTROL_OUTCOMES",
    )
    return {
        "schema_version": 1,
        "target_cli": "2.1.304",
        "native_binary_sha256": expected,
        "original_qa_fixture_tree_sha256": source["sha"],
        "auditor_sha256": digest(Path(__file__)),
        "managed_cohort_scenarios": summaries,
        "native_proof_count": len(actual_proofs),
        "actual_native_proof_sha256": sorted(x["proof_sha256"] for x in actual_proofs),
        "private_wire_sha256": sorted(x["wire_sha256"] for x in actual_proofs),
        "private_debug_sha256": sorted(x["debug_sha256"] for x in actual_proofs),
        "actual_host_probe_model_turns": 0,
        "actual_host_probes_are_separate_host_invocations_not_hot_reload": True,
        "external_gate_only_controls_opted_in_operations": True,
        "unregistered_or_unmediated_sessions_protected": False,
        "cross_machine_or_production_scope_validated": False,
        "stable_release_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--official-binary", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    o = parser.parse_args()
    if o.out.exists() or o.out.is_symlink():
        raise SystemExit("REFUSED: cannot overwrite immutable native host report")
    try:
        report = audit(o.private_root, o.official_binary)
    except (OSError, ValueError, TypeError, KeyError, UpdateBlocked):
        raise SystemExit("BLOCKED: actual native managed-cohort evidence incomplete") from None
    o.out.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    print(
        json.dumps(
            {
                "native_proofs": report["native_proof_count"],
                "scenarios": len(report["managed_cohort_scenarios"]),
                "production_wide": False,
                "stable": False,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
