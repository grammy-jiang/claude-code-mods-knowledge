"""P6 deterministic, private release wrapper: no public-directory claims."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mods_knowledge.compiler import build_artifacts
from mods_knowledge.release_builder import (
    ReleaseBuildError,
    build_release,
    verify_release,
)

ROOT = Path(__file__).resolve().parents[1]
TAG = "v0.1.0-rc.1"
COMMIT = "a" * 40


def source_build(tmp_path: Path) -> Path:
    dist = tmp_path / "dist"
    build_artifacts(
        ROOT,
        dist,
        api_version="2.1.296",
        surface="cli",
        package_version="0.1.0-rc.1",
        source_revision=COMMIT,
    )
    return dist


def host_matrix() -> dict:
    return {
        "schema_version": 1,
        "platforms": {
            "macbook": {"static_tests": "pass", "token_based_agent_test": "not_run"},
            "raspberrypi": {"static_tests": "pass", "token_based_agent_test": "not_run"},
            "sextant": {"static_tests": "pass", "token_based_agent_test": "not_run"},
        },
        "chatgpt": {
            "marketplace_source": "prepared",
            "local_package_cache": "not_verified",
            "chat_skill_activation": "not_run",
            "chat_answer_evaluation": "not_run",
        },
    }


def test_release_bundle_is_a_prerelease_and_never_claims_chatgpt_host_pass(tmp_path: Path) -> None:
    dist = source_build(tmp_path)
    folder = tmp_path / "release"
    out = build_release(
        ROOT,
        dist,
        folder,
        source_revision=COMMIT,
        tag=TAG,
        host_matrix=host_matrix(),
    )
    assert out["status"] == "prerelease_host_runtime_unverified"
    assert out["tag"] == TAG
    assert out["source_revision"] == COMMIT
    assert out["p4"]["cases_total"] == 46
    assert out["p4"]["resource_checks_passed"] == 46
    assert out["p4"]["host_runtime_cases_passed"] == 0
    assert out["p5"]["chatgpt"]["chat_skill_activation"] == "not_run"
    assert out["approved_claims"] == 26
    assert out["excluded_candidates"] == 5
    assert (folder / "claude-code-mods-knowledge-0.1.0-rc.1.zip").is_file()
    assert (folder / "claude-code-mods-development-0.1.0-rc.1.zip").is_file()
    assert (folder / "SOURCE-SBOM.json").is_file()
    assert (folder / "P4-STATIC.json").is_file()
    assert (folder / "P5-HOST-MATRIX.json").is_file()
    assert (folder / "RELEASE.json").is_file()
    assert (folder / "SHA256SUMS").is_file()
    assert verify_release(folder)["status"] == "prerelease_host_runtime_unverified"


def test_same_source_and_host_matrix_yield_bit_for_bit_identical_release(tmp_path: Path) -> None:
    dist = source_build(tmp_path)
    left = tmp_path / "left"
    right = tmp_path / "right"
    build_release(ROOT, dist, left, source_revision=COMMIT, tag=TAG, host_matrix=host_matrix())
    build_release(ROOT, dist, right, source_revision=COMMIT, tag=TAG, host_matrix=host_matrix())
    names = [p.name for p in left.iterdir() if p.is_file()]
    assert len(names) == 7
    for name in names:
        assert (left / name).read_bytes() == (right / name).read_bytes()


def test_release_rejects_tampered_dist_without_touching_existing_output(
    tmp_path: Path,
) -> None:
    dist = source_build(tmp_path)
    released = tmp_path / "release"
    released.mkdir()
    marker = released / "precious.txt"
    marker.write_text("must not disappear")
    package = dist / "packages/claude-code-mods-knowledge-0.1.0-rc.1.zip"
    package.write_bytes(package.read_bytes() + b"x")
    with pytest.raises(ReleaseBuildError):
        build_release(
            ROOT,
            dist,
            released,
            source_revision=COMMIT,
            tag=TAG,
            host_matrix=host_matrix(),
        )
    assert marker.read_text() == "must not disappear"


def test_release_rejects_wrong_source_revision_and_unverified_matrix(
    tmp_path: Path,
) -> None:
    dist = source_build(tmp_path)
    with pytest.raises(ReleaseBuildError, match="revision"):
        build_release(
            ROOT,
            dist,
            tmp_path / "release",
            source_revision="b" * 40,
            tag=TAG,
            host_matrix=host_matrix(),
        )
    bad = host_matrix()
    bad["chatgpt"]["chat_skill_activation"] = "pass"
    with pytest.raises(ReleaseBuildError, match="not_run|runtime|ChatGPT|Chat mode"):
        build_release(
            ROOT,
            dist,
            tmp_path / "release",
            source_revision=COMMIT,
            tag=TAG,
            host_matrix=bad,
        )


def test_release_checksum_tampering_detected(tmp_path: Path) -> None:
    dist = source_build(tmp_path)
    release = tmp_path / "release"
    build_release(ROOT, dist, release, source_revision=COMMIT, tag=TAG, host_matrix=host_matrix())
    path = release / "SOURCE-SBOM.json"
    path.write_bytes(path.read_bytes() + b"changed")
    with pytest.raises(ReleaseBuildError, match="SHA|checksum|hash"):
        verify_release(release)


def test_release_sbom_only_first_party_sources_support_active_claims(
    tmp_path: Path,
) -> None:
    dist = source_build(tmp_path)
    release = tmp_path / "release"
    build_release(ROOT, dist, release, source_revision=COMMIT, tag=TAG, host_matrix=host_matrix())
    sbom = json.loads((release / "SOURCE-SBOM.json").read_text())
    assert sbom["approved_claim_count"] == 26
    assert len(sbom["approved_claim_ids"]) == 26
    assert set(s["trust_layer"] for s in sbom["sources"]) <= {"L0", "L1"}
    assert all(s["url"].startswith("https://code.claude.com/docs/en/") for s in sbom["sources"])
    assert all("html_sha256" in s for s in sbom["sources"])
    assert all("K-0001" not in x for x in sbom["approved_claim_ids"])


def test_existing_different_release_cannot_be_overwritten_without_explicit_action(
    tmp_path: Path,
) -> None:
    dist = source_build(tmp_path)
    release = tmp_path / "release"
    build_release(ROOT, dist, release, source_revision=COMMIT, tag=TAG, host_matrix=host_matrix())
    old = (release / "RELEASE.json").read_bytes()
    matrix = host_matrix()
    matrix["platforms"]["macbook"]["static_tests"] = "not_run"
    with pytest.raises(ReleaseBuildError, match="existing|overwrite|different"):
        build_release(ROOT, dist, release, source_revision=COMMIT, tag=TAG, host_matrix=matrix)
    assert (release / "RELEASE.json").read_bytes() == old


def test_chat_mode_activation_requires_observed_resource_read_evidence(tmp_path: Path) -> None:
    dist = source_build(tmp_path)
    matrix = host_matrix()
    matrix["chatgpt"]["chat_skill_activation"] = "pass"
    matrix["chatgpt"]["chat_answer_evaluation"] = "partial"
    matrix["chatgpt"]["chat_cases"] = []
    with pytest.raises(ReleaseBuildError, match="Chat|chat|evidence"):
        build_release(
            ROOT,
            dist,
            tmp_path / "release",
            source_revision=COMMIT,
            tag=TAG,
            host_matrix=matrix,
        )


def test_live_chat_mode_smoke_evidence_is_embedded_but_not_a_full_p4_pass(
    tmp_path: Path,
) -> None:
    dist = source_build(tmp_path)
    matrix = host_matrix()
    matrix["chatgpt"]["chat_skill_activation"] = "pass"
    matrix["chatgpt"]["chat_answer_evaluation"] = "partial"
    matrix["chatgpt"]["chat_cases"] = [
        {
            "case_id": "POS-E-01",
            "plugin_version": "0.1.0-rc.1",
            "conversation_sha256": "a" * 64,
            "response_sha256": "b" * 64,
            "skill_loaded": True,
            "resource_uris": [
                "skills://plugins/claude-code-mods-knowledge/claude-code-mods-development",
                "skills://plugins/claude-code-mods-knowledge/claude-code-mods-development/references/events.md",
            ],
            "answer_quality": "pass",
            "notes": "Synthetic test-only Chat resource trace fixture, not real host evidence",
        },
    ]
    release = build_release(
        ROOT,
        dist,
        tmp_path / "release",
        source_revision=COMMIT,
        tag=TAG,
        host_matrix=matrix,
    )
    assert release["status"] == "prerelease_host_runtime_unverified"
    assert release["p5"]["chatgpt"]["chat_skill_activation"] == "pass"
    assert release["p5"]["chatgpt"]["chat_answer_evaluation"] == "partial"
    assert release["p4"]["host_runtime_cases_passed"] == 0
    assert verify_release(tmp_path / "release")["p5"]["chatgpt"]["chat_skill_activation"] == "pass"
