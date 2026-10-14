"""Known valid Mod registration and CLI test-directory constraints are source-bound."""

from pathlib import Path

from mods_knowledge.claims import load_claims
from mods_knowledge.registry import load_registry

ROOT = Path(__file__).resolve().parents[1]


def test_registration_export_guardrail_is_official_and_reviewed() -> None:
    source = load_registry(ROOT / "sources/registry.json")
    c = load_claims(ROOT / "claims", source, ROOT / "sources/snapshots", ROOT / "decisions")
    item = c["K-0032"]
    assert item["lifecycle"] == "approved"
    assert item["authority"] == "guidance"
    assert item["subject"] == "mods.types.named-registration-export"
    assert "export function register(on)" in item["statement"]
    assert "export default function register({ on })" in item["statement"]
    assert item["evidence"][0]["source_id"] == "M003"
    assert item["evidence"][0]["locator"].endswith("#files")
    assert item["verification"]["source"] == "reviewed"


def test_cli_test_directory_guardrail_is_official_and_reviewed() -> None:
    source = load_registry(ROOT / "sources/registry.json")
    c = load_claims(ROOT / "claims", source, ROOT / "sources/snapshots", ROOT / "decisions")
    item = c["K-0033"]
    assert item["lifecycle"] == "approved"
    assert item["authority"] == "guidance"
    assert item["subject"] == "mods.testing.plugin-test-mod-directory"
    assert "claude plugin test" in item["statement"]
    assert ".test.ts" in item["statement"]
    assert item["evidence"][0]["source_id"] == "M008"
    assert item["evidence"][0]["locator"].endswith("#write-a-test")
    assert item["verification"]["source"] == "reviewed"
    for row in (c["K-0032"], item):
        assert row["applies_to"]["claude_code"] == {
            "min_inclusive": "2.1.296",
            "max_exclusive": "2.1.297",
        }
        assert row["applies_to"]["surfaces"] == ["cli"]
