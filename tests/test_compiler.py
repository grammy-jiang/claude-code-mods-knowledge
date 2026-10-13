"""Deterministic multi-host Skill & ChatGPT Plugin compiler contracts."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import zipfile
from io import BytesIO
from pathlib import Path

import pytest

from mods_knowledge.compiler import CompilerError, build_artifacts, compile_knowledge

ROOT = Path(__file__).resolve().parents[1]
NAME = "claude-code-mods-development"
PLUGIN = "claude-code-mods-knowledge"
REFERENCE_AREAS = ("events", "state", "types", "testing", "security", "interface")
PREFIXES = {
    "common": f"common/{NAME}",
    "claude": f"claude-code/.claude/skills/{NAME}",
    "codex": f"codex/.agents/skills/{NAME}",
    "pi": f"pi/.agents/skills/{NAME}",
    "chatgpt": f"chatgpt/{PLUGIN}/skills/{NAME}",
}


@pytest.fixture(scope="module")
def artifacts() -> dict[str, bytes]:
    return compile_knowledge(
        ROOT,
        api_version="2.1.296",
        surface="cli",
        source_revision="fixture-sha-for-tests",
    )


def test_four_host_skills_are_identical_to_one_common_source(artifacts: dict) -> None:
    expected = [
        "SKILL.md",
        *(f"references/{a}.md" for a in REFERENCE_AREAS),
        "references/source-index.md",
        "references/official-examples.md",
    ]
    for rel in expected:
        content = artifacts[f"{PREFIXES['common']}/{rel}"]
        assert content
        for adapter in ("claude", "codex", "pi", "chatgpt"):
            assert artifacts[f"{PREFIXES[adapter]}/{rel}"] == content


def test_skills_have_correct_portable_frontmatter_and_target_guard(artifacts: dict) -> None:
    text = artifacts[f"{PREFIXES['common']}/SKILL.md"].decode()
    assert text.startswith("---\nname: claude-code-mods-development\n")
    assert re.search(r"\ndescription: .{40,1024}\n---\n", text)
    assert "2.1.296" in text
    assert "CLI" in text
    assert "claude --version" in text
    assert "unverified" in text.lower()
    assert "references/events.md" in text
    assert len(text) < 9000


def test_all_six_areas_have_four_guidance_claims_and_one_runtime_observation(
    artifacts: dict,
) -> None:
    e = artifacts[f"{PREFIXES['common']}/references/events.md"].decode()
    assert "K-0002" in e
    for area in REFERENCE_AREAS:
        page = artifacts[f"{PREFIXES['common']}/references/{area}.md"].decode()
        expected = 6 if area == "events" else 4
        assert page.count("## K-") == expected
        assert "https://code.claude.com/docs/en/" in page
        assert "Source:" in page
        assert "Target:" in page


def test_history_candidate_community_does_not_leak_into_active_skill(artifacts: dict) -> None:
    packed = "\n".join(b.decode() for p, b in artifacts.items() if p.endswith(".md"))
    for forbidden in ("K-0001", "K-0003", "K-0004", "K-0005", "K-0006", "M035", "M045", "M070"):
        assert forbidden not in packed
    assert "github.com/anthropics/claude-code/issues/91870" not in packed
    assert "claude.com/resources/articles/claude-code-mods" not in packed


def test_source_index_supports_official_navigation_without_approving_unread(
    artifacts: dict,
) -> None:
    page = artifacts[f"{PREFIXES['common']}/references/source-index.md"].decode()
    assert page.count("https://code.claude.com/docs/") == 43
    assert "M001" in page and "M034" in page and "M075" in page
    assert "unreviewed" in page.lower()
    examples = artifacts[f"{PREFIXES['common']}/references/official-examples.md"].decode()
    assert "Anthropic" in examples
    assert "not an API contract" in examples
    assert "M070" not in examples


def test_portable_chatgpt_plugin_has_no_mcp_or_side_effecting_hooks(artifacts: dict) -> None:
    manifest = json.loads(artifacts[f"chatgpt/{PLUGIN}/plugin.json"])
    assert manifest["$schema"] == "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
    assert manifest["name"] == PLUGIN
    assert manifest["version"] == "0.1.0"
    assert set(manifest) <= {
        "$schema",
        "name",
        "version",
        "description",
        "author",
        "repository",
        "keywords",
    }
    assert all(not p.endswith(("mcp.json", "hooks.json")) for p in artifacts)


def test_zip_packages_are_reproducible_and_contain_one_correct_top_level_dir(
    artifacts: dict,
) -> None:
    zipfiles = {p: b for p, b in artifacts.items() if p.endswith(".zip")}
    assert len(zipfiles) == 2
    for name, raw in zipfiles.items():
        with zipfile.ZipFile(BytesIO(raw)) as archive:
            assert archive.testzip() is None
            files = sorted(archive.namelist())
            assert any(p.endswith("SKILL.md") for p in files)
            assert all(info.date_time == (1980, 1, 1, 0, 0, 0) for info in archive.infolist())
            assert files[0].split("/")[0] in (PLUGIN, NAME)
            if "plugin-" in name or PLUGIN in name:
                assert f"{PLUGIN}/plugin.json" in files


def test_manifest_contains_correct_file_hashes_and_revisions(artifacts: dict) -> None:
    manifest = json.loads(artifacts["manifests/build-manifest.json"])
    assert manifest["target"] == {"api_version": "2.1.296", "surface": "cli"}
    assert manifest["source_revision"] == "fixture-sha-for-tests"
    assert manifest["approved_claims"] == 26
    assert manifest["candidate_claims_excluded"] == 5
    assert all(len(val) == 64 for val in manifest["input_sha256"].values())
    payloads = {name: sha for name, sha in manifest["artifact_sha256"].items()}
    assert "manifests/build-manifest.json" not in payloads
    for name, sha in payloads.items():
        assert hashlib.sha256(artifacts[name]).hexdigest() == sha
    expected = "".join(f"{sha}  {name}\n" for name, sha in sorted(payloads.items()))
    assert artifacts["manifests/checksums.sha256"] == expected.encode()


def test_two_builds_in_same_environment_are_byte_identical(artifacts: dict) -> None:
    again = compile_knowledge(
        ROOT,
        api_version="2.1.296",
        surface="cli",
        source_revision="fixture-sha-for-tests",
    )
    assert again == artifacts


@pytest.mark.parametrize(
    "version,surface",
    [
        ("latest", "cli"),
        ("2.1.295", "cli"),
        ("2.1.297", "cli"),
        ("2.1.296", "desktop"),
        ("2.1.296", "vscode"),
        ("2.1.296", "headless"),
        ("2.1.296", "unknown"),
    ],
)
def test_compiler_fails_closed_when_no_approved_matching_scope(version: str, surface: str) -> None:
    with pytest.raises(CompilerError):
        compile_knowledge(ROOT, api_version=version, surface=surface)


def test_compile_is_offline(monkeypatch) -> None:
    import socket
    import urllib.request

    monkeypatch.setattr(socket, "socket", lambda *_a, **_k: pytest.fail("socket opened"))
    monkeypatch.setattr(urllib.request, "urlopen", lambda *_a, **_k: pytest.fail("network access"))
    assert compile_knowledge(ROOT, api_version="2.1.296", surface="cli")


def test_source_tampering_invalidates_compilation(tmp_path: Path) -> None:
    # Keep a minimal independent checkout with all evidence dependencies.
    for folder in ("claims", "decisions", "sources", "targets", "evidence"):
        shutil.copytree(ROOT / folder, tmp_path / folder)
    target = tmp_path / "claims/K-0007.json"
    record = json.loads(target.read_text())
    record["statement"] += " unauthorized change"
    target.write_text(json.dumps(record))
    with pytest.raises(CompilerError):
        compile_knowledge(tmp_path, api_version="2.1.296", surface="cli")


def test_build_artifacts_writes_only_inside_the_output_tree(tmp_path: Path) -> None:
    result = build_artifacts(
        ROOT,
        tmp_path / "out",
        api_version="2.1.296",
        surface="cli",
        source_revision="fixture-sha-for-tests",
    )
    assert result["approved_claims"] == 26
    output_files = {
        p.relative_to(tmp_path / "out").as_posix(): p.read_bytes()
        for p in (tmp_path / "out").rglob("*")
        if p.is_file()
    }
    assert output_files == compile_knowledge(
        ROOT, api_version="2.1.296", surface="cli", source_revision="fixture-sha-for-tests"
    )


def test_build_does_not_replace_previous_output_if_validation_fails(
    tmp_path: Path,
) -> None:
    out = tmp_path / "dist"
    out.mkdir()
    (out / "keep").write_text("must remain")
    with pytest.raises(CompilerError):
        build_artifacts(ROOT, out, api_version="2.1.297", surface="cli")
    assert (out / "keep").read_text() == "must remain"


def test_build_manifest_pins_validator_contracts_and_lockfile(artifacts: dict) -> None:
    manifest = json.loads(artifacts["manifests/build-manifest.json"])
    deps = manifest["input_sha256"]
    required = {
        "compiler/src/mods_knowledge/compiler.py",
        "compiler/src/mods_knowledge/claims.py",
        "compiler/src/mods_knowledge/review_evidence.py",
        "compiler/src/mods_knowledge/runtime_evidence.py",
        "schema/source.schema.json",
        "schema/claim.schema.json",
        "schema/target.schema.json",
        "env/pyproject.toml",
        "env/uv.lock",
    }
    assert required <= set(deps)


def test_symlinked_output_root_is_rejected(tmp_path: Path) -> None:
    target = tmp_path / "destination"
    target.mkdir()
    link = tmp_path / "dist"
    link.symlink_to(target)
    with pytest.raises(CompilerError, match="Unsafe"):
        build_artifacts(ROOT, link, api_version="2.1.296", surface="cli")
    assert list(target.iterdir()) == []


def test_chatgpt_without_local_shell_must_not_fake_target_version(artifacts: dict) -> None:
    instructions = artifacts[f"{PREFIXES['chatgpt']}/SKILL.md"].decode()
    assert "no shell" in instructions.lower() or "cannot run" in instructions.lower()
    assert "ask the user" in instructions.lower()
    assert "authorized connector" in instructions.lower()


def test_main_skill_local_reference_links_all_resolve(artifacts: dict) -> None:
    prefix = PREFIXES["common"]
    text = artifacts[f"{prefix}/SKILL.md"].decode()
    links = re.findall(r"\]\((references/[^)#?]+)\)", text)
    assert len(links) == 9
    for relative in links:
        assert f"{prefix}/{relative}" in artifacts


def test_official_review_attestation_tamper_blocks_build(tmp_path: Path) -> None:
    for folder in ("claims", "decisions", "sources", "targets", "evidence"):
        shutil.copytree(ROOT / folder, tmp_path / folder)
    file = tmp_path / "sources/reviews/M004.json"
    record = json.loads(file.read_text())
    record["sections"][0]["anchor"] = "fake-event-that-never-existed"
    file.write_text(json.dumps(record))
    with pytest.raises(CompilerError):
        compile_knowledge(tmp_path, api_version="2.1.296", surface="cli")


def test_plugin_metadata_identifies_project_and_scope(artifacts: dict) -> None:
    data = json.loads(artifacts["chatgpt/claude-code-mods-knowledge/plugin.json"])
    assert data["author"]["name"] == "Mods Knowledge Project"
    assert data["repository"].startswith(
        "https://github.com/grammy-jiang/claude-code-mods-knowledge"
    )
    assert "claude-code-mods" in data["keywords"]


def test_can_compile_versioned_prerelease_plugin_without_mismatched_zip_names() -> None:
    result = compile_knowledge(
        ROOT,
        api_version="2.1.296",
        surface="cli",
        package_version="0.1.0-rc.1",
        source_revision="source-commit-for-test",
    )
    manifest = json.loads(result["manifests/build-manifest.json"])
    assert manifest["package_version"] == "0.1.0-rc.1"
    assert "packages/claude-code-mods-knowledge-0.1.0-rc.1.zip" in result
    assert (
        json.loads(result["chatgpt/claude-code-mods-knowledge/plugin.json"])["version"]
        == "0.1.0-rc.1"
    )


def test_chat_mode_regression_observer_callback_uses_all_three_arguments(
    artifacts: dict,
) -> None:
    """A real Chat-mode answer omitted $: keep a complete source-backed example prominent."""
    main = artifacts[f"{PREFIXES['common']}/SKILL.md"].decode()
    events = artifacts[f"{PREFIXES['common']}/references/events.md"].decode()
    expected = "on('tool.call', async ($, e, next) => { return next(e) })"
    assert expected in main
    assert expected in events
    assert "K-0031" in main
    assert "M003" in events
    assert "async (e, next)" in main


def test_compiled_skill_contains_source_derived_relevant_claim_router(
    artifacts: dict,
) -> None:
    main = artifacts[f"{PREFIXES['common']}/SKILL.md"].decode()
    assert "## Reviewed Claim lookup" in main
    for id in (
        "K-0007",
        "K-0009",
        "K-0011",
        "K-0012",
        "K-0015",
        "K-0016",
        "K-0017",
        "K-0018",
        "K-0019",
        "K-0021",
        "K-0023",
        "K-0026",
        "K-0027",
        "K-0028",
        "K-0030",
        "K-0031",
    ):
        assert id in main
    assert "references/events.md" in main and "references/security.md" in main
    assert "Reviewed Claims:" in main
    assert "Official sources:" in main
    assert "https://code.claude.com/docs/en/plugins/mods/" in main
    assert "multiple domains" in main.lower()
    assert "source links" in main.lower()


def test_compiled_skill_fails_closed_on_version_and_security_boundary_terms(
    artifacts: dict,
) -> None:
    main = artifacts[f"{PREFIXES['chatgpt']}/SKILL.md"].decode()
    head = main.split("---", 2)[1]
    for key in (
        "Claude Code Mods",
        "tool.check",
        "allowManagedModsOnly",
        "CLAUDE_CODE_ENABLE_FUNCTION_HOOKS",
        "VS Code",
        "2.1.296",
    ):
        assert key in main or key in head
    assert "without checking" in main.lower()
    assert "credential" in main.lower()
    assert "historical" in main.lower()
    assert "do not activate" in main.lower()


def test_full_code_snippet_uses_official_register_signature(
    artifacts: dict,
) -> None:
    main = artifacts[f"{PREFIXES['common']}/SKILL.md"].decode()
    events = artifacts[f"{PREFIXES['common']}/references/events.md"].decode()
    assert "export function register(on)" in main
    assert "on('tool.call', async ($, e, next)" in main
    assert "return next(e)" in main
    assert "export default function register({ on })" not in main
    assert "K-0018" in main and "K-0031" in main
    assert "M002" in main or "M003" in main
    assert "K-0031" in events


def test_reference_pages_remind_agent_to_cite_reviewed_claim_and_official_url(
    artifacts: dict,
) -> None:
    for area in REFERENCE_AREAS:
        page = artifacts[f"{PREFIXES['common']}/references/{area}.md"].decode()
        assert "answer contract" in page.lower()
        assert "Claim ID" in page
        assert "official URL" in page
        assert "https://code.claude.com/docs/" in page


def test_critical_api_guidance_uses_real_markdown_newlines() -> None:
    output = compile_knowledge(ROOT, api_version="2.1.296", surface="cli")
    text = output[f"{PREFIXES['common']}/SKILL.md"].decode()
    assert r"\n\n" not in text
    assert "## Implementation-critical, source-backed callback signature\n\n" in text
    assert "\n\n## Minimal officially documented Mod registration pattern\n\n" in text
