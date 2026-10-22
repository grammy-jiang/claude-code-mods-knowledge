#!/usr/bin/env python3
"""Offline multi-host Ed25519 QA verification, NOT a global safety attestation.

All expected host public keys must be pre-pinned. Every host must provide a
fresh signed receipt for the SAME coordinator challenge. Unknown, duplicate,
stale or tampered receipts are refused rather than counted as protected.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from pathlib import Path

from mods_knowledge.cli304_fleet_snapshot import (
    HOST_ID,
    FleetBlocked,
    audit_fleet,
)

NATIVE_SHA_304 = "c487117526509ab6d2ee6013e14f181faf68d6d6afe6bb0d4b2b4a9feca5ecb3"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host-ids", required=True, help="Comma-separated explicit host labels")
    parser.add_argument("--signed-dir", type=Path, required=True)
    parser.add_argument("--public-dir", type=Path, required=True)
    parser.add_argument("--openssl", type=Path, required=True)
    parser.add_argument("--challenge", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--as-of-epoch", type=int)
    args = parser.parse_args()
    names = args.host_ids.split(",")
    try:
        if (
            len(names) < 2
            or len(names) > 8
            or len(set(names)) != len(names)
            or any(HOST_ID.fullmatch(x) is None for x in names)
        ):
            raise FleetBlocked("INVALID_EXPLICIT_FLEET_MEMBERSHIP")
        if args.out.exists() or args.out.is_symlink():
            raise FleetBlocked("EVIDENCE_OUTPUT_ALREADY_EXISTS")
        if not args.signed_dir.is_dir() or not args.public_dir.is_dir():
            raise FleetBlocked("MISSING_FLEET_EVIDENCE_DIRECTORIES")
        signed = {}
        public = {}
        for host in names:
            path = args.signed_dir / f"{host}.json"
            key = args.public_dir / f"{host}.pem"
            if not path.is_file() or path.is_symlink() or path.stat().st_size > 8192:
                raise FleetBlocked("MISSING_OR_UNTRUSTED_SIGNED_OBSERVATION")
            signed[host] = json.loads(path.read_text())
            public[host] = key
        result = audit_fleet(
            signed,
            public,
            openssl=args.openssl,
            challenge=args.challenge,
            now=args.as_of_epoch,
        )
        result["verification_epoch"] = (
            args.as_of_epoch if args.as_of_epoch is not None else int(time.time())
        )
        result["historical_time_override_used"] = args.as_of_epoch is not None
        result["host_signatures_cannot_prove_running_sessions_are_current"] = True
        result["native_304_sha256_for_prior_single_host_QA_only"] = NATIVE_SHA_304
        result["signature_verification_source_sha256"] = hashlib.sha256(
            (
                Path(__file__).resolve().parents[1] / "src/mods_knowledge/cli304_fleet_snapshot.py"
            ).read_bytes()
        ).hexdigest()
        result["original_signed_envelope_sha256"] = {
            h: hashlib.sha256((args.signed_dir / f"{h}.json").read_bytes()).hexdigest()
            for h in names
        }
        result["host_labels"] = sorted(names)
        result["evidence_expiry_epoch"] = min(signed[x]["payload"]["expires_at"] for x in names)
        result["signed_receipt_is_not_proof_of_managed_host_settings_loaded"] = True
        result["production_security_gate"] = "HOLD"
        if not re.fullmatch(r"[0-9a-f]{64}", args.challenge):
            raise FleetBlocked("BAD_FLEET_NONCE")
        args.out.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
        print(
            json.dumps(
                {
                    "signed_expected_hosts": len(names),
                    "observed_processes": result["observed_native_process_candidates"],
                    "global_protection_proven": False,
                    "stable_release_authorized": False,
                },
                sort_keys=True,
            )
        )
    except (FleetBlocked, OSError, ValueError, KeyError, TypeError):
        raise SystemExit("BLOCKED: incomplete or untrusted fleet signed observations") from None
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
