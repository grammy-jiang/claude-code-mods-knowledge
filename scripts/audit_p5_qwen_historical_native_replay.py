#!/usr/bin/env python3
"""Offline-only re-audit of THREE real historical Qwen native Pi completions.

This never starts Pi, a browser, a model server, an MCP connection, or any
user-generated code. It verifies canonical original private full Pi JSON
and assistant response SHA256s against the unchanged public historical
report, then applies the reviewed current CLI302 buffered gate. It emits
ONLY non-sensitive hashes, model/release metadata and gate reason codes.

A historical source/model result evaluated under updated delivery rules is
NOT a newly completed Qwen inference or a production semantic guarantee.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

from mods_knowledge.claims import load_claims
from mods_knowledge.pi_delivery_gate import postflight_mods_case, preflight_mods_case
from mods_knowledge.registry import load_registry

ROOT = Path(__file__).resolve().parents[1]
HISTORICAL = ROOT / "docs/reports/2026-10-18-claude302-pi-local-native-recovered.json"
ORIGINAL = {
    "positive": "POS-E-01",
    "negative": "NEG-TYPESCRIPT",
    "boundary": "BOUND-VERSION-NEW",
}
SOURCE_TARGET = "2.1.302"
MODEL = "qwen36-35b-a3b-mtp"
PROVIDER = "mac-qwen"


class HistoricalQwenReplayBlocked(ValueError):
    """Original full native wire, user prompt, model, or SHA proof is invalid."""


def digest(data: bytes | str) -> str:
    return hashlib.sha256(data.encode() if isinstance(data, str) else data).hexdigest()


def _read_json(path: Path) -> dict:
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 256_000:
        raise HistoricalQwenReplayBlocked("Source report or evidence missing")
    obj = json.loads(path.read_text())
    if not isinstance(obj, dict):
        raise HistoricalQwenReplayBlocked("Expected JSON report object")
    return obj


def verify_original_trace(
    raw_wire: bytes, *, expected_wire_sha256: str, expected_answer_sha256: str
) -> tuple[list[dict], str, str]:
    """Prove the original full wire and last answer match frozen public hashes."""
    if (
        not isinstance(raw_wire, bytes)
        or not 100 <= len(raw_wire) <= 6_000_000
        or not re.fullmatch(r"[a-f0-9]{64}", expected_wire_sha256)
        or not re.fullmatch(r"[a-f0-9]{64}", expected_answer_sha256)
        or digest(raw_wire) != expected_wire_sha256
    ):
        raise HistoricalQwenReplayBlocked("Original native wire SHA mismatch")
    try:
        events = [json.loads(line) for line in raw_wire.splitlines() if line.strip()]
    except (ValueError, UnicodeError) as exc:
        raise HistoricalQwenReplayBlocked("Original native trace is not JSONL") from exc
    if not events or len(events) > 7000 or not all(isinstance(x, dict) for x in events):
        raise HistoricalQwenReplayBlocked("Original model events are malformed")
    replies = []
    users = []
    for event in events:
        if event.get("type") != "message_end":
            continue
        message = event.get("message") or {}
        if not isinstance(message, dict):
            continue
        content = message.get("content") or []
        if not isinstance(content, list):
            continue
        text = "".join(
            item.get("text") or ""
            for item in content
            if isinstance(item, dict)
            and item.get("type") == "text"
            and isinstance(item.get("text"), str)
        )
        if message.get("role") == "assistant" and text.strip():
            replies.append((text, message.get("stopReason")))
        if message.get("role") == "user":
            users.append(text)
    if (
        len(users) != 1
        or "TASK_ID:" not in users[0]
        or not replies
        or replies[-1][1] != "stop"
        or digest(replies[-1][0]) != expected_answer_sha256
    ):
        raise HistoricalQwenReplayBlocked("Original model final answer SHA/stop mismatch")
    return events, users[0], replies[-1][0]


def _original_skill_root(events: list[dict]) -> str:
    roots = set()
    for e in events:
        if e.get("type") != "tool_execution_start" or e.get("toolName") != "read":
            continue
        path = (e.get("args") or {}).get("path")
        if (
            isinstance(path, str)
            and "/claude-code-mods-development/" in path
            and path.startswith("/")
        ):
            roots.add(
                path.split("/claude-code-mods-development/")[0] + "/claude-code-mods-development"
            )
    if len(roots) > 1:
        raise HistoricalQwenReplayBlocked("Conflicting scoped original native Skill roots")
    return next(
        iter(roots), "/private/legacy-observation-no-skill-read/claude-code-mods-development"
    )


def _head(root: Path) -> str:
    executable = shutil.which("git")
    if executable is None:
        raise HistoricalQwenReplayBlocked("Local Git binary unavailable")
    result = subprocess.run(  # noqa: S603 - local Git rev-parse only, no account
        [executable, "-C", str(root), "rev-parse", "HEAD"],
        capture_output=True,
        check=True,
        text=True,
        timeout=8,
    ).stdout.strip()
    if not re.fullmatch(r"[0-9a-f]{40}", result):
        raise HistoricalQwenReplayBlocked("Reviewed source commit is missing")
    return result


def audit(private_root: Path, *, reviewed_root: Path = ROOT) -> dict:
    old = _read_json(reviewed_root / HISTORICAL.relative_to(ROOT))
    if (
        old.get("target_claude_code_cli") != SOURCE_TARGET
        or old.get("pi_agent_version") != "1.3.0"
        or old.get("observed_native_model") != f"{PROVIDER}/{MODEL}"
        or old.get("native_model_rounds_completed") != 3
        or not isinstance(old.get("cases"), list)
        or {x.get("case_id") for x in old["cases"]} != set(ORIGINAL)
    ):
        raise HistoricalQwenReplayBlocked("Historical public original cohort is not frozen")
    old_by_case = {x["case_id"]: x for x in old["cases"]}
    frozen = _read_json(reviewed_root / "evals/p4_cases_cli_2_1_302.json")
    cases = {x["id"]: x for x in frozen["cases"]}
    if not set(ORIGINAL.values()).issubset(cases):
        raise HistoricalQwenReplayBlocked("Current frozen reviewed native target cases missing")
    sources = load_claims(
        reviewed_root / "claims",
        load_registry(reviewed_root / "sources/registry.json"),
        reviewed_root / "sources/snapshots",
        reviewed_root / "decisions",
    )
    current_evaluator_sha = _head(reviewed_root)
    results = []
    seen_users: set[str] = set()
    for original_label, frozen_case_id in ORIGINAL.items():
        observation = old_by_case[original_label]
        p = private_root / f"{original_label}.native-wire.private.jsonl"
        if not p.is_file() or p.is_symlink() or p.stat().st_size > 6_000_000:
            raise HistoricalQwenReplayBlocked("Original native model wire file is unavailable")
        events, user_prompt, _ = verify_original_trace(
            p.read_bytes(),
            expected_wire_sha256=observation["original_native_wire_sha256"],
            expected_answer_sha256=observation["original_final_answer_sha256"],
        )
        user_fp = digest(user_prompt)
        if user_fp in seen_users:
            raise HistoricalQwenReplayBlocked("Duplicate original native user prompt")
        seen_users.add(user_fp)
        if observation.get("native_process_exit_code") != 0:
            raise HistoricalQwenReplayBlocked("Historical native model did not complete")
        if observation.get("real_model_successfully_completed") is not True:
            raise HistoricalQwenReplayBlocked("Original model completion not authenticated")
        model_observed = {
            (e["message"].get("provider"), e["message"].get("model"))
            for e in events
            if e.get("type") == "message_end"
            and isinstance(e.get("message"), dict)
            and e["message"].get("role") == "assistant"
        }
        if model_observed != {(PROVIDER, MODEL)}:
            raise HistoricalQwenReplayBlocked("Original Qwen model identity is not correct")
        task = {**cases[frozen_case_id], "prompt": user_prompt}
        before = preflight_mods_case(task, target_version=SOURCE_TARGET)
        reevaluation = postflight_mods_case(
            task,
            events,
            claims=sources,
            skill_root=_original_skill_root(events),
            source_revision=current_evaluator_sha,
            provider=PROVIDER,
            model=MODEL,
            pi_version="1.3.0",
            native_exit_code=0,
            timed_out=False,
            native_host="macbook-pro",
            target_version=SOURCE_TARGET,
        )
        expected_outcome = (
            "allow_structural_only" if original_label == "negative" else "block_candidate"
        )
        if reevaluation.get("action") != expected_outcome:
            raise HistoricalQwenReplayBlocked(
                "Genuine historical failure no longer blocked by current gate"
            )
        reasons = reevaluation.get("reason_codes") or []
        if (
            original_label == "positive" and "missing_exact_approved_claim_sources" not in reasons
        ) or (
            original_label == "boundary"
            and (
                "preflight_was_not_enforced" not in reasons
                or before.get("action") != "abstain_before_model"
            )
        ):
            raise HistoricalQwenReplayBlocked("Required positive/boundary safety gate missing")
        if original_label == "negative" and reasons:
            raise HistoricalQwenReplayBlocked("Original unrelated negative incorrectly rejected")
        results.append(
            {
                "case_id": frozen_case_id,
                "original_case_type": original_label,
                "original_native_wire_sha256": observation["original_native_wire_sha256"],
                "original_visible_answer_sha256": observation["original_final_answer_sha256"],
                "original_user_prompt_sha256": user_fp,
                "original_model_and_final_sha_verified": True,
                "prior_genuine_skill_read_count": observation["actual_mod_skill_read_count"],
                "preflight_action_if_current_gate_were_used": before["action"],
                "current_postflight_action": reevaluation["action"],
                "current_postflight_reason_codes": reasons,
                "output_of_historical_model_newly_delivered": False,
                "full_generated_mod_runtime_semantics_verified": False,
            }
        )
    return {
        "schema_version": 1,
        "date": "2026-10-18",
        "scope": "offline replay of existing true native Qwen model completions only",
        "reviewed_current_target": SOURCE_TARGET,
        "native_model": f"{PROVIDER}/{MODEL}",
        "original_historical_genuine_completed_turns": 3,
        "original_model_wire_and_final_sha256_verified": 3,
        "approved_claims_git_revision_at_replay": current_evaluator_sha,
        "offline_replay_verifier_source_sha256": digest(Path(__file__).read_bytes()),
        "original_beta_model_rerun": False,
        "new_model_or_browser_requests_performed": 0,
        "original_tool_payload_refetched_independently": False,
        "positive_exact_source_error_blocked": True,
        "historical_unsupported_future_model_output_blocked": True,
        "unrelated_negative_structural_pass": True,
        "entire_native_qwen_semantics_certified": False,
        "complete_p5_host_acceptance": False,
        "stable_release_authorized": False,
        "original_private_model_answers_prompts_or_paths_exported": False,
        "cases": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists() or args.out.is_symlink():
        raise SystemExit("REFUSED: original historical replay report already exists")
    try:
        report = audit(args.private_root)
    except (
        HistoricalQwenReplayBlocked,
        OSError,
        KeyError,
        ValueError,
        TypeError,
        subprocess.CalledProcessError,
    ):
        raise SystemExit("BLOCKED: genuine native historical evidence mismatch") from None
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    print(
        {
            "new_model_requests": 0,
            "prior_true_native_turns_reverified": report[
                "original_historical_genuine_completed_turns"
            ],
            "positive_missing_claim_url_blocked": report["positive_exact_source_error_blocked"],
            "historical_future_version_output_blocked": report[
                "historical_unsupported_future_model_output_blocked"
            ],
            "negative_structural_only": report["unrelated_negative_structural_pass"],
            "stable_release_authorized": False,
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
