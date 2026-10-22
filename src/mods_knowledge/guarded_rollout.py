"""Opt-in, external fail-closed gate for Claude Mods updates on POSIX hosts.

Only actions mediated by this gate can be protected. Native Claude Code tools
and existing unregistered sessions cannot be stopped by this library. It is a
single-filesystem, single-controller QA coordinator, NOT a production updater.
There is deliberately no "force ready", bypass or time-based permit expiry.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import secrets
import shutil
import stat
import subprocess
import tempfile
import time
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import Any

HEX_SHA = re.compile(r"[0-9a-f]{64}\Z")
SESSION = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}\Z")
PHASES = frozenset(("blocked", "ready", "quiescing", "applying", "verifying", "rolling_back"))
MAX_STATE = 262_144
MAX_PLUGIN_BYTES = 8_000_000
NATIVE_CLI304_SHA = "c487117526509ab6d2ee6013e14f181faf68d6d6afe6bb0d4b2b4a9feca5ecb3"


class UpdateBlocked(RuntimeError):
    """Refuse access or rollout when evidence, sessions, or state are incomplete."""


def _require(ok: bool, reason: str) -> None:
    if not ok:
        raise UpdateBlocked(reason)


def _sha(value: str) -> bool:
    return isinstance(value, str) and HEX_SHA.fullmatch(value) is not None


def installed_tree(path: Path) -> dict:
    """Digest actual plugin bytes; disallow symlink and unreviewed cache markers."""
    _require(path.is_dir() and not path.is_symlink(), "UNSAFE_PLUGIN_ROOT")
    files: list[Path] = []
    total = 0
    for item in sorted(path.rglob("*")):
        _require(not item.is_symlink(), "PLUGIN_SYMLINK_FORBIDDEN")
        _require(item.is_file() or item.is_dir(), "NONREGULAR_PLUGIN_ENTRY")
        if item.is_file():
            _require(item.name != ".orphaned_at", "VOLATILE_CACHE_METADATA_FORBIDDEN")
            files.append(item)
            total += item.stat().st_size
            _require(len(files) <= 100 and total <= MAX_PLUGIN_BYTES, "PLUGIN_TOO_LARGE")
    _require(bool(files), "EMPTY_PLUGIN")
    tree = hashlib.sha256()
    for item in files:
        name = item.relative_to(path).as_posix().encode("utf-8")
        data = item.read_bytes()
        tree.update(len(name).to_bytes(4, "big"))
        tree.update(name)
        tree.update(len(data).to_bytes(8, "big"))
        tree.update(data)
    manifest = path / ".claude-plugin/plugin.json"
    _require(manifest in files, "PLUGIN_MANIFEST_MISSING")
    try:
        meta = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise UpdateBlocked("INVALID_PLUGIN_MANIFEST") from exc
    _require(isinstance(meta, dict), "INVALID_PLUGIN_MANIFEST")
    return {
        "sha": tree.hexdigest(),
        "name": meta.get("name"),
        "version": meta.get("version"),
        "files": len(files),
    }


def verified_candidate(
    candidate: Path,
    native_binary: Path,
    *,
    expected_tree: str,
    expected_version: str,
    expected_name: str,
    expected_binary_sha: str = NATIVE_CLI304_SHA,
) -> dict:
    """Check exact frozen bytes and the native CLI strict validation gate."""
    _require(_sha(expected_tree) and _sha(expected_binary_sha), "INVALID_EXPECTED_HASH")
    _require(
        native_binary.is_file()
        and not native_binary.is_symlink()
        and native_binary.stat().st_size <= 350_000_000,
        "OFFICIAL_NATIVE_BINARY_MISSING",
    )
    with native_binary.open("rb") as stream:
        native_digest = hashlib.file_digest(stream, "sha256").hexdigest()
    _require(native_digest == expected_binary_sha, "OFFICIAL_NATIVE_BINARY_MISMATCH")
    original = installed_tree(candidate)
    _require(
        original["sha"] == expected_tree
        and original["version"] == expected_version
        and original["name"] == expected_name,
        "CANDIDATE_REVIEWED_BYTES_OR_ID_MISMATCH",
    )
    with tempfile.TemporaryDirectory(prefix="mods-qa-frozen-", dir=candidate.parent) as work:
        frozen = Path(work) / "plugin"
        shutil.copytree(candidate, frozen, symlinks=False)
        _require(installed_tree(frozen) == original, "FROZEN_COPY_CHANGED")
        try:
            r = subprocess.run(  # noqa: S603 - pinned native binary, no shell
                [str(native_binary), "plugin", "validate", "--strict", str(frozen)],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise UpdateBlocked("OFFICIAL_NATIVE_VALIDATOR_UNAVAILABLE") from exc
        output = r.stdout + "\n" + r.stderr
        _require(
            r.returncode == 0
            and "Validation passed" in output
            and "Validation failed" not in output
            and "gating hook without .catch" not in output
            and re.search(r"\b(?:warning|error)\b", output, flags=re.I) is None,
            "NATIVE_STRICT_CANDIDATE_REJECTED",
        )
        _require(installed_tree(frozen) == original, "FROZEN_COPY_CHANGED_DURING_CHECK")
    _require(installed_tree(candidate) == original, "CANDIDATE_CHANGED_DURING_PREFLIGHT")
    return original


class GuardedRollout:
    """Atomic state machine for explicitly registered, externally gated work.

    Session secrets are returned once during enrolment and stored hashed on
    disk. A caller must NEVER put raw session secrets in Git or public reports.
    All API operations recheck the on-disk state under one OS-level file lock.
    """

    def __init__(
        self, directory: Path, *, clock: Callable[[], float] = time.time, ttl: int = 120
    ) -> None:
        self.directory = directory
        self.clock = clock
        _require(5 <= ttl <= 3600, "INVALID_LEASE_TTL")
        self.ttl = ttl

    def _folder(self, *, create: bool = False) -> None:
        root = self.directory
        if create:
            root.mkdir(mode=0o700, parents=False, exist_ok=False)
        _require(root.is_dir() and not root.is_symlink(), "UNSAFE_COORDINATOR_DIRECTORY")
        metadata = root.stat()
        _require(
            metadata.st_uid == os.getuid() and stat.S_IMODE(metadata.st_mode) == 0o700,
            "UNSAFE_COORDINATOR_DIRECTORY_PERMISSIONS",
        )

    @contextmanager
    def _lock(self) -> Iterator[None]:
        self._folder()
        fd = os.open(
            self.directory / ".lock",
            os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0),
            0o600,
        )
        try:
            meta = os.fstat(fd)
            _require(
                stat.S_ISREG(meta.st_mode)
                and meta.st_uid == os.getuid()
                and stat.S_IMODE(meta.st_mode) == 0o600,
                "UNSAFE_LOCK_FILE",
            )
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    def _read(self) -> dict[str, Any]:
        p = self.directory / "state.json"
        _require(p.is_file() and not p.is_symlink(), "MISSING_OR_UNSAFE_STATE")
        m = p.stat()
        _require(
            m.st_size <= MAX_STATE and m.st_uid == os.getuid() and stat.S_IMODE(m.st_mode) == 0o600,
            "UNSAFE_STATE_FILE",
        )
        try:
            state = json.loads(p.read_text())
        except (OSError, ValueError) as exc:
            raise UpdateBlocked("CORRUPTED_STATE") from exc
        _require(
            isinstance(state, dict)
            and state.get("schema") == 1
            and state.get("phase") in PHASES
            and isinstance(state.get("sessions"), dict)
            and isinstance(state.get("inventory"), list)
            and isinstance(state.get("epoch"), int)
            and _sha(state.get("good_tree"))
            and isinstance(state.get("good_version"), str),
            "UNRECOGNIZED_STATE",
        )
        return state

    def _save(self, state: dict[str, Any]) -> None:
        content = (json.dumps(state, sort_keys=True, separators=(",", ":")) + "\n").encode()
        _require(len(content) <= MAX_STATE, "STATE_TOO_LARGE")
        fd, tmp = tempfile.mkstemp(prefix=".state-new-", dir=self.directory)
        try:
            with os.fdopen(fd, "wb") as stream:
                os.fchmod(stream.fileno(), 0o600)
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(tmp, self.directory / "state.json")
            dr = os.open(self.directory, os.O_RDONLY)
            try:
                os.fsync(dr)
            finally:
                os.close(dr)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    @staticmethod
    def _initial_session() -> dict[str, Any]:
        return {
            "secret_sha": "",
            "seen_at": 0,
            "verified_epoch": -1,
            "acked_epoch": -1,
            "challenge": "",
            "proof_sha": "",
            "permits": {},
        }

    def create(self, inventory: list[str], *, good_version: str, good_tree: str) -> None:
        _require(
            isinstance(inventory, list)
            and 1 <= len(inventory) <= 32
            and len(set(inventory)) == len(inventory)
            and all(isinstance(x, str) and SESSION.fullmatch(x) for x in inventory),
            "INVALID_EXPLICIT_SESSION_INVENTORY",
        )
        _require(_sha(good_tree), "INVALID_KNOWN_GOOD_DIGEST")
        _require(bool(re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", good_version)), "INVALID_VERSION")
        self._folder(create=True)
        with self._lock():
            self._save(
                {
                    "schema": 1,
                    "phase": "blocked",
                    "epoch": 0,
                    "good_version": good_version,
                    "good_tree": good_tree,
                    "inventory": sorted(inventory),
                    "sessions": {s: self._initial_session() for s in inventory},
                    "transaction": None,
                    "rollback_bytes_verified": False,
                    "block_reason": "UNVERIFIED_BASELINE",
                }
            )

    @staticmethod
    def _hash_secret(secret: str) -> str:
        return hashlib.sha256(secret.encode()).hexdigest()

    def _session(self, state: dict, session: str, secret: str) -> dict:
        participant = state["sessions"].get(session)
        _require(
            isinstance(participant, dict)
            and bool(participant.get("secret_sha"))
            and isinstance(secret, str)
            and len(secret) >= 32
            and secrets.compare_digest(participant["secret_sha"], self._hash_secret(secret)),
            "UNREGISTERED_OR_UNAUTHORIZED_SESSION",
        )
        return participant

    def enroll(self, session: str) -> str:
        with self._lock():
            state = self._read()
            _require(state["phase"] == "blocked" and state["epoch"] == 0, "ENROLLMENT_CLOSED")
            _require(session in state["inventory"], "SESSION_NOT_IN_EXPLICIT_INVENTORY")
            entry = state["sessions"][session]
            _require(not entry["secret_sha"], "SESSION_ALREADY_ENROLLED")
            secret = secrets.token_urlsafe(32)
            entry["secret_sha"] = self._hash_secret(secret)
            entry["seen_at"] = self.clock()
            entry["challenge"] = secrets.token_hex(20)
            self._save(state)
            return secret

    def heartbeat(self, session: str, secret: str) -> None:
        with self._lock():
            state = self._read()
            entry = self._session(state, session, secret)
            entry["seen_at"] = self.clock()
            self._save(state)

    def _fresh(self, state: dict, *, now: float) -> bool:
        return all(
            entry["secret_sha"] and 0 <= now - entry["seen_at"] <= self.ttl
            for entry in state["sessions"].values()
        )

    def challenge(self, session: str, secret: str) -> dict:
        with self._lock():
            state = self._read()
            entry = self._session(state, session, secret)
            return {
                "session": session,
                "epoch": state["epoch"],
                "challenge": entry["challenge"],
                "tree_sha": state["transaction"]["tree"]
                if state["phase"] == "verifying"
                else state["good_tree"],
            }

    def attest(
        self,
        session: str,
        secret: str,
        proof: Path,
        *,
        verifier: Callable[[Path, str, str, str, int], str],
    ) -> None:
        """Accept only a trusted, independently parsed per-session proof.

        The verifier must read original private native host events; a boolean,
        static report, or self-declared 'ok' is NOT sufficient.
        """
        with self._lock():
            state = self._read()
            _require(state["phase"] in ("blocked", "verifying", "rolling_back"), "NOT_ATTESTING")
            entry = self._session(state, session, secret)
            digest = (
                state["transaction"]["tree"]
                if state["phase"] == "verifying"
                else state["good_tree"]
            )
            challenge = entry["challenge"]
            epoch = state["epoch"]
            _require(isinstance(challenge, str) and len(challenge) == 40, "NO_FRESH_CHALLENGE")
            _require(self._fresh_except(state, session), "OTHER_PARTICIPANT_LEASE_EXPIRED")
            # No concurrent state transition can replace the challenge while
            # the verifier reads its private sources under the state lock.
            proof_sha = verifier(proof, session, challenge, digest, epoch)
            _require(_sha(proof_sha), "UNATTESTED_HOST_PROOF")
            entry["verified_epoch"] = epoch
            entry["proof_sha"] = proof_sha
            entry["seen_at"] = self.clock()
            entry["challenge"] = ""  # one-time use, blocks replay
            self._save(state)

    def _fresh_except(self, state: dict, session: str) -> bool:
        now = self.clock()
        return all(
            entry["secret_sha"] and 0 <= now - entry["seen_at"] <= self.ttl
            for sid, entry in state["sessions"].items()
            if sid != session
        )

    def ready(self, *, installed: Path | None = None) -> None:
        with self._lock():
            state = self._read()
            _require(
                state["phase"] in ("blocked", "verifying", "rolling_back"), "INVALID_READY_PHASE"
            )
            _require(
                state["phase"] != "blocked" or state["epoch"] == 0,
                "FAILED_COHORT_REQUIRES_EXPLICIT_RESTORATION",
            )
            _require(
                state["phase"] != "rolling_back" or state["rollback_bytes_verified"] is True,
                "ROLLBACK_BYTES_NOT_CONFIRMED",
            )
            if state["phase"] in ("verifying", "rolling_back"):
                _require(installed is not None, "INSTALLED_BYTES_MUST_BE_RECHECKED_AT_RELEASE")
                observed = installed_tree(installed)
                want_tree = (
                    state["transaction"]["tree"]
                    if state["phase"] == "verifying"
                    else state["good_tree"]
                )
                want_version = (
                    state["transaction"]["version"]
                    if state["phase"] == "verifying"
                    else state["good_version"]
                )
                _require(
                    observed["sha"] == want_tree and observed["version"] == want_version,
                    "INSTALLED_CHANGED_AFTER_ATTESTATION",
                )
            _require(self._fresh(state, now=self.clock()), "EXPIRED_PARTICIPANT")
            _require(
                all(
                    entry["verified_epoch"] == state["epoch"]
                    and entry["proof_sha"]
                    and not entry["permits"]
                    for entry in state["sessions"].values()
                ),
                "UNVERIFIED_OR_BUSY_PARTICIPANT",
            )
            if state["phase"] == "verifying":
                state["good_tree"] = state["transaction"]["tree"]
                state["good_version"] = state["transaction"]["version"]
            state.update(
                phase="ready", transaction=None, rollback_bytes_verified=False, block_reason=None
            )
            self._save(state)

    def enter(self, session: str, secret: str) -> str:
        """The ONLY gate for protected, externally mediated operations."""
        with self._lock():
            state = self._read()
            entry = self._session(state, session, secret)
            _require(state["phase"] == "ready", "PROTECTED_ACTION_FROZEN")
            _require(self._fresh(state, now=self.clock()), "SESSION_LEASE_EXPIRED")
            _require(entry["verified_epoch"] == state["epoch"], "STALE_SESSION_ATTESTATION")
            permit = secrets.token_hex(24)
            entry["permits"][permit] = self.clock()
            self._save(state)
            return permit

    def leave(self, session: str, secret: str, permit: str) -> None:
        with self._lock():
            state = self._read()
            entry = self._session(state, session, secret)
            _require(
                isinstance(permit, str) and permit in entry["permits"], "UNKNOWN_ACTIVE_PERMIT"
            )
            del entry["permits"][permit]
            entry["seen_at"] = self.clock()
            self._save(state)

    def begin(self, *, transaction_id: str, new_version: str, new_tree: str) -> None:
        _require(bool(SESSION.fullmatch(transaction_id)), "INVALID_TRANSACTION_ID")
        _require(_sha(new_tree), "INVALID_CANDIDATE_DIGEST")
        _require(bool(re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", new_version)), "INVALID_VERSION")
        with self._lock():
            state = self._read()
            _require(state["phase"] == "ready", "CURRENT_COHORT_NOT_READY")
            _require(self._fresh(state, now=self.clock()), "SESSION_LEASE_EXPIRED")
            _require(new_tree != state["good_tree"], "NO_EXACT_CANDIDATE_CHANGE")
            state["epoch"] += 1
            state["phase"] = "quiescing"
            state["transaction"] = {
                "id": transaction_id,
                "version": new_version,
                "tree": new_tree,
                "previous_version": state["good_version"],
                "previous_tree": state["good_tree"],
            }
            state["block_reason"] = "UPDATE_QUIESCING"
            for entry in state["sessions"].values():
                entry["acked_epoch"] = -1
                entry["verified_epoch"] = -1
                entry["proof_sha"] = ""
                entry["challenge"] = ""
            self._save(state)

    def acknowledge(self, session: str, secret: str) -> None:
        with self._lock():
            state = self._read()
            _require(state["phase"] == "quiescing", "NOT_QUIESCING")
            entry = self._session(state, session, secret)
            _require(not entry["permits"], "INFLIGHT_PROTECTED_OP")
            entry["seen_at"] = self.clock()
            entry["acked_epoch"] = state["epoch"]
            self._save(state)

    def start_apply(
        self,
        *,
        candidate: Path,
        native_binary: Path,
        plugin_name: str,
        expected_native_sha: str = NATIVE_CLI304_SHA,
    ) -> dict:
        with self._lock():
            state = self._read()
            _require(state["phase"] == "quiescing", "NOT_QUIESCING")
            _require(self._fresh(state, now=self.clock()), "SESSION_LEASE_EXPIRED")
            _require(
                all(
                    entry["acked_epoch"] == state["epoch"] and not entry["permits"]
                    for entry in state["sessions"].values()
                ),
                "NOT_ALL_SESSIONS_QUIESCED",
            )
            verified_candidate(
                candidate,
                native_binary,
                expected_tree=state["transaction"]["tree"],
                expected_version=state["transaction"]["version"],
                expected_name=plugin_name,
                expected_binary_sha=expected_native_sha,
            )
            state.update(phase="applying", block_reason="CANDIDATE_UPDATE_IN_PROGRESS")
            self._save(state)
            return dict(state["transaction"])

    def candidate_applied(self, *, installed: Path) -> None:
        with self._lock():
            state = self._read()
            _require(state["phase"] == "applying", "NOT_APPLYING")
            observed = installed_tree(installed)
            _require(
                observed["sha"] == state["transaction"]["tree"]
                and observed["version"] == state["transaction"]["version"],
                "INSTALLED_BYTES_MISMATCH",
            )
            state["phase"] = "verifying"
            state["block_reason"] = "AWAITING_PER_SESSION_HOST_HEALTH"
            for entry in state["sessions"].values():
                entry["challenge"] = secrets.token_hex(20)
            self._save(state)

    def begin_rollback(self, *, reason: str) -> None:
        """Never restore ready automatically after a failed candidate reload."""
        with self._lock():
            state = self._read()
            _require(
                state["phase"] in ("applying", "verifying", "quiescing"),
                "ROLLBACK_UNAVAILABLE",
            )
            state["phase"] = "rolling_back"
            state["rollback_bytes_verified"] = False
            state["epoch"] += 1  # invalidate all failed candidate attestations
            state["block_reason"] = reason[:160]
            for entry in state["sessions"].values():
                entry["verified_epoch"] = -1
                entry["proof_sha"] = ""
                entry["acked_epoch"] = -1
                entry["challenge"] = secrets.token_hex(20)
            self._save(state)

    def rollback_bytes_restored(self, *, installed: Path) -> None:
        with self._lock():
            state = self._read()
            _require(state["phase"] == "rolling_back", "NOT_ROLLING_BACK")
            observed = installed_tree(installed)
            _require(
                observed["sha"] == state["good_tree"]
                and observed["version"] == state["good_version"],
                "ROLLBACK_BYTES_MISMATCH",
            )
            state["rollback_bytes_verified"] = True
            state["block_reason"] = "ROLLBACK_AWAITING_ALL_SESSION_HEALTH"
            self._save(state)

    def fail_closed(self, reason: str) -> None:
        with self._lock():
            state = self._read()
            state["phase"] = "blocked"
            state["epoch"] += 1
            state["block_reason"] = reason[:160]
            state["transaction"] = None
            state["rollback_bytes_verified"] = False
            for entry in state["sessions"].values():
                entry["verified_epoch"] = -1
                entry["proof_sha"] = ""
                entry["acked_epoch"] = -1
                entry["challenge"] = secrets.token_hex(20)
            self._save(state)

    def status(self) -> dict:
        with self._lock():
            state = self._read()
            return {
                "phase": state["phase"],
                "epoch": state["epoch"],
                "cohort_size": len(state["inventory"]),
                "outstanding_permits": sum(
                    len(entry["permits"]) for entry in state["sessions"].values()
                ),
                "acknowledged": sum(
                    entry["acked_epoch"] == state["epoch"] for entry in state["sessions"].values()
                ),
                "verified": sum(
                    entry["verified_epoch"] == state["epoch"]
                    for entry in state["sessions"].values()
                ),
                "all_sessions_fresh": self._fresh(state, now=self.clock()),
                "protected_native_unregistered_sessions": False,
                "production_wide_guarantee": False,
                "stable_release_authorized": False,
                "block_reason": state["block_reason"],
            }


def fixture_verifier_for_tests_only(
    path: Path, session: str, challenge: str, tree: str, epoch: int
) -> str:
    """Deliberately SYNTHETIC proof reader; NEVER use for genuine host QA."""
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        raise UpdateBlocked("INVALID_TEST_PROOF") from exc
    _require(
        data
        == {
            "session": session,
            "challenge": challenge,
            "tree": tree,
            "epoch": epoch,
            "TEST_ONLY": True,
        },
        "INVALID_TEST_PROOF",
    )
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_isolated_qa_update(
    gate: GuardedRollout,
    *,
    participant_secrets: Mapping[str, str],
    candidate: Path,
    old_source: Path,
    installed: Path,
    native_binary: Path,
    plugin_name: str,
    apply: Callable[[Path, Path], None],
    restore: Callable[[Path, Path], None],
    request_health: Callable[[str, dict], Path],
    verify_health: Callable[[Path, str, str, str, int], str],
    expected_binary_sha: str = NATIVE_CLI304_SHA,
) -> dict:
    """Controlled QA update with automatic compensation; never target a live user profile.

    Before this call, all known participants MUST acknowledge quiescence.
    The callbacks must be trusted implementation code, not model output,
    and every protected operation MUST independently call gate.enter().
    A Native Claude Code process that bypasses the external gate is unprotected.
    A process kill between apply/restore leaves durable blocked state, not safety.
    """
    with gate._lock():  # noqa: SLF001 - internal transaction boundary
        state = gate._read()  # noqa: SLF001
        _require(
            sorted(participant_secrets) == state["inventory"],
            "INCOMPLETE_MANAGED_SESSION_INVENTORY",
        )
        _require(installed_tree(old_source)["sha"] == state["good_tree"], "UNREVIEWED_ROLLBACK")
        _require(installed_tree(installed)["sha"] == state["good_tree"], "BASELINE_INSTALL_DRIFT")
        _require(state["phase"] == "quiescing", "TRANSACTION_NOT_QUIESCED")
    try:
        gate.start_apply(
            candidate=candidate,
            native_binary=native_binary,
            plugin_name=plugin_name,
            expected_native_sha=expected_binary_sha,
        )
        apply(candidate, installed)
        gate.candidate_applied(installed=installed)
        for session, secret in participant_secrets.items():
            challenge = gate.challenge(session, secret)
            receipt = request_health(session, challenge)
            gate.attest(session, secret, receipt, verifier=verify_health)
        gate.ready(installed=installed)
        return {
            "outcome": "candidate_healthy_in_managed_cohort_only",
            "cohort_size": len(participant_secrets),
            "non_cooperative_sessions_protected": False,
            "stable_release_authorized": False,
        }
    except Exception as error:
        # Never promote an update by returning "success" after a failed proof.
        incident = type(error).__name__
        try:
            gate.begin_rollback(reason="UPDATE_OR_PROOF_FAILED")
            restore(old_source, installed)
            gate.rollback_bytes_restored(installed=installed)
            for session, secret in participant_secrets.items():
                challenge = gate.challenge(session, secret)
                receipt = request_health(session, challenge)
                gate.attest(session, secret, receipt, verifier=verify_health)
            gate.ready(installed=installed)
        except Exception:
            gate.fail_closed("ROLLBACK_OR_HOST_HEALTH_FAILED")
            return {
                "outcome": "blocked_requires_manual_recovery",
                "failure_type": incident,
                "phase": gate.status()["phase"],
                "non_cooperative_sessions_protected": False,
                "stable_release_authorized": False,
            }
        return {
            "outcome": "candidate_rejected_old_version_recovered_in_managed_cohort",
            "failure_type": incident,
            "phase": gate.status()["phase"],
            "non_cooperative_sessions_protected": False,
            "stable_release_authorized": False,
        }
