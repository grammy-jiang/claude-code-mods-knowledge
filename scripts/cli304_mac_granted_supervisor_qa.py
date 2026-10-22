#!/usr/bin/env python3
"""QA-only Mac epoch grant -> local Pi lease -> real native CLI304 managed tools.

The per-host supervisor creates a unique private request and waits for a
**Mac-signed** grant file. An independent managed PreToolUse verifies both
that grant and the local short PID-bound lease EVERY time a tool is requested.
No renewal grant delivery is simulated by withholding further Mac messages.
This is NOT a transport-layer network partition, nor organization-wide policy.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import selectors
import shutil
import signal
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

from cli304_supervised_qa import _bwrap_argv, prepare

from mods_knowledge.cli304_coordinator_grant import (
    GrantBlocked,
    accept,
    authorized,
)
from mods_knowledge.cli304_supervised_lease import (
    NATIVE_CLI304_SHA,
    PrivateLease,
    SupervisorBlocked,
    boot_id,
)

MARKER = "QA_SUPERVISED_READ_OK_20261022"
MAX_WIRE = 4_000_000


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise SupervisorBlocked(reason)


def _safe_write(path: Path, data: dict) -> None:
    require(not path.exists() and not path.is_symlink(), "DO_NOT_OVERWRITE_PRIVATE_QA")
    raw = (json.dumps(data, sort_keys=True, separators=(",", ":")) + "\n").encode()
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as target:
        target.write(raw)
        target.flush()
        os.fsync(target.fileno())


class SignedRenewal:
    def __init__(self, lease: PrivateLease, files: dict[str, Path], openssl: Path):
        self.lease = lease
        self.files = files
        self.openssl = openssl
        self.failed = threading.Event()
        self.stop = threading.Event()
        self.worker = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        while not self.stop.wait(0.3):
            try:
                authorized(
                    self.files["request"],
                    self.files["grant"],
                    self.files["pub"],
                    self.openssl,
                    self.files["receipt"],
                )
                self.lease.refresh()
            except (GrantBlocked, SupervisorBlocked, OSError, ValueError):
                try:
                    self.lease.refresh("frozen")
                except (SupervisorBlocked, OSError):
                    pass
                self.failed.set()
                self.stop.set()

    def begin(self):
        self.worker.start()

    def end(self):
        self.stop.set()
        if self.worker.is_alive():
            self.worker.join(timeout=3)
            require(not self.worker.is_alive(), "QA_RENEWAL_THREAD_UNSTOPPABLE")


def main_run(
    *,
    root: Path,
    binary: Path,
    python: Path,
    wrapper: Path,
    cohort: str,
    host: str,
    public: Path,
    openssl: Path,
    timeout: int,
    scenario: str,
) -> dict:
    require(host in ("rpi-a", "rpi-b"), "UNKNOWN_QA_HOST")
    require(scenario in ("grant-expiry", "recovered-new-generation"), "BAD_QA_SCENARIO")
    require(20 <= timeout <= 100, "UNBOUNDED_QA_WAIT")
    require(public.is_file() and not public.is_symlink(), "MAC_PUBLIC_KEY_REQUIRED")
    require(openssl.is_absolute() and openssl.is_file(), "EXACT_LOCAL_OPENSSL_REQUIRED")
    require(wrapper.is_absolute() and wrapper.is_file(), "PINNED_MANAGED_HOOK_REQUIRED")
    prepare(root=root, cli=binary, python=python, hook=wrapper)
    private = root / "private"
    pub_dest = private / "coordinator-public.pem"
    shutil.copyfile(public, pub_dest)
    pub_dest.chmod(0o600)
    session = str(uuid.uuid4())
    lease = PrivateLease(private / "supervisor-lease.json", session=session, ttl=2)
    policy = root / "managed/managed-settings.json"
    native_hook = json.loads(policy.read_text())
    hook = native_hook["hooks"]["PreToolUse"][0]["hooks"][0]
    # The managed command is mandatory: local lease is necessary but
    # insufficient. Independent Mac signature is checked inside the hook.
    hook["args"] = [
        str(wrapper),
        "--lease",
        str(lease.path),
        "--workspace",
        str(root / "work"),
        "--request",
        str(private / "coordinator-request.private.json"),
        "--grant",
        str(private / "coordinator-grant.private.json"),
        "--public",
        str(pub_dest),
        "--receipt",
        str(private / "coordinator-receipt.private.json"),
        "--openssl",
        str(openssl),
    ]
    policy.write_text(json.dumps(native_hook, sort_keys=True, indent=2) + "\n")
    policy.chmod(0o600)
    policy_sha = hashlib.sha256(policy.read_bytes()).hexdigest()
    require(
        native_hook["allowManagedHooksOnly"] is True
        and hook["onFailure"] == "block"
        and hook["timeout"] == 5,
        "UNSAFE_NATIVE_HOOK_SETTINGS",
    )
    request = {
        "schema": 1,
        "host": host,
        "cohort": cohort,
        "nonce": secrets.token_hex(32),
        "generation": lease.generation,
        "session_sha256": hashlib.sha256(session.encode()).hexdigest(),
        "boot_sha256": hashlib.sha256(boot_id().encode()).hexdigest(),
        "policy_sha256": policy_sha,
        "native_binary_sha256": NATIVE_CLI304_SHA,
    }
    request_file = private / "coordinator-request.private.json"
    grant_file = private / "coordinator-grant.private.json"
    receipt_file = private / "coordinator-receipt.private.json"
    _safe_write(request_file, request)
    # This source file is the remote protocol input for the Mac signer. Keep
    # it private; only the reviewed opaque request is transferred, never
    # shell commands, private keys, or native Claude account content.
    renewal = None
    process = None
    records: list[dict] = []
    denied_after = False
    try:
        end = time.monotonic() + timeout
        while time.monotonic() < end and not grant_file.exists():
            time.sleep(0.15)
        require(grant_file.exists(), "MAC_AUTHORIZATION_NOT_DELIVERED")
        receipt = accept(request_file, grant_file, pub_dest, openssl, receipt_file)
        epoch = receipt["epoch"]
        lease.refresh("ready")
        files = {
            "request": request_file,
            "grant": grant_file,
            "pub": pub_dest,
            "receipt": receipt_file,
        }
        renewal = SignedRenewal(lease, files, openssl)
        renewal.begin()
        wire = root / "raw/native-wire.private.jsonl"
        debug = root / "raw/native-debug.private.log"
        stderr = root / "raw/native-stderr.private.log"
        args = [
            "--print",
            "--verbose",
            "--strict-mcp-config",
            "--setting-sources",
            "",
            "--permission-prompts",
            "none",
            "--permission-mode",
            "dontAsk",
            "--tools",
            "Read",
            "--allowedTools",
            "Read",
            "--no-session-persistence",
            "--input-format",
            "stream-json",
            "--output-format",
            "stream-json",
            "--session-id",
            session,
            "--max-turns",
            "2",
            "--max-budget-usd",
            "0.25",
            "--model",
            "sonnet",
            "--effort",
            "medium",
            "--debug-file",
            str(debug),
        ]
        env = os.environ.copy()
        env["CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"] = "1"
        with wire.open("wb") as out, stderr.open("wb") as err:
            process = subprocess.Popen(  # noqa: S603 - exact native binary and fixed sandbox
                _bwrap_argv(root, binary, args),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=err,
                cwd=root / "work",
                env=env,
                start_new_session=True,
            )
            poller = selectors.DefaultSelector()
            poller.register(process.stdout, selectors.EVENT_READ)

            def turn(label: str) -> dict:
                require(process is not None and process.poll() is None, "NATIVE_HOST_NOT_RUNNING")
                prompt = (
                    f"Controlled QA: invoke Read exactly once for {root / 'work/safe-read.txt'}. "
                    "If denied, do not retry or use another tool."
                )
                message = {
                    "type": "user",
                    "message": {"role": "user", "content": [{"type": "text", "text": prompt}]},
                }
                process.stdin.write((json.dumps(message) + "\n").encode())
                process.stdin.flush()
                until = time.monotonic() + 18
                row = {
                    "phase": label,
                    "complete": False,
                    "tools": [],
                    "read_marker": False,
                    "coordinator_deny": False,
                }
                while time.monotonic() < until:
                    if not poller.select(0.4):
                        require(process.poll() is None, "HOST_EXITED_DURING_QA_TURN")
                        continue
                    line = process.stdout.readline()
                    if not line:
                        break
                    require(out.tell() + len(line) <= MAX_WIRE, "OVERSIZE_NATIVE_WIRE")
                    out.write(line)
                    out.flush()
                    try:
                        ev = json.loads(line)
                    except ValueError:
                        continue
                    if ev.get("type") == "assistant":
                        for item in (ev.get("message") or {}).get("content", []):
                            if isinstance(item, dict) and item.get("type") == "tool_use":
                                row["tools"].append(item.get("name"))
                    if ev.get("type") == "user":
                        for item in (ev.get("message") or {}).get("content", []):
                            if isinstance(item, dict) and item.get("type") == "tool_result":
                                text = json.dumps(item)
                                row["read_marker"] |= MARKER in text
                                row["coordinator_deny"] |= "MAC_AUTHORITY_QA_DENIED" in text
                    if ev.get("type") == "result":
                        row["complete"] = (
                            ev.get("subtype") == "success" and ev.get("is_error") is False
                        )
                        row["model_turns"] = ev.get("num_turns")
                        break
                require(
                    row["complete"] and row["tools"] == ["Read"], "REAL_NATIVE_QA_TURN_INCOMPLETE"
                )
                records.append(row)
                return row

            before = turn("valid_mac_grant")
            require(
                before["read_marker"] and not before["coordinator_deny"],
                "MAC_GRANTED_NATIVE_READ_NOT_CONFIRMED",
            )
            if scenario == "grant-expiry":
                grant_expiry = json.loads(grant_file.read_text())["payload"]["expires_at"]
                deadline = time.monotonic() + max(0, grant_expiry + 2 - time.time())
                while time.monotonic() < deadline:
                    time.sleep(0.25)
                require(
                    renewal.failed.wait(timeout=3),
                    "LOCAL_SUPERVISOR_FAILED_TO_FREEZE_ON_MAC_EXPIRY",
                )
                after = turn("mac_grant_delivery_stopped")
                denied_after = not after["read_marker"] and after["coordinator_deny"]
                require(denied_after, "NATIVE_TOOL_BYPASSED_EXPIRED_COORDINATOR_AUTHORITY")
            else:
                # The new supervisor generation and strictly larger signed
                # epoch itself is the recovery; no old frozen supervisor thaws.
                denied_after = False
            process.stdin.close()
            process.wait(timeout=4)
        require(stderr.stat().st_size == 0, "NATIVE_HOST_STDERR_UNEXPECTED")
        return {
            "schema": 1,
            "host": host,
            "scenario": scenario,
            "epoch": epoch,
            "native_target": "2.1.304",
            "native_binary_sha256": NATIVE_CLI304_SHA,
            "policy_sha256": policy_sha,
            "source_grant_sha256": hashlib.sha256(grant_file.read_bytes()).hexdigest(),
            "signed_mac_public_key_sha256": hashlib.sha256(pub_dest.read_bytes()).hexdigest(),
            "original_native_wire_sha256": hashlib.sha256(wire.read_bytes()).hexdigest(),
            "original_native_debug_sha256": hashlib.sha256(debug.read_bytes()).hexdigest(),
            "native_turns": records,
            "local_supervisor_froze_on_coordinator_expiry": renewal.failed.is_set(),
            "actual_native_tool_blocked_after_mac_grant_expiry": denied_after,
            "production_host_modified": False,
            "unregistered_sessions_protected": False,
            "stable_release_authorized": False,
        }
    finally:
        if renewal is not None:
            renewal.end()
        try:
            lease.refresh("blocked")
        except (SupervisorBlocked, OSError):
            pass
        if process is not None and process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=4)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--host", choices=("rpi-a", "rpi-b"), required=True)
    p.add_argument("--cohort", required=True)
    p.add_argument("--native", type=Path, required=True)
    p.add_argument("--python", type=Path, required=True)
    p.add_argument("--hook", type=Path, required=True)
    p.add_argument("--mac-public", type=Path, required=True)
    p.add_argument("--openssl", type=Path, required=True)
    p.add_argument("--request-wait", type=int, default=80)
    p.add_argument(
        "--scenario", choices=("grant-expiry", "recovered-new-generation"), required=True
    )
    a = p.parse_args()
    try:
        result = main_run(
            root=a.root,
            binary=a.native,
            python=a.python,
            wrapper=a.hook,
            cohort=a.cohort,
            host=a.host,
            public=a.mac_public,
            openssl=a.openssl,
            timeout=a.request_wait,
            scenario=a.scenario,
        )
        out = a.root / "private/sanitized-outcome.json"
        _safe_write(out, result)
    except (
        OSError,
        ValueError,
        TypeError,
        GrantBlocked,
        SupervisorBlocked,
        subprocess.SubprocessError,
    ):
        print(
            "BLOCKED: original Mac coordinator grant/native host test incomplete", file=sys.stderr
        )
        return 77
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
