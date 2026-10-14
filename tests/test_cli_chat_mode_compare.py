"""CLI comparison of independently collected redacted Chat-mode A/B records."""

from __future__ import annotations

import json
from pathlib import Path

from mods_knowledge import cli

ROOT = Path(__file__).resolve().parents[1]


def record(cid: str, version: str, grade: str) -> dict:
    import hashlib

    return {
        "case_id": cid,
        "category": "positive",
        "plugin_version": version,
        "conversation_sha256": hashlib.sha256((cid + version).encode()).hexdigest(),
        "response_sha256": "a" * 64,
        "plugin_id_sha256": "b" * 64,
        "skill_loaded": True,
        "resource_uris": [
            "skills://plugins/claude-code-mods-knowledge/claude-code-mods-development"
        ],
        "expected_activation": True,
        "observed_claim_ids": ["K-0007"],
        "official_source_cited": True,
        "code_callback_signature_correct": True,
        "answer_quality": grade,
        "quality_flags": [] if grade == "pass" else ["missing-expected-claim-ids"],
        "notes": "Test-only record",
        "invocation_mode": "automatic",
    }


def test_cli_chat_compare_writes_structural_delta_without_replies(tmp_path: Path, capsys) -> None:
    before = tmp_path / "before.json"
    after = tmp_path / "after.json"
    output = tmp_path / "comparison.json"
    before.write_text(json.dumps([record("POS-E-01", "0.2.0-beta.1", "fail")]))
    after.write_text(json.dumps([record("POS-E-01", "0.2.0-beta.2", "pass")]))
    code = cli.main(
        [
            "chat-compare",
            "--before",
            str(before),
            "--after",
            str(after),
            "--before-version",
            "0.2.0-beta.1",
            "--after-version",
            "0.2.0-beta.2",
            "--out",
            str(output),
        ]
    )
    assert code == 0
    published = json.loads(output.read_text())
    assert published["structurally_recovered"] == ["POS-E-01"]
    assert published["full_suite_qa_pass"] is False
    summary = json.loads(capsys.readouterr().out)
    assert summary["cases_both_observed"] == 1
    assert summary["recovered"] == 1
    assert summary["regressed"] == 0


def test_cli_chat_compare_fails_on_corrupt_evidence_without_output(tmp_path: Path) -> None:
    before = tmp_path / "before.json"
    after = tmp_path / "after.json"
    output = tmp_path / "comparison.json"
    before.write_text(json.dumps([record("POS-E-01", "0.2.0-beta.1", "pass")]))
    after.write_text(
        json.dumps(
            [
                {
                    **record("POS-E-01", "0.2.0-beta.2", "fail"),
                    "prompt": "Raw private prompt not allowed",
                }
            ]
        )
    )
    code = cli.main(
        [
            "chat-compare",
            "--before",
            str(before),
            "--after",
            str(after),
            "--before-version",
            "0.2.0-beta.1",
            "--after-version",
            "0.2.0-beta.2",
            "--out",
            str(output),
        ]
    )
    assert code == 2
    assert not output.exists()
