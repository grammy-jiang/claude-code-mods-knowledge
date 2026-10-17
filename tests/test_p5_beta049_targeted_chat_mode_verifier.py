"""Synthetic targeted 12-case evidence tests; no real ChatGPT account I/O."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from verify_p5_beta049_targeted_chat_mode import (  # noqa: E402
    CASE_INDICES,
    SOURCE_SHA,
    TargetedEvidenceBlocked,
    audit,
)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _write(path: Path, data: dict | list) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False))


def make_synthetic(root: Path) -> None:
    for name in ("prompts", "receipts", "private_replies"):
        (root / name).mkdir()
    cases, sends, reads, rows = [], [], [], []
    for n in CASE_INDICES:
        category = "positive" if n <= 4 else "negative" if n <= 32 else "boundary"
        case_id = f"SYNTH-MODS-{n:02d}"
        message = f"TASK_ID: TEST-NO-REAL-CHAT-{n}\nSynthetic request\n"
        answer = f"Synthetic completed model answer {n}."
        chat = f"synthetic-this-is-not-a-chat-{n:02d}"
        prompt = root / "prompts" / f"{n:02d}.txt"
        prompt.write_text(message)
        (root / "private_replies" / f"{n:02d}.txt").write_text(answer)
        _write(
            root / "receipts" / f"{n:02d}.json",
            {
                "conversation_id": chat,
                "resolved": True,
                "model": "gpt-6-thinking",
                "effort": "standard",
                "system_hints": [],
                "search": False,
            },
        )
        result = {
            "positive": "structural_fail",
            "negative": "negative_nonactivation_pass",
            "boundary": "boundary_activation_fail",
        }[category]
        cases.append(
            {
                "n": n,
                "id": case_id,
                "category": category,
                "prompt_file": str(prompt),
                "prompt_sha256": _sha(message),
            }
        )
        sends.append(
            {
                "n": n,
                "id": case_id,
                "prompt_sha256": _sha(message),
                "conversation_id_sha256": _sha(chat),
            }
        )
        reads.append(
            {"n": n, "case_id": case_id, "conversation_sha256": _sha(chat), "result": result}
        )
        rows.append(
            {
                "n": n,
                "case_id": case_id,
                "category": category,
                "conversation_sha256": _sha(chat),
                "reply_sha256": _sha(answer),
                "result": result,
                "model_and_effort_verified": True,
                "manual_generated_code_semantics_pass": False,
                "actual_matching_plugin_reads": 0,
                "activated_right_plugin": False,
                "required_claim_ids": [],
                "missing_required_claims": [],
                "missing_exact_source_claims": [],
                "cited_wrong_scope_claims": [],
            }
        )
    _write(
        root / "manifest.private.json",
        {
            "target_cli": "2.1.302",
            "source_revision": SOURCE_SHA,
            "installed_version": "0.4.9-beta.1",
            "model": "gpt-6-thinking",
            "effort": "standard",
            "no_composer_plugin_hint": True,
            "web_search_requested": False,
            "cases": cases,
        },
    )
    _write(
        root / "progress.private.json", {"phase": "all_12_sent_confirmed", "sent_confirmed": sends}
    )
    _write(
        root / "read-progress.private.json",
        {"phase": "all_12_original_answers_read", "blocked": None, "completed": reads},
    )
    _write(root / "46-redacted.private.json", rows)


def test_independent_real_original_metadata_integrity_without_network(tmp_path: Path) -> None:
    make_synthetic(tmp_path)
    report = audit(tmp_path)
    assert report["new_distinct_sends_verified"] == 12
    assert report["canonical_final_replies_verified"] == 12
    assert report["family_counts"] == {"positive": 2, "negative": 2, "boundary": 8}
    assert report["structural_successes_by_category"] == {
        "positive": 0,
        "negative": 2,
        "boundary": 0,
    }
    assert report["stable_release_approved"] is False
    assert report["full_46_case_plugin_qualification"] is False
    serialized = json.dumps(report, ensure_ascii=False)
    assert str(tmp_path) not in serialized
    assert "synthetic-this-is-not-a-chat" not in serialized
    assert "Synthetic completed model answer" not in serialized


def test_refuse_partial_or_transport_blocked_targeted_read(tmp_path: Path) -> None:
    make_synthetic(tmp_path)
    path = tmp_path / "read-progress.private.json"
    doc = json.loads(path.read_text())
    doc["phase"] = "blocked_read"
    doc["blocked"] = {"n": 42, "type": "TransportError"}
    _write(path, doc)
    with pytest.raises(TargetedEvidenceBlocked):
        audit(tmp_path)
    doc["phase"] = "all_12_original_answers_read"
    doc["blocked"] = None
    doc["completed"] = doc["completed"][:-1]
    _write(path, doc)
    with pytest.raises(TargetedEvidenceBlocked):
        audit(tmp_path)


def test_refuse_duplicate_or_tampered_original_targeted_content(tmp_path: Path) -> None:
    make_synthetic(tmp_path)
    f = tmp_path / "private_replies" / "01.txt"
    f.write_text("not the original full reply")
    with pytest.raises(TargetedEvidenceBlocked):
        audit(tmp_path)
    f.write_text("Synthetic completed model answer 1.")
    receipt = tmp_path / "receipts" / "04.json"
    data = json.loads(receipt.read_text())
    data["conversation_id"] = "synthetic-this-is-not-a-chat-01"
    _write(receipt, data)
    with pytest.raises(TargetedEvidenceBlocked):
        audit(tmp_path)


def test_wrong_version_or_source_cannot_be_attributed_to_beta049(tmp_path: Path) -> None:
    make_synthetic(tmp_path)
    f = tmp_path / "manifest.private.json"
    doc = json.loads(f.read_text())
    doc["source_revision"] = "e" * 40
    _write(f, doc)
    with pytest.raises(TargetedEvidenceBlocked):
        audit(tmp_path)
