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
        "references/claim-evidence.md",
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


def test_automatic_or_explicit_mods_activation_requires_same_reference_evidence(
    artifacts: dict,
) -> None:
    """Activation mode must not weaken exact evidence or version constraints."""
    skill = artifacts[f"{PREFIXES['chatgpt']}/SKILL.md"].decode()
    header = "## Every activated Mods task — source-verified answer contract"
    assert header in skill
    contract = skill.split(header, 1)[1].split("## Before implementation", 1)[0]
    assert skill.index(header) < skill.index("## Before implementation")
    assert "automatically discovered" in contract
    assert "explicitly invoked" in contract
    assert "references/claim-evidence.md" in contract
    for requirement in (
        "references/*.md",
        "K- Claim ID",
        "direct first-party",
        "cannot access",
        "do not claim",
        "K-0038",
        "K-0033",
        "K-0034",
        "semantic",
    ):
        assert requirement.lower() in contract.lower(), requirement
    assert "2.1.296" in skill
    assert "official" in contract
    assert len(skill) < 9000


def test_knowledge_contract_does_not_promise_guaranteed_model_activation(
    artifacts: dict,
) -> None:
    skill = artifacts[f"{PREFIXES['common']}/SKILL.md"].decode()
    assert "model routing" in skill.lower()
    assert "not" in skill.lower()
    assert "100% guaranteed activation" not in skill.lower()
    assert "not a real CLI execution" in skill
    for host in ("claude", "codex", "pi", "chatgpt"):
        assert (
            artifacts[f"{PREFIXES[host]}/SKILL.md"] == artifacts[f"{PREFIXES['common']}/SKILL.md"]
        )


def test_all_six_areas_have_four_guidance_claims_and_one_runtime_observation(
    artifacts: dict,
) -> None:
    e = artifacts[f"{PREFIXES['common']}/references/events.md"].decode()
    assert "K-0002" in e
    for area in REFERENCE_AREAS:
        page = artifacts[f"{PREFIXES['common']}/references/{area}.md"].decode()
        expected = 7 if area in ("types", "events") else (5 if area == "testing" else 4)
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
    assert manifest["approved_claims"] == 31
    assert manifest["candidate_claims_excluded"] == 5
    assert manifest["deprecated_claims_excluded"] == 2
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
    assert result["approved_claims"] == 31
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


def test_main_skill_critical_sections_are_real_markdown_not_literal_backslash_n(
    artifacts: dict,
) -> None:
    text = artifacts[f"{PREFIXES['common']}/SKILL.md"].decode()
    assert r"\n\n" not in text
    assert "## Implementation-critical, source-backed callback signature\n\n" in text
    assert "## CLI syntax and test-command guardrails — source verified\n\n" in text
    assert "Reference: [approved K-0031](references/events.md)." in text


def test_generated_skill_handles_native_validate_path_argument(artifacts: dict) -> None:
    """A real Chat Mode source-read case proposed an invalid pathless validate."""
    skill = artifacts[f"{PREFIXES['common']}/SKILL.md"].decode()
    assert "claude plugin validate --strict ." in skill
    assert "K-0035 / M002" in skill
    assert "K-0016" in skill
    assert "https://code.claude.com/docs/en/plugins/mods/create" in skill
    assert "Claude Code CLI 2.1.296" in skill
    assert "missing required argument 'path'" in skill
    assert len(skill) < 9000
    for adapter in ("claude", "codex", "pi", "chatgpt"):
        assert skill == artifacts[f"{PREFIXES[adapter]}/SKILL.md"].decode()


def test_explicit_plugin_claim_citation_requires_exact_approved_source_anchor(
    artifacts: dict,
) -> None:
    """2026-10-16 real Chat Mode UI reply cited K-0035 but another M002 anchor."""
    skill = artifacts[f"{PREFIXES['common']}/SKILL.md"].decode()
    section = skill.split("## Every activated Mods task", 1)[1].split(
        "## Before implementation", 1
    )[0]
    assert "for EVERY cited K-Claim" in section
    assert "exact `Source:`" in section
    assert "#fragment" in section
    assert "another section anchor on the same page" in section
    for host in ("claude", "codex", "pi", "chatgpt"):
        assert artifacts[f"{PREFIXES[host]}/SKILL.md"].decode() == skill


def test_p5_local_agent_safety_scope_is_in_all_compiled_skills(artifacts: dict) -> None:
    for adapter in ("claude", "codex", "pi", "chatgpt"):
        skill = artifacts[f"{PREFIXES[adapter]}/SKILL.md"].decode()
        assert "source checks disallowed, STOP" in skill
        assert "2.1.296 examples" in skill
        assert "Test rejecting diagnostics" in skill
        assert "target-generated types" in skill


def test_auto_activation_evidence_pack_is_identical_on_all_hosts(artifacts: dict) -> None:
    """Auto-routed Mods tasks should see exactly the same approved source cards."""
    rel = "references/claim-evidence.md"
    cards = artifacts[f"{PREFIXES['common']}/{rel}"].decode()
    skill = artifacts[f"{PREFIXES['common']}/SKILL.md"].decode()
    assert "## Every activated Mods task — source-verified answer contract" in skill
    assert "automatically discovered and explicitly invoked" in skill
    assert "references/claim-evidence.md" in skill
    assert "STOP before generating implementation code" in skill
    assert "do not control model routing" in skill
    assert "Pre-delivery checklist" in skill
    assert "2.1.296" in cards and "CLI ONLY" in cards
    assert len(cards) < 15000
    assert cards.count("Official URL: ") == 32
    assert len(re.findall(r"^\*\*K-[0-9]{4}\*\*", cards, re.M)) == 31
    assert "Official URL: https://code.claude.com/docs/en/plugins/mods/test#write-a-test" in cards
    for host in ("claude", "codex", "pi", "chatgpt"):
        assert artifacts[f"{PREFIXES[host]}/{rel}"].decode() == cards
        assert artifacts[f"{PREFIXES[host]}/SKILL.md"].decode() == skill


def test_evidence_cards_are_derived_only_from_approved_ssot_and_exact_support(
    artifacts: dict,
) -> None:
    """No candidates, inferred URLs or mismatched anchors in card references."""
    from mods_knowledge.claims import approved_claims, load_claims
    from mods_knowledge.registry import load_registry

    registry = load_registry(ROOT / "sources/registry.json")
    all_claims = load_claims(
        ROOT / "claims", registry, ROOT / "sources/snapshots", ROOT / "decisions"
    )
    active = approved_claims(all_claims, "2.1.296", "cli")
    cards = artifacts[f"{PREFIXES['common']}/references/claim-evidence.md"].decode()
    ids = re.findall(r"^\*\*(K-[0-9]{4})\*\*", cards, re.M)
    assert len(ids) == len(set(ids)) == len(active)
    assert set(ids) == {c["claim_id"] for c in active}
    for claim in active:
        start = cards.index(f"**{claim['claim_id']}**")
        next_claim = re.search(r"^\*\*K-[0-9]{4}\*\*", cards[start + 1 :], re.M)
        section = cards[start : start + 1 + next_claim.start()] if next_claim else cards[start:]
        expected_urls = [
            e["locator"]
            for e in claim["evidence"]
            if e.get("role") == "supports"
            and e.get("kind") == "official-doc"
            and e.get("source_id", "").startswith("M")
            and "#" in e["locator"]
            and e["locator"].startswith("https://code.claude.com/docs/en/plugins/mods/")
        ]
        assert expected_urls
        for url in expected_urls:
            assert f"Official URL: {url}" in section
    assert "K-0001" not in cards
    assert "K-0032" not in cards
    assert "K-0036" not in cards


def test_evidence_pack_fails_closed_on_broken_first_party_support() -> None:
    """Compiler must not emit superficially credible cards with invented URLs."""
    from copy import deepcopy

    from mods_knowledge.claims import approved_claims, load_claims
    from mods_knowledge.compiler import _render_claim_evidence
    from mods_knowledge.registry import load_registry

    registry = load_registry(ROOT / "sources/registry.json")
    all_claims = load_claims(
        ROOT / "claims", registry, ROOT / "sources/snapshots", ROOT / "decisions"
    )
    active = deepcopy(approved_claims(all_claims, "2.1.296", "cli"))
    target = next(c for c in active if c["claim_id"] == "K-0019")
    target["evidence"] = []
    with pytest.raises(CompilerError, match="lacks a first-party exact source"):
        _render_claim_evidence("2.1.296", "cli", active, registry)


def test_topic_references_start_with_direct_copyable_claim_evidence(artifacts: dict) -> None:
    """Models should not have to extract URL fragments from Markdown links."""
    prefix = PREFIXES["common"]
    for name in REFERENCE_AREAS:
        page = artifacts[f"{prefix}/references/{name}.md"].decode()
        assert "## Copy-ready citations — approved Claim ID + exact official URL" in page
        assert page.index("## Copy-ready citations") < page.index("## Detailed approved guidance")
        copied = re.findall(
            r"^- (K-[0-9]{4}) — (https://code\.claude\.com/docs/en/plugins/mods/\S+)$",
            page,
            re.M,
        )
        assert len(copied) >= 4
        assert all("#" in url for _, url in copied)
        detailed = set(re.findall(r"^## (K-[0-9]{4}) — ", page, re.M))
        assert {cid for cid, _ in copied} == detailed
        for cid, url in copied:
            assert url in artifacts[f"{prefix}/references/claim-evidence.md"].decode()
            assert cid in artifacts[f"{prefix}/references/claim-evidence.md"].decode()


def test_automatic_skill_description_exposes_source_contract_even_before_read(
    artifacts: dict,
) -> None:
    """The Skill listing, not just its document, must describe citation behavior."""
    main = artifacts[f"{PREFIXES['common']}/SKILL.md"].decode()
    description = main.split("description: ", 1)[1].split("\n", 1)[0]
    assert "Use when a task concerns Claude Code Mods" in description
    assert "Whenever activated" in description
    assert "approved K-Claim" in description
    assert "exact first-party official URL fragment" in description
    assert "CLI 2.1.296" in description
    assert "unreviewed APIs" in description


def test_p5_plugin_description_selects_versions_and_security_boundaries(artifacts: dict) -> None:
    for adapter in ("claude", "codex", "pi", "chatgpt"):
        skill = artifacts[f"{PREFIXES[adapter]}/SKILL.md"].decode()
        desc = skill.split("description: ", 1)[1].split("\n", 1)[0]
        assert "version compatibility (old/new/unknown)" in desc
        assert "unsafe installation" in desc
        assert "legacy preview flags" in desc
        assert "Ignore unrelated Python" in desc
        assert len(desc) < 1024
        assert "Unsupported version and security boundary questions" in skill
        assert "Do not invent a version timeline" in skill
        assert "upload secrets" in skill


def test_p5_all_claim_citations_need_exact_official_locator_including_body(artifacts: dict) -> None:
    for adapter in ("claude", "codex", "pi", "chatgpt"):
        skill = artifacts[f"{PREFIXES[adapter]}/SKILL.md"].decode()
        assert "the ENTIRE answer" in skill
        assert "for EVERY cited K-Claim" in skill
        assert "If the exact locator" in skill
