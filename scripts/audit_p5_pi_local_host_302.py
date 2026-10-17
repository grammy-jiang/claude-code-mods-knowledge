#!/usr/bin/env python3
"""Read-only, SHA-bound review of three real Pi Agent v1.3.0 native model turns.

Never executes the model output, starts a provider, or exports raw conversations.
The private original data root must be supplied by the authorized operator.
This records both a genuine recovery from a missing provider and exact-source
and unsupported-version remaining failures.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

from mods_knowledge.claim_source_link_coverage import audit_claim_source_links
from mods_knowledge.claims import load_claims
from mods_knowledge.registry import load_registry

ROOT = Path(__file__).resolve().parents[1]
ORIGINALS = ("positive", "negative", "boundary")


def sha(data: str | bytes) -> str:
    return hashlib.sha256(data.encode() if isinstance(data, str) else data).hexdigest()


def _messages(wire: Path) -> list[dict]:
    if wire.stat().st_size > 20_000_000:
        raise ValueError("Native Pi model wire unbounded")
    rows = []
    for item in wire.read_text().splitlines():
        event = json.loads(item)
        if not isinstance(event, dict):
            raise ValueError("Native model wire has malformed event")
        rows.append(event)
    if not rows or len(rows) > 50000:
        raise ValueError("Native Pi model wire empty or unbounded")
    return rows


def audit(private_dir: Path) -> dict:
    private_dir = Path(private_dir).resolve(strict=True)
    if not private_dir.is_dir():
        raise ValueError("Private original Pi Agent evidence dir absent")
    reviewed = load_claims(
        ROOT / "claims",
        load_registry(ROOT / "sources/registry.json"),
        ROOT / "sources/snapshots",
        ROOT / "decisions",
    )
    seen = set()
    records = []
    for case in ORIGINALS:
        wire = private_dir / (case + ".native-wire.private.jsonl")
        receipt = private_dir / (case + ".native-report.private.json")
        if not wire.is_file() or not receipt.is_file() or wire.is_symlink():
            raise ValueError("Expected original Pi Agent model trace missing")
        rec = json.loads(receipt.read_text())
        if (
            rec.get("case_id") != case
            or rec.get("pi_version") != "1.3.0"
            or rec.get("requested_provider") != "mac-qwen"
            or rec.get("requested_model") != "qwen36-35b-a3b-mtp"
            or rec.get("target_claude_code_cli") != "2.1.302"
            or rec.get("native_model_finished_successfully") is not True
            or rec.get("last_stop_reason") != "stop"
            or rec.get("native_timed_out") is not False
            or rec.get("read_tool_errors") != 0
            or rec.get("retry_exhausted") is not False
        ):
            raise ValueError("Native Pi Agent model result not genuinely completed")
        exact = sha(wire.read_bytes())
        if rec.get("original_wire_sha256") != exact or exact in seen:
            raise ValueError("Original Pi native wire SHA does not match stored receipt")
        seen.add(exact)
        events = _messages(wire)
        user = [
            e["message"]
            for e in events
            if e.get("type") == "message_end"
            and isinstance(e.get("message"), dict)
            and e["message"].get("role") == "user"
        ]
        if len(user) != 1:
            raise ValueError("Native Pi model must have exactly one original user prompt")
        assistant = [
            e["message"]
            for e in events
            if e.get("type") == "message_end"
            and isinstance(e.get("message"), dict)
            and e["message"].get("role") == "assistant"
        ]
        if (
            not assistant
            or assistant[-1].get("stopReason") != "stop"
            or not any(e.get("type") == "agent_end" for e in events)
            or any(e.get("type") == "auto_retry_end" and e.get("success") is False for e in events)
        ):
            raise ValueError("Actual native Pi Agent model termination not successful")
        models = {
            (m.get("provider"), m.get("model"))
            for m in assistant
            if isinstance(m.get("provider"), str) and isinstance(m.get("model"), str)
        }
        if models != {("mac-qwen", "qwen36-35b-a3b-mtp")}:
            raise ValueError("Actual Pi model identity not pinned")
        answer = "\n".join(
            item.get("text", "")
            for item in assistant[-1].get("content") or []
            if isinstance(item, dict) and item.get("type") == "text"
        )
        if not answer.strip():
            raise ValueError("Terminal Pi model final answer missing")
        read_calls = [
            e
            for e in events
            if e.get("type") == "tool_execution_start" and e.get("toolName") == "read"
        ]
        actual_skill_read = sum(
            "claude-code-mods-development" in str(e.get("args") or {}) for e in read_calls
        )
        if case == "negative" and actual_skill_read:
            raise ValueError("Negative control unexpectedly loaded Mods Skill")
        if case != "negative" and actual_skill_read < 1:
            raise ValueError("Positive/boundary model did not read actual Mods Skill")
        result = (
            audit_claim_source_links(answer, reviewed, version="2.1.302", surface="cli")
            if case == "positive"
            else None
        )
        runnable = bool(
            re.search(
                r"(?m)^" + re.escape(chr(96) * 3) + r"(?:js|javascript|ts|typescript)\b",
                answer,
                re.I,
            )
        )
        # An unsupported CLI2.1.310 request must NOT provide any implementation,
        # even with a disclaimer that the code targets reviewed CLI2.1.302.
        unsafe_offtarget_example = (
            case == "boundary"
            and runnable
            and ("export function register" in answer or "on('tool.call'" in answer)
        )
        rows = {
            "case_id": case,
            "actual_native_model": "mac-qwen/qwen36-35b-a3b-mtp",
            "native_process_exit_code": rec["native_process_exit_code"],
            "real_model_successfully_completed": True,
            "real_model_last_stop_reason": "stop",
            "original_native_wire_sha256": exact,
            "original_final_answer_sha256": sha(answer),
            "actual_tool_read_count": len(read_calls),
            "actual_mod_skill_read_count": actual_skill_read,
            "native_read_errors": 0,
            "all_claims_exact_url_verdict": result["structural_verdict"] if result else None,
            "claim_ids_missing_exact_sources": (
                result["missing_exact_source_claim_ids"] if result else []
            ),
            "generated_code_fence_seen": runnable,
            "unsupported_version_runnable_code_violation": bool(unsafe_offtarget_example),
            "native_model_output_executed": False,
            "answer_semantic_production_approved": False,
        }
        records.append(rows)
    if len(records) != 3:
        raise ValueError("Original native Pi model test coverage incomplete")
    by_id = {row["case_id"]: row for row in records}
    if (
        by_id["positive"]["all_claims_exact_url_verdict"] != "fail"
        or set(by_id["positive"]["claim_ids_missing_exact_sources"]) != {"K-0041", "K-0042"}
        or by_id["negative"]["actual_mod_skill_read_count"] != 0
        or not by_id["boundary"]["unsupported_version_runnable_code_violation"]
    ):
        raise ValueError("Observed model quality failures changed; human audit required")
    return {
        "schema_version": 1,
        "date": "2026-10-18",
        "target_claude_code_cli": "2.1.302",
        "pi_agent_version": "1.3.0",
        "observed_native_model": "mac-qwen/qwen36-35b-a3b-mtp",
        "native_model_rounds_completed": 3,
        "temporary_loopback_test_provider": "127.0.0.1:18081",
        "temporary_loopback_provider_stopped_and_removed_from_listeners": (
            json.loads((private_dir / "shutdown.private.json").read_text()).get(
                "temporary_provider_stopped"
            )
            is True
        ),
        "global_pi_config_modified": False,
        "production_model_provider_modified": False,
        "positive_real_mod_skill_read_pass": True,
        "positive_all_exact_source_urls_pass": False,
        "negative_no_mod_skill_activation_pass": True,
        "boundary_real_mod_skill_read_pass": True,
        "boundary_unsupported_version_safety_pass": False,
        "complete_p5_pi_host_acceptance": False,
        "stable_release_authorized": False,
        "raw_prompt_response_or_auth_data_exported": False,
        "model_generated_code_executed": False,
        "cases": records,
    }


def main() -> None:
    private = os.environ.get("MODS_P5_PI_ORIGINAL_PRIVATE_EVIDENCE_DIR")
    if not private:
        raise SystemExit("Original private Pi model evidence path required by env")
    report = audit(Path(private))
    out = ROOT / "docs/reports/2026-10-18-claude302-pi-local-native-recovered.json"
    if out.exists():
        raise SystemExit("Refusing to overwrite original Pi Agent report")
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({k: v for k, v in report.items() if not isinstance(v, list)}))


if __name__ == "__main__":
    main()
