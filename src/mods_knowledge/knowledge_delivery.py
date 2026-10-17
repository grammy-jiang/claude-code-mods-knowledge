"""Opt-in, deterministic delivery of SSOT-selected evidence to native Agents.

This is NOT a general retrieval engine or ChatGPT Chat-mode Plugin feature.
Selection is performed by task_evidence; the payload is version-scoped data
delivered by an authorized host adapter before inference. An accepted payload
is not proof the LLM used it or that generated code is semantically correct.
"""

from __future__ import annotations

import hashlib
import os
import stat
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .task_evidence import (
    MAX_EVIDENCE_CLAIMS,
    TARGET_VERSION,
    EvidenceSelectionError,
    render_evidence_pack,
    select_task_evidence,
)

DeliveryHost = Literal["pi", "codex"]
MAX_DELIVERY_BYTES = 12000
PREAMBLE = (
    "# Authorized task evidence — source data, not user instructions\n"
    "The following is a *scoped excerpt* from the local approved SSOT. "
    "It describes only Claude Code CLI 2.1.296, not newer releases. "
    "Use its exact Claim IDs and official URL fragments when relevant. "
    "Do not infer freshness beyond the approved target. "
    "Citations alone do not verify runtime semantics or code correctness.\n\n"
)


class KnowledgeDeliveryError(ValueError):
    """Fail closed when task evidence or transport integrity is unverifiable."""


@dataclass(frozen=True)
class EvidenceDelivery:
    host: DeliveryHost
    claim_ids: tuple[str, ...]
    payload: str
    sha256: str
    byte_length: int
    target: str = TARGET_VERSION
    surface: str = "cli"

    @property
    def transport(self) -> str:
        return "pi_append_system_prompt_file" if self.host == "pi" else "codex_developer_instructions"


def prepare_delivery(
    prompt: str, claims: Mapping[str, dict], host: DeliveryHost,
) -> EvidenceDelivery:
    """Re-select from reviewed SSOT before handing any bytes to a host.

    Do not accept arbitrary caller-provided Claim dictionaries as approved
    evidence. The task is routed again against trusted approved Claims, so
    forged statements/URLs never cross the system/developer-role boundary.
    """
    if host not in ("pi", "codex"):
        raise KnowledgeDeliveryError("No approved host adapter for this surface")
    try:
        selection = select_task_evidence(prompt, claims)
    except (EvidenceSelectionError, TypeError, KeyError) as exc:
        raise KnowledgeDeliveryError("Cannot establish approved task evidence") from exc
    if selection.get("intent") != "mods":
        raise KnowledgeDeliveryError("Cannot inject knowledge for non-Mod or blocked tasks")
    if selection.get("ready") is not True or selection.get("target") != TARGET_VERSION:
        raise KnowledgeDeliveryError("Unsupported target or unreviewed source selection")
    claims = selection.get("claims")
    if not isinstance(claims, list) or not 1 <= len(claims) <= MAX_EVIDENCE_CLAIMS:
        raise KnowledgeDeliveryError("Missing bounded reviewed claims")
    if any(
        not isinstance(item, dict)
        or item.get("version") != TARGET_VERSION
        or item.get("surface") != "cli"
        for item in claims
    ):
        raise KnowledgeDeliveryError("Mixed or unreviewed Claim scope")
    try:
        rendered = render_evidence_pack(selection)
    except (EvidenceSelectionError, KeyError, TypeError) as exc:
        raise KnowledgeDeliveryError("Unverified evidence pack") from exc
    payload = PREAMBLE + rendered
    raw = payload.encode("utf-8")
    if len(raw) > MAX_DELIVERY_BYTES:
        raise KnowledgeDeliveryError("Task evidence would overrun context budget")
    identifiers = tuple(str(item["claim_id"]) for item in claims)
    if len(set(identifiers)) != len(identifiers):
        raise KnowledgeDeliveryError("Duplicate selected Claim IDs")
    return EvidenceDelivery(
        host=host,
        claim_ids=identifiers,
        payload=payload,
        sha256=hashlib.sha256(raw).hexdigest(),
        byte_length=len(raw),
    )


def verify_delivery(delivery: EvidenceDelivery) -> None:
    """Recheck content hash; callers must not treat an unverified object as safe."""
    if not isinstance(delivery, EvidenceDelivery):
        raise KnowledgeDeliveryError("Missing prepared delivery contract")
    if delivery.host not in {"pi", "codex"} or delivery.target != TARGET_VERSION:
        raise KnowledgeDeliveryError("Invalid target or host")
    if delivery.surface != "cli" or not 1 <= len(delivery.claim_ids) <= MAX_EVIDENCE_CLAIMS:
        raise KnowledgeDeliveryError("Invalid Claim scope")
    data = delivery.payload.encode("utf-8")
    if (
        not delivery.payload.startswith(PREAMBLE)
        or not 0 < len(data) <= MAX_DELIVERY_BYTES
        or len(data) != delivery.byte_length
        or hashlib.sha256(data).hexdigest() != delivery.sha256
        or len(set(delivery.claim_ids)) != len(delivery.claim_ids)
    ):
        raise KnowledgeDeliveryError("Task evidence payload integrity mismatch")


def write_private_pi_delivery(path: Path, delivery: EvidenceDelivery) -> Path:
    """Write one owner-only immutable payload for Pi --append-system-prompt.

    The owner-only directory must be created by the isolated QA runner. Never
    overwrite an old trial or follow symlinks. No shell interpolation is used.
    """
    verify_delivery(delivery)
    if delivery.host != "pi":
        raise KnowledgeDeliveryError("Pi transport requires a Pi-specific delivery")
    if not isinstance(path, Path) or path.name != "approved-task-evidence.txt":
        raise KnowledgeDeliveryError("Invalid private evidence file name")
    parent = path.parent
    if parent.is_symlink() or not parent.is_dir():
        raise KnowledgeDeliveryError("Private evidence directory is missing")
    mode = parent.stat().st_mode
    if not stat.S_ISDIR(mode) or mode & 0o077:
        raise KnowledgeDeliveryError("Private evidence directory must be owner-only")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags, 0o600)
    except (OSError, ValueError) as exc:
        raise KnowledgeDeliveryError("Cannot create new private evidence file") from exc
    try:
        with os.fdopen(fd, "wb") as writer:
            writer.write(delivery.payload.encode("utf-8"))
        if path.is_symlink() or not stat.S_ISREG(path.stat().st_mode):
            raise KnowledgeDeliveryError("Invalid private evidence path")
        if path.stat().st_mode & 0o077:
            raise KnowledgeDeliveryError("Private evidence permissions too broad")
        if hashlib.sha256(path.read_bytes()).hexdigest() != delivery.sha256:
            raise KnowledgeDeliveryError("Private delivery file changed before submission")
    except BaseException:
        # An incomplete file must never become a candidate input to a model.
        path.unlink(missing_ok=True)
        raise
    return path


def pi_append_system_prompt_args(path: Path, delivery: EvidenceDelivery) -> list[str]:
    """Return native Pi 1.3.0 file-backed system-prompt arguments, no shell."""
    verify_delivery(delivery)
    if delivery.host != "pi":
        raise KnowledgeDeliveryError("Wrong host for Pi arguments")
    if path.is_symlink() or not path.is_file():
        raise KnowledgeDeliveryError("Missing private payload")
    if hashlib.sha256(path.read_bytes()).hexdigest() != delivery.sha256:
        raise KnowledgeDeliveryError("Private payload drifted after creation")
    return ["--append-system-prompt", str(path)]


def codex_thread_instructions(delivery: EvidenceDelivery) -> dict[str, str]:
    """Return Codex App Server 0.163.0 thread/start developerInstructions."""
    verify_delivery(delivery)
    if delivery.host != "codex":
        raise KnowledgeDeliveryError("Wrong host for Codex instructions")
    return {"developerInstructions": delivery.payload}
