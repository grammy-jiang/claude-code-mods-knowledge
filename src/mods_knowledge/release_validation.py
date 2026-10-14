"""Offline validator for reproducible ChatGPT Skills-only plugin and Skill ZIP archives.

Never extract untrusted ZIPs: inspect paths, modes, sizes, manifests and links
in memory. This validator establishes *package integrity*, not ChatGPT activation.
"""

from __future__ import annotations

import hashlib
import io
import json
import re
import stat
import zipfile
from pathlib import Path

EXPECTED_PLUGIN = "claude-code-mods-knowledge"
EXPECTED_SKILL = "claude-code-mods-development"
SCHEMA_URL = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
MAX_ARCHIVE_SIZE = 8_000_000
MAX_MEMBER_SIZE = 2_000_000
MAX_MEMBERS = 120
FIXED_TIME = (1980, 1, 1, 0, 0, 0)
AREAS = ("events", "state", "types", "testing", "security", "interface")


class ReleaseValidationError(ValueError):
    """A package cannot safely be handed to the ChatGPT plugin installer."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_relative_name(name: str) -> str:
    if not isinstance(name, str) or not name or "\\" in name or "\x00" in name:
        raise ReleaseValidationError("Unsafe archive member path")
    if (
        name.startswith("/")
        or "//" in name
        or re.match(r"^[A-Za-z]:", name)
        or any(p in ("", ".", "..") for p in name.split("/"))
    ):
        raise ReleaseValidationError("Unsafe archive member path traversal")
    return name


def _check_member(info: zipfile.ZipInfo) -> None:
    name = _safe_relative_name(info.filename)
    if info.is_dir() or info.file_size < 1 or info.file_size > MAX_MEMBER_SIZE:
        raise ReleaseValidationError(f"Unsupported or oversized archive member: {name}")
    mode = info.external_attr >> 16
    kind = stat.S_IFMT(mode)
    if kind not in (0, stat.S_IFREG):
        raise ReleaseValidationError(f"Archive may not contain symlinks or special files: {name}")
    if mode & 0o111:
        raise ReleaseValidationError(f"Archive may not include executable files: {name}")
    if info.date_time != FIXED_TIME:
        raise ReleaseValidationError(f"Archive timestamp must be reproducible: {name}")
    if name.endswith((".js", ".mjs", ".py", ".sh", ".exe", ".so", ".dylib", ".dll")):
        raise ReleaseValidationError(f"Skills-only archive cannot contain executable code: {name}")
    if name.endswith(("mcp.json", ".mcp.json", ".app.json", "hooks.json")):
        raise ReleaseValidationError(f"Unexpected MCP or hooks integration: {name}")


def _read_checked_archive(contents: bytes) -> dict[str, bytes]:
    if not isinstance(contents, bytes) or not 0 < len(contents) <= MAX_ARCHIVE_SIZE:
        raise ReleaseValidationError("Invalid or oversized ZIP data")
    try:
        with zipfile.ZipFile(io.BytesIO(contents), "r") as archive:
            infos = archive.infolist()
            if not infos or len(infos) > MAX_MEMBERS:
                raise ReleaseValidationError("Invalid archive member count")
            if len(set(i.filename for i in infos)) != len(infos):
                raise ReleaseValidationError("Duplicate archive member paths")
            if sum(i.file_size for i in infos) > MAX_ARCHIVE_SIZE:
                raise ReleaseValidationError("Uncompressed archive size exceeds limit")
            data = {}
            for info in infos:
                _check_member(info)
                data[info.filename] = archive.read(info)
            if archive.testzip() is not None:
                raise ReleaseValidationError("Corrupt ZIP content")
            return data
    except (zipfile.BadZipFile, OSError, RuntimeError, EOFError) as exc:
        raise ReleaseValidationError(f"Corrupt ZIP archive: {exc}") from exc


def _check_skill(
    root: str,
    files: dict[str, bytes],
    skill_root: str,
    allowed_claim_ids: set[str] | None = None,
    target: dict | None = None,
) -> set[str]:
    skill_file = f"{skill_root}/SKILL.md"
    if skill_file not in files:
        raise ReleaseValidationError(f"Missing SKILL.md at {skill_file}")
    try:
        text = files[skill_file].decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ReleaseValidationError("SKILL.md must be UTF-8") from exc
    header = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
    if not header:
        raise ReleaseValidationError("Missing Skill YAML frontmatter")
    if "name: " + EXPECTED_SKILL not in header.group(1):
        raise ReleaseValidationError("Skill frontmatter name mismatch")
    if "Claude Code Mods" not in header.group(1) or "Use when" not in header.group(1):
        raise ReleaseValidationError("Skill description lacks appropriate Mods trigger")
    if len(text) > 12_000 or "**Documented target:**" not in text:
        raise ReleaseValidationError("Invalid Skill target guard")
    if target is not None:
        if not isinstance(target, dict) or set(target) != {"api_version", "surface"}:
            raise ReleaseValidationError("Invalid expected target contract")
        actual_target = f"Claude Code {target['api_version']}, {target['surface'].upper()} only."
        if actual_target not in text:
            raise ReleaseValidationError("Skill target/version is inconsistent with build manifest")
    for name in AREAS + ("source-index", "official-examples"):
        if f"{skill_root}/references/{name}.md" not in files:
            raise ReleaseValidationError(f"Missing Skill reference: {name}")
    # Check all local file references, including those in detailed pages.
    for file_path, raw in files.items():
        if not file_path.endswith(".md"):
            continue
        try:
            body = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ReleaseValidationError("Reference files must be UTF-8") from exc
        for url in re.findall(r"\]\(([^)]+)\)", body):
            if url.startswith("http"):
                if not url.startswith("https://"):
                    raise ReleaseValidationError("Non-HTTPS external source reference")
                continue
            if not url.startswith("references/"):
                raise ReleaseValidationError(f"Unsafe local reference in {file_path}: {url}")
            if f"{skill_root}/{url}" not in files:
                raise ReleaseValidationError(f"Missing local reference file: {url}")
    active_ids = set()
    for name, content in files.items():
        if name.endswith(".md") and "/references/" in name:
            active_ids.update(
                re.findall(r"^## (K-[0-9]{4,}) ", content.decode("utf-8"), re.MULTILINE)
            )
    if not active_ids:
        raise ReleaseValidationError("The Skill has no active approved knowledge")
    combined = "\n".join(
        contents.decode("utf-8") for name, contents in files.items() if name.endswith(".md")
    )
    visible_claim_ids = set(re.findall(r"K-[0-9]{4,}", combined))
    if allowed_claim_ids is not None:
        if not isinstance(allowed_claim_ids, set) or not all(
            re.fullmatch(r"K-[0-9]{4,}", item) for item in allowed_claim_ids
        ):
            raise ReleaseValidationError("Invalid SSOT approved Claim allowlist")
        if active_ids != allowed_claim_ids or visible_claim_ids != allowed_claim_ids:
            raise ReleaseValidationError(
                "Candidate/unapproved Claim or approved Claim mismatch: "
                f"active={sorted(active_ids)}, allowed={sorted(allowed_claim_ids)}"
            )
    if any(
        s in combined
        for s in (
            "https://github.com/anthropics/claude-code/issues/91870",
            "https://claude.com/resources/articles/claude-code-mods",
        )
    ):
        raise ReleaseValidationError("Historical sources must not become active API content")
    for area in AREAS:
        content = files[f"{skill_root}/references/{area}.md"].decode()
        if "Source:" not in content or "Target:" not in content:
            raise ReleaseValidationError(f"{area}: source/target traceability missing")
    return active_ids


def _check_manifest(raw: bytes) -> dict:
    try:
        manifest = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise ReleaseValidationError("Invalid plugin manifest JSON") from exc
    if not isinstance(manifest, dict):
        raise ReleaseValidationError("Plugin manifest must be a JSON object")
    permitted = {
        "$schema",
        "name",
        "version",
        "description",
        "author",
        "homepage",
        "repository",
        "keywords",
    }
    if not set(manifest) <= permitted:
        raise ReleaseValidationError("Unexpected fields in portable manifest")
    if (
        manifest.get("$schema") != SCHEMA_URL
        or manifest.get("name") != EXPECTED_PLUGIN
        or not re.fullmatch(
            r"[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.-]+)?", str(manifest.get("version", ""))
        )
        or not isinstance(manifest.get("description"), str)
        or not manifest["description"].strip()
    ):
        raise ReleaseValidationError(
            "Plugin manifest schema, name, version, or description invalid"
        )
    if "author" in manifest:
        author = manifest["author"]
        if not isinstance(author, dict) or not set(author) <= {"name", "email", "url"}:
            raise ReleaseValidationError("Invalid plugin manifest author metadata")
    return manifest


def validate_bundle(
    contents: bytes, *, allowed_claim_ids: set[str] | None = None, target: dict | None = None
) -> dict:
    """Check a ZIP payload without extraction and report its package-only status."""
    files = _read_checked_archive(contents)
    roots = {name.partition("/")[0] for name in files}
    if roots == {EXPECTED_PLUGIN}:
        kind = "plugin"
        root = EXPECTED_PLUGIN
        skill_root = f"{root}/skills/{EXPECTED_SKILL}"
        manifest_path = f"{root}/plugin.json"
        if manifest_path not in files:
            raise ReleaseValidationError("Missing root plugin.json manifest")
        plugin_manifest = _check_manifest(files[manifest_path])
        version = plugin_manifest["version"]
    elif roots == {EXPECTED_SKILL}:
        kind = "skill"
        root = EXPECTED_SKILL
        skill_root = root
        if any(name.endswith("/plugin.json") for name in files):
            raise ReleaseValidationError("Standalone Skill must not contain a plugin manifest")
        version = None
    else:
        raise ReleaseValidationError("Unexpected or multiple ZIP top-level roots")
    # A valid archive may contain exactly the files emitted by the reviewed
    # compiler. Any additional Skill, reference or prompt-like Markdown would
    # otherwise evade _check_skill and could smuggle unreviewed instructions.
    required = {f"{skill_root}/SKILL.md"} | {
        f"{skill_root}/references/{name}.md"
        for name in AREAS + ("source-index", "official-examples")
    }
    if kind == "plugin":
        required.add(f"{root}/plugin.json")
    if set(files) != required:
        raise ReleaseValidationError(
            "Unexpected or missing files in approved single-Skill archive; "
            "multiple Skills require a separate, explicitly nonpublishable preview"
        )
    observed_claim_ids = _check_skill(root, files, skill_root, allowed_claim_ids, target)
    return {
        "type": kind,
        "root": root,
        "skill_name": EXPECTED_SKILL,
        "approved_claim_ids": sorted(observed_claim_ids),
        "version": version,
        "file_count": len(files),
        "contains_mcp": False,
        "has_executables": False,
        "bundle_sha256": _sha(contents),
    }


def validate_dist(root: Path) -> dict:
    """Verify the complete deterministic compiler output against the build manifest."""
    root = Path(root)
    manifest_file = root / "manifests/build-manifest.json"
    checksum_file = root / "manifests/checksums.sha256"
    if not manifest_file.is_file() or not checksum_file.is_file():
        raise ReleaseValidationError("Missing build manifest/checksum file")
    try:
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        checksums = checksum_file.read_text(encoding="utf-8")
    except (OSError, ValueError) as exc:
        raise ReleaseValidationError("Cannot load build manifest") from exc
    declared = manifest.get("artifact_sha256")
    if not isinstance(declared, dict) or not declared:
        raise ReleaseValidationError("Invalid build manifest artifact hashes")
    if "preview_extension" in manifest:
        raise ReleaseValidationError(
            "Experimental multi-Skill preview is never an approved normal release"
        )
    files = {
        file.relative_to(root).as_posix(): file
        for file in root.rglob("*")
        if file.is_file() or file.is_symlink()
    }
    expected = set(declared) | {"manifests/build-manifest.json", "manifests/checksums.sha256"}
    if set(files) != expected:
        raise ReleaseValidationError(
            f"Unexpected/extra or missing compiled files: {sorted(set(files) ^ expected)}"
        )
    for name, sha in sorted(declared.items()):
        file = files[name]
        if file.is_symlink() or _sha(file.read_bytes()) != sha:
            raise ReleaseValidationError(f"Compiled artifact SHA-256 hash mismatch: {name}")
    want_checksums = "".join(f"{sha}  {name}\n" for name, sha in sorted(declared.items()))
    if checksums != want_checksums:
        raise ReleaseValidationError("Checksum file disagrees with build manifest")
    plugin_name = next(
        (
            n
            for n in declared
            if n.startswith("packages/claude-code-mods-knowledge-") and n.endswith(".zip")
        ),
        None,
    )
    skill_name = next(
        (
            n
            for n in declared
            if n.startswith("packages/claude-code-mods-development-") and n.endswith(".zip")
        ),
        None,
    )
    if not plugin_name or not skill_name:
        raise ReleaseValidationError("Missing plugin and Skill ZIP release packages")
    claim_ids = manifest.get("approved_claim_ids")
    if not isinstance(claim_ids, list) or len(claim_ids) != len(set(claim_ids)):
        raise ReleaseValidationError("Build manifest approved Claim IDs are invalid")
    allowed_claim_ids = set(claim_ids)
    if len(allowed_claim_ids) != manifest.get("approved_claims"):
        raise ReleaseValidationError("Build manifest approved Claim count mismatch")
    plugin = validate_bundle(
        files[plugin_name].read_bytes(),
        allowed_claim_ids=allowed_claim_ids,
        target=manifest.get("target"),
    )
    skill = validate_bundle(
        files[skill_name].read_bytes(),
        allowed_claim_ids=allowed_claim_ids,
        target=manifest.get("target"),
    )
    if plugin["type"] != "plugin" or skill["type"] != "skill":
        raise ReleaseValidationError("Mismatched ZIP types")
    # Ensure the ZIP copy exactly equals the generated installed source tree.
    for name, zipped in ((plugin_name, plugin), (skill_name, skill)):
        archive = _read_checked_archive(files[name].read_bytes())
        for path, content in archive.items():
            bits = path.split("/", 1)
            relative = bits[1]
            if zipped["type"] == "plugin":
                compiled = f"chatgpt/{EXPECTED_PLUGIN}/{relative}"
            else:
                compiled = f"common/{EXPECTED_SKILL}/{relative}"
            if compiled not in files or files[compiled].read_bytes() != content:
                raise ReleaseValidationError(f"ZIP/archive differs from compiled tree: {compiled}")
    return {
        "status": "package_verified_host_not_tested",
        "artifacts_verified": len(declared),
        "approved_claims": manifest.get("approved_claims"),
        "plugin_zip_sha256": plugin["bundle_sha256"],
        "skill_zip_sha256": skill["bundle_sha256"],
        "target": manifest.get("target"),
        "source_revision": manifest.get("source_revision"),
    }
