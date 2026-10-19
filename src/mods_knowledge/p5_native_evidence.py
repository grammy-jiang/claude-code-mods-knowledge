"""Fail-closed native P5 model acceptance evidence for Codex and Pi Agent.

Purely reads caller-supplied *private* native events, never starts a model or
echoes prompts/replies, user file paths, conversation/thread IDs or secrets.
A model returning a credible code sample is not a runtime/semantic PASS.
"""

from __future__ import annotations

import hashlib
import json
import re
import shlex
from collections.abc import Mapping, Sequence
from pathlib import Path

from .answer_lint import lint_mods_answer
from .claim_source_link_coverage import audit_claim_source_links
from .pi_model_evidence import summarize_pi_model_trace

_REV = re.compile(r"[0-9a-f]{40}\Z")
_VER = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+\Z")
_MODEL = re.compile(r"[A-Za-z0-9_.:-]{1,96}\Z")
_CASE = re.compile(r"[A-Z][A-Z0-9_-]{3,60}\Z")
_HOSTS = {"macbook-pro", "raspberry-pi", "sextant"}
_AGENTS = {"codex", "pi"}
_SKILL = "claude-code-mods-development"


class NativeP5EvidenceError(ValueError):
    """Input cannot be safely scored or has a broken evidence envelope."""


def _case_check(case: Mapping, source_revision: str, host: str, cli_version: str) -> None:
    if (
        not isinstance(case, Mapping)
        or not isinstance(case.get("id"), str)
        or not _CASE.fullmatch(case["id"])
        or case.get("category") not in {"positive", "negative", "boundary"}
        or not isinstance(case.get("prompt"), str)
        or not case["prompt"].strip()
        or type(case.get("expected_activation")) is not bool
        or not isinstance(source_revision, str)
        or not _REV.fullmatch(source_revision)
        or host not in _HOSTS
        or not isinstance(cli_version, str)
        or not _VER.fullmatch(cli_version)
    ):
        raise NativeP5EvidenceError("Invalid native evidence scope")


def _text_content(value: object) -> str:
    if not isinstance(value, list):
        return ""
    return "\n".join(
        item["text"]
        for item in value
        if isinstance(item, Mapping)
        and item.get("type") == "text"
        and isinstance(item.get("text"), str)
    )


def _codex_valid_read(
    item: Mapping, skill_root: str, *, verified_cwd: str | None = None
) -> tuple[bool, bool]:
    """Recognize an actually *completed* read command, not a mention of a path.

    We deliberately do not parse complex shell pipelines or claim that
    anything else is a successful Skill read. A false negative is preferable
    to laundering narrative or failed commands into loader evidence.
    """
    if (
        item.get("type") != "commandExecution"
        or item.get("status") != "completed"
        or item.get("exitCode") != 0
        or not isinstance(item.get("aggregatedOutput"), str)
        or not item["aggregatedOutput"].strip()
    ):
        return False, False
    cmd = item.get("command")
    if not isinstance(cmd, str) or len(cmd) > 4000:
        return False, False
    # Current native Codex shell commands take the form /bin/zsh -lc '<cmd>'.
    try:
        args = shlex.split(cmd)
        if len(args) >= 3 and args[0].endswith(("/zsh", "/bash", "/sh")) and args[1] == "-lc":
            args = shlex.split(args[2])
        if not args or args[0] not in {"cat", "sed", "head", "tail"}:
            return False, False
        # Multi-command shell syntax is not independently attributable to
        # this read action. Reject it instead of guessing what ran.
        if any(
            token in {";", "|", "||", "&&", "&", ">", ">>", "<"} or "$(" in token or "`" in token
            for token in args
        ):
            return False, False
    except ValueError:
        return False, False

    def safe_path(path: str) -> tuple[bool, bool]:
        # Old absolute-path behavior remains unchanged. For new isolated
        # Codex HOME, allow relative reads only if same-thread thread/start
        # AND thread/read both attest cwd. Resolve symlinks and compare the
        # actual file under the candidate's root: no guessing based on a
        # textual substring in a shell command.
        if not path.startswith(skill_root + "/"):
            if not verified_cwd or Path(path).is_absolute():
                return False, False
            try:
                resolved = (Path(verified_cwd) / path).resolve(strict=True)
                root = Path(skill_root).resolve(strict=True)
                rel = resolved.relative_to(root).as_posix()
            except (OSError, ValueError):
                return False, False
        else:
            rel = path[len(skill_root) + 1 :]
        if rel == "SKILL.md":
            return True, False
        if re.fullmatch(r"references/[A-Za-z0-9_-]+\.md", rel):
            return False, True
        return False, False

    found_skill = found_reference = False
    for arg in args[1:]:
        main, ref = safe_path(arg)
        found_skill |= main
        found_reference |= ref
    return found_skill, found_reference


def _source_and_lint(
    case: Mapping,
    answer: str,
    claims: Mapping[str, dict],
    *,
    target_version: str = "2.1.296",
) -> dict:
    if not answer.strip():
        return {
            "source_verdict": "not_observed",
            "missing_exact_source_claim_ids": [],
            "uncited_required_claim_ids": [],
            "unsupported_claim_ids": [],
            "risk_flags": [],
            "manual_review_flags": [],
        }
    links = audit_claim_source_links(
        answer,
        claims,
        version=target_version,
        surface="cli",
        required_claim_ids=case.get("expected_claim_ids", []),
    )
    lint = lint_mods_answer(answer, case_id=case["id"], target_version=target_version)
    manual = set(lint["requires_manual_review"])
    if (
        case.get("category") == "boundary"
        and "without checking" in case.get("prompt", "").lower()
        and any(
            token in answer
            for token in (
                "export function",
                "export const",
                "claude plugin test",
                "claude plugin validate",
                "on('tool.call'",
                'on("tool.call"',
            )
        )
    ):
        manual.add("unreviewed-version-implementation-present")
    return {
        "source_verdict": links["structural_verdict"],
        "missing_exact_source_claim_ids": links["missing_exact_source_claim_ids"],
        "uncited_required_claim_ids": links["uncited_required_claim_ids"],
        "unsupported_claim_ids": links["unsupported_claim_ids"],
        "risk_flags": lint["risk_flags"],
        "manual_review_flags": sorted(manual),
    }


def summarize_codex_native_trace(
    case: Mapping,
    wire_events: Sequence[dict],
    *,
    source_revision: str,
    host: str,
    cli_version: str,
    skill_root: str,
    claims: Mapping[str, dict],
    expected_model: str = "gpt-6.1-sol",
    expected_effort: str = "medium",
    allow_isolated_relative_skills: bool = False,
    target_version: str = "2.1.296",
) -> dict:
    """Check a *same-thread* native App Server model turn + resolved identity.

    The input is the native JSON-RPC response/event stream from thread/start,
    turn/start, turn/completed and thread/read on the SAME living process.
    A bare codex exec --json or a model/list entry cannot satisfy it.
    """
    _case_check(case, source_revision, host, cli_version)
    if target_version not in ("2.1.296", "2.1.302"):
        raise NativeP5EvidenceError("Unknown reviewed native target version")
    if (
        not isinstance(wire_events, (list, tuple))
        or len(wire_events) > 100_000
        or not all(isinstance(e, Mapping) for e in wire_events)
        or not isinstance(skill_root, str)
        or not skill_root.startswith("/")
        or not skill_root.endswith("/" + _SKILL)
        or "/../" in skill_root
        or not all(
            isinstance(v, str) and _MODEL.fullmatch(v) for v in (expected_model, expected_effort)
        )
        or not isinstance(claims, Mapping)
    ):
        raise NativeP5EvidenceError("Invalid Codex native event stream or expected scope")
    starts = [x.get("result") for x in wire_events if x.get("id") == 2 and "result" in x]
    reads = [x.get("result") for x in wire_events if x.get("id") == 4 and "result" in x]
    if len(starts) != 1 or len(reads) != 1:
        # Unknown provenance must be an explicit BLOCK, not a provenance PASS.
        start = readback = {}
    else:
        start, readback = starts[0], reads[0]
    start_thread = start.get("thread", {}) if isinstance(start, Mapping) else {}
    thread = readback.get("thread", {}) if isinstance(readback, Mapping) else {}
    sid = start_thread.get("id") if isinstance(start_thread, Mapping) else None
    thread_match = isinstance(sid, str) and len(sid) >= 8 and thread.get("id") == sid
    resolved = (
        thread_match
        and start.get("model") == thread.get("model") == expected_model
        and start.get("modelProvider") == thread.get("modelProvider") == "openai"
        and start.get("reasoningEffort") == thread.get("reasoningEffort") == expected_effort
        and thread.get("cliVersion") == cli_version
        and thread.get("ephemeral") is True
    )
    turns_started = [
        e.get("params", {}).get("turn", {})
        for e in wire_events
        if e.get("method") == "turn/started" and e.get("params", {}).get("threadId") == sid
    ]
    turns_completed = [
        e.get("params", {}).get("turn", {})
        for e in wire_events
        if e.get("method") == "turn/completed" and e.get("params", {}).get("threadId") == sid
    ]
    turn_ok = (
        len(turns_started) == len(turns_completed) == 1
        and isinstance(turns_started[0], Mapping)
        and isinstance(turns_completed[0], Mapping)
        and turns_started[0].get("id") == turns_completed[0].get("id")
        and turns_completed[0].get("status") == "completed"
    )
    verified_cwd = None
    if allow_isolated_relative_skills:
        # Two actual native App Server replies must agree with the unique
        # disposable skill root. This opt-in never reclassifies the old
        # global Skill or accepts a path outside the scoped workspace.
        from pathlib import Path as _Path

        expected_cwd = str(_Path(skill_root).parent.parent.parent)
        if start_thread.get("cwd") == thread.get("cwd") == expected_cwd:
            verified_cwd = expected_cwd
    user_texts: list[str] = []
    answer_segments: list[str] = []
    actual_read = False
    reference_read = False
    read_commands = 0
    for e in wire_events:
        if e.get("method") != "item/completed" or e.get("params", {}).get("threadId") != sid:
            continue
        item = e.get("params", {}).get("item")
        if not isinstance(item, Mapping):
            continue
        if item.get("type") == "userMessage":
            user_texts.append(_text_content(item.get("content")))
        elif item.get("type") == "agentMessage" and isinstance(item.get("text"), str):
            if item["text"].strip():
                answer_segments.append(item["text"])
        else:
            main, reference = _codex_valid_read(item, skill_root, verified_cwd=verified_cwd)
            if main or reference:
                read_commands += 1
                actual_read |= main
                reference_read |= reference
    prompt_ok = len(user_texts) == 1 and user_texts[0] == case["prompt"]
    answer = "\n".join(answer_segments)
    support = _source_and_lint(case, answer, claims, target_version=target_version)
    complete = bool(turn_ok and answer.strip() and prompt_ok)
    if not resolved or not prompt_ok:
        verdict = "invalid_provenance"
    elif not complete:
        verdict = "blocked_or_incomplete"
    elif actual_read != case["expected_activation"]:
        verdict = "activation_failed"
    elif case["category"] == "negative":
        verdict = "negative_nonactivation_observed"
    elif case["category"] == "boundary":
        verdict = (
            "boundary_scope_violated"
            if "unreviewed-version-implementation-present" in support["manual_review_flags"]
            else "boundary_manual_review_required"
        )
    elif (
        support["source_verdict"] != "pass"
        or support["risk_flags"]
        or support["manual_review_flags"]
    ):
        verdict = "structural_or_semantic_review_required"
    else:
        verdict = "structural_ok_semantics_unverified"
    raw_sha = hashlib.sha256(
        json.dumps(wire_events, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()
    return {
        "schema_version": 1,
        "case_id": case["id"],
        "agent": "codex",
        "host": host,
        "cli_version": cli_version,
        "source_revision": source_revision,
        "target_version": f"Claude Code CLI {target_version}",
        "model_requested": expected_model,
        "model_server_resolved": expected_model if resolved else None,
        "effort_server_resolved": expected_effort if resolved else None,
        "model_provider_server_resolved": "openai" if resolved else None,
        "model_provenance": "same-thread-app-server-response+thread-read"
        if resolved
        else "unknown",
        "prompt_matched": prompt_ok,
        "agent_completed": turn_ok,
        "answer_present": bool(answer.strip()),
        "answer_sha256": hashlib.sha256(answer.encode()).hexdigest() if answer.strip() else None,
        "skill_loaded": actual_read,
        "reference_read": reference_read,
        "scoped_successful_read_commands": read_commands,
        "expected_activation": case["expected_activation"],
        "semantic_review_complete": False,
        "native_mod_runtime_verified": False,
        "original_wire_sha256": raw_sha,
        "verdict": verdict,
        **support,
    }


def summarize_pi_native_trace(
    case: Mapping,
    events: Sequence[dict],
    *,
    source_revision: str,
    host: str,
    cli_version: str,
    skill_root: str,
    claims: Mapping[str, dict],
    expected_provider: str = "mac-qwen",
    expected_model: str = "qwen36-35b-a3b-mtp",
    model_was_pinned: bool = True,
    target_version: str = "2.1.296",
) -> dict:
    """Extend Pi model evidence with exact version-matched Claim/URL coverage."""
    _case_check(case, source_revision, host, cli_version)
    if target_version not in ("2.1.296", "2.1.302"):
        raise NativeP5EvidenceError("Unknown reviewed Pi evidence target version")
    if not isinstance(events, (list, tuple)) or len(events) > 100_000:
        raise NativeP5EvidenceError("Unbounded Pi event trace")
    report = summarize_pi_model_trace(
        case,
        events,
        expected_provider=expected_provider,
        expected_model=expected_model,
        model_was_pinned=model_was_pinned,
        skill_root=skill_root,
        source_revision=source_revision,
        pi_version=cli_version,
    )
    finals = [
        _text_content(e["message"].get("content"))
        for e in events
        if e.get("type") == "message_end"
        and isinstance(e.get("message"), Mapping)
        and e["message"].get("role") == "assistant"
    ]
    answer = finals[-1] if finals else ""
    support = _source_and_lint(case, answer, claims, target_version=target_version)
    if (
        report["verdict"] == "boundary_manual_review_required"
        and "unreviewed-version-implementation-present" in support["manual_review_flags"]
    ):
        report["verdict"] = "boundary_scope_violated"
    if report["verdict"] == "structural_ok_semantics_unverified" and (
        support["source_verdict"] != "pass"
        or support["risk_flags"]
        or support["manual_review_flags"]
    ):
        report["verdict"] = "structural_or_semantic_review_required"
    # Do not leak local tool paths or model/private raw transcript.
    report["agent"] = "pi"
    report["host"] = host
    report["cli_version"] = cli_version
    report["target_version"] = "Claude Code CLI " + target_version
    report["model_provenance"] = (
        "native-message_end"
        if report["model_pin_matched"] and report["agent_completed"]
        else "invalid"
    )
    report["native_mod_runtime_verified"] = False
    report["original_wire_sha256"] = hashlib.sha256(
        json.dumps(events, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()
    report.update(support)
    return report


def aggregate_native_matrix(
    summaries: Sequence[Mapping],
    *,
    source_revision: str,
    hosts: Sequence[str] = ("macbook-pro", "raspberry-pi", "sextant"),
    agents: Sequence[str] = ("codex", "pi"),
    cases: Sequence[str] = ("POS-E-01", "POS-Q-01", "NEG-TYPESCRIPT", "BOUND-VERSION-NEW"),
) -> dict:
    """Aggregate genuinely observed host/model cases, preserving missing cells."""
    if not isinstance(source_revision, str) or not _REV.fullmatch(source_revision):
        raise NativeP5EvidenceError("Invalid source revision")
    if (
        not isinstance(summaries, (list, tuple))
        or len(summaries) > 100
        or any(not isinstance(x, Mapping) for x in summaries)
        or any(x not in _HOSTS for x in hosts)
        or any(x not in _AGENTS for x in agents)
        or any(not _CASE.fullmatch(x) for x in cases)
        or len(set(hosts)) != len(hosts)
        or len(set(agents)) != len(agents)
        or len(set(cases)) != len(cases)
    ):
        raise NativeP5EvidenceError("Invalid bounded native matrix dimensions")
    rows = {}
    for s in summaries:
        key = (s.get("host"), s.get("agent"), s.get("case_id"))
        if (
            key in rows
            or s.get("source_revision") != source_revision
            or key[0] not in hosts
            or key[1] not in agents
            or key[2] not in cases
            or s.get("semantic_review_complete") is not False
            or s.get("native_mod_runtime_verified") is not False
            or not isinstance(s.get("original_wire_sha256"), str)
            or not re.fullmatch(r"[a-f0-9]{64}", s["original_wire_sha256"])
            or type(s.get("skill_loaded")) is not bool
            or not isinstance(s.get("cli_version"), str)
            or not _VER.fullmatch(s["cli_version"])
            or s.get("model_provenance")
            not in {
                "same-thread-app-server-response+thread-read",
                "native-message_end",
                "invalid",
                "unknown",
            }
            or (
                (s.get("model_server_resolved") or s.get("model_observed")) is not None
                and (
                    not isinstance(s.get("model_server_resolved") or s.get("model_observed"), str)
                    or not re.fullmatch(
                        r"[A-Za-z0-9._:/-]{1,128}",
                        s.get("model_server_resolved") or s.get("model_observed"),
                    )
                )
            )
            or s.get("source_verdict") not in {"pass", "fail", "not_observed"}
            or s.get("verdict")
            not in {
                "invalid_provenance",
                "blocked_or_incomplete",
                "activation_failed",
                "negative_nonactivation_observed",
                "boundary_manual_review_required",
                "boundary_scope_violated",
                "structural_or_semantic_review_required",
                "structural_failed",
                "structural_ok_semantics_unverified",
            }
        ):
            raise NativeP5EvidenceError("Invalid, duplicate or overclaimed matrix observation")
        rows[key] = s
    cells = []
    for host in hosts:
        for agent in agents:
            for case in cases:
                item = rows.get((host, agent, case))
                cells.append(
                    {
                        "host": host,
                        "agent": agent,
                        "case_id": case,
                        "status": item["verdict"] if item else "not_observed",
                        "real_model_trace": bool(item),
                        "model_provenance": item.get("model_provenance") if item else None,
                        "cli_version": item.get("cli_version") if item else None,
                        "model": (
                            (item.get("model_server_resolved") or item.get("model_observed"))
                            if item
                            else None
                        ),
                        "effort": item.get("effort_server_resolved") if item else None,
                        "skill_loaded": item.get("skill_loaded") if item else None,
                        "source_verdict": item.get("source_verdict") if item else None,
                        "evidence_sha256": item.get("original_wire_sha256") if item else None,
                        "native_mod_runtime_verified": False,
                    }
                )
    return {
        "schema_version": 1,
        "source_revision": source_revision,
        "cells": cells,
        "observed": len(rows),
        "missing": len(cells) - len(rows),
        "full_p5_acceptance": False,
        "notes": "Measured model turns are not automatically semantic or production host acceptance",
    }
