#!/usr/bin/env python3
"""Fail closed if any expected QA supervisor witness is missing or expired.

Live-at-issue-time is a short observation, NOT persistent or global readiness.
No key or receipt from any user production environment may be sent to Git.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

from mods_knowledge.cli304_supervised_attestation import LiveWitnessBlocked, audit_quorum


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--hosts", required=True, help="Explicit comma-separated QA host labels")
    for name in ("receipt-dir", "public-key-dir", "openssl", "out"):
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--nonce", required=True)
    p.add_argument("--as-of-epoch", type=int)
    a = p.parse_args()
    try:
        hosts = a.hosts.split(",")
        if len(hosts) < 2 or len(hosts) > 8 or len(set(hosts)) != len(hosts):
            raise LiveWitnessBlocked("INVALID_QA_HOST_INVENTORY")
        if a.out.exists() or a.out.is_symlink() or not a.out.is_absolute():
            raise LiveWitnessBlocked("OUTPUT_ALREADY_EXISTS_OR_NOT_ABSOLUTE")
        receipts, keys = {}, {}
        for name in hosts:
            packet = a.receipt_dir / (name + ".json")
            public = a.public_key_dir / (name + ".pem")
            if not packet.is_file() or packet.is_symlink() or packet.stat().st_size > 8192:
                raise LiveWitnessBlocked("MISSING_OR_UNSAFE_NATIVE_WITNESS")
            receipts[name] = json.loads(packet.read_text())
            keys[name] = public
        instant = int(time.time()) if a.as_of_epoch is None else a.as_of_epoch
        verified = audit_quorum(receipts, keys, openssl=a.openssl, nonce=a.nonce, now=instant)
        verified.update(
            verification_epoch=instant,
            historical_as_of_override=a.as_of_epoch is not None,
            this_is_only_valid_for_original_observation_window=True,
            signed_receipt_sha256={
                name: hashlib.sha256((a.receipt_dir / (name + ".json")).read_bytes()).hexdigest()
                for name in hosts
            },
            public_key_sha256={
                name: hashlib.sha256(keys[name].read_bytes()).hexdigest() for name in hosts
            },
        )
        a.out.write_text(json.dumps(verified, sort_keys=True, indent=2) + "\n")
    except (LiveWitnessBlocked, OSError, ValueError, KeyError, TypeError):
        print("BLOCKED: incomplete/expired/untrusted live QA fleet", file=sys.stderr)
        return 77
    print(
        json.dumps(
            {
                "observed_live_qa_hosts_at_issue": len(hosts),
                "production_wide_coverage": False,
                "stable_release_authorized": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
