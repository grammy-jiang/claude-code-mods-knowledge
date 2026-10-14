"""CLI answer lint must never print or store the user's raw ChatGPT reply."""

import json
from pathlib import Path

from mods_knowledge import cli


def test_cli_lint_flags_bad_registration_without_echoing_raw_text(tmp_path: Path, capsys) -> None:
    source = tmp_path / "private-reply.txt"
    source.write_text(
        "PRIVATE_ACCOUNT_DATA_DO_NOT_COPY\n"
        "```ts\nexport default function register({ on }) {}\n```\n",
        encoding="utf-8",
    )
    report = tmp_path / "sanitized.json"
    result = cli.main(
        ["answer-lint", "--case-id", "POS-E-02", "--answer-file", str(source), "--out", str(report)]
    )
    assert result == 0
    saved = json.loads(report.read_text())
    assert "unsupported-default-register-destructuring" in saved["risk_flags"]
    assert "PRIVATE_ACCOUNT_DATA_DO_NOT_COPY" not in report.read_text()
    assert "PRIVATE_ACCOUNT_DATA_DO_NOT_COPY" not in capsys.readouterr().out
    assert saved["semantic_review_complete"] is False


def test_cli_lint_rejects_invalid_case_id_without_writing_output(tmp_path: Path) -> None:
    file = tmp_path / "answer.txt"
    file.write_text("A sample reply.")
    out = tmp_path / "report.json"
    rc = cli.main(
        ["answer-lint", "--case-id", "../unsafe", "--answer-file", str(file), "--out", str(out)]
    )
    assert rc == 2
    assert not out.exists()
