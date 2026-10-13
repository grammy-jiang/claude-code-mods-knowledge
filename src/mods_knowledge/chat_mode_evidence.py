"""Sanitized ChatGPT **Chat-mode** Skill activation evidence.

Transforms a real, already-fetched conversation into auditable, conservative
structural checks. No account access, model call or network is in this module.
A static answer-shape PASS is not an independent semantic code review.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping

PLUGIN_SKILL_URI = "skills://plugins/claude-code-mods-knowledge/claude-code-mods-development"
HOOK_CALLBACK_RE = re.compile(
    r"on\s*\(\s*['\"]tool\.call['\"]\s*,\s*async\s*"
    r"\(\s*\$\s*,\s*e\s*,\s*next\s*\)"
)
CLAIM_ID = re.compile(r"K-[0-9]{4,}\b")
SEMVER = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.-]+)?\Z")


class ChatEvidenceError(ValueError):
    """A Chat-mode QA observation could not be summarized safely."""


def _sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def summarize_chat_mode_case(
    case: Mapping,
    plugin_version: str,
    conversation_id: str,
    reply: str,
    messages: list[dict],
) -> dict:
    """Summarize one Chat-mode QA case; preserve no raw account content."""
    if not isinstance(plugin_version, str) or not SEMVER.fullmatch(plugin_version):
        raise ChatEvidenceError("Chat evidence requires an exact plugin version")
    if (
        not isinstance(case, Mapping)
        or not isinstance(case.get("id"), str)
        or not isinstance(case.get("category"), str)
        or not isinstance(conversation_id, str)
        or not conversation_id.strip()
        or not isinstance(reply, str)
        or not reply.strip()
        or not isinstance(messages, list)
    ):
        raise ChatEvidenceError("Invalid Chat-mode conversation evidence input")
    read_uris: set[str] = set()
    skill_plugin_ids: set[str] = set()
    for message in messages:
        if not isinstance(message, dict):
            continue
        author = message.get("author") or {}
        if author.get("role") != "tool" or author.get("name") != "api_tool.read_resource":
            continue
        metadata = message.get("metadata") or {}
        resource = metadata.get("invoked_resource") or {}
        uri = resource.get("resource_uri")
        plugin_id = metadata.get("skill_plugin_id")
        if (
            metadata.get("skill_name") == "claude-code-mods-development"
            and isinstance(uri, str)
            and (uri == PLUGIN_SKILL_URI or uri.startswith(PLUGIN_SKILL_URI + "/"))
            and isinstance(plugin_id, str)
            and plugin_id.startswith("Plugin_")
        ):
            read_uris.add(uri)
            skill_plugin_ids.add(plugin_id)
    skill_loaded = bool(read_uris) and len(skill_plugin_ids) == 1
    category = case["category"]
    observed = sorted(set(CLAIM_ID.findall(reply)))
    expected = set(case.get("expected_claim_ids") or [])
    callback_correct = bool(HOOK_CALLBACK_RE.search(reply))
    official_cited = "https://code.claude.com/docs/en/plugins/mods/" in reply
    flags: list[str] = []
    if category == "negative":
        if skill_loaded:
            quality = "fail"
            flags.append("unexpected-plugin-activation")
        else:
            quality = "pass"
            flags.append("nonactivation-observed")
    elif category == "positive":
        if not skill_loaded:
            flags.append("missing-skill-resource-read")
        missing = expected - set(observed)
        if missing:
            flags.append("missing-expected-claim-ids")
        if not official_cited:
            flags.append("missing-official-source-link")
        if case["id"] == "POS-E-01" and not callback_correct:
            flags.append("missing-hook-first-argument")
        quality = "fail" if flags else "pass"
    else:
        if not skill_loaded and case.get("expected_activation"):
            flags.append("missing-skill-resource-read")
        # Context-sensitive abstention/permissions cannot be graded by simple regex.
        quality = "inconclusive" if not flags else "fail"
        flags.append("manual-semantic-review-required")
    result = {
        "case_id": case["id"],
        "category": category,
        "plugin_version": plugin_version,
        "conversation_sha256": _sha(conversation_id),
        "response_sha256": _sha(reply),
        "plugin_id_sha256": _sha(next(iter(skill_plugin_ids))) if skill_loaded else None,
        "skill_loaded": skill_loaded,
        "resource_uris": sorted(read_uris),
        "expected_activation": case.get("expected_activation"),
        "observed_claim_ids": observed,
        "official_source_cited": official_cited,
        "code_callback_signature_correct": callback_correct if case["id"] == "POS-E-01" else None,
        "answer_quality": quality,
        "quality_flags": flags,
        "notes": (
            "Observed in authenticated ChatGPT Chat mode; checks are structural "
            "only and do not establish complete API correctness."
        ),
    }
    return result
