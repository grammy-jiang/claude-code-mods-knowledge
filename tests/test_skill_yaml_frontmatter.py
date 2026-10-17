"""Packaged SKILL.md frontmatter must be real parseable YAML, not a text regex.

Regression: beta047 had valid frontmatter; beta048/049 introduced an
unquoted embedded colon-space ("Claude Code Mods: hooks"), which means
common YAML parsers refuse to discover the skill even though ZIP and
installation can appear healthy.
"""

from __future__ import annotations

import io
import warnings
import zipfile
from pathlib import Path

import pytest
import yaml

from mods_knowledge.compiler import compile_knowledge
from mods_knowledge.release_validation import ReleaseValidationError, validate_bundle

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("api_version", ["2.1.296", "2.1.302"])
def test_all_compiled_host_skills_have_real_yaml_frontmatter(api_version: str) -> None:
    artifacts = compile_knowledge(
        ROOT, api_version=api_version, surface="cli", source_revision="qa-parseable-fixture"
    )
    for host in ("common", "chatgpt", "claude-code", "codex", "pi"):
        matched = [
            (p, contents)
            for p, contents in artifacts.items()
            if p.endswith("/SKILL.md") and f"/{host}/" in f"/{p}"
        ]
        assert matched, f"Missing Skill in compiled {host}"
        for _, raw in matched:
            text = raw.decode("utf-8")
            assert text.startswith("---\n")
            frontmatter = text.split("---", 2)[1]
            fields = yaml.safe_load(frontmatter)
            assert fields["name"] == "claude-code-mods-development"
            assert set(fields) == {"name", "description"}
            assert isinstance(fields["description"], str)
            assert fields["description"].startswith("Use when")
            assert "Claude Code Mods" in fields["description"]


def test_compiled_current_302_plugin_and_skill_zip_fail_closed_on_yaml() -> None:
    artifacts = compile_knowledge(
        ROOT, api_version="2.1.302", surface="cli", source_revision="qa-parseable-fixture"
    )
    packages = {name: raw for name, raw in artifacts.items() if name.startswith("packages/")}
    assert len(packages) == 2
    for name, raw in packages.items():
        assert name.endswith(".zip")
        # Must parse the archive's SKILL.md, not just regex-search raw frontmatter.
        meta = validate_bundle(raw)
        assert meta["skill_name"] == "claude-code-mods-development"


def test_rejects_quoted_frontmatter_turning_into_invalid_plain_yaml() -> None:
    artifacts = compile_knowledge(
        ROOT, api_version="2.1.296", surface="cli", source_revision="qa-parseable-fixture"
    )
    zip_path = next(p for p in artifacts if p.startswith("packages/claude-code-mods-knowledge-"))
    source = artifacts[zip_path]
    buffer = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(source)) as zipped, zipfile.ZipFile(buffer, "w") as output:
        for info in zipped.infolist():
            raw = zipped.read(info)
            if info.filename.endswith("/SKILL.md"):
                text = raw.decode("utf-8")
                lines = text.splitlines(keepends=True)
                index = next(i for i, line in enumerate(lines) if line.startswith("description: "))
                # Real YAML defect that slipped past old ZIP regex checks.
                lines[index] = (
                    "description: Use when Claude Code Mods: hooks, UI, state, security.\n"
                )
                raw = "".join(lines).encode()
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                output.writestr(info, raw)
    with pytest.raises(ReleaseValidationError, match="YAML|frontmatter"):
        validate_bundle(buffer.getvalue())
