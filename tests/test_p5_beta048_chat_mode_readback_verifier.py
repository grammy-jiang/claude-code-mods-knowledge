"""Synthetic private Chat Mode report integrity checks; no account/network calls."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from verify_p5_beta048_chat_mode_readback import ChatEvidenceBlocked, audit  # noqa: E402


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _write(path: Path, obj: dict | list) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2))


def _synthetic_complete(root: Path) -> None:
    (root / "receipts").mkdir()
    (root / "private_replies").mkdir()
    (root / "prompts").mkdir()
    rows, cases, sends, reads = [], [], [], []
    for n in range(1, 47):
        category = "positive" if n <= 30 else "negative" if n <= 38 else "boundary"
        expected_result = {
            "positive": "structural_fail",
            "negative": "negative_nonactivation_pass",
            "boundary": "boundary_activation_fail",
        }[category]
        case_id = f"SYNTH-{n:02d}"
        tid = f"SYNTHETIC-CASE-{n:02d}"
        prompt = f"TASK_ID: {tid}\n\nSynthetic non-secret test request {n}\n"
        response = f"Synthetic non-secret completed answer {n}"
        cid = f"synthetic-not-a-real-chat-uuid-{n:02d}"
        promptfile = root / "prompts" / f"{n:02d}.txt"
        promptfile.write_text(prompt)
        (root / "private_replies" / f"{n:02d}.txt").write_text(response)
        _write(
            root / "receipts" / f"{n:02d}.json",
            {
                "conversation_id": cid,
                "resolved": True,
                "model": "gpt-6-thinking",
                "effort": "standard",
                "system_hints": [],
                "search": False,
            },
        )
        cases.append(
            {
                "n": n,
                "id": case_id,
                "category": category,
                "prompt_file": str(promptfile),
                "prompt_sha256": _sha(prompt),
            }
        )
        sends.append(
            {
                "n": n,
                "id": case_id,
                "prompt_sha256": _sha(prompt),
                "conversation_id_sha256": _sha(cid),
            }
        )
        reads.append(
            {
                "n": n,
                "case_id": case_id,
                "conversation_sha256": _sha(cid),
                "result": expected_result,
            }
        )
        rows.append(
            {
                "n": n,
                "case_id": case_id,
                "category": category,
                "conversation_sha256": _sha(cid),
                "reply_sha256": _sha(response),
                "result": expected_result,
                "model_and_effort_verified": True,
                "manual_generated_code_semantics_pass": False,
                "actual_matching_plugin_reads": 0,
                "activated_right_plugin": False,
                "required_claim_ids": [],
                "missing_required_claims": [],
                "missing_exact_source_claims": [],
                "cited_wrong_scope_claims": [],
                "source_structural_verdict": "fail",
            }
        )
    _write(
        root / "manifest.private.json",
        {
            "target_cli": "2.1.302",
            "installed_version": "0.4.8-beta.1",
            "model": "gpt-6-thinking",
            "effort": "standard",
            "no_composer_plugin_hint": True,
            "web_search_requested": False,
            "source_revision": "e" * 40,
            "cases": cases,
        },
    )
    _write(
        root / "progress.private.json", {"phase": "all_46_sent_confirmed", "sent_confirmed": sends}
    )
    _write(
        root / "read-progress.private.json",
        {"phase": "all_46_original_answers_read", "blocked": None, "completed": reads},
    )
    _write(root / "46-redacted.private.json", rows)


def test_full_original_synthetic_readback_has_true_denominator_and_no_data_leak(
    tmp_path: Path,
) -> None:
    _synthetic_complete(tmp_path)
    outcome = audit(tmp_path)
    assert outcome["original_unique_sends_with_receipts"] == 46
    assert outcome["original_completed_final_replies_sha256_verified"] == 46
    assert outcome["categories"] == {"positive": 30, "negative": 8, "boundary": 8}
    assert outcome["per_category_structural_success_counts"] == {"negative": 8}
    assert outcome["all_original_responses_semantically_approved"] is False
    assert outcome["stable_release_authorized"] is False
    data = json.dumps(outcome, ensure_ascii=False)
    assert "synthetic-not-a-real-chat" not in data
    assert str(tmp_path) not in data
    assert "Synthetic non-secret completed answer" not in data


def test_block_partial_original_or_failed_read_without_guessing(tmp_path: Path) -> None:
    _synthetic_complete(tmp_path)
    file = tmp_path / "read-progress.private.json"
    data = json.loads(file.read_text())
    data["phase"] = "blocked_read"
    data["blocked"] = {"n": 4, "type": "TransportError"}
    _write(file, data)
    with pytest.raises(ChatEvidenceBlocked):
        audit(tmp_path)
    data["phase"] = "all_46_original_answers_read"
    data["blocked"] = None
    data["completed"] = data["completed"][:-1]
    _write(file, data)
    with pytest.raises(ChatEvidenceBlocked):
        audit(tmp_path)


def test_block_tampered_prompt_answer_or_duplicate_chat(tmp_path: Path) -> None:
    _synthetic_complete(tmp_path)
    original = tmp_path / "private_replies" / "01.txt"
    original.write_text("Altered after the original Chat Mode completion")
    with pytest.raises(ChatEvidenceBlocked):
        audit(tmp_path)
    original.write_text("Synthetic non-secret completed answer 1")
    source = tmp_path / "receipts" / "02.json"
    data = json.loads(source.read_text())
    data["conversation_id"] = "synthetic-not-a-real-chat-uuid-01"
    _write(source, data)
    with pytest.raises(ChatEvidenceBlocked):
        audit(tmp_path)


def test_block_unreviewed_release_safety_claim(tmp_path: Path) -> None:
    _synthetic_complete(tmp_path)
    file = tmp_path / "46-redacted.private.json"
    rows = json.loads(file.read_text())
    rows[0]["manual_generated_code_semantics_pass"] = True
    _write(file, rows)
    with pytest.raises(ChatEvidenceBlocked):
        audit(tmp_path)
