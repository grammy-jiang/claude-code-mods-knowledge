#!/usr/bin/env python3
"""Required Mac-authorized managed PreToolUse gate in isolated Linux CLI304 QA.

Even if the local supervisor keeps refreshing its local lease, any stale,
wrong-host, invalid-signature or wall/monotonic expired Mac-issued grant
causes fail-closed native Read denial. No fallback to local-only readiness.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from cli304_supervised_pretool import check as check_supervisor

from mods_knowledge.cli304_coordinator_grant import GrantBlocked, authorized
from mods_knowledge.cli304_supervised_lease import SupervisorBlocked


def check(
    event: object,
    *,
    lease: Path,
    workspace: Path,
    request: Path,
    grant: Path,
    public: Path,
    receipt: Path,
    openssl: Path,
) -> None:
    # Order does not weaken either check: both must succeed before a tool may run.
    check_supervisor(event, lease=lease, workspace=workspace)
    authorized(request, grant, public, openssl, receipt)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("lease", "workspace", "request", "grant", "public", "receipt", "openssl"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    try:
        raw = sys.stdin.buffer.read(65537)
        if len(raw) > 65536 or not raw:
            raise SupervisorBlocked("INVALID_NATIVE_TOOL_EVENT_LENGTH")
        event = json.loads(raw)
        check(
            event,
            lease=args.lease,
            workspace=args.workspace,
            request=args.request,
            grant=args.grant,
            public=args.public,
            receipt=args.receipt,
            openssl=args.openssl,
        )
        return 0
    except (SupervisorBlocked, GrantBlocked, OSError, ValueError, UnicodeError, TypeError):
        print("MAC_AUTHORITY_QA_DENIED", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
