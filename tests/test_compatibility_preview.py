"""An optional second ChatGPT-only compatibility Skill stays SSOT-derived.

This preview is not a GA release and does not change the existing canonical
Skill, or alter the default four-platform deterministic compiler.
"""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from pathlib import Path

import pytest

from mods_knowledge.compatibility_preview import (
    PreviewValidationError,
    build_compatibility_preview,
    compile_compatibility_preview,
    verify_compatibility_preview,
)
from mods_knowledge.compiler import compile_knowledge

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "chatgpt/claude-code-mods-knowledge/"
EXTRA = PREFIX + "skills/claude-mods-compatibility/"


@pytest.fixture(scope="module")
def preview() -> dict[str, bytes]:
    return compile_compatibility_preview(
        ROOT,
        api_version="2.1.296",
        surface="cli",
        package_version="0.2.0-preview.1",
        source_revision="fixture-preview-source",
    )


def test_generated_extra_skill_is_source_bound_and_canonically_scoped(preview) -> None:
    extra = preview[EXTRA + "SKILL.md"].decode()
    assert extra.startswith("---\nname: claude-mods-compatibility\ndescription: ")
    line = extra.split("---", 2)[1].strip().splitlines()[1]
    text = json.loads(line.removeprefix("description: "))
    assert "Claude Code Mods" in text and "2.1.310" in text and "allowManagedModsOnly" in text
    assert "2.1.296" in extra
    assert "not verified" in extra.lower() or "unverified" in extra.lower()
    for claim_id in ("K-0015", "K-0016", "K-0023", "K-0026", "K-0030"):
        assert claim_id in extra
    assert "https://code.claude.com/docs/en/plugins/mods/" in extra
    assert "K-0001" not in extra and "K-0003" not in extra
    assert len(extra) < 7500
    for page in ("types", "security", "interface", "source-index"):
        assert preview[EXTRA + f"references/{page}.md"]


def test_preview_retains_original_canonical_skill_and_four_agents(preview) -> None:
    canonical = compile_knowledge(
        ROOT,
        api_version="2.1.296",
        surface="cli",
        package_version="0.2.0-preview.1",
        source_revision="fixture-preview-source",
    )
    assert len(preview) == len(canonical) + 5
    excluded = {
        "manifests/build-manifest.json",
        "manifests/checksums.sha256",
        "packages/claude-code-mods-knowledge-0.2.0-preview.1.zip",
    }
    for name, raw in canonical.items():
        if name not in excluded:
            assert preview[name] == raw, name
    assert preview[PREFIX + "plugin.json"] == canonical[PREFIX + "plugin.json"]
    assert b"0.2.0-preview.1" in preview[PREFIX + "plugin.json"]


def test_preview_zip_has_only_data_and_exactly_two_skills(preview) -> None:
    path = "packages/claude-code-mods-knowledge-0.2.0-preview.1.zip"
    with zipfile.ZipFile(io.BytesIO(preview[path])) as z:
        assert z.testzip() is None
        members = z.namelist()
        assert len(members) == 15
        assert len(set(members)) == 15
        assert all(n.startswith("claude-code-mods-knowledge/") for n in members)
        assert "claude-code-mods-knowledge/skills/claude-mods-compatibility/SKILL.md" in members
        assert "claude-code-mods-knowledge/skills/claude-code-mods-development/SKILL.md" in members
        assert all(n.endswith((".md", ".json")) for n in members)
        assert all(i.date_time == (1980, 1, 1, 0, 0, 0) for i in z.infolist())


def test_preview_manifest_is_always_marked_experimental_and_not_published(preview) -> None:
    doc = json.loads(preview["manifests/build-manifest.json"])
    assert doc["preview_extension"]["type"] == "narrow_compatibility_skill"
    assert doc["preview_extension"]["publishable"] is False
    assert doc["preview_extension"]["canonical_skill_unchanged"] is True
    assert doc["preview_extension"]["approved_source_claim_ids"] == [
        "K-0015",
        "K-0016",
        "K-0023",
        "K-0026",
        "K-0030",
    ]
    assert doc["approved_claims"] == 29
    assert doc["candidate_claims_excluded"] == 5
    assert doc["target"] == {"api_version": "2.1.296", "surface": "cli"}
    assert len(doc["artifact_sha256"]) == 53
    for name, sha in doc["artifact_sha256"].items():
        assert hashlib.sha256(preview[name]).hexdigest() == sha
    sums = preview["manifests/checksums.sha256"].decode()
    assert len(sums.splitlines()) == len(doc["artifact_sha256"])


def test_two_preview_compilations_are_byte_identical(preview) -> None:
    again = compile_compatibility_preview(
        ROOT,
        api_version="2.1.296",
        surface="cli",
        package_version="0.2.0-preview.1",
        source_revision="fixture-preview-source",
    )
    assert again == preview


@pytest.mark.parametrize(
    "version,surface",
    [
        ("2.1.220", "cli"),
        ("2.1.310", "cli"),
        ("2.1.296", "desktop"),
        ("2.1.296", "vscode"),
        ("latest", "cli"),
    ],
)
def test_preview_fails_closed_outside_source_review_scope(version, surface) -> None:
    with pytest.raises(PreviewValidationError):
        compile_compatibility_preview(
            ROOT,
            api_version=version,
            surface=surface,
            package_version="0.2.0-preview.1",
        )


def test_preview_is_verified_without_account_install(tmp_path: Path) -> None:
    out = tmp_path / "dist-preview"
    data = build_compatibility_preview(
        ROOT,
        out,
        api_version="2.1.296",
        surface="cli",
        package_version="0.2.0-preview.1",
        source_revision="fixture-preview-source",
    )
    assert data["preview_extension"]["publishable"] is False
    assert (
        verify_compatibility_preview(ROOT, out)["status"]
        == "experimental_preview_validated_no_host_claim"
    )
    assert len([p for p in out.rglob("*") if p.is_file()]) == len(
        compile_compatibility_preview(
            ROOT,
            api_version="2.1.296",
            surface="cli",
            package_version="0.2.0-preview.1",
            source_revision="fixture-preview-source",
        )
    )


def test_tampered_extra_reference_is_rejected(tmp_path: Path) -> None:
    out = tmp_path / "preview"
    build_compatibility_preview(
        ROOT, out, api_version="2.1.296", surface="cli", package_version="0.2.0-preview.1"
    )
    f = out / (EXTRA + "SKILL.md")
    f.write_bytes(f.read_bytes() + b"\nEXTRA UNREVIEWED INSTRUCTION\n")
    with pytest.raises(PreviewValidationError):
        verify_compatibility_preview(ROOT, out)


def test_preview_package_does_not_contain_external_actions_or_historical_claims(preview) -> None:
    main = preview[EXTRA + "SKILL.md"].decode()
    assert "K-0001" not in main
    assert "K-0003" not in main
    assert "CLAUDE_CODE_ENABLE_FUNCTION_HOOKS" in main
    assert "Do not install" in main or "do not install" in main
    assert "unverified" in main.lower()
    assert "www.github.com" not in main
    assert all(
        not name.endswith((".js", ".py", ".sh", "mcp.json", "hooks.json"))
        for name in preview
        if name.startswith(EXTRA)
    )


def test_compilation_remains_offline_and_does_not_create_outputs(
    monkeypatch, tmp_path: Path
) -> None:
    import socket
    import urllib.request

    monkeypatch.setattr(socket, "socket", lambda *_a, **_k: pytest.fail("socket opened"))
    monkeypatch.setattr(urllib.request, "urlopen", lambda *_a, **_k: pytest.fail("web accessed"))
    before = set(tmp_path.iterdir())
    assert compile_compatibility_preview(
        ROOT, api_version="2.1.296", surface="cli", package_version="0.2.0-preview.1"
    )
    assert set(tmp_path.iterdir()) == before


def test_preview_package_cannot_pass_normal_release_validation(tmp_path: Path) -> None:
    from mods_knowledge.release_validation import ReleaseValidationError, validate_dist

    out = tmp_path / "preview"
    build_compatibility_preview(ROOT, out, api_version="2.1.296", surface="cli")
    with pytest.raises(ReleaseValidationError):
        validate_dist(out)


def test_second_skill_yaml_description_can_be_parsed_without_extra_dependencies(preview) -> None:
    doc = preview[EXTRA + "SKILL.md"].decode()
    front = doc.split("---", 2)[1].strip().splitlines()
    assert front[0] == "name: claude-mods-compatibility"
    description = json.loads(front[1].removeprefix("description: "))
    assert ": " in description and 40 < len(description) < 1024
    assert "Claude Code Mods" in description
    assert "tool.check" in description


def test_cannot_overwrite_an_existing_preview_directory(tmp_path: Path) -> None:
    out = tmp_path / "preview"
    out.mkdir()
    (out / "keep").write_text("preserve")
    with pytest.raises(PreviewValidationError, match="existing|unsafe"):
        build_compatibility_preview(ROOT, out, api_version="2.1.296", surface="cli")
    assert (out / "keep").read_text() == "preserve"
