"""CLI safely aggregates content-addressed real Chat-mode P4 records offline."""

from __future__ import annotations

import json
from pathlib import Path

from mods_knowledge import cli

ROOT = Path(__file__).resolve().parents[1]
REVISION = "33706131f05f0aedf49fbb1fc0459854a579316d"


def _record() -> dict:
    return {
        "case_id": "POS-E-01",
        "category": "positive",
        "plugin_version": "0.2.0-beta.1",
        "conversation_sha256": "a" * 64,
        "response_sha256": "b" * 64,
        "plugin_id_sha256": "c" * 64,
        "skill_loaded": True,
        "resource_uris": [
            "skills://plugins/claude-code-mods-knowledge/claude-code-mods-development"
        ],
        "expected_activation": True,
        "observed_claim_ids": ["K-0007", "K-0031"],
        "official_source_cited": True,
        "code_callback_signature_correct": True,
        "answer_quality": "pass",
        "quality_flags": [],
        "notes": "Test fixture only.",
    }


def test_cli_chat_report_writes_private_safe_status(tmp_path: Path, capsys) -> None:
    inp = tmp_path / "records.json"
    output = tmp_path / "report.json"
    inp.write_text(json.dumps([_record()]))
    rc = cli.main(
        [
            "--root",
            str(ROOT),
            "chat-report",
            "--records",
            str(inp),
            "--out",
            str(output),
            "--plugin-version",
            "0.2.0-beta.1",
            "--source-revision",
            REVISION,
            "--blocked",
            "POS-E-03",
        ]
    )
    assert rc == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["status"] == "PARTIAL_LIVE_CHAT_MODE_EVALUATION"
    assert summary["observed"] == 1
    assert summary["full_qa_pass"] is False
    result = json.loads(output.read_text())
    assert result["summary"]["blocked"] == 1
    assert result["summary"]["inconclusive"] == 1
    assert result["summary"]["passed"] == 0


def test_cli_chat_report_invalid_record_does_not_create_output(tmp_path: Path, capsys) -> None:
    inp = tmp_path / "records.json"
    output = tmp_path / "report.json"
    entry = _record()
    entry["prompt"] = "private account material"
    inp.write_text(json.dumps([entry]))
    rc = cli.main(
        [
            "--root",
            str(ROOT),
            "chat-report",
            "--records",
            str(inp),
            "--out",
            str(output),
            "--plugin-version",
            "0.2.0-beta.1",
            "--source-revision",
            REVISION,
        ]
    )
    assert rc == 2
    assert not output.exists()
    assert capsys.readouterr().err


def test_cli_chat_report_manual_review_can_complete_a_case(tmp_path: Path, capsys) -> None:
    inp = tmp_path / "records.json"
    output = tmp_path / "report.json"
    review = tmp_path / "review.json"
    inp.write_text(json.dumps([_record()]))
    review.write_text(
        json.dumps(
            {
                "POS-E-01": {
                    "verdict": "pass",
                    "rationale": "I inspected the actual three argument callback and its cited source.",
                }
            }
        )
    )
    rc = cli.main(
        [
            "--root",
            str(ROOT),
            "chat-report",
            "--records",
            str(inp),
            "--manual-reviews",
            str(review),
            "--out",
            str(output),
            "--plugin-version",
            "0.2.0-beta.1",
            "--source-revision",
            REVISION,
        ]
    )
    assert rc == 0
    result = json.loads(output.read_text())
    assert result["summary"]["passed"] == 1
    assert result["summary"]["inconclusive"] == 0
