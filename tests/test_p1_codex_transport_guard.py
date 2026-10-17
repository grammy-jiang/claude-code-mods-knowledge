"""Native Codex injection requires canonical approved task evidence before IPC."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from mods_knowledge.claims import load_claims
from mods_knowledge.knowledge_delivery import prepare_delivery
from mods_knowledge.registry import load_registry

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run_p5_p123_codex_native as native  # noqa: E402


@pytest.fixture(scope="module")
def claims() -> dict:
    return load_claims(
        ROOT / "claims",
        load_registry(ROOT / "sources/registry.json"),
        ROOT / "sources/snapshots",
        ROOT / "decisions",
    )


def test_native_refuses_arbitrary_developer_role_text_before_any_model_call() -> None:
    with pytest.raises(ValueError, match="Unverified task evidence"):
        native.run_native_case(
            "POS-E-01", "macbook-pro", 105,
            evidence_delivery="malicious arbitrary string",  # type: ignore[arg-type]
        )


def test_native_rejects_correctly_hashed_evidence_for_wrong_task(claims: dict) -> None:
    valid_but_different = prepare_delivery(
        "How do I test a Claude Code Mod offline using .test.ts?", claims, "codex"
    )
    with pytest.raises(ValueError, match="differs from approved SSOT"):
        native.run_native_case(
            "POS-E-01", "macbook-pro", 105,
            evidence_delivery=valid_but_different,
        )


def test_canonical_native_preflight_passes_payload_verification(
    claims: dict,
) -> None:
    prompt = next(
        c["prompt"]
        for c in __import__("json").loads((ROOT / "evals/p4_cases.json").read_text())["cases"]
        if c["id"] == "POS-E-01"
    )
    valid = prepare_delivery(prompt, claims, "codex")
    with pytest.raises(RuntimeError, match="isolated owner-only workspace"):
        native.run_native_case(
            "POS-E-01", "macbook-pro", 105, evidence_delivery=valid,
        )
