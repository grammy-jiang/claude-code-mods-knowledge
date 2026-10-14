"""Optional, source-derived two-Skill ChatGPT routing preview.

This module does not install, approve, run an AI model, or publish a release.
The default compiler and every existing canonical Skill remain byte-identical.
"""

from __future__ import annotations

import hashlib
import json
import re
import tempfile
from pathlib import Path

from .claims import approved_claims, load_claims
from .compiler import (
    COMPILER_VERSION,
    PLUGIN_NAME,
    SKILL_NAME,
    _json_bytes,
    _safe_text,
    _sha,
    _zip_payload,
    compile_knowledge,
)
from .errors import ClaimError, RegistryError
from .registry import load_registry
from .release_validation import ReleaseValidationError, _read_checked_archive, validate_bundle

EXTRA_SKILL = "claude-mods-compatibility"
EXTRA_REFS = ("types", "security", "interface", "source-index")
SUBJECTS = (
    "mods.types.local-version-declarations",
    "mods.types.static-hook-inspection",
    "mods.security.mods-are-not-sandboxed",
    "mods.security.organization-only-policy",
    "mods.ui.surfaces-and-fallbacks",
)
PREVIEW_VERSION = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+-preview\.[0-9]+\Z")


class PreviewValidationError(ValueError):
    """An opt-in compatibility Skill experiment is invalid or unsafe."""


def _render_extra(version: str, surface: str, claims: list[dict]) -> bytes:
    description = (
        "Use when Claude Code Mods compatibility or security is the task: old/new "
        "API versions such as tool.check in 2.1.220 or 2.1.310, "
        "CLAUDE_CODE_ENABLE_FUNCTION_HOOKS history, allowManagedModsOnly "
        "managed policy, unknown-source Mod installation, or VS Code/Desktop Pane "
        "support. Not for generic TypeScript, normal Claude settings hooks, MCP or HVAC."
    )
    lines = [
        "---",
        f"name: {EXTRA_SKILL}",
        "description: " + json.dumps(description, ensure_ascii=False),
        "---",
        "",
        "# Claude Code Mods compatibility and permissions — reviewed scope",
        "",
        "This is an *experimental, supplementary routing Skill*. It uses only",
        "central approved first-party Claims, not a new or independently maintained API.",
        "",
        "## Version and evidence gate",
        "",
        f"Reviewed target: Claude Code {version}, {surface.upper()} only.",
        "For other versions and surfaces the precise API contract is **unverified**.",
        "Never fabricate §tool.check§ field names, managed permission payloads or",
        "cross-host Pane guarantees. Use the target build's generated",
        "§.claude-plugin/types/§, current official Mods docs and isolated host tests.",
        "No unverified historical preview flags should be presented as current.",
        "",
        "## Approved Claims and official source links",
        "",
    ]
    for claim in sorted(claims, key=lambda c: c["claim_id"]):
        evidence = next((e for e in claim["evidence"] if e["role"] == "supports"), None)
        if not evidence or not evidence["locator"].startswith(
            "https://code.claude.com/docs/en/plugins/mods/"
        ):
            raise PreviewValidationError(
                "Approved compatibility Claim is missing official evidence"
            )
        lines.extend(
            [
                f"### {claim['claim_id']} — {claim['subject']}",
                _safe_text(claim["statement"]),
                f"Source {evidence['source_id']}: {evidence['locator']}",
                "",
            ]
        )
    lines.extend(
        [
            "## Read references before answering",
            "",
            "- For types and local version verification: [types](references/types.md).",
            "- For unknown plugins, secrets and managed Mods: [security](references/security.md).",
            "- For VS Code, Desktop and terminal surfaces: [interface](references/interface.md).",
            "- For official documents not yet reviewed: [source index](references/source-index.md).",
            "- Cite relevant reviewed K IDs and *direct* first-party source URLs.",
            "- Never substitute a historical/community page for a current-version API contract.",
            "- Do not install unknown privileged Mods or skip mandatory tests.",
            "- Never upload credentials or private files to an untrusted source.",
            "- If the task is unrelated to Claude Code Mods, do not activate this Skill.",
            "- Automatic activation is controlled by ChatGPT and is NOT guaranteed by this ZIP.",
            "",
        ]
    )
    return "\n".join(lines).replace("§", chr(96)).encode("utf-8")


def compile_compatibility_preview(
    root: Path,
    *,
    api_version: str,
    surface: str,
    package_version: str = "0.2.0-preview.1",
    knowledge_version: str = "0.1.0",
    source_revision: str = "working-tree",
) -> dict[str, bytes]:
    """Compile one additional ChatGPT compatibility Skill from approved SSOT."""
    if not PREVIEW_VERSION.fullmatch(package_version):
        raise PreviewValidationError("Opt-in routing preview requires a -preview.N package version")
    root = Path(root)
    try:
        base = compile_knowledge(
            root,
            api_version=api_version,
            surface=surface,
            package_version=package_version,
            knowledge_version=knowledge_version,
            source_revision=source_revision,
        )
        sources = load_registry(root / "sources/registry.json")
        records = load_claims(
            root / "claims", sources, root / "sources/snapshots", root / "decisions"
        )
        eligible = approved_claims(records, api_version, surface)
    except (ClaimError, RegistryError, ValueError, OSError) as exc:
        raise PreviewValidationError(f"Unverified or unsupported preview SSOT: {exc}") from exc

    selected: dict[str, dict] = {}
    for claim in eligible:
        subject = claim["subject"]
        if subject in SUBJECTS:
            if subject in selected:
                raise PreviewValidationError("Duplicate reviewed subject in compatibility Skill")
            selected[subject] = claim
    if set(selected) != set(SUBJECTS):
        raise PreviewValidationError("No approved Claims covering all compatibility topics")
    active = [selected[name] for name in SUBJECTS]
    plugin_root = f"chatgpt/{PLUGIN_NAME}/"
    canonical = plugin_root + f"skills/{SKILL_NAME}/"
    extra = plugin_root + f"skills/{EXTRA_SKILL}/"
    content = {"SKILL.md": _render_extra(api_version, surface, active)}
    for ref in EXTRA_REFS:
        key = f"references/{ref}.md"
        content[key] = base[canonical + key]
    result = dict(base)
    for path, value in content.items():
        name = extra + path
        if name in result:
            raise PreviewValidationError("Repeated Skill artifact name")
        result[name] = value
    bundle = f"packages/{PLUGIN_NAME}-{package_version}.zip"
    plugin_files = {
        name.removeprefix(plugin_root): value
        for name, value in result.items()
        if name.startswith(plugin_root)
    }
    result[bundle] = _zip_payload(PLUGIN_NAME, plugin_files)
    manifest = json.loads(base["manifests/build-manifest.json"])
    manifest["preview_extension"] = {
        "type": "narrow_compatibility_skill",
        "publishable": False,
        "canonical_skill_unchanged": True,
        "source_of_truth": "approved_claims_only",
        "approved_source_claim_ids": sorted(x["claim_id"] for x in active),
        "compiler_version": COMPILER_VERSION,
        "warning": "Preview only. This does not establish auto-activation or host QA.",
    }
    hashes = {
        path: _sha(value) for path, value in result.items() if not path.startswith("manifests/")
    }
    manifest["artifact_sha256"] = dict(sorted(hashes.items()))
    result["manifests/build-manifest.json"] = _json_bytes(manifest)
    result["manifests/checksums.sha256"] = "".join(
        f"{digest}  {path}\n" for path, digest in sorted(hashes.items())
    ).encode("utf-8")
    return dict(sorted(result.items()))


def build_compatibility_preview(
    root: Path,
    destination: Path,
    *,
    api_version: str,
    surface: str,
    package_version: str = "0.2.0-preview.1",
    knowledge_version: str = "0.1.0",
    source_revision: str = "working-tree",
) -> dict:
    """Write a new isolated preview dir, refusing any existing installation."""
    source = Path(root).resolve()
    out = Path(destination)
    if out.is_symlink() or out.resolve() == source or out.exists():
        raise PreviewValidationError("Preview output is symlinked, existing or unsafe")
    artifacts = compile_compatibility_preview(
        source,
        api_version=api_version,
        surface=surface,
        package_version=package_version,
        knowledge_version=knowledge_version,
        source_revision=source_revision,
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".mods-preview-", dir=out.parent) as tmp:
        stage = Path(tmp) / "artifacts"
        stage.mkdir()
        for name, data in artifacts.items():
            path = stage / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        stage.rename(out)
    return json.loads(artifacts["manifests/build-manifest.json"])


def verify_compatibility_preview(root: Path, output: Path) -> dict:
    """Reproduce exact bytes from approved input files and inspect ZIP safety."""
    dest = Path(output)
    if not dest.is_dir() or dest.is_symlink():
        raise PreviewValidationError("No safe preview output directory")
    try:
        doc = json.loads((dest / "manifests/build-manifest.json").read_text())
        extra = doc["preview_extension"]
        if (
            extra.get("publishable") is not False
            or extra.get("type") != "narrow_compatibility_skill"
        ):
            raise PreviewValidationError("Unmarked or falsely publishable compatibility Skill")
        target = doc["target"]
        expected = compile_compatibility_preview(
            root,
            api_version=target["api_version"],
            surface=target["surface"],
            package_version=doc["package_version"],
            knowledge_version=doc["knowledge_version"],
            source_revision=doc["source_revision"],
        )
        observed = {
            p.relative_to(dest).as_posix(): p
            for p in dest.rglob("*")
            if p.is_file() or p.is_symlink()
        }
        if set(observed) != set(expected):
            raise PreviewValidationError("Unexpected or missing preview artifact")
        for path, value in expected.items():
            file = observed[path]
            if file.is_symlink() or file.read_bytes() != value:
                raise PreviewValidationError("SSOT byte mismatch: " + path)
        name = f"packages/{PLUGIN_NAME}-{doc['package_version']}.zip"
        archive = _read_checked_archive(observed[name].read_bytes())
        if len(archive) != 15:
            raise PreviewValidationError("Expected exactly 2 Skills, 15 metadata/files")
        for original, raw in archive.items():
            internal = original.removeprefix(PLUGIN_NAME + "/")
            if original != PLUGIN_NAME + "/" + internal:
                raise PreviewValidationError("Unexpected ZIP member root")
            if expected[f"chatgpt/{PLUGIN_NAME}/{internal}"] != raw:
                raise PreviewValidationError("Unexpected ZIP member content")
        generic = f"packages/{SKILL_NAME}-{doc['package_version']}.zip"
        assert validate_bundle(observed[generic].read_bytes())["type"] == "skill"
        return {
            "status": "experimental_preview_validated_no_host_claim",
            "file_count": len(observed),
            "approved_claims": doc["approved_claims"],
            "plugin_zip_sha256": hashlib.sha256(observed[name].read_bytes()).hexdigest(),
            "canonical_skill_unchanged": True,
            "publishable": False,
        }
    except (
        ReleaseValidationError,
        KeyError,
        OSError,
        ValueError,
        TypeError,
        AssertionError,
    ) as exc:
        if isinstance(exc, PreviewValidationError):
            raise
        raise PreviewValidationError(f"Preview package verification failed: {exc}") from exc
