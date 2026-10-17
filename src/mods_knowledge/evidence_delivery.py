"""P5 Skill-side task evidence for an explicitly controlled Codex thread.

No model changes, hosted API requests, source mutation or automatic host
installation. Context is data derived from the existing reviewed SSOT.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping

from .task_evidence import EvidenceSelectionError, render_evidence_pack

MAX_CONTEXT_CHARS = 6200


def make_verified_task_context(selection: Mapping) -> str:
    """Render an independently reviewed, version-pinned Skill context.

    This text is submitted through the native Codex App Server thread
    developerInstructions field without changing the frozen USER prompt.
    It does not assert that the model actually used the supplied evidence.
    """
    if not isinstance(selection, Mapping) or selection.get("intent") != "mods":
        raise EvidenceSelectionError("Only approved Mods tasks may receive task evidence")
    content = render_evidence_pack(selection)
    wrapped = (
        "Task-specific, source-verified context supplied by the local "
        "claude-code-mods-development Skill runner.\n"
        "The target is Claude Code CLI 2.1.296 only. Other versions "
        "and host surfaces are unreviewed.\n"
        "Use only the relevant approved atomic Claim IDs and exact official "
        "documentation URLs, including their URL fragments. "
        "Do not substitute other Claims or invent URLs. "
        "If the evidence does not support a requested API, abstain. "
        "The original user question is supplied separately and has not been changed. "
        "Correct citations alone do not prove executable Mod code semantics.\n"
        "\n" + content
    )
    if not 0 < len(wrapped) <= MAX_CONTEXT_CHARS:
        raise EvidenceSelectionError("Task evidence exceeds bounded Codex context")
    return wrapped


def evidence_fingerprint(text: str) -> str:
    if not isinstance(text, str) or not 0 < len(text) <= MAX_CONTEXT_CHARS:
        raise EvidenceSelectionError("Invalid bounded native Skill context")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
