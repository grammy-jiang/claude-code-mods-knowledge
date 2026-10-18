"""Paired Chat Mode control evaluator is offline, privacy-preserving and fail-closed."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from verify_p4_boundary_paired_chatmode import (  # noqa: E402
    EXPECTED_PAIRS,
    SOURCE_REVISION,
    PairedEvidenceBlocked,
    audit,
)


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _write(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False) + "\n")


def _populate(root: Path) -> None:
    for directory in ("prompts", "receipts", "private_replies"):
        (root / directory).mkdir()
    cases, sent, read, records = [], [], [], []
    for n, (case_id, mode) in enumerate(EXPECTED_PAIRS, 1):
        task_id = f"SYNTH_BOUNDARY_PAIR_{n:02d}"
        body_hash = _hash(f"Original question text for {case_id}")
        message = (
            f"TASK_ID: {task_id}\n"
            + ("Explicit request for a specific Skill\n" if mode == "explicit" else "")
            + f"Original question text for {case_id}\n"
        )
        conversation = f"synthetic-boundary-chat-not-real-{n:02d}"
        response = f"Synthetic completed answer {n}"
        prompt = root / "prompts" / f"{n:02d}.txt"
        prompt.write_text(message)
        (root / "private_replies" / f"{n:02d}.txt").write_text(response)
        _write(
            root / "receipts" / f"{n:02d}.json",
            {
                "resolved": True,
                "conversation_id": conversation,
                "model": "gpt-6-thinking",
                "effort": "standard",
                "search": False,
                "system_hints": [],
                "project": None,
            },
        )
        cases.append(
            {
                "n": n,
                "case_id": case_id,
                "condition": mode,
                "task_id": task_id,
                "original_body_sha256": body_hash,
                "prompt_file": str(prompt),
                "prompt_sha256": _hash(message),
            }
        )
        sent.append(
            {
                "n": n,
                "case_id": case_id,
                "condition": mode,
                "original_conversation_sha256": _hash(conversation),
                "prompt_sha256": _hash(message),
                "sent_at": "2026-10-18T00:01:00+00:00",
            }
        )
        is_active = mode == "explicit"
        read.append(
            {
                "n": n,
                "case_id": case_id,
                "condition": mode,
                "plugin_read": is_active,
            }
        )
        records.append(
            {
                "n": n,
                "case_id": case_id,
                "condition": mode,
                "original_conversation_sha256": _hash(conversation),
                "original_visible_reply_sha256": _hash(response),
                "original_prompt_sha256": _hash(message),
                "model_and_effort_verified": True,
                "canonical_plugin_resource_reads": 2 if is_active else 0,
                "real_plugin_read": is_active,
                "skill_entrypoint_read": is_active,
                "reference_read": is_active,
                "tool_event_counts": {"api_tool.read_resource": 2} if is_active else {},
                "other_plugin_instance_read_detected": False,
                "independent_generated_code_semantics_approved": False,
                "all_raw_account_material_private": True,
            }
        )
    _write(
        root / "manifest.private.json",
        {
            "installed_plugin_version": "0.4.10-beta.1",
            "source_revision": SOURCE_REVISION,
            "target_cli": "2.1.302",
            "model": "gpt-6-thinking",
            "effort": "standard",
            "no_search_requested": True,
            "no_system_hints": True,
            "no_resends": True,
            "cases": cases,
        },
    )
    _write(
        root / "sender-progress.private.json",
        {
            "phase": "all_six_original_sends_confirmed",
            "completed": sent,
        },
    )
    _write(
        root / "reader-progress.private.json",
        {
            "phase": "all_six_original_replies_read",
            "completed": read,
            "blocked": None,
        },
    )
    _write(root / "scored.private.json", {"phase": "complete", "records": records})


def test_complete_original_paired_evidence_is_not_a_release_pass(tmp_path: Path) -> None:
    _populate(tmp_path)
    report = audit(tmp_path)
    assert report["total_distinct_sent_and_read_originals"] == 6
    assert report["observed_counts"] == {
        "natural_cases": 3,
        "natural_actual_skill_reads": 0,
        "natural_skill_and_reference_reads": 0,
        "explicit_cases": 3,
        "explicit_actual_skill_reads": 3,
        "explicit_skill_and_reference_reads": 3,
    }
    assert report["stable_release_authorized"] is False
    assert report["genuine_model_code_semantics_certified"] is False
    content = json.dumps(report)
    assert str(tmp_path) not in content
    assert "synthetic-boundary-chat-not-real" not in content
    assert "Synthetic completed answer" not in content


def test_ambiguous_transport_or_partial_read_never_pass(tmp_path: Path) -> None:
    _populate(tmp_path)
    path = tmp_path / "reader-progress.private.json"
    obj = json.loads(path.read_text())
    obj["blocked"] = {"n": 2, "type": "TransportError"}
    _write(path, obj)
    with pytest.raises(PairedEvidenceBlocked):
        audit(tmp_path)
    obj["blocked"] = None
    obj["completed"].pop()
    _write(path, obj)
    with pytest.raises(PairedEvidenceBlocked):
        audit(tmp_path)


def test_tampering_or_duplicate_chat_rejected(tmp_path: Path) -> None:
    _populate(tmp_path)
    answer = tmp_path / "private_replies" / "01.txt"
    answer.write_text("Altered original")
    with pytest.raises(PairedEvidenceBlocked):
        audit(tmp_path)
    answer.write_text("Synthetic completed answer 1")
    receipt = tmp_path / "receipts" / "02.json"
    row = json.loads(receipt.read_text())
    row["conversation_id"] = "synthetic-boundary-chat-not-real-01"
    _write(receipt, row)
    with pytest.raises(PairedEvidenceBlocked):
        audit(tmp_path)


def test_reject_fabricated_plugin_or_host_model_provenance(tmp_path: Path) -> None:
    _populate(tmp_path)
    path = tmp_path / "scored.private.json"
    rows = json.loads(path.read_text())
    rows["records"][0]["real_plugin_read"] = True
    _write(path, rows)
    with pytest.raises(PairedEvidenceBlocked):
        audit(tmp_path)
    rows["records"][0]["real_plugin_read"] = False
    rows["records"][2]["model_and_effort_verified"] = False
    _write(path, rows)
    with pytest.raises(PairedEvidenceBlocked):
        audit(tmp_path)
