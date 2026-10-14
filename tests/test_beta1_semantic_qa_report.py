"""Only sanitized real Chat-mode QA results may be published."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILE = ROOT / "docs/reports/2026-10-14-beta1-complete-semantic-qa.json"


def test_complete_observation_but_not_a_fully_passing_model_suite() -> None:
    data = json.loads(FILE.read_text(encoding="utf-8"))
    assert data["schema_version"] == 1
    assert data["plugin_version"] == "0.2.0-beta.1"
    assert data["runtime_model_invocations"] == 46
    assert data["all_cases_observed"] is True
    assert data["full_qa_pass"] is False
    summary = data["summary"]
    assert (summary["passed"], summary["failed"], summary["inconclusive"]) == (15, 25, 6)
    assert summary["by_category"]["positive"] == {
        "total": 30,
        "passed": 7,
        "failed": 17,
        "inconclusive": 6,
        "blocked": 0,
        "not_run": 0,
    }
    assert summary["by_category"]["negative"]["passed"] == 8
    assert summary["by_category"]["boundary"]["failed"] == 8
    assert len(data["cases"]) == 46
    assert len({c["case_id"] for c in data["cases"]}) == 46


def test_confirmed_known_answer_hazards_are_explicit() -> None:
    data = json.loads(FILE.read_text())
    assert data["confirmed_code_hazards"] == {
        "unsupported-default-register-destructuring": 1,
        "historical-early-access-types-reference": 1,
        "plugin-test-expects-mod-directory": 1,
    }
    rows = {r["case_id"]: r for r in data["cases"]}
    assert "unsupported-default-register-destructuring" in rows["POS-E-02"]["known_hazard_flags"]
    assert "historical-early-access-types-reference" in rows["POS-T-03"]["known_hazard_flags"]
    assert "plugin-test-expects-mod-directory" in rows["POS-Q-01"]["known_hazard_flags"]
    assert rows["POS-E-01"]["final_verdict"] == "passed"
    assert rows["POS-E-02"]["final_verdict"] == "failed"
    assert rows["POS-Q-01"]["final_verdict"] == "failed"


def test_public_report_excludes_raw_sessions_and_identity() -> None:
    body = FILE.read_text(encoding="utf-8")
    for keyword in (
        "conversation_id",
        "chatgpt.com/c/",
        "Cookie",
        "Authorization: Bearer",
        "Plugin_",
        "session_token",
        "/Users/",
        "/home/",
    ):
        assert keyword not in body
    assert not re.search(r"gh[pousr]_[A-Za-z0-9]{20,}", body)
    assert not re.search(r"sk-[A-Za-z0-9_-]{20,}", body)
    data = json.loads(body)
    for row in data["cases"]:
        assert re.fullmatch(r"[a-f0-9]{64}", row["reply_sha256"])
        assert "raw_reply" not in row
        assert "prompt" not in row
