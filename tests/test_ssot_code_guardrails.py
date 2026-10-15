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


def test_strict_manifest_author_warning_is_source_reviewed_version_scoped() -> None:
    sources = load_registry(ROOT / "sources/registry.json")
    all_claims = load_claims(
        ROOT / "claims", sources, ROOT / "sources/snapshots", ROOT / "decisions"
    )
    claim = all_claims["K-0034"]
    assert claim["lifecycle"] == "approved"
    assert claim["subject"] == "mods.types.strict-plugin-author-attribution"
    assert claim["authority"] == "guidance"
    assert claim["areas"]["primary"] == ["T"]
    assert "claude plugin validate --strict" in claim["statement"]
    assert "author" in claim["statement"]
    assert "普通" in claim["statement"] or "non-strict" in claim["statement"]
    assert claim["evidence"][0]["source_id"] == "M003"
    assert claim["evidence"][0]["locator"].endswith("#files")
    assert claim["verification"]["source"] == "reviewed"
    assert claim["applies_to"]["surfaces"] == ["cli"]
    assert claim["applies_to"]["claude_code"] == {
        "min_inclusive": "2.1.296",
        "max_exclusive": "2.1.297",
    }


def test_native_validate_path_requirement_is_approved_and_source_attributed() -> None:
    """The target-scoped argument rule must live in the SSOT, not the compiler."""
    source = load_registry(ROOT / "sources/registry.json")
    claims = load_claims(ROOT / "claims", source, ROOT / "sources/snapshots", ROOT / "decisions")
    claim = claims["K-0035"]
    assert claim["lifecycle"] == "approved"
    assert claim["authority"] == "guidance"
    assert claim["subject"] == "mods.types.plugin-validate-directory-required"
    assert claim["applies_to"]["claude_code"] == {
        "min_inclusive": "2.1.296",
        "max_exclusive": "2.1.297",
    }
    assert claim["applies_to"]["surfaces"] == ["cli"]
    assert "claude plugin validate --strict ." in claim["statement"]
    assert "missing required argument 'path'" in claim["statement"]
    assert claim["evidence"][0]["source_id"] == "M002"
    assert claim["evidence"][0]["locator"].endswith("#check-what-claude-code-reads-from-your-mod")
    assert claim["verification"]["source"] == "reviewed"


def test_fail_isolated_observer_diagnostics_is_approved_source_bound() -> None:
    """Unprotected logs in a transparent tool.call observer can mask tool failures."""
    registry = load_registry(ROOT / "sources/registry.json")
    claims = load_claims(ROOT / "claims", registry, ROOT / "sources/snapshots", ROOT / "decisions")
    claim = claims["K-0036"]
    assert claim["lifecycle"] == "approved"
    assert claim["authority"] == "guidance"
    assert claim["subject"] == "mods.events.fail-isolated-transparent-observer-diagnostics"
    assert claim["applies_to"]["claude_code"] == {
        "min_inclusive": "2.1.296",
        "max_exclusive": "2.1.297",
    }
    assert claim["applies_to"]["surfaces"] == ["cli"]
    assert "next(e)" in claim["statement"]
    assert "try" in claim["statement"] and "finally" in claim["statement"]
    assert "日志" in claim["statement"] and "原始" in claim["statement"]
    assert claim["evidence"][0]["source_id"] == "M004"
    assert claim["evidence"][0]["locator"].endswith("#observe-an-event")
    assert claim["verification"]["source"] == "reviewed"
