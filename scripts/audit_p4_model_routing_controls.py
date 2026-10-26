#!/usr/bin/env python3
"""Independently replay three native auto model arms and three text-directed controls.

This is genuine private Chat Mode trace QA, not a ChatGPT router feature.
Historical baseline uses already audited 15-case report; unrelated requests
are still separate negative controls. Every model-only arm here failed to
auto-load; every text-directed arm actually loaded the correct account Skill.
Original conversations and account IDs must never be committed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from mods_knowledge.chat_mode_evidence import summarize_chat_mode_case
from mods_knowledge.chat_visible_reply import collect_latest_visible_reply

FROZEN_SUITE_SHA = "372dc392e2efb83e9d922ffa306072bb57a78fddd566a50e91e844aabe82b554"
PRIOR_PUBLIC_SHA = "777a263a2ecdc8fae74ae7131f833b8b94234ba3b7519edd401fed06de6f3534"
PLUGIN_VERSION = "0.4.12-beta.1"
PLUGIN_SKILL_ROOT = "skills://plugins/claude-code-mods-knowledge/claude-code-mods-development"
ARM_INFO = {
    "HIGH-POS-E-01": ("POS-E-01", "gpt-6-thinking", "extended", "automatic"),
    "EXTRA-POS-E-01": ("POS-E-01", "gpt-6-thinking", "max", "automatic"),
    "OLD-POS-E-01": ("POS-E-01", "gpt-5-6-thinking", "standard", "automatic"),
    "NAMED-POS-E-01": ("POS-E-01", "gpt-6-thinking", "standard", "text_directed"),
    "NAMED-POS-T-01": ("POS-T-01", "gpt-6-thinking", "standard", "text_directed"),
    "NAMED-POS-U-01": ("POS-U-01", "gpt-6-thinking", "standard", "text_directed"),
}


class ModelRoutingBlocked(ValueError):
    """Original model routing evidence is unsafe, missing or inconsistent."""


def require(value: bool, reason: str) -> None:
    if not value:
        raise ModelRoutingBlocked(reason)


def sha(raw: bytes | str) -> str:
    return hashlib.sha256(raw.encode() if isinstance(raw, str) else raw).hexdigest()


def safe_json(path: Path, *, max_bytes: int = 6_000_000) -> tuple[dict, str]:
    require(path.is_file() and not path.is_symlink(), "PRIVATE_ORIGINAL_FILE_MISSING")
    require(20 < path.stat().st_size <= max_bytes, "ORIGINAL_EVIDENCE_SIZE_INVALID")
    raw = path.read_bytes()
    value = json.loads(raw)
    require(isinstance(value, dict), "PRIVATE_EVIDENCE_WRONG_TYPE")
    return value, sha(raw)


def chain(conversation: dict) -> list[dict]:
    mapping = conversation.get("mapping")
    node = conversation.get("current_node")
    require(isinstance(mapping, dict) and isinstance(node, str), "NATIVE_CHAT_CHAIN_MISSING")
    out: list[dict] = []
    seen: set[str] = set()
    while node and node in mapping and node not in seen:
        seen.add(node)
        m = mapping[node].get("message") or {}
        require(isinstance(m, dict), "NATIVE_CHAT_MESSAGE_INVALID")
        out.append(m)
        node = mapping[node].get("parent")
    require(1 < len(out) < 500, "NATIVE_CHAT_CHAIN_NOT_BOUNDED")
    out.reverse()
    return out


def native_model_info(messages: list[dict]) -> tuple[list[str], list[str]]:
    models, efforts = set(), set()
    for m in messages:
        if (
            (m.get("author") or {}).get("role") == "assistant"
            and m.get("recipient") in (None, "all")
            and (m.get("content") or {}).get("content_type") == "text"
        ):
            meta = m.get("metadata") or {}
            if meta.get("resolved_model_slug"):
                models.add(meta["resolved_model_slug"])
            if meta.get("thinking_effort"):
                efforts.add(meta["thinking_effort"])
    return sorted(models), sorted(efforts)


def audit(private: Path, suite_file: Path, previous_file: Path, account_file: Path) -> dict:
    require(private.is_dir() and not private.is_symlink(), "PRIVATE_ORIGINAL_MATRIX_MISSING")
    source, source_sha = safe_json(suite_file)
    require(source_sha == FROZEN_SUITE_SHA, "FROZEN_ORIGINAL_PROMPT_SUITE_CHANGED")
    prior, prior_sha = safe_json(previous_file)
    require(
        prior_sha == PRIOR_PUBLIC_SHA
        and prior["plugin_version"] == PLUGIN_VERSION
        and prior["automatic_cases_by_category"]["positive"]["canonical_skill_loads"] == 0
        and prior["explicit_selected_positive_control"]["actual_correct_plugin_resource_reads"]
        == 4,
        "ORIGINAL_FIFTEEN_CASE_BASELINE_NOT_VERIFIED",
    )
    account = account_file.read_text()
    require(
        "version 0.4.12-beta.1, status ENABLED, installed yes" in account,
        "ACTUAL_PERSONAL_PLUGIN_VERSION_NOT_READ",
    )
    m = re.search(r"\bid\s+(Plugin_[a-f0-9]{32})", account)
    require(m is not None, "INSTALLED_ACCOUNT_PLUGIN_INSTANCE_UNVERIFIED")
    selected_id = m.group(1)
    require(sha(selected_id) == prior["account_plugin_instance_sha256"], "PLUGIN_INSTANCE_CHANGED")
    cases = {item["id"]: item for item in source["cases"]}
    outcome = []
    sent_ids: set[str] = set()
    for arm, (case_id, model, effort, mode) in ARM_INFO.items():
        receipt, receipt_sha = safe_json(private / f"sends/{arm}.private.json")
        require(
            receipt["model"] == model
            and receipt["effort"] == effort
            and receipt.get("system_hints") == []
            and not receipt.get("search")
            and not receipt.get("project")
            and receipt.get("resolved") is True
            and isinstance(receipt.get("conversation_id"), str),
            "MODEL_A_B_SEND_HAS_DIFFERENT_REQUEST_OR_COMPOSER_HINT",
        )
        cid = receipt["conversation_id"]
        require(cid not in sent_ids, "SAME_REAL_CHAT_REUSED_FOR_DIFFERENT_CONTROL")
        sent_ids.add(cid)
        prompt = private / f"private/{arm}.private.txt"
        if not prompt.exists():
            # For auto arms, the original approved POS-E-01 prompt is shared.
            prompt = private / "private/POS-E-01.private.txt"
        require(prompt.is_file() and not prompt.is_symlink(), "ORIGINAL_PROMPT_MISSING")
        prompt_text = prompt.read_text()
        original = cases[case_id]["prompt"]
        if mode == "automatic":
            require(prompt_text == original, "AUTOMATIC_ARM_USER_PROMPT_CHANGED")
        else:
            require(
                original in prompt_text
                and "use my installed claude-code-mods-knowledge Plugin" in prompt_text
                and "claude-code-mods-development Skill" in prompt_text
                and prompt_text.endswith(original),
                "TEXT_DIRECTED_MISSING_EXPLICIT_PLUGIN_REQUEST_OR_ORIGINAL_PROMPT",
            )
        conv, wire_sha = safe_json(private / f"conversations/{arm}.private.json")
        events = chain(conv)
        users = [e for e in events if (e.get("author") or {}).get("role") == "user"]
        require(
            len(users) == 1 and (users[0].get("content") or {}).get("parts") == [prompt_text],
            "REAL_ACCOUNT_USER_MESSAGE_DIFFERS_FROM_EXACT_QA_ARM",
        )
        visible = collect_latest_visible_reply(events)
        observed_models, observed_efforts = native_model_info(events)
        require(
            observed_models == [model] and observed_efforts == [effort],
            "ACTUAL_MODEL_EFFORT_UNVERIFIED_OR_DIFFERENT",
        )
        expected = cases[case_id]
        grade = summarize_chat_mode_case(
            expected,
            PLUGIN_VERSION,
            cid,
            visible.reply_text,
            events,
            invocation_mode="automatic" if mode == "automatic" else "unverified",
        )
        reads = [
            x
            for x in events
            if (x.get("author") or {}).get("role") == "tool"
            and (x.get("author") or {}).get("name") == "api_tool.read_resource"
        ]
        valid_reads = [
            e
            for e in reads
            if (e.get("metadata") or {}).get("skill_plugin_id") == selected_id
            and isinstance(
                ((e.get("metadata") or {}).get("invoked_resource") or {}).get("resource_uri"), str
            )
            and (
                ((e.get("metadata") or {}).get("invoked_resource") or {})["resource_uri"]
                == PLUGIN_SKILL_ROOT
                or ((e.get("metadata") or {}).get("invoked_resource") or {})[
                    "resource_uri"
                ].startswith(PLUGIN_SKILL_ROOT + "/")
            )
        ]
        require(len(valid_reads) == len(reads), "CROSS_PLUGIN_RESOURCE_READ_IN_CONTROL")
        if mode == "automatic":
            require(
                not grade["skill_loaded"] and not valid_reads and grade["answer_quality"] == "fail",
                "CONTROLLED_AUTO_MODEL_ARM_ROUTING_RESULT_CHANGED",
            )
        else:
            require(
                grade["skill_loaded"]
                and len(valid_reads) >= 3
                and grade["answer_quality"] == "pass",
                "EXPLICIT_TEXT_ROUTING_CONTROL_WAS_NOT_REAL_SKILL_READ",
            )
        outcome.append(
            {
                "case_id": case_id,
                "arm": arm,
                "user_request_mode": mode,
                "selected_plugin_system_hint": False,
                "actual_model": model,
                "actual_effort": effort,
                "original_prompt_sha256": sha(prompt_text),
                "original_send_receipt_sha256": receipt_sha,
                "original_chat_id_sha256": sha(cid),
                "original_conversation_sha256": wire_sha,
                "complete_visible_reply_sha256": visible.reply_sha256,
                "visible_reply_segments": visible.segment_count,
                "real_plugin_resource_reads": len(reads),
                "real_plugin_instance_matched": True,
                "skill_loaded": grade["skill_loaded"],
                "answer_structural_verdict": grade["answer_quality"],
                "answer_claim_ids": grade["observed_claim_ids"],
                "independent_semantic_review": "not_run",
                "native_executable_code_review": "not_run",
            }
        )
    automatic = [r for r in outcome if r["user_request_mode"] == "automatic"]
    named = [r for r in outcome if r["user_request_mode"] == "text_directed"]
    require(len(automatic) == len(named) == 3, "MISSING_CONTROL_ARM")
    return {
        "schema_version": 1,
        "experiment_type": "historical-current-Plugin model-effort A/B and supported text-directed invocation control",
        "plugin_name": "claude-code-mods-knowledge",
        "installed_account_version": PLUGIN_VERSION,
        "reviewed_target_cli": "2.1.302",
        "original_pr126_real_chat_baseline_sha256": PRIOR_PUBLIC_SHA,
        "source_frozen_46_suite_sha256": FROZEN_SUITE_SHA,
        "plugin_instance_sha256": sha(selected_id),
        "auditor_source_sha256": sha(Path(__file__).read_bytes()),
        "real_model_arms_without_plugin_selection": len(automatic),
        "real_model_arms_skill_auto_loads": sum(r["skill_loaded"] for r in automatic),
        "text_explicit_plugin_name_controls": len(named),
        "text_explicit_plugin_name_skill_loads": sum(r["skill_loaded"] for r in named),
        "automatic_baseline_standard_9_positive_loads": 0,
        "text_request_is_explicit_intent_not_native_automatic_invocation": True,
        "first_party_routing_causality_proven": False,
        "source_or_plugin_metadata_modified": False,
        "account_or_global_model_setting_modified": False,
        "all_full_user_visible_turns_scored": True,
        "new_provider_auto_selection_fix_proven": False,
        "full_p4_46_case_accepted": False,
        "stable_release_authorized": False,
        "cases": outcome,
        "private_model_text_account_ids_and_auth_not_committed": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-originals", required=True, type=Path)
    parser.add_argument("--frozen-suite", required=True, type=Path)
    parser.add_argument("--prior-p4-report", required=True, type=Path)
    parser.add_argument("--private-account-show", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    o = parser.parse_args()
    if o.out.exists() or o.out.is_symlink():
        raise SystemExit("REFUSED: immutable evidence report path exists")
    try:
        result = audit(
            o.private_originals, o.frozen_suite, o.prior_p4_report, o.private_account_show
        )
    except (ModelRoutingBlocked, KeyError, OSError, ValueError, TypeError):
        raise SystemExit(
            "BLOCKED: original model routing QA evidence missing or inconsistent"
        ) from None
    o.out.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(
        json.dumps(
            {
                "model_config_autoload": f"{result['real_model_arms_skill_auto_loads']}/{result['real_model_arms_without_plugin_selection']}",
                "explicit_text_load": f"{result['text_explicit_plugin_name_skill_loads']}/{result['text_explicit_plugin_name_controls']}",
                "native_auto_selection_fixed": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
