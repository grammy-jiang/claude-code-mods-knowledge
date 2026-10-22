#!/usr/bin/env python3
"""Mac-only isolated CLI304 cohort epoch signer: private key never exported.

Issue only for explicit pinned expected host IDs, per-launch request bytes,
and one known cohort. No production allowlist or global safety is claimed.
"""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from pathlib import Path

from mods_knowledge.cli304_coordinator_grant import (
    GrantBlocked,
    grant_payload,
    sign,
    validate_request,
)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--host", choices=("rpi-a", "rpi-b"), required=True)
    p.add_argument("--cohort", required=True)
    p.add_argument("--epoch", type=int, required=True)
    p.add_argument("--request", type=Path, required=True)
    p.add_argument("--private-key", type=Path, required=True)
    p.add_argument("--openssl", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    try:
        if a.out.exists() or a.out.is_symlink() or not a.out.is_absolute():
            raise GrantBlocked("REFUSED_EXISTING_AUTHORITY_GRANT")
        root = a.out.parent
        if not root.is_dir() or stat.S_IMODE(root.stat().st_mode) != 0o700:
            raise GrantBlocked("UNSAFE_ISSUER_DIRECTORY")
        data = json.loads(a.request.read_text())
        validate_request(data)
        if data["host"] != a.host or data["cohort"] != a.cohort:
            raise GrantBlocked("NOT_EXPECTED_COHORT_HOST")
        epoch = grant_payload(data, epoch=a.epoch, ttl=24)
        envelope = sign(epoch, key=a.private_key, openssl=a.openssl)
        raw = (json.dumps(envelope, sort_keys=True, separators=(",", ":")) + "\n").encode()
        fd = os.open(a.out, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "wb") as out:
            out.write(raw)
            out.flush()
            os.fsync(out.fileno())
        print(
            json.dumps(
                {
                    "host": a.host,
                    "epoch": a.epoch,
                    "signed": True,
                    "expires_at": epoch["expires_at"],
                    "global_coverage": False,
                }
            )
        )
    except (OSError, ValueError, GrantBlocked, json.JSONDecodeError):
        print("BLOCKED: no signed authority grant issued", file=sys.stderr)
        return 77
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
