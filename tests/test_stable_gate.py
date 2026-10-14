"""A stable Plugin release cannot be certified from ZIP/static/partial Chat evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from mods_knowledge.compiler import build_artifacts
from mods_knowledge.stable_gate import (
    StableGateError,
    assess_stable_release,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "1" * 40
VERSION = "0.3.0"


def _bundle(tmp_path: Path) -> Path:
    folder = tmp_path / "dist"
    build_artifacts(
        ROOT,
        folder,
        api_version="2.1.296",
        surface="cli",
        package_version=VERSION,
        source_revision=SOURCE,
    )
    return folder


def _chat() -> dict:
    suite = json.loads((ROOT / "evals/p4_cases.json").read_text())
    records = []
    for entry in suite["cases"]:
        cid = entry["id"]
        positive = entry["expected_activation"]
        record = {
            "id": cid,
            "category": entry["category"],
            "expected_activation": positive,
            "received": True,
            "final_verdict": "passed",
            "skill_loaded": positive,
            "invocation_mode": "automatic",
            "conversation_sha256": hashlib.sha256((cid + "-conversation").encode()).hexdigest(),
            "response_sha256": hashlib.sha256((cid + "-response").encode()).hexdigest(),
            "plugin_id_sha256": "a" * 64 if positive else None,
            "resource_uris": [
                "skills://plugins/claude-code-mods-knowledge/claude-code-mods-development"
            ]
            if positive
            else [],
            "semantic_review": {"verdict": "pass", "rationale_sha256": "b" * 64}
            if positive
            else None,
        }
        records.append(record)
    return {
        "schema_version": 1,
        "mode": "chat",
        "plugin_version": VERSION,
        "source_revision": SOURCE,
        "summary": {
            "total": 46,
            "observed": 46,
            "passed": 46,
            "failed": 0,
            "blocked": 0,
            "inconclusive": 0,
            "not_run": 0,
            "full_qa_pass": True,
        },
        "items": records,
    }


def _agents() -> dict:
    hosts = {}
    for host in ("claude_code", "codex", "pi_agent"):
        tests = []
        for category, cid in (
            ("positive", "POS-E-01"),
            ("boundary", "BOUND-VERSION-NEW"),
            ("negative", "NEG-HVAC"),
        ):
            tests.append(
                {
                    "category": category,
                    "case_id": cid,
                    "real_inference": True,
                    "answer_verdict": "pass",
                    "skill_loaded": category != "negative",
                    "evidence_sha256": hashlib.sha256((host + cid).encode()).hexdigest(),
                }
            )
        hosts[host] = {
            "agent_version": {
                "claude_code": "2.1.296",
                "codex": "0.160.0",
                "pi_agent": "1.1.0",
            }[host],
            "model_inference_status": "pass",
            "native_discovery": "pass",
            "tests": tests,
        }
    return {
        "schema_version": 1,
        "source_revision": SOURCE,
        "target": {"api_version": "2.1.296", "surface": "cli"},
        "hosts": hosts,
    }


def _account(dist: Path) -> dict:
    file = dist / "packages" / f"claude-code-mods-knowledge-{VERSION}.zip"
    return {
        "schema_version": 1,
        "installed_plugin_version": VERSION,
        "installed_enabled": True,
        "skill_enabled": True,
        "chat_surface": "chat",
        "installed_bundle_sha256": hashlib.sha256(file.read_bytes()).hexdigest(),
        "rollback_verified": True,
        "evidence_sha256": "f" * 64,
    }


def _evaluate(tmp: Path, **overrides) -> dict:
    dist = _bundle(tmp)
    chat = overrides.get("chat", _chat())
    agents = overrides.get("agents", _agents())
    account = overrides.get("account", _account(dist))
    return assess_stable_release(ROOT, dist, chat=chat, agents=agents, account=account)


def test_hypothetical_fully_verified_fixture_passes_eligible_gate(tmp_path: Path) -> None:
    report = _evaluate(tmp_path)
    assert report["status"] == "READY_FOR_STABLE_RELEASE"
    assert report["eligible_for_stable_release"] is True
    assert report["blockers"] == []
    assert report["checks"]["package_integrity"] == "pass"
    assert report["checks"]["chat_46_case_quality"] == "pass"
    assert report["checks"]["three_agent_model_validation"] == "pass"
    assert report["checks"]["account_install_rollback"] == "pass"


def test_real_beta1_fails_closed_even_after_package_qa_success(tmp_path: Path) -> None:
    dist = _bundle(tmp_path)
    chat = json.loads(
        (ROOT / "docs/reports/2026-10-14-beta1-complete-semantic-qa.json").read_text()
    )
    hosts = json.loads(
        (ROOT / "docs/reports/2026-10-14-native-agent-skill-discovery.json").read_text()
    )
    report = assess_stable_release(
        ROOT,
        dist,
        chat=chat,
        agents=hosts,
        account={"installed_plugin_version": "0.2.0-beta.1", "installed_enabled": True},
    )
    assert report["status"] == "STABLE_RELEASE_BLOCKED"
    assert report["eligible_for_stable_release"] is False
    assert report["checks"]["package_integrity"] == "pass"
    assert len(report["blockers"]) >= 3
    assert not any("conversation_id" in str(item) for item in report["blockers"])


@pytest.mark.parametrize(
    "mutate",
    [
        lambda rows: rows.pop(),
        lambda rows: rows[0].update({"skill_loaded": False}),
        lambda rows: rows[0].update({"final_verdict": "failed"}),
        lambda rows: rows[0].update({"semantic_review": None}),
        lambda rows: rows[0].update({"plugin_id_sha256": None}),
        lambda rows: rows[0].update({"response_sha256": "notsha"}),
        lambda rows: rows[1].update({"conversation_sha256": rows[0]["conversation_sha256"]}),
        lambda rows: rows[30].update({"skill_loaded": True}),
    ],
)
def test_any_missing_wrong_or_duplicate_chat_evidence_blocks_release(
    tmp_path: Path, mutate
) -> None:
    chat = _chat()
    mutate(chat["items"])
    report = _evaluate(tmp_path, chat=chat)
    assert report["eligible_for_stable_release"] is False
    assert report["checks"]["chat_46_case_quality"] == "fail"


@pytest.mark.parametrize(
    "mutate",
    [
        lambda h: h.pop("claude_code"),
        lambda h: h["codex"].update({"model_inference_status": "not_run"}),
        lambda h: h["pi_agent"]["tests"][0].update({"real_inference": False}),
        lambda h: h["claude_code"]["tests"][2].update({"skill_loaded": True}),
        lambda h: h["codex"]["tests"][1].update({"answer_verdict": "fail"}),
        lambda h: h["claude_code"]["tests"][0].update({"evidence_sha256": "invalid"}),
    ],
)
def test_missing_agent_inference_or_regression_blocks_release(tmp_path: Path, mutate) -> None:
    agents = _agents()
    mutate(agents["hosts"])
    report = _evaluate(tmp_path, agents=agents)
    assert not report["eligible_for_stable_release"]
    assert report["checks"]["three_agent_model_validation"] == "fail"


@pytest.mark.parametrize(
    "change",
    [
        {"installed_enabled": False},
        {"installed_plugin_version": "0.2.0-beta.1"},
        {"chat_surface": "work"},
        {"installed_bundle_sha256": "e" * 64},
        {"rollback_verified": False},
        {"evidence_sha256": "invalid"},
    ],
)
def test_installation_mismatch_fails_stable_gate(tmp_path: Path, change) -> None:
    dist = _bundle(tmp_path)
    acc = _account(dist)
    acc.update(change)
    report = assess_stable_release(ROOT, dist, chat=_chat(), agents=_agents(), account=acc)
    assert not report["eligible_for_stable_release"]
    assert report["checks"]["account_install_rollback"] == "fail"


def test_tampered_release_build_is_not_evaluated_as_valid(tmp_path: Path) -> None:
    dist = _bundle(tmp_path)
    p = dist / "packages" / f"claude-code-mods-knowledge-{VERSION}.zip"
    p.write_bytes(p.read_bytes() + b"TAMPERED")
    with pytest.raises(StableGateError, match="build|package|dist"):
        assess_stable_release(
            ROOT,
            dist,
            chat=_chat(),
            agents=_agents(),
            account=_account(_bundle(tmp_path / "untampered")),
        )


def test_no_raw_chat_or_account_secrets_in_stable_gate_report(tmp_path: Path) -> None:
    report = _evaluate(tmp_path)
    serialized = json.dumps(report)
    for marker in (
        "conversation_id",
        "raw_reply",
        "chatgpt.com/c/",
        "access_token",
        "Cookie:",
        "api_key",
        "private_message",
    ):
        assert marker not in serialized


def test_model_host_wrong_claude_version_blocks_target_certification(tmp_path: Path) -> None:
    agents = _agents()
    agents["hosts"]["claude_code"]["agent_version"] = "2.1.289"
    result = _evaluate(tmp_path, agents=agents)
    assert not result["eligible_for_stable_release"]
    assert "P5_CLAUDE_CODE_TARGET_VERSION_NOT_MATCHED" in result["blockers"]


def test_same_agent_evidence_reused_for_two_hosts_is_not_independent(tmp_path: Path) -> None:
    agents = _agents()
    agents["hosts"]["codex"]["tests"][0]["evidence_sha256"] = agents["hosts"]["claude_code"][
        "tests"
    ][0]["evidence_sha256"]
    assert not _evaluate(tmp_path, agents=agents)["eligible_for_stable_release"]


def test_explicit_invocation_cannot_be_counted_as_automatic_pass(tmp_path: Path) -> None:
    chat = _chat()
    chat["items"][0]["invocation_mode"] = "explicit"
    assert not _evaluate(tmp_path, chat=chat)["eligible_for_stable_release"]


def test_unhashable_or_missing_evidence_cannot_crash_or_pass(tmp_path: Path) -> None:
    for change in (
        {"id": ["POS-E-01"]},
        {"resource_uris": [{"malicious": "value"}]},
        {"conversation_sha256": ["notsha"]},
    ):
        row = _chat()
        row["items"][0].update(change)
        assert (
            _evaluate(tmp_path / hashlib.sha256(str(change).encode()).hexdigest()[:9], chat=row)[
                "eligible_for_stable_release"
            ]
            is False
        )


def test_missing_summary_failure_count_blocks_stable(tmp_path: Path) -> None:
    chat = _chat()
    del chat["summary"]["failed"]
    assert not _evaluate(tmp_path, chat=chat)["eligible_for_stable_release"]


def test_unhashable_agent_case_id_fails_closed(tmp_path: Path) -> None:
    agents = _agents()
    agents["hosts"]["codex"]["tests"][0]["case_id"] = ["POS-E-01"]
    assert not _evaluate(tmp_path, agents=agents)["eligible_for_stable_release"]


@pytest.mark.parametrize(
    "resource_uri",
    [
        "skills://plugins/claude-code-mods-knowledge/other-skill",
        "skills://plugins/claude-code-mods-knowledge/claude-code-mods-development-fake",
        "skills://plugins/claude-code-mods-knowledge/claude-code-mods-development/../other-skill",
    ],
)
def test_wrong_or_disguised_skill_read_cannot_qualify_stable_release(
    tmp_path: Path, resource_uri: str
) -> None:
    chat = _chat()
    chat["items"][0]["resource_uris"] = [resource_uri]
    report = _evaluate(tmp_path, chat=chat)
    assert report["eligible_for_stable_release"] is False
    assert "CHAT_RESOURCE_READ_WRONG_PLUGIN" in report["blockers"]
