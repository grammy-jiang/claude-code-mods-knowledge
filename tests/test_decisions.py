"""Test audited, explicit Claim lifecycle transitions without online fetches."""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

import pytest

from mods_knowledge.claims import load_claims
from mods_knowledge.decisions import transition_claim
from mods_knowledge.errors import ClaimError
from mods_knowledge.registry import load_registry

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "docs/design/mods_ssot_design_v0_1/EXAMPLE_CANDIDATE_CLAIM.json"


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


@pytest.fixture
def project(tmp_path: Path) -> Path:
    (tmp_path / "sources").mkdir()
    shutil.copy2(ROOT / "sources/registry.json", tmp_path / "sources/registry.json")
    shutil.copytree(ROOT / "sources/snapshots", tmp_path / "sources/snapshots")
    target = tmp_path / "targets/profiles.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "targets/profiles.json", target)
    claim = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    _write(tmp_path / "claims/K-0001.json", claim)
    return tmp_path


def make_source_evidence_reviewable(project: Path) -> None:
    registry_file = project / "sources/registry.json"
    reg = json.loads(registry_file.read_text(encoding="utf-8"))
    entry = next(item for item in reg["sources"] if item["source_id"] == "M003")
    digest = json.loads((project / "sources/snapshots/index.json").read_text())["sources"]["M003"][
        "current"
    ]
    entry["review_state"] = "pinned"
    entry["snapshot"].update(
        state="pinned", sha256=digest, checked_at=datetime.now(UTC).isoformat()
    )
    _write(registry_file, reg)
    # Synthetic official-markdown review attestation. This is test-only
    # metadata, never a declaration that the real upstream was reviewed.
    official_md = b"## Mod lifecycle\\nsynthetic official review text"
    section = official_md
    _write(
        project / "sources/reviews/M003.json",
        {
            "schema_version": 1,
            "source_id": "M003",
            "html_url": entry["url"],
            "html_sha256": digest,
            "markdown_url": entry["url"] + ".md",
            "markdown_sha256": hashlib.sha256(official_md).hexdigest(),
            "reviewed_at": entry["snapshot"]["checked_at"],
            "reviewer": "synthetic-test-reviewer",
            "scope": "Synthetic fixture only, not real API review",
            "sections": [
                {
                    "anchor": "mod-lifecycle",
                    "heading": "Mod lifecycle",
                    "line_start": 1,
                    "line_end": 2,
                    "section_sha256": hashlib.sha256(section).hexdigest(),
                }
            ],
        },
    )
    claim_file = project / "claims/K-0001.json"
    claim = json.loads(claim_file.read_text())
    claim["evidence"][0].update(
        role="supports",
        locator="https://code.claude.com/docs/en/plugins/mods/reference#mod-lifecycle",
        snapshot_sha256=digest,
        notes="Reviewed official source against the pinned observation; synthetic test scenario",
    )
    claim["verification"]["source"] = "reviewed"
    _write(claim_file, claim)


def make_normative(project: Path) -> None:
    make_source_evidence_reviewable(project)
    file = project / "claims/K-0001.json"
    claim = json.loads(file.read_text())
    claim.update(authority="normative", kind="behavior")
    claim["applies_to"]["claude_code"].update(min_inclusive="2.1.296", max_exclusive="2.1.297")
    claim["applies_to"]["surfaces"] = ["cli"]
    _write(file, claim)


def make_runtime_report(project: Path) -> None:
    claim_file = project / "claims/K-0001.json"
    claim = json.loads(claim_file.read_text())
    log_path = project / "evidence/runtime/K-0001-macbook-20261013.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    body = b"synthetic integration test pass; no live API verification\n"
    log_path.write_bytes(body)
    report_path = project / "evidence/runtime/K-0001-macbook-20261013.json"
    _write(
        report_path,
        {
            "schema_version": 1,
            "claim_id": "K-0001",
            "profile_id": "macbook-20261013",
            "claude_code_version": "2.1.296",
            "surface": "cli",
            "command": "synthetic-test-only; NOT real production evidence",
            "exit_code": 0,
            "result": "pass",
            "log_path": "evidence/runtime/K-0001-macbook-20261013.log",
            "log_sha256": hashlib.sha256(body).hexdigest(),
            "observed_at": "2026-10-13T12:00:00Z",
        },
    )
    claim["verification"].update(
        runtime="integration-pass",
        runtime_profiles=["macbook-20261013"],
        test_evidence=[
            "evidence/runtime/K-0001-macbook-20261013.json#sha256="
            + hashlib.sha256(report_path.read_bytes()).hexdigest()
        ],
    )
    _write(claim_file, claim)


NOW = datetime(2026, 10, 13, 12, 3, 45, tzinfo=UTC)


def test_candidate_cannot_review_without_pinned_evidence(project: Path) -> None:
    original = (project / "claims/K-0001.json").read_bytes()
    with pytest.raises(ClaimError):
        transition_claim(project, "K-0001", "reviewed", "agent-review", "Reviewed placeholder", NOW)
    assert (project / "claims/K-0001.json").read_bytes() == original
    assert not (project / "decisions/K-0001.json").exists()


def test_review_and_approval_follow_explicit_audited_two_step_flow(project: Path) -> None:
    make_normative(project)
    make_runtime_report(project)
    first = transition_claim(
        project,
        "K-0001",
        "reviewed",
        "test-reviewer",
        "Reviewed pinned source and synthetic local test evidence in fixture",
        NOW,
    )
    assert first["lifecycle"] == "reviewed"
    second = transition_claim(
        project,
        "K-0001",
        "approved",
        "test-reviewer",
        "Confirmed a bounded synthetic test record for validation only",
        NOW,
    )
    assert second["lifecycle"] == "approved"
    audit = json.loads((project / "decisions/K-0001.json").read_text())
    assert [event["to_state"] for event in audit["events"]] == ["reviewed", "approved"]
    assert audit["events"][1]["previous_event_sha256"] == audit["events"][0]["event_sha256"]
    claims = load_claims(
        project / "claims",
        load_registry(project / "sources/registry.json"),
        project / "sources/snapshots",
        project / "decisions",
    )
    assert claims["K-0001"]["lifecycle"] == "approved"


def test_unverified_runtime_never_enters_normative_approval(project: Path) -> None:
    make_normative(project)
    transition_claim(project, "K-0001", "reviewed", "reviewer", "Checked source and metadata", NOW)
    claim_before = (project / "claims/K-0001.json").read_bytes()
    audit_before = (project / "decisions/K-0001.json").read_bytes()
    with pytest.raises(ClaimError, match="runtime"):
        transition_claim(
            project,
            "K-0001",
            "approved",
            "reviewer",
            "Tried to approve without a verified runtime test",
            NOW,
        )
    assert (project / "claims/K-0001.json").read_bytes() == claim_before
    assert (project / "decisions/K-0001.json").read_bytes() == audit_before


def test_tampered_decision_is_detected(project: Path) -> None:
    make_source_evidence_reviewable(project)
    transition_claim(
        project, "K-0001", "reviewed", "reviewer", "Reviewed source and digest metadata", NOW
    )
    p = project / "decisions/K-0001.json"
    ledger = json.loads(p.read_text())
    ledger["events"][0]["rationale"] = "tampered"
    _write(p, ledger)
    with pytest.raises(ClaimError, match="hash"):
        load_claims(
            project / "claims",
            load_registry(project / "sources/registry.json"),
            project / "sources/snapshots",
            project / "decisions",
        )


def test_invalid_transition_or_empty_reason_does_not_mutate(project: Path) -> None:
    before = (project / "claims/K-0001.json").read_bytes()
    for target, rationale in (("approved", "valid nonempty reason"), ("reviewed", "")):
        with pytest.raises(ClaimError):
            transition_claim(project, "K-0001", target, "reviewer", rationale, NOW)
    assert (project / "claims/K-0001.json").read_bytes() == before
    assert not (project / "decisions/K-0001.json").exists()


def test_direct_rejection_keeps_audited_record_and_history(project: Path) -> None:
    out = transition_claim(
        project,
        "K-0001",
        "rejected",
        "reviewer",
        "Evidence is not current and must not be promoted",
        NOW,
    )
    assert out["lifecycle"] == "rejected"
    ledger = json.loads((project / "decisions/K-0001.json").read_text())
    assert ledger["events"][0]["from_state"] == "candidate"
    assert ledger["events"][0]["to_state"] == "rejected"


def test_tampered_claim_body_breaks_ledger_binding(project: Path) -> None:
    make_source_evidence_reviewable(project)
    transition_claim(
        project,
        "K-0001",
        "reviewed",
        "reviewer",
        "Reviewed source and metadata for synthetic test",
        NOW,
    )
    file = project / "claims/K-0001.json"
    claim = json.loads(file.read_text())
    claim["statement"] += " ALTERED"
    _write(file, claim)
    with pytest.raises(ClaimError, match="hash"):
        load_claims(
            project / "claims",
            load_registry(project / "sources/registry.json"),
            project / "sources/snapshots",
            project / "decisions",
        )


def test_reviewer_is_a_recorded_label_and_cannot_be_blank(project: Path) -> None:
    with pytest.raises(ClaimError):
        transition_claim(project, "K-0001", "rejected", " ", "Some valid reason", NOW)
    with pytest.raises(ClaimError):
        transition_claim(
            project, "K-0001", "rejected", "reviewer", "Some valid reason", datetime(2026, 10, 13)
        )


@pytest.mark.parametrize(
    "tamper",
    [
        lambda x: x.update(log_sha256="a" * 64),
        lambda x: x.update(claude_code_version="2.1.999"),
        lambda x: x.update(profile_id="unknown-mac"),
        lambda x: x.update(log_path="../../../../etc/passwd"),
        lambda x: x.update(result="fail"),
        lambda x: x.update(exit_code=1),
        lambda x: x.update(command=""),
        lambda x: x.update(claim_id="K-7777"),
    ],
)
def test_normative_approval_rejects_unverified_runtime_report(project: Path, tamper) -> None:
    make_normative(project)
    make_runtime_report(project)
    transition_claim(
        project,
        "K-0001",
        "reviewed",
        "test-reviewer",
        "Reviewed synthetic source and bounded evidence fixture",
        NOW,
    )
    report_path = project / "evidence/runtime/K-0001-macbook-20261013.json"
    report = json.loads(report_path.read_text())
    tamper(report)
    _write(report_path, report)
    before = (project / "claims/K-0001.json").read_bytes()
    with pytest.raises(ClaimError):
        transition_claim(
            project,
            "K-0001",
            "approved",
            "test-reviewer",
            "Attempted to approve a deliberately altered runtime report",
            NOW,
        )
    assert (project / "claims/K-0001.json").read_bytes() == before


@pytest.mark.parametrize(
    "tamper",
    [
        lambda x: x.update(log_sha256="f" * 64),
        lambda x: x.update(claude_code_version="2.1.999"),
        lambda x: x.update(profile_id="unregistered"),
        lambda x: x.update(log_path="../../secrets.json"),
        lambda x: x.update(result="fail"),
        lambda x: x.update(exit_code=1),
        lambda x: x.update(command=""),
        lambda x: x.update(claim_id="K-7777"),
        lambda x: x.update(surface="desktop"),
    ],
)
def test_normative_approval_rejects_semantically_invalid_repinned_runtime_evidence(
    project: Path, tamper
) -> None:
    """Rehash the tampered report; semantic policy must still block approval."""
    make_normative(project)
    make_runtime_report(project)
    report_path = project / "evidence/runtime/K-0001-macbook-20261013.json"
    report = json.loads(report_path.read_text())
    tamper(report)
    _write(report_path, report)
    claim_path = project / "claims/K-0001.json"
    claim = json.loads(claim_path.read_text())
    claim["verification"]["test_evidence"] = [
        "evidence/runtime/K-0001-macbook-20261013.json#sha256="
        + hashlib.sha256(report_path.read_bytes()).hexdigest()
    ]
    _write(claim_path, claim)
    transition_claim(
        project,
        "K-0001",
        "reviewed",
        "test-reviewer",
        "Reviewed the official source, before deciding on runtime evidence",
        NOW,
    )
    with pytest.raises(ClaimError):
        transition_claim(
            project,
            "K-0001",
            "approved",
            "test-reviewer",
            "Reject altered runtime report despite a matching report digest",
            NOW,
        )


def test_approved_claim_is_filtered_by_explicit_version_and_surface(project: Path) -> None:
    from mods_knowledge.claims import approved_claims

    make_normative(project)
    make_runtime_report(project)
    transition_claim(
        project,
        "K-0001",
        "reviewed",
        "test-reviewer",
        "Review for bounded synthetic test case",
        NOW,
    )
    transition_claim(
        project,
        "K-0001",
        "approved",
        "test-reviewer",
        "Approve synthetic fixture to exercise version-aware filtering",
        NOW,
    )
    claims = load_claims(
        project / "claims",
        load_registry(project / "sources/registry.json"),
        project / "sources/snapshots",
        project / "decisions",
    )
    assert [c["claim_id"] for c in approved_claims(claims, "2.1.296", "cli")] == ["K-0001"]
    assert approved_claims(claims, "2.1.295", "cli") == []
    assert approved_claims(claims, "2.1.297", "cli") == []
    assert approved_claims(claims, "2.1.296", "desktop") == []


def test_approved_claim_fails_if_runtime_report_is_later_mutated(project: Path) -> None:
    make_normative(project)
    make_runtime_report(project)
    transition_claim(
        project,
        "K-0001",
        "reviewed",
        "reviewer",
        "Reviewed version and pinned official source",
        NOW,
    )
    transition_claim(
        project,
        "K-0001",
        "approved",
        "reviewer",
        "Test approval of synthetic reference report",
        NOW,
    )
    report_file = project / "evidence/runtime/K-0001-macbook-20261013.json"
    record = json.loads(report_file.read_text())
    record["command"] = "silently changed after approval"
    _write(report_file, record)
    with pytest.raises(ClaimError, match="SHA-256"):
        load_claims(
            project / "claims",
            load_registry(project / "sources/registry.json"),
            project / "sources/snapshots",
            project / "decisions",
        )


def test_overlapping_approved_normative_subjects_are_rejected(project: Path) -> None:
    make_normative(project)
    make_runtime_report(project)
    first = json.loads((project / "claims/K-0001.json").read_text())
    second = json.loads(json.dumps(first))
    second["claim_id"] = "K-0002"
    report_path = project / "evidence/runtime/K-0001-macbook-20261013.json"
    report = json.loads(report_path.read_text())
    report["claim_id"] = "K-0002"
    report["log_path"] = "evidence/runtime/K-0002-macbook-20261013.log"
    original_log = project / "evidence/runtime/K-0001-macbook-20261013.log"
    other_log = project / report["log_path"]
    other_log.write_bytes(original_log.read_bytes())
    other_report = project / "evidence/runtime/K-0002-macbook-20261013.json"
    _write(other_report, report)
    second["verification"]["test_evidence"] = [
        "evidence/runtime/K-0002-macbook-20261013.json#sha256="
        + hashlib.sha256(other_report.read_bytes()).hexdigest()
    ]
    _write(project / "claims/K-0002.json", second)
    for cid in ("K-0001", "K-0002"):
        transition_claim(
            project,
            cid,
            "reviewed",
            "reviewer",
            "Reviewed pinned source for this synthetic test Claim",
            NOW,
        )
    transition_claim(
        project,
        "K-0001",
        "approved",
        "reviewer",
        "First scoped, runtime-tested synthetic Claim",
        NOW,
    )
    before = (project / "claims/K-0002.json").read_bytes()
    with pytest.raises(ClaimError, match="overlapping normative claims"):
        transition_claim(
            project,
            "K-0002",
            "approved",
            "reviewer",
            "Second synthetic Claim conflicts for same subject and runtime",
            NOW,
        )
    assert (project / "claims/K-0002.json").read_bytes() == before


@pytest.mark.parametrize("mutation", ["url", "timestamp"])
def test_approved_normative_rejects_source_metadata_identity_drift(
    project: Path, mutation: str
) -> None:
    make_normative(project)
    make_runtime_report(project)
    transition_claim(
        project,
        "K-0001",
        "reviewed",
        "reviewer",
        "Reviewed synthetic official source and matching current pointer",
        NOW,
    )
    transition_claim(
        project,
        "K-0001",
        "approved",
        "reviewer",
        "Approved bounded local policy fixture as a synthetic test",
        NOW,
    )
    path = project / "sources/registry.json"
    registry = json.loads(path.read_text())
    entry = next(item for item in registry["sources"] if item["source_id"] == "M003")
    if mutation == "url":
        entry["url"] = "https://code.claude.com/docs/en/different-document"
        entry["canonical_url"] = entry["url"]
    else:
        entry["snapshot"]["checked_at"] = "2026-10-12T00:00:00Z"
    _write(path, registry)
    with pytest.raises(ClaimError):
        load_claims(
            project / "claims",
            load_registry(project / "sources/registry.json"),
            project / "sources/snapshots",
            project / "decisions",
        )


def test_review_rejects_locator_into_wrong_document(project: Path) -> None:
    make_source_evidence_reviewable(project)
    path = project / "claims/K-0001.json"
    claim = json.loads(path.read_text())
    claim["evidence"][0]["locator"] = (
        "https://code.claude.com/docs/en/plugins/mods/test#some-other-section"
    )
    _write(path, claim)
    with pytest.raises(ClaimError):
        transition_claim(
            project,
            "K-0001",
            "reviewed",
            "reviewer",
            "Tried to review evidence from a different document",
            NOW,
        )


def test_approval_rechecks_active_target_profile_version_not_archived_design(project: Path) -> None:
    make_normative(project)
    make_runtime_report(project)
    transition_claim(
        project,
        "K-0001",
        "reviewed",
        "reviewer",
        "Reviewed official evidence before bounded target verification",
        NOW,
    )
    transition_claim(
        project,
        "K-0001",
        "approved",
        "reviewer",
        "Approved only scoped synthetic test profile",
        NOW,
    )
    path = project / "targets/profiles.json"
    profiles = json.loads(path.read_text())
    next(p for p in profiles if p["profile_id"] == "macbook-20261013")["claude_code_version"] = (
        "2.1.999"
    )
    _write(path, profiles)
    with pytest.raises(ClaimError, match="version"):
        load_claims(
            project / "claims",
            load_registry(project / "sources/registry.json"),
            project / "sources/snapshots",
            project / "decisions",
        )


def test_active_target_profile_ids_must_be_unique(project: Path) -> None:
    make_normative(project)
    make_runtime_report(project)
    transition_claim(
        project,
        "K-0001",
        "reviewed",
        "reviewer",
        "Reviewed official evidence and expected target version",
        NOW,
    )
    path = project / "targets/profiles.json"
    profiles = json.loads(path.read_text())
    import copy

    profiles.append(copy.deepcopy(profiles[0]))
    _write(path, profiles)
    with pytest.raises(ClaimError, match="duplicate"):
        transition_claim(
            project,
            "K-0001",
            "approved",
            "reviewer",
            "Conflicting target registration cannot establish test identity",
            NOW,
        )


def test_official_example_commit_string_alone_cannot_review_guidance(
    project: Path,
) -> None:
    file = project / "claims/K-0001.json"
    claim = json.loads(file.read_text())
    claim["evidence"][0].update(
        source_id="M036",
        kind="official-example",
        role="supports",
        locator="https://claude.dev/blog/getting-started-with-claude-code-mods/",
        commit_sha="a" * 40,
    )
    claim["verification"]["source"] = "reviewed"
    _write(file, claim)
    with pytest.raises(ClaimError, match="pinned"):
        transition_claim(
            project,
            "K-0001",
            "reviewed",
            "reviewer",
            "Unverified example commit must not be treated as an official pin",
            NOW,
        )


def test_concurrent_transition_never_writes_two_conflicting_audit_events(
    project: Path,
) -> None:
    from concurrent.futures import ThreadPoolExecutor

    def reject_once() -> str:
        try:
            transition_claim(
                project,
                "K-0001",
                "rejected",
                "reviewer",
                "Two concurrent attempts must result in one terminal rejection",
                NOW,
            )
            return "accepted"
        except ClaimError:
            return "rejected"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: reject_once(), range(2)))
    assert sorted(results) == ["accepted", "rejected"]
    ledger = json.loads((project / "decisions/K-0001.json").read_text())
    assert len(ledger["events"]) == 1
    assert ledger["events"][0]["to_state"] == "rejected"
