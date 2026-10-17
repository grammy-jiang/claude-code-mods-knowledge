"""A stable Plugin release cannot be certified from ZIP/static/partial Chat evidence."""

from __future__ import annotations

import hashlib
import io
import json
import stat
import zipfile
from pathlib import Path

import pytest

from mods_knowledge.account_archive import _expected_server_sidecar, verify_account_download
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


def _download(dist: Path) -> bytes:
    """Synthetic, deterministic account-format ZIP; never an account observation."""
    original = (dist / "packages" / f"claude-code-mods-knowledge-{VERSION}.zip").read_bytes()
    with zipfile.ZipFile(io.BytesIO(original)) as source:
        prefix = "claude-code-mods-knowledge/"
        entries = {
            info.filename[len(prefix) :]: source.read(info.filename) for info in source.infolist()
        }
    manifest = json.loads(entries["plugin.json"])
    entries[".codex-plugin/plugin.json"] = json.dumps(
        _expected_server_sidecar(manifest), sort_keys=True
    ).encode()
    target = io.BytesIO()
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, payload in sorted(entries.items()):
            member = zipfile.ZipInfo(name, date_time=(2026, 10, 14, 16, 0, 0))
            member.compress_type = zipfile.ZIP_DEFLATED
            member.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(member, payload)
    return target.getvalue()


def _account(dist: Path) -> dict:
    file = dist / "packages" / f"claude-code-mods-knowledge-{VERSION}.zip"
    audit = verify_account_download(file.read_bytes(), _download(dist))
    return {
        "schema_version": 1,
        "installed_plugin_version": VERSION,
        "installed_enabled": True,
        "skill_enabled": True,
        "chat_surface": "chat",
        "installed_bundle_sha256": audit["downloaded_zip_sha256"],
        "source_bundle_sha256": audit["uploaded_zip_sha256"],
        "canonical_content_sha256": audit["canonical_content_sha256"],
        "server_sidecar_sha256": audit["server_sidecar_sha256"],
        "rollback_verified": True,
        "evidence_sha256": "f" * 64,
    }


def _evaluate(tmp: Path, **overrides) -> dict:
    dist = _bundle(tmp)
    chat = overrides.get("chat", _chat())
    agents = overrides.get("agents", _agents())
    account = overrides.get("account", _account(dist))
    download = overrides.get("account_download_zip", _download(dist))
    return assess_stable_release(
        ROOT,
        dist,
        chat=chat,
        agents=agents,
        account=account,
        account_download_zip=download,
    )


def test_hypothetical_fully_verified_fixture_passes_eligible_gate(tmp_path: Path) -> None:
    report = _evaluate(tmp_path)
    assert report["status"] == "READY_FOR_STABLE_RELEASE"
    assert report["eligible_for_stable_release"] is True
    assert report["blockers"] == []
    assert report["checks"]["package_integrity"] == "pass"
    assert report["checks"]["chat_46_case_quality"] == "pass"
    assert report["checks"]["three_agent_model_validation"] == "pass"
    assert report["checks"]["account_install_rollback"] == "pass"
    assert report["checks"]["account_archive_content"] == "pass"


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
    report = assess_stable_release(
        ROOT,
        dist,
        chat=_chat(),
        agents=_agents(),
        account=acc,
        account_download_zip=_download(dist),
    )
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


def test_account_report_without_downloaded_archive_cannot_certify_stable(tmp_path: Path) -> None:
    """A claimed installed upload checksum cannot establish account ZIP equality."""
    dist = _bundle(tmp_path)
    report = assess_stable_release(
        ROOT, dist, chat=_chat(), agents=_agents(), account=_account(dist)
    )
    assert report["eligible_for_stable_release"] is False
    assert "ACCOUNT_DOWNLOAD_ARCHIVE_MISSING" in report["blockers"]


def test_account_downloaded_bytes_are_required_not_merely_attested_hashes(tmp_path: Path) -> None:
    dist = _bundle(tmp_path)
    report = assess_stable_release(
        ROOT,
        dist,
        chat=_chat(),
        agents=_agents(),
        account=_account(dist),
        account_download_zip=b"not really a ChatGPT download",
    )
    assert report["eligible_for_stable_release"] is False
    assert report["checks"]["account_archive_content"] == "fail"


@pytest.mark.parametrize(
    "field",
    [
        "installed_bundle_sha256",
        "source_bundle_sha256",
        "canonical_content_sha256",
        "server_sidecar_sha256",
    ],
)
def test_account_report_hash_must_match_verified_bytes(tmp_path: Path, field: str) -> None:
    dist = _bundle(tmp_path)
    account = _account(dist)
    account[field] = "0" * 64
    result = assess_stable_release(
        ROOT,
        dist,
        chat=_chat(),
        agents=_agents(),
        account=account,
        account_download_zip=_download(dist),
    )
    assert result["eligible_for_stable_release"] is False
    assert result["checks"]["account_archive_content"] == "pass"
    assert result["checks"]["account_install_rollback"] == "fail"
    assert "CHATGPT_ACCOUNT_ARCHIVE_EVIDENCE_MISMATCH" in result["blockers"]


def test_raw_account_secrets_cannot_be_smuggled_into_audit(tmp_path: Path) -> None:
    dist = _bundle(tmp_path)
    account = _account(dist)
    account["Cookie"] = "unexpected account secret"
    result = assess_stable_release(
        ROOT,
        dist,
        chat=_chat(),
        agents=_agents(),
        account=account,
        account_download_zip=_download(dist),
    )
    assert result["eligible_for_stable_release"] is False
    assert "CHATGPT_ACCOUNT_EVIDENCE_SCHEMA_INVALID" in result["blockers"]
    assert "unexpected account secret" not in json.dumps(result)


def test_corrupt_account_download_must_fail_even_with_matching_claimed_report(
    tmp_path: Path,
) -> None:
    dist = _bundle(tmp_path)
    result = assess_stable_release(
        ROOT,
        dist,
        chat=_chat(),
        agents=_agents(),
        account=_account(dist),
        account_download_zip=b"corrupt ZIP, not a ChatGPT account read",
    )
    assert result["eligible_for_stable_release"] is False
    assert "ACCOUNT_DOWNLOAD_CONTENT_MISMATCH_OR_INVALID" in result["blockers"]


def test_empty_or_untyped_account_download_fails_closed(tmp_path: Path) -> None:
    for value in (b"", {}, "fake ZIP"):
        result = _evaluate(
            tmp_path / hashlib.sha256(str(value).encode()).hexdigest()[:8],
            account_download_zip=value,
        )
        assert result["eligible_for_stable_release"] is False
        assert result["checks"]["account_archive_content"] == "fail"


@pytest.mark.parametrize("schema", [True, "1", 2, None])
def test_account_evidence_schema_version_type_checked(tmp_path: Path, schema) -> None:
    dist = _bundle(tmp_path)
    acc = _account(dist)
    acc["schema_version"] = schema
    report = assess_stable_release(
        ROOT,
        dist,
        chat=_chat(),
        agents=_agents(),
        account=acc,
        account_download_zip=_download(dist),
    )
    assert not report["eligible_for_stable_release"]
    assert "CHATGPT_ACCOUNT_EVIDENCE_SCHEMA_INVALID" in report["blockers"]


def test_latest_cli_302_suite_is_scored_as_blocked_without_original_real_model_evidence(
    tmp_path: Path,
) -> None:
    from mods_knowledge.evaluator import validate_suite

    suite = json.loads((ROOT / "evals/p4_cases_cli_2_1_302.json").read_text())
    validate_suite(suite)
    assert suite["target"] == {"claude_code_version": "2.1.302", "surface": "cli"}
    assert len(suite["cases"]) == 46
    positive = [c for c in suite["cases"] if c["category"] == "positive"]
    negatives = [c for c in suite["cases"] if c["category"] == "negative"]
    boundary = [c for c in suite["cases"] if c["category"] == "boundary"]
    assert (len(positive), len(negatives), len(boundary)) == (30, 8, 8)
    assert all("Target exactly Claude Code CLI 2.1.302." in c["prompt"] for c in positive)
    assert all("Target exactly Claude Code CLI 2.1.302." not in c["prompt"] for c in negatives)
    assert all("Target exactly Claude Code CLI 2.1.302." not in c["prompt"] for c in boundary)
    dist = tmp_path / "latest_302_dist"
    build_artifacts(
        ROOT,
        dist,
        api_version="2.1.302",
        surface="cli",
        package_version=VERSION,
        source_revision=SOURCE,
    )
    gate = assess_stable_release(
        ROOT, dist, chat=None, agents=None, account=None, account_download_zip=None
    )
    assert gate["target"] == {"api_version": "2.1.302", "surface": "cli"}
    assert gate["checks"]["package_integrity"] == "pass"
    assert gate["status"] == "STABLE_RELEASE_BLOCKED"
    assert "CHAT_REPORT_MISSING" in gate["blockers"]
    assert "P5_REAL_HOST_MODEL_EVIDENCE_MISSING" in gate["blockers"]
    assert gate["eligible_for_stable_release"] is False
