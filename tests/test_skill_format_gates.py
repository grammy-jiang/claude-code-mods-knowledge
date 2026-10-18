"""Deterministic pre-build, packaged and multi-host Skill format gates.

The real beta048/beta049 incident was a colon-space in unquoted YAML. A test
that only searches for a 'description:' string cannot detect it. These tests
must fail if generation, package acceptance or per-host copies bypass parsing.
"""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from pathlib import Path

import pytest

from mods_knowledge import compiler
from mods_knowledge.compiler import CompilerError, build_artifacts, compile_knowledge
from mods_knowledge.release_validation import ReleaseValidationError, validate_bundle, validate_dist

ROOT = Path(__file__).resolve().parents[1]
VALID_SOURCE = "a" * 40


def _bad_yaml_header(text: str) -> str:
    lines = text.splitlines(keepends=True)
    for index, line in enumerate(lines):
        if line.startswith("description: "):
            value = json.loads(line.removeprefix("description: ").strip())
            lines[index] = "description: " + value + "\n"
            return "".join(lines)
    raise AssertionError("Expected generated quoted description")


def _duplicate_yaml_description(text: str) -> str:
    lines = text.splitlines(keepends=True)
    for index, line in enumerate(lines):
        if line.startswith("description: "):
            lines.insert(index + 1, line)
            return "".join(lines)
    raise AssertionError("Expected generated description")


def _mutated_zip(source: bytes, mutate) -> bytes:
    result = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(source)) as original:
        with zipfile.ZipFile(result, "w") as output:
            for info in original.infolist():
                item = original.read(info)
                if info.filename.endswith("/SKILL.md"):
                    item = mutate(item.decode("utf-8")).encode("utf-8")
                output.writestr(info, item)
    return result.getvalue()


@pytest.mark.parametrize("version", ["2.1.296", "2.1.302"])
def test_compiler_fails_before_returning_unparseable_skill(monkeypatch, version: str) -> None:
    old = compiler._skill_main

    def malformed(*args, **kwargs):
        return _bad_yaml_header(old(*args, **kwargs).decode()).encode()

    monkeypatch.setattr(compiler, "_skill_main", malformed)
    with pytest.raises(CompilerError, match="YAML|frontmatter"):
        compile_knowledge(ROOT, api_version=version, surface="cli", source_revision=VALID_SOURCE)


def test_build_refuses_invalid_skill_without_destroying_existing_dist(
    tmp_path: Path, monkeypatch
) -> None:
    dest = tmp_path / "dist"
    build_artifacts(ROOT, dest, api_version="2.1.302", surface="cli", source_revision=VALID_SOURCE)
    original = (dest / "common/claude-code-mods-development/SKILL.md").read_bytes()
    before = hashlib.sha256(original).hexdigest()
    old = compiler._skill_main

    def malformed(*args, **kwargs):
        return _bad_yaml_header(old(*args, **kwargs).decode()).encode()

    monkeypatch.setattr(compiler, "_skill_main", malformed)
    with pytest.raises(CompilerError, match="YAML|frontmatter"):
        build_artifacts(
            ROOT, dest, api_version="2.1.302", surface="cli", source_revision=VALID_SOURCE
        )
    assert (
        hashlib.sha256(
            (dest / "common/claude-code-mods-development/SKILL.md").read_bytes()
        ).hexdigest()
        == before
    )
    assert validate_dist(dest)["status"] == "package_verified_host_not_tested"


@pytest.mark.parametrize("which", ["plugin", "skill"])
def test_both_zip_types_reject_duplicate_yaml_keys(which: str) -> None:
    outputs = compile_knowledge(
        ROOT, api_version="2.1.302", surface="cli", source_revision=VALID_SOURCE
    )
    prefix = (
        "packages/claude-code-mods-knowledge-"
        if which == "plugin"
        else "packages/claude-code-mods-development-"
    )
    base = next(value for name, value in outputs.items() if name.startswith(prefix))
    with pytest.raises(ReleaseValidationError, match="YAML|frontmatter|duplicate"):
        validate_bundle(_mutated_zip(base, _duplicate_yaml_description))


@pytest.mark.parametrize("mutation", ["invalid_yaml", "valid_but_divergent"])
def test_dist_rejects_one_bad_host_even_when_attacker_updates_checksums(
    mutation: str, tmp_path: Path
) -> None:
    dest = tmp_path / "dist"
    build_artifacts(ROOT, dest, api_version="2.1.302", surface="cli", source_revision=VALID_SOURCE)
    target_name = "claude-code/.claude/skills/claude-code-mods-development/SKILL.md"
    target = dest / target_name
    text = target.read_text()
    if mutation == "invalid_yaml":
        target.write_text(_bad_yaml_header(text))
    else:
        target.write_text(
            text.replace("Claude Code Mods: hooks", "Claude Code Mods: revised hooks")
        )
    # A checksum alone cannot prove the generated host source is parseable,
    # or that all four local host copies match the Plugin's reviewed Skill.
    manifest = dest / "manifests/build-manifest.json"
    doc = json.loads(manifest.read_text())
    doc["artifact_sha256"][target_name] = hashlib.sha256(target.read_bytes()).hexdigest()
    manifest.write_text(json.dumps(doc, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    checksums = dest / "manifests/checksums.sha256"
    checksums.write_text(
        "".join(f"{sha}  {name}\n" for name, sha in sorted(doc["artifact_sha256"].items()))
    )
    with pytest.raises(ReleaseValidationError, match="YAML|frontmatter|Skill|host|mismatch"):
        validate_dist(dest)


@pytest.mark.parametrize(
    "metadata",
    [
        # The actual beta048/beta049 defect: unquoted colon followed by a space.
        "name: claude-code-mods-development\n"
        "description: Use when Claude Code Mods: hooks, UI, state, security.\n",
        # Wrong YAML scalar type, absent/empty keys and extraneous configuration.
        "name: claude-code-mods-development\ndescription: [Use when, Claude Code Mods, events]\n",
        "name: claude-code-mods-development\ndescription: false\n",
        "name: claude-code-mods-development\n",
        "description: Use when working on Claude Code Mods source and events\n",
        "name: claude-code-mods-development\ndescription: ''\n",
        "name: claude-code-mods-development\n"
        'description: "Use when working on Claude Code Mods official guidance."\n'
        "permissions: unrestricted\n",
        # A valid-looking second scalar must not silently override the first.
        "name: claude-code-mods-development\n"
        'description: "Use when working on Claude Code Mods official guidance."\n'
        'description: "Use when working on Claude Code Mods revised guidance."\n',
        "name: claude-code-mods-development\n"
        "name: claude-code-mods-development\n"
        'description: "Use when working on Claude Code Mods official guidance."\n',
        # PyYAML SafeLoader does not evaluate arbitrary Python constructors.
        "name: claude-code-mods-development\n"
        "description: !!python/object/apply:os.system ['echo unsafe']\n",
    ],
)
def test_strict_skill_yaml_parser_rejects_malformed_and_ambiguous_metadata(
    metadata: str,
) -> None:
    from mods_knowledge.release_validation import validate_skill_frontmatter

    sample = f"---\n{metadata}---\n\n# Valid body text irrelevant to header correctness\n"
    with pytest.raises(ReleaseValidationError, match="YAML|frontmatter|description"):
        validate_skill_frontmatter(sample.encode())


def test_skills_lint_cli_checks_all_current_compiled_outputs(tmp_path: Path, capsys) -> None:
    from mods_knowledge import cli

    dest = tmp_path / "dist"
    build_artifacts(ROOT, dest, api_version="2.1.302", surface="cli", source_revision=VALID_SOURCE)
    assert cli.main(["skills-lint", "--dist", str(dest)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "SKILL_FORMAT_VALID"
    assert result["host_skill_files_parsed"] == 5
    assert result["skill_zip_files_parsed"] == 2
    assert result["model_or_platform_routing_tested"] is False

    # The named lightweight CLI gate must fail independently of checksums
    # when a single platform's skill is changed after compilation.
    edited = dest / "pi/.agents/skills/claude-code-mods-development/SKILL.md"
    edited.write_text(_bad_yaml_header(edited.read_text()))
    assert cli.main(["skills-lint", "--dist", str(dest)]) == 2
    assert "YAML" in capsys.readouterr().err


def test_skills_lint_cli_requires_both_compiled_zip_variants(tmp_path: Path, capsys) -> None:
    from mods_knowledge import cli

    dest = tmp_path / "dist"
    build_artifacts(ROOT, dest, api_version="2.1.302", surface="cli", source_revision=VALID_SOURCE)
    (dest / "packages/claude-code-mods-development-0.1.0.zip").unlink()
    assert cli.main(["skills-lint", "--dist", str(dest)]) == 2
    assert "ZIP" in capsys.readouterr().err
