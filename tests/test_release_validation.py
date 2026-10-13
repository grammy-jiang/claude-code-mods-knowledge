"""P5 release package validation: hostile ZIP inputs and static Skills-only invariants."""

from __future__ import annotations

import io
import json
import stat
import warnings
import zipfile
from pathlib import Path

import pytest

from mods_knowledge.compiler import compile_knowledge
from mods_knowledge.release_validation import ReleaseValidationError, validate_bundle, validate_dist

ROOT = Path(__file__).resolve().parents[1]


def built_artifacts() -> dict[str, bytes]:
    return compile_knowledge(
        ROOT, api_version="2.1.296", surface="cli", source_revision="qa-fixture"
    )


def hostile_zip(entries: list[tuple[str, bytes]], *, symlink: bool = False) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as f:
        for name, payload in entries:
            info = zipfile.ZipInfo(name)
            info.date_time = (1980, 1, 1, 0, 0, 0)
            if symlink:
                info.create_system = 3
                info.external_attr = (stat.S_IFLNK | 0o777) << 16
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", message="Duplicate name", category=UserWarning)
                f.writestr(info, payload)
    return buf.getvalue()


def test_valid_skill_and_chatgpt_plugin_are_accepted() -> None:
    artifacts = built_artifacts()
    for name in (
        "packages/claude-code-mods-development-0.1.0.zip",
        "packages/claude-code-mods-knowledge-0.1.0.zip",
    ):
        meta = validate_bundle(artifacts[name])
        assert meta["file_count"] >= 9
        assert meta["skill_name"] == "claude-code-mods-development"
        assert meta["root"] in {"claude-code-mods-development", "claude-code-mods-knowledge"}
        assert meta["type"] in {"skill", "plugin"}
        assert meta["has_executables"] is False
        assert meta["contains_mcp"] is False


@pytest.mark.parametrize(
    "name",
    [
        "../escape.json",
        "/absolute.json",
        "plugin/../../secret",
        "plugin\\bad.json",
        "plugin//bad.json",
        "C:/Windows/foo",
        "otherdir/file.json",
    ],
)
def test_rejects_unsafe_member_paths(name: str) -> None:
    valid = built_artifacts()["packages/claude-code-mods-knowledge-0.1.0.zip"]
    with zipfile.ZipFile(io.BytesIO(valid)) as src:
        entries = [(i.filename, src.read(i)) for i in src.infolist()]
    entries.append((name, b"bad"))
    with pytest.raises(ReleaseValidationError):
        validate_bundle(hostile_zip(entries))


def test_rejects_symlink_entries_even_if_member_name_is_safe() -> None:
    with pytest.raises(ReleaseValidationError, match="symlink|file"):
        validate_bundle(
            hostile_zip([("claude-code-mods-knowledge/plugin.json", b"{}")], symlink=True)
        )


def test_rejects_duplicate_member_path() -> None:
    with pytest.raises(ReleaseValidationError):
        validate_bundle(
            hostile_zip(
                [
                    ("claude-code-mods-knowledge/plugin.json", b"{}"),
                    ("claude-code-mods-knowledge/plugin.json", b"{}"),
                ]
            )
        )


def test_missing_referenced_skill_file_is_rejected() -> None:
    valid = built_artifacts()["packages/claude-code-mods-knowledge-0.1.0.zip"]
    with zipfile.ZipFile(io.BytesIO(valid)) as src:
        entries = [
            (i.filename, src.read(i))
            for i in src.infolist()
            if not i.filename.endswith("references/types.md")
        ]
    with pytest.raises(ReleaseValidationError, match="reference|missing"):
        validate_bundle(hostile_zip(entries))


def test_manifest_wrong_name_is_rejected() -> None:
    valid = built_artifacts()["packages/claude-code-mods-knowledge-0.1.0.zip"]
    with zipfile.ZipFile(io.BytesIO(valid)) as src:
        entries = []
        for info in src.infolist():
            data = src.read(info)
            if info.filename.endswith("/plugin.json"):
                manifest = json.loads(data)
                manifest["name"] = "other-plugin"
                data = json.dumps(manifest).encode()
            entries.append((info.filename, data))
    with pytest.raises(ReleaseValidationError, match="manifest|name"):
        validate_bundle(hostile_zip(entries))


def test_candidate_claim_id_cannot_appear_in_packaged_knowledge() -> None:
    valid = built_artifacts()["packages/claude-code-mods-knowledge-0.1.0.zip"]
    with zipfile.ZipFile(io.BytesIO(valid)) as src:
        entries = []
        for info in src.infolist():
            data = src.read(info)
            if info.filename.endswith("/references/events.md"):
                data += b"\n## K-0003 unreviewed state API\n"
            entries.append((info.filename, data))
    with pytest.raises(ReleaseValidationError, match="candidate|unapproved"):
        validate_bundle(hostile_zip(entries))


def test_validate_dist_checks_all_sha256_and_no_extra_file(tmp_path: Path) -> None:
    artifacts = built_artifacts()
    for name, content in artifacts.items():
        dest = tmp_path / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(content)
    meta = validate_dist(tmp_path)
    assert meta["artifacts_verified"] == 48
    assert meta["approved_claims"] == 25
    assert meta["plugin_zip_sha256"]
    (tmp_path / "untracked-file").write_text("unexpected")
    with pytest.raises(ReleaseValidationError, match="extra|unexpected"):
        validate_dist(tmp_path)


def test_tampered_release_file_fails_hash_audit(tmp_path: Path) -> None:
    artifacts = built_artifacts()
    for name, content in artifacts.items():
        dest = tmp_path / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(content)
    plugin = tmp_path / "chatgpt/claude-code-mods-knowledge/plugin.json"
    plugin.write_bytes(plugin.read_bytes() + b"\n")
    with pytest.raises(ReleaseValidationError, match="SHA|hash"):
        validate_dist(tmp_path)
