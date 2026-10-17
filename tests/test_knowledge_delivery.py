"""P1 pre-inference delivery contracts and private data guardrails."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from mods_knowledge.claims import load_claims
from mods_knowledge.knowledge_delivery import (
    KnowledgeDeliveryError,
    codex_thread_instructions,
    pi_append_system_prompt_args,
    prepare_delivery,
    verify_delivery,
    write_private_pi_delivery,
)
from mods_knowledge.registry import load_registry
from mods_knowledge.task_evidence import select_task_evidence

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def claims() -> dict:
    return load_claims(
        ROOT / "claims",
        load_registry(ROOT / "sources/registry.json"),
        ROOT / "sources/snapshots",
        ROOT / "decisions",
    )


def test_preloaded_payload_is_exact_ssot_content_without_user_prompt(claims: dict) -> None:
    prompt = "How do I test a Claude Code Mod offline using .test.ts?"
    delivery = prepare_delivery(prompt, claims, "codex")
    assert delivery.transport == "codex_developer_instructions"
    assert "K-0019" in delivery.claim_ids
    assert "https://code.claude.com/docs/en/plugins/mods/test#write-a-test" in delivery.payload
    assert prompt not in delivery.payload
    assert delivery.byte_length < 12000
    assert codex_thread_instructions(delivery) == {"developerInstructions": delivery.payload}
    assert delivery.sha256 == hashlib.sha256(delivery.payload.encode()).hexdigest()


def test_pi_private_file_injection_is_owner_only_and_cannot_be_overwritten(
    claims: dict, tmp_path: Path
) -> None:
    delivery = prepare_delivery("How to test a Claude Code Mod offline?", claims, "pi")
    safe = tmp_path / "private"
    safe.mkdir(mode=0o700)
    path = write_private_pi_delivery(safe / "approved-task-evidence.txt", delivery)
    assert pi_append_system_prompt_args(path, delivery) == ["--append-system-prompt", str(path)]
    assert path.stat().st_mode & 0o077 == 0
    with pytest.raises(KnowledgeDeliveryError):
        write_private_pi_delivery(path, delivery)
    path.write_text("tampered")
    with pytest.raises(KnowledgeDeliveryError):
        pi_append_system_prompt_args(path, delivery)


def test_symlink_and_unrestricted_directory_fail_closed(
    claims: dict, tmp_path: Path
) -> None:
    delivery = prepare_delivery("How to test a Claude Code Mod?", claims, "pi")
    public_dir = tmp_path / "public"
    public_dir.mkdir(mode=0o755)
    public_dir.chmod(0o755)  # QA host umask may be 077; explicitly exercise the rejection
    with pytest.raises(KnowledgeDeliveryError, match="owner-only"):
        write_private_pi_delivery(public_dir / "approved-task-evidence.txt", delivery)
    other = tmp_path / "protected"
    other.mkdir(mode=0o700)
    target = other / "real"
    target.write_text("sentinel")
    link = other / "approved-task-evidence.txt"
    link.symlink_to(target)
    with pytest.raises(KnowledgeDeliveryError):
        write_private_pi_delivery(link, delivery)
    assert target.read_text() == "sentinel"


@pytest.mark.parametrize(
    "prompt",
    [
        "What is the latest Claude Code Mods API for observer logging?",
        "Use Claude Code Mods 2.1.310 API.",
        "Implement Claude Code Mods on VS Code.",
        "Debug this ordinary Python program, not Mods.",
    ],
)
def test_never_preload_unreviewed_or_unrelated_knowledge(prompt: str, claims: dict) -> None:
    selection = select_task_evidence(prompt, claims)
    assert selection["ready"] is False
    with pytest.raises(KnowledgeDeliveryError):
        prepare_delivery(prompt, claims, "codex")


def test_host_type_and_mutation_defense(claims: dict) -> None:
    delivery = prepare_delivery(
        "How to test a Claude Code Mod?",
        claims,
        "codex",
    )
    with pytest.raises(KnowledgeDeliveryError):
        verify_delivery(replace(delivery, payload=delivery.payload + "unreviewed"))
    with pytest.raises(KnowledgeDeliveryError):
        pi_append_system_prompt_args(Path("none"), delivery)
    with pytest.raises(KnowledgeDeliveryError):
        prepare_delivery(
            "How to test a Claude Code Mod?", claims,
            "chatgpt",  # type: ignore[arg-type]
        )


def test_all_four_frozen_positives_have_bounded_codex_evidence(claims: dict) -> None:
    frozen = {item["id"]: item for item in json.loads((ROOT / "evals/p4_cases.json").read_text())["cases"]}
    for case_id in ("POS-E-01", "POS-Q-01", "POS-S-02", "POS-P-01"):
        delivery = prepare_delivery(frozen[case_id]["prompt"], claims, "codex")
        assert len(delivery.claim_ids) <= 6
        assert set(frozen[case_id]["expected_claim_ids"]) <= set(delivery.claim_ids)
        assert delivery.target == "2.1.296"

def test_missing_ssot_approval_blocks_delivery(claims: dict) -> None:
    prompt = "How do I test a Claude Code Mod offline using .test.ts?"
    changed = {cid: record for cid, record in claims.items() if cid != "K-0019"}
    with pytest.raises(KnowledgeDeliveryError):
        prepare_delivery(prompt, changed, "codex")
