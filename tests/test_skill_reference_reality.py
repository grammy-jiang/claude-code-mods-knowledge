"""Generated Skill cannot instruct agents to read non-packaged references.

Actual Sonnet/Medium CLI 2.1.302 attempted selected-evidence.md which does
not exist in the installed 0.4.11-beta.1 package. This failure is detectable
from the package deterministically without inference or account access.
"""

from __future__ import annotations

import io
import re
import zipfile
from pathlib import Path

import pytest

from mods_knowledge import compiler
from mods_knowledge.compiler import CompilerError, compile_knowledge
from mods_knowledge.release_validation import ReleaseValidationError, validate_bundle

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("target", ["2.1.296", "2.1.302"])
def test_every_generated_host_skill_mentions_only_packaged_reference_names(target: str) -> None:
    out = compile_knowledge(ROOT, api_version=target, surface="cli", source_revision="qaref-check")
    known = {
        "references/" + path.split("/references/", 1)[1]
        for path in out
        if path.startswith("common/") and "/references/" in path and path.endswith(".md")
    }
    assert len(known) == 9
    for name, raw in out.items():
        if name.endswith("/SKILL.md"):
            literal = set(re.findall(r"references/[A-Za-z0-9_-]+\.md", raw.decode()))
            assert literal <= known, f"Nonexistent file advertised in {name}: {literal - known}"
            assert "references/selected-evidence.md" not in raw.decode()
            assert "references/claim-evidence.md" in literal


@pytest.mark.parametrize("zip_type", ["plugin", "skill"])
def test_generated_zip_refuses_nonexistent_literal_reference_even_in_code_spans(
    zip_type: str,
) -> None:
    out = compile_knowledge(
        ROOT, api_version="2.1.302", surface="cli", source_revision="qaref-check"
    )
    prefix = (
        "packages/claude-code-mods-knowledge-"
        if zip_type == "plugin"
        else "packages/claude-code-mods-development-"
    )
    archive_bytes = next(v for k, v in out.items() if k.startswith(prefix))
    dst = io.BytesIO()
    with (
        zipfile.ZipFile(io.BytesIO(archive_bytes)) as original,
        zipfile.ZipFile(dst, "w") as rewritten,
    ):
        for member in original.infolist():
            body = original.read(member)
            if member.filename.endswith("/SKILL.md"):
                text = body.decode()
                text += (
                    "\nVerification preflight: read "
                    + chr(96)
                    + "references/not-a-real-file.md"
                    + chr(96)
                    + ".\n"
                )
                body = text.encode()
            rewritten.writestr(member, body)
    with pytest.raises(ReleaseValidationError, match="nonexistent|missing|reference|Skill"):
        validate_bundle(dst.getvalue())


def test_compiler_fails_before_building_uninstallable_ghost_reference(monkeypatch) -> None:
    old = compiler._skill_main

    def invalid(*args, **kwargs):
        extra = (
            "\nRead " + chr(96) + "references/unavailable.md" + chr(96) + " before replying.\n"
        ).encode()
        return old(*args, **kwargs) + extra

    monkeypatch.setattr(compiler, "_skill_main", invalid)
    with pytest.raises(CompilerError, match="reference|Skill|package"):
        compile_knowledge(ROOT, api_version="2.1.302", surface="cli", source_revision="qaref-check")
