"""Personal ChatGPT Desktop plugin marketplace: safe copy, idempotence and trust boundaries."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mods_knowledge.compiler import build_artifacts
from mods_knowledge.personal_marketplace import MarketplaceError, stage_personal_plugin

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def assets(tmp_path: Path) -> Path:
    output = tmp_path / "dist"
    build_artifacts(ROOT, output, api_version="2.1.296", surface="cli")
    return output


def test_dry_run_does_not_touch_user_home(tmp_path: Path, assets: Path) -> None:
    home = tmp_path / "user"
    result = stage_personal_plugin(assets, home, apply=False)
    assert result["status"] == "dry_run"
    assert not home.exists()


def test_create_personal_marketplace_with_no_other_plugins(tmp_path: Path, assets: Path) -> None:
    home = tmp_path / "user"
    result = stage_personal_plugin(assets, home, apply=True)
    assert result["status"] == "marketplace_prepared_not_host_verified"
    assert result["plugin_name"] == "claude-code-mods-knowledge"
    assert result["chatgpt_runtime_verified"] is False
    plugin = home / ".codex/plugins/claude-code-mods-knowledge"
    assert (plugin / "plugin.json").is_file()
    assert (plugin / "skills/claude-code-mods-development/SKILL.md").is_file()
    source = assets / "chatgpt/claude-code-mods-knowledge"
    for file in source.rglob("*"):
        if file.is_file():
            assert (plugin / file.relative_to(source)).read_bytes() == file.read_bytes()
    catalog = json.loads((home / ".agents/plugins/marketplace.json").read_text())
    assert catalog["name"] == "mods-knowledge-local"
    assert catalog["plugins"][0]["name"] == "claude-code-mods-knowledge"
    assert catalog["plugins"][0]["source"] == {
        "source": "local",
        "path": "./.codex/plugins/claude-code-mods-knowledge",
    }
    assert catalog["plugins"][0]["policy"]["installation"] == "AVAILABLE"


def test_repeat_install_is_idempotent(tmp_path: Path, assets: Path) -> None:
    home = tmp_path / "user"
    stage_personal_plugin(assets, home, apply=True)
    manifest = home / ".agents/plugins/marketplace.json"
    before = manifest.read_bytes()
    first = stage_personal_plugin(assets, home, apply=True)
    assert first["status"] == "marketplace_prepared_not_host_verified"
    assert manifest.read_bytes() == before


def test_existing_other_marketplace_plugins_are_preserved(tmp_path: Path, assets: Path) -> None:
    home = tmp_path / "user"
    manifest = home / ".agents/plugins/marketplace.json"
    manifest.parent.mkdir(parents=True)
    original = {
        "name": "my-dev-local",
        "plugins": [
            {
                "name": "other-plugin",
                "source": {"source": "local", "path": "./plugins/other"},
                "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
                "category": "Productivity",
            }
        ],
    }
    manifest.write_text(json.dumps(original))
    stage_personal_plugin(assets, home, apply=True)
    after = json.loads(manifest.read_text())
    assert after["name"] == "my-dev-local"
    assert after["plugins"][0] == original["plugins"][0]
    assert len(after["plugins"]) == 2


def test_unmanaged_existing_plugin_folder_causes_no_overwrite(tmp_path: Path, assets: Path) -> None:
    home = tmp_path / "user"
    other = home / ".codex/plugins/claude-code-mods-knowledge"
    other.mkdir(parents=True)
    marker = other / "do-not-touch"
    marker.write_text("original")
    with pytest.raises(MarketplaceError, match="unmanaged|existing"):
        stage_personal_plugin(assets, home, apply=True)
    assert marker.read_text() == "original"
    assert not (home / ".agents/plugins/marketplace.json").exists()


def test_malformed_existing_catalog_is_not_overwritten(tmp_path: Path, assets: Path) -> None:
    home = tmp_path / "user"
    manifest = home / ".agents/plugins/marketplace.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text("{broken json")
    with pytest.raises(MarketplaceError):
        stage_personal_plugin(assets, home, apply=True)
    assert manifest.read_text() == "{broken json"


def test_tampered_plugin_payload_prevents_any_home_write(tmp_path: Path, assets: Path) -> None:
    plugin_file = assets / "chatgpt/claude-code-mods-knowledge/plugin.json"
    plugin_file.write_bytes(plugin_file.read_bytes() + b"tampered")
    home = tmp_path / "user"
    with pytest.raises(MarketplaceError):
        stage_personal_plugin(assets, home, apply=True)
    assert not home.exists()


def test_catalog_target_symlink_is_rejected(tmp_path: Path, assets: Path) -> None:
    home = tmp_path / "user"
    catalog = home / ".agents/plugins/marketplace.json"
    catalog.parent.mkdir(parents=True)
    alt = tmp_path / "sensitive"
    alt.write_text("{}")
    catalog.symlink_to(alt)
    with pytest.raises(MarketplaceError, match="symlink"):
        stage_personal_plugin(assets, home, apply=True)
    assert alt.read_text() == "{}"


def test_copy_failure_preserves_existing_user_plugin_and_catalog(
    tmp_path: Path, assets: Path, monkeypatch
) -> None:
    import mods_knowledge.personal_marketplace as pm

    home = tmp_path / "user"
    stage_personal_plugin(assets, home, apply=True)
    original_plugin = home / ".codex/plugins/claude-code-mods-knowledge/plugin.json"
    original_bytes = original_plugin.read_bytes()
    catalog = home / ".agents/plugins/marketplace.json"
    before = catalog.read_bytes()

    # Dist is still valid but marker intentionally differs, to force an update path.
    marker = home / ".agents/plugins/mods-knowledge-install.json"
    data = json.loads(marker.read_text())
    data["plugin_zip_sha256"] = "0" * 64
    marker.write_text(json.dumps(data))

    def fail_copy(*_args, **_kwargs):
        raise OSError("synthetic filesystem copy failure")

    monkeypatch.setattr(pm.shutil, "copytree", fail_copy)
    with pytest.raises(MarketplaceError):
        stage_personal_plugin(assets, home, apply=True)
    assert original_plugin.read_bytes() == original_bytes
    assert catalog.read_bytes() == before


def test_modifying_installed_skill_file_requires_manual_repair_not_silent_overwrite(
    tmp_path: Path, assets: Path
) -> None:
    home = tmp_path / "user"
    stage_personal_plugin(assets, home, apply=True)
    target = (
        home
        / ".codex/plugins/claude-code-mods-knowledge/skills/claude-code-mods-development/SKILL.md"
    )
    target.write_bytes(target.read_bytes() + b"\n# user edited\n")
    with pytest.raises(MarketplaceError, match="modified|checksum"):
        stage_personal_plugin(assets, home, apply=True)
    assert target.read_bytes().endswith(b"# user edited\n")
