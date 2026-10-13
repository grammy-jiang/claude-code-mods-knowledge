"""Safely stage the released Skills-only Plugin in ChatGPT Desktop's local marketplace.

This creates a local source catalog, NOT a verified ChatGPT application install.
Activation requires host package-manager acceptance and a new ChatGPT Chat-mode run.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path

from .release_validation import (
    EXPECTED_PLUGIN,
    ReleaseValidationError,
    validate_dist,
)

MARKETPLACE = "mods-knowledge-local"
SOURCE = f"./.codex/plugins/{EXPECTED_PLUGIN}"
MARKER = "mods-knowledge-install.json"


class MarketplaceError(ValueError):
    """Local plugin staging is unsafe or its package is not verified."""


def _serialized(data: object) -> bytes:
    return (json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _write_atomic(path: Path, contents: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=path.parent, prefix=".pending-marketplace-", delete=False
        ) as file:
            temp = Path(file.name)
            file.write(contents)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temp, path)
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)


def _read_catalog(path: Path) -> dict:
    if not path.exists():
        return {
            "name": MARKETPLACE,
            "interface": {"displayName": "Claude Mods Knowledge — Local"},
            "plugins": [],
        }
    if path.is_symlink():
        raise MarketplaceError("Existing personal marketplace catalog is a symlink")
    try:
        contents = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise MarketplaceError("Existing personal marketplace catalog is invalid JSON") from exc
    if (
        not isinstance(contents, dict)
        or not isinstance(contents.get("name"), str)
        or not isinstance(contents.get("plugins"), list)
    ):
        raise MarketplaceError("Existing personal marketplace has unsupported structure")
    return contents


def _new_marketplace_entry() -> dict:
    return {
        "name": EXPECTED_PLUGIN,
        "source": {"source": "local", "path": SOURCE},
        "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
        "category": "Productivity",
    }


def _tree_digest(folder: Path) -> str:
    if folder.is_symlink() or not folder.is_dir():
        raise MarketplaceError("Plugin source tree is not an ordinary directory")
    digest = hashlib.sha256()
    for file in sorted(folder.rglob("*")):
        if file.is_symlink():
            raise MarketplaceError("Plugin source tree contains a symlink")
        if file.is_file():
            digest.update(file.relative_to(folder).as_posix().encode("utf-8") + b"\0")
            digest.update(hashlib.sha256(file.read_bytes()).digest())
    return digest.hexdigest()


def stage_personal_plugin(dist: Path, home: Path, *, apply: bool = False) -> dict:
    """Validate first; only explicit apply mutates the user's personal source.

    On update the previous payload is renamed as a backup temporarily. A
    failed catalog write restores it. Runtime/plugin activation is not asserted.
    """
    dist = Path(dist)
    home = Path(home)
    try:
        verified = validate_dist(dist)
    except (ReleaseValidationError, OSError) as exc:
        raise MarketplaceError(f"Cannot stage unverified Plugin: {exc}") from exc
    plugin_source = dist / "chatgpt" / EXPECTED_PLUGIN
    package_tree_sha256 = _tree_digest(plugin_source)
    dest = home / ".codex" / "plugins" / EXPECTED_PLUGIN
    catalog_path = home / ".agents" / "plugins" / "marketplace.json"
    record_path = home / ".agents" / "plugins" / MARKER
    if dest.is_symlink() or catalog_path.is_symlink() or record_path.is_symlink():
        raise MarketplaceError("Refusing to overwrite symlinked plugin/marketplace files")
    for ancestor in (dest.parent, dest.parent.parent, catalog_path.parent):
        if ancestor.is_symlink():
            raise MarketplaceError("Refusing a symlinked personal plugin parent directory")
    catalog = _read_catalog(catalog_path)
    if dest.exists():
        if not dest.is_dir():
            raise MarketplaceError("Existing plugin destination is not a directory")
        if not record_path.is_file():
            raise MarketplaceError("Existing unmanaged plugin cannot be overwritten")
        try:
            old_marker = json.loads(record_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise MarketplaceError("Existing plugin ownership marker is unreadable") from exc
        if old_marker.get("plugin_name") != EXPECTED_PLUGIN or old_marker.get("source") != SOURCE:
            raise MarketplaceError("Existing plugin ownership marker mismatch")
        if old_marker.get("source_tree_sha256") != _tree_digest(dest):
            raise MarketplaceError("Existing installed source was modified: checksum mismatch")
    else:
        old_marker = None
    entries = catalog["plugins"]
    related = [e for e in entries if isinstance(e, dict) and e.get("name") == EXPECTED_PLUGIN]
    if len(related) > 1 or (
        related and related[0].get("source") != _new_marketplace_entry()["source"]
    ):
        raise MarketplaceError("Existing plugin marketplace entry conflicts with owned plugin")
    if not related:
        entries.append(_new_marketplace_entry())
    desired_catalog = _serialized(catalog)
    marker = {
        "schema_version": 1,
        "plugin_name": EXPECTED_PLUGIN,
        "source": SOURCE,
        "plugin_zip_sha256": verified["plugin_zip_sha256"],
        "source_tree_sha256": package_tree_sha256,
        "runtime_verified": False,
    }
    desired_marker = _serialized(marker)
    plan = {
        "status": "dry_run" if not apply else "marketplace_prepared_not_host_verified",
        "plugin_name": EXPECTED_PLUGIN,
        "plugin_dir": str(dest),
        "marketplace_file": str(catalog_path),
        "marketplace_name": catalog["name"],
        "chatgpt_runtime_verified": False,
        "plugin_zip_sha256": verified["plugin_zip_sha256"],
    }
    if not apply:
        return plan
    if (
        old_marker == marker
        and catalog_path.is_file()
        and catalog_path.read_bytes() == desired_catalog
        and all(
            (dest / f.relative_to(plugin_source)).is_file()
            and (dest / f.relative_to(plugin_source)).read_bytes() == f.read_bytes()
            for f in plugin_source.rglob("*")
            if f.is_file()
        )
    ):
        return plan
    dest.parent.mkdir(parents=True, exist_ok=True)
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".pending-mods-plugin-", dir=dest.parent))
    backup = dest.parent / f".backup-{EXPECTED_PLUGIN}"
    if backup.exists():
        shutil.rmtree(stage)
        raise MarketplaceError("Stale personal plugin backup exists; recover manually first")
    previous_catalog = catalog_path.read_bytes() if catalog_path.exists() else None
    previous_marker = record_path.read_bytes() if record_path.exists() else None
    moved_existing = False
    installed_new = False
    try:
        shutil.copytree(plugin_source, stage / EXPECTED_PLUGIN)
        if dest.exists():
            os.replace(dest, backup)
            moved_existing = True
        os.replace(stage / EXPECTED_PLUGIN, dest)
        installed_new = True
        _write_atomic(catalog_path, desired_catalog)
        _write_atomic(record_path, desired_marker)
        if moved_existing:
            shutil.rmtree(backup)
    except (OSError, ValueError) as exc:
        if installed_new and dest.exists():
            shutil.rmtree(dest)
        if moved_existing and backup.exists():
            os.replace(backup, dest)
        if previous_catalog is None:
            catalog_path.unlink(missing_ok=True)
        else:
            _write_atomic(catalog_path, previous_catalog)
        if previous_marker is None:
            record_path.unlink(missing_ok=True)
        else:
            _write_atomic(record_path, previous_marker)
        raise MarketplaceError(f"Could not prepare personal marketplace: {exc}") from exc
    finally:
        shutil.rmtree(stage, ignore_errors=True)
    return plan
