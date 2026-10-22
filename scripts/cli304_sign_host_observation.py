#!/usr/bin/env python3
"""Sign one short-lived read-only host inventory observation (P1 QA only).

Host private Ed25519 key stays in a 0700 QA directory, mode 0600.
A signed snapshot does not attest completeness of all running Claude sessions.
No user/process cmdlines, sessions, paths, or credentials leave the host.
"""

from __future__ import annotations

import argparse
import json
import os
import stat
from pathlib import Path

from mods_knowledge.cli304_fleet_snapshot import (
    HOST_ID,
    FleetBlocked,
    observe,
    public_key,
    sign,
)


def _new_file(path: Path, data: bytes, *, mode: int = 0o600) -> None:
    if not path.is_absolute() or path.exists() or path.is_symlink():
        raise FleetBlocked("IMMUTABLE_ABSOLUTE_QA_OUTPUT_PATH_REQUIRED")
    parent = path.parent
    if (
        not parent.is_dir()
        or parent.is_symlink()
        or parent.stat().st_uid != os.getuid()
        or stat.S_IMODE(parent.stat().st_mode) != 0o700
    ):
        raise FleetBlocked("QA_OUTPUT_DIRECTORY_MUST_BE_USER_ONLY")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host-id", required=True)
    parser.add_argument("--challenge", required=True)
    parser.add_argument("--openssl", type=Path, required=True)
    parser.add_argument("--private-key", type=Path, required=True)
    parser.add_argument("--envelope-out", type=Path, required=True)
    parser.add_argument("--public-key-out", type=Path, required=True)
    opt = parser.parse_args()
    try:
        if not HOST_ID.fullmatch(opt.host_id):
            raise FleetBlocked("INVALID_HOST_ID")
        payload = observe(opt.host_id, opt.challenge)
        envelope = sign(payload, private=opt.private_key, openssl=opt.openssl)
        _new_file(
            opt.envelope_out,
            (json.dumps(envelope, sort_keys=True, separators=(",", ":")) + "\n").encode(),
        )
        _new_file(opt.public_key_out, public_key(opt.private_key, opt.openssl), mode=0o600)
        print(
            json.dumps(
                {
                    "host_id": opt.host_id,
                    "signed_observation": True,
                    "candidate_process_count": payload["candidate_native_processes"],
                    "complete_inventory_proven": False,
                    "stable_release_authorized": False,
                },
                sort_keys=True,
            )
        )
    except (FleetBlocked, OSError, ValueError) as exc:
        raise SystemExit(f"BLOCKED: host observation incomplete ({type(exc).__name__})") from None
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
