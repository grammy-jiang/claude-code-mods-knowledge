#!/usr/bin/env python3
"""Audit original Mac Chat Mode 0.4.12-beta.1 automatic/explicit pilot.

Re-read private original conversation payloads and authenticated receipts,
compare the actual account download with source ZIP canonical content,
and independently rescore original complete visible assistant turns.

Never submit a Chat message, install a Plugin, alter account state or infer
a model semantic PASS from a structural/ToolUse PASS.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from mods_knowledge.account_archive import verify_account_download
from mods_knowledge.chat_mode_evidence import summarize_chat_mode_case
from mods_knowledge.chat_visible_reply import collect_latest_visible_reply

PLUGIN = "claude-code-mods-knowledge"
SKILL = "claude-code-mods-development"
VERSION = "0.4.12-beta.1"
TARGET = "2.1.302"
MODEL = "gpt-6-thinking"
EFFORT = "standard"
SOURCE_REVISION = "6f92571f0a0ab5b637b1b36607d5ff2ddd4860a8"
FROZEN_SUITE_SHA = "372dc392e2efb83e9d922ffa306072bb57a78fddd566a50e91e844aabe82b554"
SOURCE_ZIP_SHA = "f16f02b492977a8365e82125ac64ab199bc3e0b3e189c23cc22e34ff87d64827"
ACCOUNT_ZIP_SHA = "e86e334136b78b35e58c31fb4cb840624b03add017169809aa9d9e8fb1e83453"
EXPECTED = {
    "positive": 9,
    "negative": 3,
    "boundary": 3,
}
MAX_ORIGINAL = 4_000_000


class PilotEvidenceBlocked(ValueError):
    """Incomplete, mixed-version, tampered or unsafe Chat Mode evidence."""


def require(value: bool, reason: str) -> None:
    if not value:
        raise PilotEvidenceBlocked(reason)


def sha(raw: bytes | str) -> str:
    if isinstance(raw, str):
        raw = raw.encode()
    return hashlib.sha256(raw).hexdigest()


def read_bytes(path: Path) -> bytes:
    require(path.is_file() and not path.is_symlink(), "MISSING_OR_UNSAFE_PRIVATE_QA_FILE")
    require(0 < path.stat().st_size <= MAX_ORIGINAL, "OVERSIZE_OR_EMPTY_ORIGINAL_QA_FILE")
    return path.read_bytes()


def read_json(path: Path) -> dict:
    result = json.loads(read_bytes(path))
    require(isinstance(result, dict), "ORIGINAL_EXPECTED_JSON_OBJECT")
    return result


def native_chain(conv: dict) -> list[dict]:
    mapping = conv.get("mapping")
    current = conv.get("current_node")
    require(isinstance(mapping, dict) and isinstance(current, str), "INVALID_RAW_CONVERSATION")
    out = []
    seen = set()
    while current and current in mapping and current not in seen:
        seen.add(current)
        row = mapping[current].get("message") or {}
        require(isinstance(row, dict), "INVALID_ORIGINAL_CHAT_MESSAGE")
        out.append(row)
        current = mapping[current].get("parent")
    require(out and len(out) < 500, "INVALID_OR_TOO_LARGE_CHAT_CHAIN")
    out.reverse()
    return out


def actual_model_and_effort(messages: list[dict]) -> tuple[list[str], list[str]]:
    relevant = [
        x
        for x in messages
        if (x.get("author") or {}).get("role") == "assistant"
        and x.get("recipient") in (None, "all")
        and (x.get("content") or {}).get("content_type") == "text"
        and any(isinstance(p, str) and p.strip() for p in (x.get("content") or {}).get("parts", []))
    ]
    models = sorted(
        {
            (x.get("metadata") or {}).get("resolved_model_slug")
            for x in relevant
            if (x.get("metadata") or {}).get("resolved_model_slug")
        }
    )
    efforts = sorted(
        {
            (x.get("metadata") or {}).get("thinking_effort")
            for x in relevant
            if (x.get("metadata") or {}).get("thinking_effort")
        }
    )
    return models, efforts


def score_original(qa: Path, cases: dict, name: str, plugin_id: str, *, control: bool) -> dict:
    area = qa / "explicit-controls" if control else qa / "sends"
    receipt = read_json(area / f"{name}.private.json")
    expected = cases[name]
    prompt = read_bytes(qa / "prompts" / f"{name}.private.txt")
    require(prompt.decode("utf-8") == expected["prompt"], "ORIGINAL_USER_PROMPT_DRIFT")
    require(receipt.get("resolved") is True, "UNRESOLVED_OR_PROVISIONAL_REAL_CHAT")
    require(
        receipt.get("model") == MODEL and receipt.get("effort") == EFFORT,
        "SEND_NOT_PINNED_TO_TEST_MODEL",
    )
    require(
        not receipt.get("project") and receipt.get("search") is False,
        "NOT_BASELINE_ORDINARY_CHAT_SEND",
    )
    hints = receipt.get("system_hints")
    require(
        hints == (["plugin:" + plugin_id] if control else []),
        "EXPLICIT_VERSUS_AUTOMATIC_INVOCATION_NOT_DISTINCT",
    )
    chat_id = receipt.get("conversation_id")
    require(isinstance(chat_id, str) and len(chat_id) > 12, "MISSING_REAL_CHAT_CONFIRMATION")
    private_conversation = (
        qa / "explicit-controls" / f"{name}.private-conversation.json"
        if control
        else qa / "private-conversations" / f"{name}.private.json"
    )
    raw = read_bytes(private_conversation)
    conv = json.loads(raw)
    chain = native_chain(conv)
    last_users = [m for m in chain if (m.get("author") or {}).get("role") == "user"]
    require(
        len(last_users) == 1
        and (last_users[-1].get("content") or {}).get("parts") == [expected["prompt"]],
        "ORIGINAL_CHAT_USER_TEXT_DIFFERS_FROM_FROZEN_CASE",
    )
    visible = collect_latest_visible_reply(chain)
    models, efforts = actual_model_and_effort(chain)
    require(models == [MODEL] and efforts == [EFFORT], "ACTUAL_HOST_MODEL_NOT_CONFIRMED")
    scoring = summarize_chat_mode_case(
        expected,
        VERSION,
        chat_id,
        visible.reply_text,
        chain,
        invocation_mode="explicit" if control else "automatic",
    )
    original = read_json(
        (qa / "explicit-controls" / f"{name}.private-report.json")
        if control
        else (qa / "reports" / f"{name}.private.json")
    )
    require(
        scoring == (original["scored"] if control else original["structural"]),
        "REPLAY_DOES_NOT_MATCH_ORIGINAL_CHAT_SCORING",
    )
    require(
        scoring["conversation_sha256"] == sha(chat_id)
        and scoring["response_sha256"] == visible.reply_sha256
        and (original.get("reply_segments") if control else original["visible_segment_count"])
        == visible.segment_count,
        "ORIGINAL_VISIBLE_CHAT_SHA_OR_COMPLETENESS_CHANGED",
    )
    require(
        (
            original.get("original_conversation_sha256")
            if control
            else original["raw_conversation_sha256"]
        )
        == sha(raw if not control else json.dumps(conv, ensure_ascii=False, sort_keys=True)),
        "PRIVATE_ORIGINAL_CONVERSATION_SHA_MISMATCH",
    )
    req = [
        m
        for m in chain
        if (m.get("author") or {}).get("role") == "tool"
        and (m.get("author") or {}).get("name") == "api_tool.read_resource"
    ]
    actual_matching = 0
    all_canonical = 0
    prefix = "skills://plugins/claude-code-mods-knowledge/claude-code-mods-development"
    for message in req:
        meta = message.get("metadata") or {}
        uri = (meta.get("invoked_resource") or {}).get("resource_uri")
        if isinstance(uri, str) and (uri == prefix or uri.startswith(prefix + "/")):
            all_canonical += 1
            if meta.get("skill_plugin_id") == plugin_id:
                actual_matching += 1
    stored_matching = (
        original["correct_plugin_read_count"]
        if control
        else original["correct_plugin_instance_read_count"]
    )
    require(actual_matching == stored_matching, "INSTALLED_PLUGIN_IDENTITY_NOT_VERIFIED")
    require(
        len(req) == (original["plugin_read_count"] if control else original["tool_resource_reads"]),
        "ACTUAL_RESOURCE_READ_EVENT_COUNT_CHANGED",
    )
    require(scoring["skill_loaded"] == (actual_matching > 0), "SKILL_SCORE_MISMATCH")
    return {
        "case_id": name,
        "category": expected["category"],
        "invocation_mode": "explicit" if control else "automatic",
        "case_prompt_sha256": sha(prompt),
        "private_send_receipt_sha256": sha(read_bytes(area / f"{name}.private.json")),
        "original_conversation_sha256": sha(chat_id),
        "original_conversation_wire_sha256": sha(raw),
        "visible_answer_sha256": visible.reply_sha256,
        "visible_assistant_segments": visible.segment_count,
        "native_chat_resolved_model": MODEL,
        "native_chat_effort": EFFORT,
        "actual_resource_read_count": len(req),
        "actual_correct_plugin_resource_reads": actual_matching,
        "actual_matching_canonical_resources": all_canonical,
        "skill_auto_or_explicit_loaded": scoring["skill_loaded"],
        "structural_verdict": scoring["answer_quality"],
        "structural_flags": scoring["quality_flags"],
        "observed_claim_ids": scoring["observed_claim_ids"],
        "semantic_review": "not_done",
        "native_generated_code_validation": "not_done",
    }


def audit(private: Path, suite_file: Path) -> dict:
    require(private.is_dir() and not private.is_symlink(), "PRIVATE_FROZEN_QA_MISSING")
    require(sha(read_bytes(suite_file)) == FROZEN_SUITE_SHA, "UNREVIEWED_SOURCE_SUITE")
    suite = read_json(suite_file)
    source = {x["id"]: x for x in suite["cases"]}
    require(
        len(source) == 46
        and suite.get("target") == {"claude_code_version": TARGET, "surface": "cli"}
        and Counter(x["category"] for x in source.values())
        == {"positive": 30, "negative": 8, "boundary": 8},
        "FROZEN_46_TARGET_UNREVIEWED",
    )
    raw = read_json(private / "account/build-manifest.private.json")
    require(
        raw["package_version"] == VERSION
        and raw["source_revision"] == SOURCE_REVISION
        and raw["target"] == {"api_version": TARGET, "surface": "cli"}
        and raw["approved_claims"] == 31,
        "ACCOUNT_MATCHED_BUILD_SOURCE_WRONG_VERSION",
    )
    uploaded = read_bytes(private / "account/uploaded.private.zip")
    downloaded = read_bytes(private / "account/downloaded.private.zip")
    require(
        sha(uploaded) == SOURCE_ZIP_SHA and sha(downloaded) == ACCOUNT_ZIP_SHA,
        "ORIGINAL_SOURCE_OR_ACCOUNT_ZIP_SHA_DRIFT",
    )
    matching = verify_account_download(uploaded, downloaded)
    require(
        matching["status"] == "ACCOUNT_ARCHIVE_CONTENTS_MATCH"
        and matching["package_version"] == VERSION
        and matching["canonical_files_matched"] == 11
        and matching["server_sidecar_verified"] is True,
        "ACCOUNT_CANONICAL_CONTENT_NOT_SOURCE_MATCHED",
    )
    account = read_bytes(private / "account/show.private.log").decode("utf-8")
    require(
        "version 0.4.12-beta.1, status ENABLED, installed yes" in account
        and "claude-code-mods-development  yes" in account,
        "ACTUAL_PERSONAL_PLUGIN_ENABLEMENT_NOT_ATTESTED",
    )
    marker = re.search(r"\bid\s+(Plugin_[a-f0-9]{32})", account)
    require(marker is not None, "ORIGINAL_INSTALLED_PLUGIN_ID_NOT_READ")
    plugin_id = marker.group(1)
    hints = read_json(private / "account/system-hints.private.json")
    catalog = hints.get("system_hints") or []
    plugin_entries = [x for x in catalog if isinstance(x, dict) and x.get("is_plugin") is True]
    ours = [x for x in plugin_entries if x.get("name") == PLUGIN]
    require(
        len(ours) == 1
        and ours[0]["is_connected"] is True
        and ours[0]["system_hint"] == "plugin:" + plugin_id,
        "EXPLICIT_COMPOSER_SELECTION_ID_MISMATCH",
    )
    qa = private / "qa"
    manifest = read_json(qa / "private-manifest.json")
    require(
        manifest["suite_sha256"] == FROZEN_SUITE_SHA
        and manifest["plugin_version"] == VERSION
        and manifest["canonical_content_sha256"] == matching["canonical_content_sha256"]
        and manifest["pinned_model"] == MODEL
        and manifest["pinned_effort"] == EFFORT
        and manifest["invocation_mode"] == "automatic"
        and len(manifest["cases"]) == 46,
        "ORIGINAL_CASE_MANIFEST_SCOPE_DRIFT",
    )
    receipts = sorted((qa / "sends").glob("*.private.json"))
    reports = sorted((qa / "reports").glob("*.private.json"))
    require(len(receipts) == len(reports) == 15, "ORIGINAL_15_FINISHED_CASES_INCOMPLETE")
    sent_ids = {p.name.removesuffix(".private.json") for p in receipts}
    report_ids = {p.name.removesuffix(".private.json") for p in reports}
    require(
        sent_ids == report_ids and sent_ids <= set(source),
        "MISSING_OR_UNACCOUNTED_REAL_CHAT_RESULT",
    )
    cases = [
        score_original(qa, source, name, plugin_id, control=False) for name in sorted(sent_ids)
    ]
    by_category = Counter(x["category"] for x in cases)
    require(dict(by_category) == EXPECTED, "ORIGINAL_CASE_CATEGORY_DISTRIBUTION_CHANGED")
    positives = [c for c in cases if c["category"] == "positive"]
    negatives = [c for c in cases if c["category"] == "negative"]
    boundaries = [c for c in cases if c["category"] == "boundary"]
    require(
        all(c["actual_correct_plugin_resource_reads"] == 0 for c in cases)
        and all(c["structural_verdict"] == "fail" for c in positives + boundaries)
        and all(c["structural_verdict"] == "pass" for c in negatives),
        "REAL_AUTOMATIC_ROUTING_OUTCOMES_CHANGED",
    )
    uncertain = "NEG-SPORTS"
    require(
        uncertain in source
        and source[uncertain]["category"] == "negative"
        and (qa / "sends" / f"{uncertain}.private.started").is_file()
        and not (qa / "sends" / f"{uncertain}.private.json").exists()
        and uncertain not in sent_ids,
        "AMBIGUOUS_SEND_WOULD_BE_WRONGLY_REPLAYED",
    )
    explicit = score_original(qa, source, "POS-E-01", plugin_id, control=True)
    require(
        explicit["actual_correct_plugin_resource_reads"] == 4
        and explicit["skill_auto_or_explicit_loaded"] is True
        and explicit["structural_verdict"] == "pass",
        "SAME_PROMPT_EXPLICIT_PLUG_IN_NOT_ACTUALLY_WORKING",
    )
    require(
        explicit["case_prompt_sha256"]
        == next(c["case_prompt_sha256"] for c in cases if c["case_id"] == "POS-E-01"),
        "EXPLICIT_POSITIVE_TASK_PROMPT_WAS_ALTERED",
    )
    return {
        "schema_version": 1,
        "auditor_source_sha256": sha(Path(__file__).read_bytes()),
        "scope": "ordinary authenticated Chat Mode, Mac Codex Skill adapter, frozen CLI302 target",
        "plugin_name": PLUGIN,
        "plugin_version": VERSION,
        "target_version": TARGET,
        "reviewed_compiled_source_revision": SOURCE_REVISION,
        "official_frozen_test_suite_sha256": FROZEN_SUITE_SHA,
        "original_uploader_package_sha256": SOURCE_ZIP_SHA,
        "original_chatgpt_download_sha256": ACCOUNT_ZIP_SHA,
        "canonical_plugin_contents_sha256": matching["canonical_content_sha256"],
        "canonical_plugin_files_matched": 11,
        "account_current_version_installed_enabled_and_skill_on_readback": True,
        "account_plugin_instance_sha256": sha(plugin_id),
        "source_origin_is_account_observed_archive_not_current_latest": True,
        "real_chat_mode_model": MODEL,
        "real_chat_mode_effort": EFFORT,
        "actual_model_configuration_confirmed_per_case": True,
        "total_expected_cases": 46,
        "automatic_cases_confirmed_finished_and_scored": len(cases),
        "automatic_cases_by_category": {
            k: {
                "completed": by_category[k],
                "canonical_skill_loads": sum(
                    c["skill_auto_or_explicit_loaded"] for c in cases if c["category"] == k
                ),
                "structural_passes": sum(
                    c["structural_verdict"] == "pass" for c in cases if c["category"] == k
                ),
            }
            for k in ("positive", "negative", "boundary")
        },
        "uncertain_send_not_counted_and_must_not_be_resent": uncertain,
        "confirmed_send_receipts": len(receipts),
        "remaining_not_run_or_not_confirmed": 46 - len(cases),
        "explicit_selected_positive_control": explicit,
        "explicit_control_is_not_part_of_automatic_denominator": True,
        "system_hint_catalog_plugin_count": len(plugin_entries),
        "system_hint_is_auto_false_for_all_catalog_plugins": all(
            x.get("is_auto") is False for x in plugin_entries
        ),
        "system_hint_is_auto_is_not_evidence_of_unique_root_cause": True,
        "cases": cases,
        "full_46_case_live_chat_mode_qa_pass": False,
        "manual_semantic_review_finished": False,
        "current_target_310_compatibility_proven": False,
        "native_generated_mod_code_validated_by_this_pilot": False,
        "stable_release_authorized": False,
        "original_chats_session_ids_plugin_ids_and_tokens_not_committed": True,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--private-freeze", type=Path, required=True)
    p.add_argument(
        "--frozen-suite",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "evals/p4_cases_cli_2_1_302.json",
    )
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    if a.out.exists() or a.out.is_symlink():
        raise SystemExit("REFUSED: immutable QA output must not be overwritten")
    try:
        result = audit(a.private_freeze, a.frozen_suite)
    except (PilotEvidenceBlocked, ValueError, KeyError, OSError, TypeError):
        raise SystemExit(
            "BLOCKED: genuine account/native pilot evidence unavailable or contradictory"
        ) from None
    a.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "automatic_finished": result["automatic_cases_confirmed_finished_and_scored"],
                "automatic_positive_loads": result["automatic_cases_by_category"]["positive"][
                    "canonical_skill_loads"
                ],
                "explicit_control_loads": result["explicit_selected_positive_control"][
                    "actual_correct_plugin_resource_reads"
                ],
                "ambiguous_send": result["uncertain_send_not_counted_and_must_not_be_resent"],
                "stable": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
