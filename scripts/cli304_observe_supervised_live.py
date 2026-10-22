#!/usr/bin/env python3
"""Sign fresh, original live supervisor+native-host QA evidence at the source.

Original signed payload and signing private key stay on the observer machine,
never in Git. Signing does not prove control of any other Claude process.
"""

from __future__ import annotations

import argparse
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

from mods_knowledge.cli304_supervised_attestation import LiveWitnessBlocked, inspect, sign


def _new(path: Path, content: bytes) -> None:
    if not path.is_absolute() or path.exists() or path.is_symlink():
        raise LiveWitnessBlocked("IMMUTABLE_ABSOLUTE_WITNESS_OUTPUT_REQUIRED")
    parent = path.parent
    if (
        not parent.is_dir()
        or parent.is_symlink()
        or parent.stat().st_uid != os.getuid()
        or stat.S_IMODE(parent.stat().st_mode) != 0o700
    ):
        raise LiveWitnessBlocked("PRIVATE_RECEIPT_DIRECTORY_REQUIRED")
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as output:
        output.write(content)
        output.flush()
        os.fsync(output.fileno())


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    for flag in ("root", "private-key", "openssl", "out", "public-key-out"):
        p.add_argument("--" + flag, type=Path, required=True)
    p.add_argument("--host-id", required=True)
    p.add_argument("--nonce", required=True)
    a = p.parse_args()
    try:
        snapshot = inspect(a.root, a.host_id, a.nonce)
        signed = sign(snapshot, private=a.private_key, openssl=a.openssl)
        result = subprocess.run(  # noqa: S603 - explicit OpenSSL CLI with no shell
            [str(a.openssl), "pkey", "-in", str(a.private_key), "-pubout"],
            capture_output=True,
            timeout=12,
            check=False,
        )
        if result.returncode != 0 or b"BEGIN PUBLIC KEY" not in result.stdout:
            raise LiveWitnessBlocked("PUBLIC_KEY_DERIVATION_FAILED")
        _new(a.out, (json.dumps(signed, sort_keys=True, separators=(",", ":")) + "\n").encode())
        _new(a.public_key_out, result.stdout)
    except (OSError, ValueError, LiveWitnessBlocked, subprocess.SubprocessError):
        print("BLOCKED: no valid live native host witness", file=sys.stderr)
        return 77
    print(
        json.dumps(
            {
                "host": a.host_id,
                "signed_live_native_observation": True,
                "expires_at": snapshot["expires_at"],
                "other_claude_hosts_protected": False,
                "stable_release_authorized": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
