"""P1: no invented Claims, correct route, bounded minimal evidence selection."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from mods_knowledge.claims import load_claims
from mods_knowledge.cli import main
from mods_knowledge.registry import load_registry
from mods_knowledge.task_evidence import (
    EvidenceSelectionError,
    render_evidence_pack,
    route_task,
    select_task_evidence,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def claims() -> dict:
    return load_claims(
        ROOT / "claims",
        load_registry(ROOT / "sources/registry.json"),
        ROOT / "sources/snapshots",
        ROOT / "decisions",
    )


@pytest.fixture(scope="module")
def frozen() -> list[dict]:
    suite = json.loads((ROOT / "evals/p5_pi_auto_12x3.json").read_text())
    cases = {
        row["id"]: row for row in json.loads((ROOT / suite["source_file"]).read_text())["cases"]
    }
    assert (
        hashlib.sha256((ROOT / suite["source_file"]).read_bytes()).hexdigest()
        == suite["source_sha256"]
    )
    return [cases[case_id] for case_id in suite["case_ids"]]


def test_all_frozen_positives_have_relevant_reviewed_claims(
    frozen: list[dict], claims: dict
) -> None:
    for row in frozen:
        if row["category"] != "positive":
            continue
        chosen = select_task_evidence(row["prompt"], claims, version="2.1.296")
        assert chosen["intent"] == "mods"
        assert chosen["ready"] is True
        assert 1 <= len(chosen["claims"]) <= 6
        assert set(row["expected_claim_ids"]) <= {c["claim_id"] for c in chosen["claims"]}
        for item in chosen["claims"]:
            assert item["version"] == "2.1.296"
            assert item["surface"] == "cli"
            assert item["area"] in row["expected_areas"] or (
                item["claim_id"] in ("K-0033", "K-0037")
                and "K-0019" in row["expected_claim_ids"]
                or "K-0007" in row["expected_claim_ids"]
            )
            assert all(
                u.startswith("https://code.claude.com/docs/en/plugins/mods/") and "#" in u
                for u in item["official_urls"]
            )
        rendered = render_evidence_pack(chosen)
        assert row["prompt"] not in rendered
        assert len(rendered) < 10000
        assert all(x in rendered for x in row["expected_claim_ids"])


def test_all_frozen_negatives_remain_nonmods_and_boundaries_fail_closed(
    frozen: list[dict], claims: dict
) -> None:
    for row in frozen:
        route = route_task(row["prompt"], target_version="2.1.296")
        pack = select_task_evidence(row["prompt"], claims, version="2.1.296")
        if row["category"] == "negative":
            assert route["intent"] == "unrelated"
        elif row["category"] == "boundary":
            assert route["intent"] == "blocked"
        else:
            continue
        assert pack["ready"] is False
        assert pack["claims"] == []
        with pytest.raises(EvidenceSelectionError):
            render_evidence_pack(pack)


def test_no_generic_python_or_trust_boundary_inference() -> None:
    examples = (
        ("Please fix a generic TypeScript callback bug, not Mods", "unrelated"),
        ("Explain a normal Claude Code settings.json PreToolUse hook, not Mods.", "unrelated"),
        ("Claude Code Mods CLI 2.1.301 next API code", "blocked"),
        ("Use old CLAUDE_CODE_ENABLE_FUNCTION_HOOKS from early preview", "blocked"),
        ("Does Claude Code Mods 2.1.296 guarantee VS Code panes?", "blocked"),
        ("How to test a Mod offline?", "mods"),
    )
    for prompt, expected in examples:
        assert route_task(prompt, target_version="2.1.296")["intent"] == expected
    for invalid in ("", " " * 20, "X" * 20000, None):
        with pytest.raises(EvidenceSelectionError):
            route_task(invalid, target_version="2.1.296")


def test_cannot_expand_selected_pack_to_unreviewed_version_or_surface(claims: dict) -> None:
    query = "How to test a Mod offline?"
    for version, surface in (("2.1.310", "cli"), ("2.1.296", "vscode")):
        result = select_task_evidence(query, claims, version=version, surface=surface)
        assert result["ready"] is False
        assert result["intent"] == "blocked"
        assert result["claims"] == []


def test_missing_or_changed_approved_claim_mapping_cannot_be_laundered(claims: dict) -> None:
    selected = "How do I test a Claude Code Mod offline using a .test.ts command?"
    changed = {k: v for k, v in claims.items() if k != "K-0019"}
    with pytest.raises(EvidenceSelectionError):
        select_task_evidence(selected, changed, version="2.1.296")
    sel = select_task_evidence(selected, claims, version="2.1.296")
    broken = dict(sel)
    broken["claims"] = [{**sel["claims"][0], "official_urls": ["https://example.com/not-official"]}]
    with pytest.raises(EvidenceSelectionError):
        render_evidence_pack(broken)


def test_private_cli_produces_valid_provenance_only_and_refuses_overwrite(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    prompt = tmp_path / "task-private.txt"
    target = tmp_path / "evidence.md"
    prompt.write_text("如何不登录、不联网测试 Claude Code Mod，使用什么 .test.ts 命令？")
    argv = [
        "--root",
        str(ROOT),
        "evidence-select",
        "--prompt-file",
        str(prompt),
        "--out",
        str(target),
    ]
    assert main(argv) == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["status"] == "selected" and parsed["inference_requested"] is False
    assert "K-0052" in parsed["approved_claim_ids"]
    assert "https://code.claude.com/docs/en/plugins/mods/test#write-a-test" in target.read_text()
    assert (target.stat().st_mode & 0o777) == 0o600
    assert main(argv) == 2
    target2 = tmp_path / "blocked.md"
    prompt.write_text("Use Claude Code Mods 2.1.310 API with code!")
    assert (
        main(
            [
                "--root",
                str(ROOT),
                "evidence-select",
                "--prompt-file",
                str(prompt),
                "--out",
                str(target2),
            ]
        )
        == 3
    )
    assert not target2.exists()
    assert "withheld" in capsys.readouterr().out


def test_symlink_prompt_and_output_disallowed(tmp_path: Path) -> None:
    real = tmp_path / "original"
    real.write_text("How to test a Mod offline?")
    linked = tmp_path / "linked"
    linked.symlink_to(real)
    assert (
        main(
            [
                "--root",
                str(ROOT),
                "evidence-select",
                "--prompt-file",
                str(linked),
                "--out",
                str(tmp_path / "answer"),
            ]
        )
        == 2
    )
    out = tmp_path / "answer"
    out.symlink_to(real)
    assert (
        main(
            ["--root", str(ROOT), "evidence-select", "--prompt-file", str(real), "--out", str(out)]
        )
        == 2
    )
    assert real.read_text() == "How to test a Mod offline?"
