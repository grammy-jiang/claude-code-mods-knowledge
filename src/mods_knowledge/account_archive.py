"""Fail-closed comparison of a reviewed Plugin ZIP and ChatGPT's normalized download.

ChatGPT's account download format has a root-level plugin.json and one
.codex-plugin/plugin.json sidecar, rather than the compiler's enclosing
claude-code-mods-knowledge/ folder. Byte-identical ZIP hashes cannot be
expected. Compare every reviewed file's bytes and reject any unreviewed
content without extracting an archive or accepting executable files.

This does not authenticate an account, prove the download came from ChatGPT,
or establish model routing and correctness.
"""

from __future__ import annotations

import hashlib
import io
import json
import stat
import zipfile

from .release_validation import (
    EXPECTED_PLUGIN,
    EXPECTED_SKILL,
    MAX_ARCHIVE_SIZE,
    MAX_MEMBER_SIZE,
    ReleaseValidationError,
    _read_checked_archive,
    _safe_relative_name,
    validate_bundle,
)

SIDECAR = ".codex-plugin/plugin.json"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_downloaded_archive(contents: bytes, allowed: set[str]) -> dict[str, bytes]:
    if not isinstance(contents, bytes) or not 0 < len(contents) <= MAX_ARCHIVE_SIZE:
        raise ReleaseValidationError("Invalid or oversized account download")
    try:
        with zipfile.ZipFile(io.BytesIO(contents)) as archive:
            members = archive.infolist()
            names = [member.filename for member in members]
            if (
                len(members) != len(allowed)
                or len(set(names)) != len(names)
                or set(names) != allowed
            ):
                raise ReleaseValidationError(
                    "Account download has missing, duplicate or extra files"
                )
            if sum(member.file_size for member in members) > MAX_ARCHIVE_SIZE:
                raise ReleaseValidationError("Account download uncompressed size exceeds limit")
            result = {}
            for member in members:
                path = _safe_relative_name(member.filename)
                mode = member.external_attr >> 16
                if (
                    member.is_dir()
                    or member.file_size < 1
                    or member.file_size > MAX_MEMBER_SIZE
                    or stat.S_IFMT(mode) not in (0, stat.S_IFREG)
                    or mode & 0o111
                    or member.flag_bits & 1
                    or member.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)
                ):
                    raise ReleaseValidationError(f"Unsafe account download member: {path}")
                result[path] = archive.read(member)
            if archive.testzip() is not None:
                raise ReleaseValidationError("Corrupt account download")
            return result
    except (zipfile.BadZipFile, OSError, RuntimeError, EOFError, NotImplementedError) as exc:
        raise ReleaseValidationError("Corrupt or unsupported account download") from exc


def _expected_server_sidecar(original_manifest: dict) -> dict:
    # Strictly verified against the downloaded ChatGPT format observed on
    # 2026-10-14. A changed platform schema requires explicit source review.
    author = original_manifest.get("author")
    if not isinstance(author, dict) or not isinstance(author.get("name"), str):
        raise ReleaseValidationError("Cannot verify ChatGPT sidecar without a reviewed author")
    return {
        **{k: v for k, v in original_manifest.items() if k != "$schema"},
        "skills": "./skills",
        "interface": {
            "displayName": original_manifest["name"],
            "shortDescription": original_manifest["description"],
            "longDescription": original_manifest["description"],
            "developerName": author["name"],
            "category": "Other",
            "capabilities": [],
            "defaultPrompt": None,
        },
    }


def verify_account_download(uploaded_zip: bytes, downloaded_zip: bytes) -> dict:
    """Return SHA-only evidence if content is *exactly* the approved bundle.

    Raises ReleaseValidationError for all unsupported structures or mismatches.
    The returned hashes are evidence for manual account provenance checks;
    this function does not claim that a provided file was actually installed.
    """
    status = validate_bundle(uploaded_zip)
    if status.get("type") != "plugin":
        raise ReleaseValidationError("Expected an approved Plugin source ZIP")
    source = _read_checked_archive(uploaded_zip)
    prefix = EXPECTED_PLUGIN + "/"
    if not all(k.startswith(prefix) for k in source):
        raise ReleaseValidationError("Source bundle root is inconsistent")
    canonical = {key[len(prefix) :]: payload for key, payload in source.items()}
    expected_paths = {"plugin.json", f"skills/{EXPECTED_SKILL}/SKILL.md"} | {
        f"skills/{EXPECTED_SKILL}/references/{name}.md"
        for name in (
            "events",
            "state",
            "types",
            "testing",
            "security",
            "interface",
            "source-index",
            "official-examples",
        )
    }
    if set(canonical) != expected_paths:
        raise ReleaseValidationError("Source canonical member allowlist mismatch")
    downloaded = _read_downloaded_archive(downloaded_zip, expected_paths | {SIDECAR})
    if any(downloaded[name] != content for name, content in canonical.items()):
        raise ReleaseValidationError("Account download differs from reviewed Plugin content")
    try:
        manifest = json.loads(canonical["plugin.json"].decode("utf-8"))
        sidecar = json.loads(downloaded[SIDECAR].decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise ReleaseValidationError("Account sidecar is not valid JSON") from exc
    if sidecar != _expected_server_sidecar(manifest):
        raise ReleaseValidationError("Account sidecar contains unapproved metadata")
    hashes = {path: _sha(content) for path, content in sorted(canonical.items())}
    canonical_digest = _sha(json.dumps(hashes, sort_keys=True, separators=(",", ":")).encode())
    return {
        "schema_version": 1,
        "status": "ACCOUNT_ARCHIVE_CONTENTS_MATCH",
        "package_version": manifest["version"],
        "uploaded_zip_sha256": _sha(uploaded_zip),
        "downloaded_zip_sha256": _sha(downloaded_zip),
        "canonical_content_sha256": canonical_digest,
        "server_sidecar_sha256": _sha(downloaded[SIDECAR]),
        "canonical_files_matched": len(canonical),
        "server_sidecar_verified": True,
        "account_authenticated": False,
        "installation_or_model_acceptance": False,
    }
