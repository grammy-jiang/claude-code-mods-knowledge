"""Specialized, source-bound native 2.1.304 QA guard probe verification.

The probe checks a single harmless prompt.submit guard challenge, and only
attests that the monitored QA host emitted a matching deny in that session.
It does not certify arbitrary Plugins, unmanaged sessions, or external tools.
Wire/debug text is user-owned and is not cryptographically host-signed.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from .guarded_rollout import UpdateBlocked

QA_MARKER = "P1D_GUARD_DENIED_"
QA_DEBUG = "P1D_GUARD_ACTIVE_"
QA_PLUGIN = "qa-cohort304-host"
MAX_WIRE = 8_000_000
MAX_DEBUG = 8_000_000


def _file(path: Path, maximum: int) -> bytes:
    if not path.is_file() or path.is_symlink() or path.stat().st_size > maximum:
        raise UpdateBlocked("INVALID_PRIVATE_HOST_EVIDENCE_FILE")
    return path.read_bytes()


def verify_native_qa_probe(
    proof: Path, session_id: str, challenge: str, tree_sha: str, epoch: int
) -> str:
    """Verify original local native event/debug artifacts for a one-time challenge.

    The wrapper that launches Claude must separately bind session_id, true
    executable SHA and plugin-dir/config to this controlled cohort. A forged
    owner-writable log can still fool this verifier; do not use it as a remote
    cryptographic identity or a universal security certification.
    """
    if not re.fullmatch(r"[0-9a-f]{40}", challenge):
        raise UpdateBlocked("INVALID_NATIVE_PROBE_CHALLENGE")
    try:
        data = json.loads(_file(proof, 8192))
    except (ValueError, UnicodeError) as exc:
        raise UpdateBlocked("INVALID_NATIVE_PROOF_MANIFEST") from exc
    if (
        not isinstance(data, dict)
        or set(data) != {"schema", "session_id", "epoch", "tree_sha", "wire", "debug"}
        or data["schema"] != 1
        or data["session_id"] != session_id
        or data["epoch"] != epoch
        or data["tree_sha"] != tree_sha
        or not isinstance(data["wire"], str)
        or not isinstance(data["debug"], str)
    ):
        raise UpdateBlocked("PROBE_NOT_BOUND_TO_EXPECTED_COHORT")
    wire = Path(data["wire"])
    debug = Path(data["debug"])
    if not wire.is_absolute() or not debug.is_absolute():
        raise UpdateBlocked("PROBE_PATH_MUST_BE_ABSOLUTE")
    raw_wire = _file(wire, MAX_WIRE)
    raw_debug = _file(debug, MAX_DEBUG)
    try:
        events = [json.loads(s) for s in raw_wire.decode().splitlines() if s.strip()]
    except (UnicodeError, ValueError) as exc:
        raise UpdateBlocked("MALFORMED_NATIVE_PROBE_WIRE") from exc
    if not events or any(not isinstance(e, dict) for e in events):
        raise UpdateBlocked("MISSING_NATIVE_PROBE_EVENTS")
    if any(e.get("session_id") != session_id for e in events):
        raise UpdateBlocked("WRONG_NATIVE_SESSION")
    init = [e for e in events if e.get("type") == "system" and e.get("subtype") == "init"]
    if not init or not all(
        isinstance(e.get("claude_code_version"), str)
        and e["claude_code_version"].startswith("2.1.304")
        for e in init
    ):
        raise UpdateBlocked("WRONG_NATIVE_PROBE_VERSION")
    result = [e for e in events if e.get("type") == "result"]
    if (
        len(result) != 1
        or result[0].get("is_error") is not False
        or result[0].get("subtype") != "success"
        or result[0].get("num_turns") != 0
        or (QA_MARKER + challenge) not in str(result[0].get("result", ""))
    ):
        raise UpdateBlocked("NO_REAL_HOST_PROBE_REFUSAL")
    log = raw_debug.decode(errors="replace")
    if (
        (QA_DEBUG + challenge) not in log
        or f"hooks module {QA_PLUGIN}@inline loaded" not in log
        or f"plugin.register: {QA_PLUGIN}" not in log
        or "prompt.submit" not in log
    ):
        raise UpdateBlocked("NO_REAL_QA_GUARD_INVOCATION")
    # Bound to exact bytes, without publishing the raw prompt/session.
    h = hashlib.sha256()
    for part in (raw_wire, raw_debug, tree_sha.encode(), challenge.encode()):
        h.update(len(part).to_bytes(8, "big"))
        h.update(part)
    return h.hexdigest()
