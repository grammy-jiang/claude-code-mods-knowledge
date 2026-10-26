#!/usr/bin/env python3
"""Prepare a version-scoped, opt-in text-directed request for installed ChatGPT Plugin.

This is a reliable, audited user/agent-controlled fallback when ChatGPT's
model-mediated automatic skill routing is unreliable. It DOES NOT auto-invoke
a ChatGPT plugin, send a Chat Mode request, or prove source/model correctness.

Only use for genuinely Claude Code Mods-related tasks: the output explicitly
requests the installed Claude Code Mods Plugin/Skill from ChatGPT. Never add
the prefix to unrelated programming/general tasks or use the output in the
original automatic-mode 46-case test denominator.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

from mods_knowledge.claims import approved_claims, load_claims
from mods_knowledge.registry import load_registry

ROOT = Path(__file__).resolve().parents[1]
SUPPORTED_VERSION = "2.1.302"
PLUGIN = "claude-code-mods-knowledge"
SKILL = "claude-code-mods-development"
MAX_INPUT_BYTES = 12_000
TESTED_PREFIX = (
    "For this Claude Code Mods task, use my installed claude-code-mods-knowledge "
    "Plugin and its claude-code-mods-development Skill. Actually read the "
    "applicable official reference pages before citing any K-Claim. "
    "Do not infer CLI 2.1.310 compatibility from older Claims. "
    "The technical task is:\n\n"
)


class ScopeRequestBlocked(ValueError):
    """Unsafe or unsupported request would misroute a ChatGPT plugin."""


def compose(question: str, *, target_version: str, approved_count: int) -> str:
    """Require a version-matched Skill and a nonempty explicit task."""
    if target_version != SUPPORTED_VERSION or approved_count != 31:
        raise ScopeRequestBlocked("NO_APPROVED_TARGET_PLUGIN_FOR_REQUESTED_VERSION")
    if (
        not isinstance(question, str)
        or not question.strip()
        or len(question.encode("utf-8")) > MAX_INPUT_BYTES
        or "\x00" in question
    ):
        raise ScopeRequestBlocked("INVALID_OR_UNBOUNDED_SOURCE_USER_REQUEST")
    return TESTED_PREFIX + question


def approved_count(root: Path, target_version: str) -> int:
    registry = load_registry(root / "sources/registry.json")
    claims = load_claims(root / "claims", registry, root / "sources/snapshots", root / "decisions")
    return len(approved_claims(claims, target_version, "cli"))


def create_private_request(input_file: Path, out: Path, *, target: str, root: Path) -> dict:
    if not input_file.is_file() or input_file.is_symlink():
        raise ScopeRequestBlocked("ORIGINAL_USER_INPUT_MISSING_OR_UNSAFE")
    if not out.parent.is_dir() or out.is_symlink() or out.exists():
        raise ScopeRequestBlocked("OUTPUT_ALREADY_EXISTS_OR_UNSAFE")
    try:
        out.resolve().relative_to(root.resolve())
    except ValueError:
        pass
    else:
        raise ScopeRequestBlocked("REFUSE_STORING_PERSONAL_QUESTION_IN_PROJECT_REPO")
    raw = input_file.read_bytes()
    if not 0 < len(raw) <= MAX_INPUT_BYTES:
        raise ScopeRequestBlocked("INPUT_FILE_NOT_BOUNDED")
    try:
        question = raw.decode("utf-8")
    except UnicodeError as exc:
        raise ScopeRequestBlocked("INPUT_MUST_BE_UTF8_TEXT") from exc
    text = compose(question, target_version=target, approved_count=approved_count(root, target))
    descriptor = os.open(out, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        stream.write(text)
    return {
        "status": "private_text_directed_request_prepared",
        "source_target_cli": target,
        "plugin_name": PLUGIN,
        "skill_name": SKILL,
        "original_input_sha256": hashlib.sha256(raw).hexdigest(),
        "result_prompt_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "changes_original_question_text": False,
        "adds_explicit_plugin_use_request": True,
        "composer_system_hint_added": False,
        "counts_as_native_model_auto_routing": False,
        "actually_sent_to_chatgpt": False,
        "real_model_or_semantic_quality_verified": False,
        "stable_release_authorized": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--target-version", required=True)
    ap.add_argument("--root", default=ROOT, type=Path)
    args = ap.parse_args()
    try:
        result = create_private_request(
            args.input, args.out, target=args.target_version, root=args.root
        )
    except (ScopeRequestBlocked, ValueError, KeyError, TypeError, OSError):
        raise SystemExit("BLOCKED: unsupported Mods target or unsafe private request") from None
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
