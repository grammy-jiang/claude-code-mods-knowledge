"""Strict SHA and provenance controls for original five Chat Mode boundaries."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from verify_p4_boundary_remaining5_chatmode import (  # noqa: E402
    CASES,
    SOURCE,
    OriginalEvidenceIncomplete,
    audit,
)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _write(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False))


def _synthetic(root: Path) -> None:
    for d in ("prompts", "receipts", "private_replies"):
        (root / d).mkdir()
    cases, sent, read, results = [], [], [], []
    for n, case_id in enumerate(CASES, 1):
        prompt = f"TASK_ID: SYNTHETIC-{n}\nOriginal boundary prompt {n}\n"
        reply = f"Synthetic no-private answer {n}\n"
        cid = f"synthetic-not-an-actual-chat-id-{n:02d}"
        path = root / "prompts" / f"{n:02d}.txt"
        path.write_text(prompt)
        (root / "private_replies" / f"{n:02d}.txt").write_text(reply)
        _write(
            root / "receipts" / f"{n:02d}.json",
            {
                "resolved": True,
                "conversation_id": cid,
                "model": "gpt-6-thinking",
                "effort": "standard",
                "system_hints": [],
                "search": False,
            },
        )
        triggered = n != 4
        cases.append(
            {
                "n": n,
                "case_id": case_id,
                "prompt_file": str(path),
                "prompt_sha256": _sha(prompt),
            }
        )
        sent.append(
            {
                "n": n,
                "case_id": case_id,
                "original_conversation_sha256": _sha(cid),
                "prompt_sha256": _sha(prompt),
            }
        )
        read.append({"n": n, "case_id": case_id, "activated": triggered})
        results.append(
            {
                "n": n,
                "case_id": case_id,
                "original_conversation_sha256": _sha(cid),
                "original_visible_reply_sha256": _sha(reply),
                "original_prompt_sha256": _sha(prompt),
                "model_and_effort_verified": True,
                "actual_matching_plugin_reads": 2 if triggered else 0,
                "skill_entrypoint_and_reference_read": triggered,
                "other_plugin_instance_read_detected": False,
                "semantic_rubric_manual_approval": False,
                "all_raw_content_private": True,
                "tool_type_counts": {"api_tool.read_resource": 2} if triggered else {},
            }
        )
    _write(
        root / "manifest.private.json",
        {
            "plugin_version": "0.4.10-beta.1",
            "source_revision": SOURCE,
            "target_cli": "2.1.302",
            "model": "gpt-6-thinking",
            "effort": "standard",
            "composer_plugin_selected": False,
            "search_requested": False,
            "no_blind_resends": True,
            "cases": cases,
        },
    )
    _write(
        root / "sender-progress.private.json",
        {
            "phase": "all_five_sends_confirmed",
            "completed": sent,
        },
    )
    _write(
        root / "reader-progress.private.json",
        {
            "phase": "all_five_original_replies_read",
            "completed": read,
            "blocked": None,
        },
    )
    _write(root / "scored.private.json", {"phase": "complete", "records": results})


def test_original_five_sha_proof_has_no_raw_account_content(tmp_path: Path) -> None:
    _synthetic(tmp_path)
    report = audit(tmp_path)
    assert report["counters"] == {
        "total": 5,
        "actual_skill_loads": 4,
        "no_skill_loads": 1,
        "partial_skill_reads": 0,
    }
    assert report["stable_release_authorized"] is False
    assert report["full_model_answer_semantics_approved"] is False
    data = json.dumps(report)
    assert str(tmp_path) not in data
    assert "synthetic-not-an-actual-chat-id" not in data
    assert "Synthetic no-private answer" not in data


def test_block_missing_or_transport_failed_read(tmp_path: Path) -> None:
    _synthetic(tmp_path)
    path = tmp_path / "reader-progress.private.json"
    obj = json.loads(path.read_text())
    obj["blocked"] = {"n": 3, "type": "TransportError"}
    _write(path, obj)
    with pytest.raises(OriginalEvidenceIncomplete):
        audit(tmp_path)
    obj["blocked"] = None
    obj["completed"].pop()
    _write(path, obj)
    with pytest.raises(OriginalEvidenceIncomplete):
        audit(tmp_path)


def test_reject_original_prompt_answer_or_conversation_tampering(tmp_path: Path) -> None:
    _synthetic(tmp_path)
    ans = tmp_path / "private_replies" / "01.txt"
    ans.write_text("tampered")
    with pytest.raises(OriginalEvidenceIncomplete):
        audit(tmp_path)
    ans.write_text("Synthetic no-private answer 1\n")
    p = tmp_path / "receipts" / "02.json"
    x = json.loads(p.read_text())
    x["conversation_id"] = "synthetic-not-an-actual-chat-id-01"
    _write(p, x)
    with pytest.raises(OriginalEvidenceIncomplete):
        audit(tmp_path)


def test_reject_false_plugin_read_or_missing_model_identity(tmp_path: Path) -> None:
    _synthetic(tmp_path)
    p = tmp_path / "scored.private.json"
    x = json.loads(p.read_text())
    x["records"][3]["skill_entrypoint_and_reference_read"] = True
    _write(p, x)
    with pytest.raises(OriginalEvidenceIncomplete):
        audit(tmp_path)
    x["records"][3]["skill_entrypoint_and_reference_read"] = False
    x["records"][0]["model_and_effort_verified"] = False
    _write(p, x)
    with pytest.raises(OriginalEvidenceIncomplete):
        audit(tmp_path)
