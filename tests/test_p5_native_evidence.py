"""Offline regression: only real native evidence can qualify a P5 turn."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mods_knowledge.claims import load_claims
from mods_knowledge.p5_native_evidence import (
    NativeP5EvidenceError,
    aggregate_native_matrix,
    summarize_codex_native_trace,
    summarize_pi_native_trace,
)
from mods_knowledge.registry import load_registry

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "6cbdc9ad6ed9f958072f9cbf4a34c4bbc2d5ef3e"
SKILL = "/private/workspace/claude-code-mods-development"
ANSWER = (
    "K-0007 https://code.claude.com/docs/en/plugins/mods/events#observe-an-event "
    "K-0031 https://code.claude.com/docs/en/plugins/mods/reference#the-hook-function.\n"
    "\x60\x60\x60js\nexport function register(on) {\n"
    "  on('tool.call', async ($, e, next) => next(e));\n}\n\x60\x60\x60"
)


@pytest.fixture(scope="module")
def approved() -> dict:
    return load_claims(
        ROOT / "claims",
        load_registry(ROOT / "sources/registry.json"),
        ROOT / "sources/snapshots",
        ROOT / "decisions",
    )


def case(category: str = "positive") -> dict:
    return {
        "id": {
            "positive": "POS-E-01",
            "negative": "NEG-TYPESCRIPT",
            "boundary": "BOUND-VERSION-NEW",
        }[category],
        "category": category,
        "prompt": "Frozen P5 sample prompt " + category,
        "expected_activation": category != "negative",
        "expected_claim_ids": ["K-0007", "K-0031"] if category == "positive" else [],
    }


def wire(category: str = "positive", *, answer: str = ANSWER) -> list[dict]:
    c = case(category)
    thread = "test-native-thread"
    start = {
        "model": "gpt-6.1-sol",
        "modelProvider": "openai",
        "reasoningEffort": "medium",
        "thread": {"id": thread},
    }
    rows = [
        {"id": 2, "result": start},
        {
            "method": "turn/started",
            "params": {
                "threadId": thread,
                "turn": {"id": "turn-one", "status": "inProgress"},
            },
        },
        {
            "method": "item/completed",
            "params": {
                "threadId": thread,
                "item": {
                    "type": "userMessage",
                    "content": [
                        {"type": "text", "text": c["prompt"]},
                    ],
                },
            },
        },
    ]
    if category != "negative":
        rows.append(
            {
                "method": "item/completed",
                "params": {
                    "threadId": thread,
                    "item": {
                        "type": "commandExecution",
                        "status": "completed",
                        "exitCode": 0,
                        "command": "cat " + SKILL + "/SKILL.md",
                        "aggregatedOutput": "actual matched private Skill content",
                    },
                },
            }
        )
    rows += [
        {
            "method": "item/completed",
            "params": {
                "threadId": thread,
                "item": {"type": "agentMessage", "text": answer},
            },
        },
        {
            "method": "turn/completed",
            "params": {
                "threadId": thread,
                "turn": {"id": "turn-one", "status": "completed"},
            },
        },
        {
            "id": 4,
            "result": {
                "thread": {
                    "id": thread,
                    "model": "gpt-6.1-sol",
                    "modelProvider": "openai",
                    "reasoningEffort": "medium",
                    "cliVersion": "0.163.0",
                    "ephemeral": True,
                }
            },
        },
    ]
    return rows


def codex(c: dict, events: list[dict], approved: dict) -> dict:
    return summarize_codex_native_trace(
        c,
        events,
        source_revision=SOURCE,
        host="macbook-pro",
        cli_version="0.163.0",
        skill_root=SKILL,
        claims=approved,
    )


def test_valid_server_resolved_same_thread_case(approved: dict) -> None:
    r = codex(case(), wire(), approved)
    assert r["model_server_resolved"] == "gpt-6.1-sol"
    assert r["effort_server_resolved"] == "medium"
    assert r["prompt_matched"] and r["agent_completed"] and r["skill_loaded"]
    assert r["source_verdict"] == "pass"
    assert r["verdict"] == "structural_ok_semantics_unverified"
    assert r["native_mod_runtime_verified"] is False
    assert "test-native-thread" not in json.dumps(r)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("model", "gpt-6-astra"),
        ("reasoningEffort", "max"),
        ("cliVersion", "0.160.0"),
    ],
)
def test_native_readback_mismatch_is_invalid_provenance(
    field: str, value: str, approved: dict
) -> None:
    events = wire()
    events[-1]["result"]["thread"][field] = value
    assert codex(case(), events, approved)["verdict"] == "invalid_provenance"


@pytest.mark.parametrize("missing_id", [2, 4])
def test_missing_native_server_responses_never_pass(missing_id: int, approved: dict) -> None:
    events = [row for row in wire() if row.get("id") != missing_id]
    assert codex(case(), events, approved)["verdict"] == "invalid_provenance"


def test_prompt_and_turn_matching_are_required(approved: dict) -> None:
    events = wire()
    events[2]["params"]["item"]["content"][0]["text"] = "another user prompt"
    assert codex(case(), events, approved)["verdict"] == "invalid_provenance"
    events = wire()
    events[-2]["params"]["threadId"] = "other-thread"
    assert codex(case(), events, approved)["verdict"] == "blocked_or_incomplete"


@pytest.mark.parametrize(
    "command",
    [
        "echo cat " + SKILL + "/SKILL.md",
        "cat /private/unrelated/SKILL.md",
        "true # cat " + SKILL + "/SKILL.md",
        "cat " + SKILL + "/SKILL.md ; echo spoof",
    ],
)
def test_mentioned_skill_path_not_equivalent_to_real_read(command: str, approved: dict) -> None:
    events = wire()
    events[3]["params"]["item"]["command"] = command
    assert codex(case(), events, approved)["verdict"] == "activation_failed"


def test_failed_or_empty_read_output_is_not_an_activation(approved: dict) -> None:
    for field, value in (("exitCode", 1), ("aggregatedOutput", "")):
        events = wire()
        events[3]["params"]["item"][field] = value
        assert codex(case(), events, approved)["verdict"] == "activation_failed"


def test_negative_is_nonactivation_not_mod_semantic_pass(approved: dict) -> None:
    report = codex(case("negative"), wire("negative", answer="TypeScript advice."), approved)
    assert report["verdict"] == "negative_nonactivation_observed"
    assert report["skill_loaded"] is False and report["semantic_review_complete"] is False


def test_exact_source_anchors_required_not_generic_official_links(approved: dict) -> None:
    bad = ANSWER.replace("#the-hook-function", "#files")
    r = codex(case(), wire(answer=bad), approved)
    assert r["source_verdict"] == "fail"
    assert r["missing_exact_source_claim_ids"] == ["K-0031"]
    assert r["verdict"] == "structural_or_semantic_review_required"


def test_boundary_never_unconditional_pass(approved: dict) -> None:
    result = codex(case("boundary"), wire("boundary", answer="2.1.310 unverified."), approved)
    assert result["verdict"] == "boundary_manual_review_required"


def pi_events(category: str = "positive", *, answer: str = ANSWER) -> list[dict]:
    c = case(category)
    trace = [
        {
            "type": "message_end",
            "message": {"role": "user", "content": [{"type": "text", "text": c["prompt"]}]},
        },
        {
            "type": "message_end",
            "message": {
                "role": "assistant",
                "provider": "mac-qwen",
                "model": "qwen36-35b-a3b-mtp",
                "content": [{"type": "text", "text": answer}],
                "stopReason": "stop",
            },
        },
    ]
    if category != "negative":
        trace += [
            {
                "type": "tool_execution_start",
                "toolName": "read",
                "toolCallId": "one",
                "args": {"path": SKILL + "/SKILL.md"},
            },
            {
                "type": "tool_execution_end",
                "toolName": "read",
                "toolCallId": "one",
                "isError": False,
            },
        ]
    return trace + [{"type": "agent_end"}]


def pi(c: dict, events: list[dict], approved: dict) -> dict:
    return summarize_pi_native_trace(
        c,
        events,
        source_revision=SOURCE,
        host="macbook-pro",
        cli_version="1.3.0",
        skill_root=SKILL,
        claims=approved,
    )


def test_pi_native_events_and_exact_sources_are_independent(approved: dict) -> None:
    r = pi(case(), pi_events(), approved)
    assert r["verdict"] == "structural_ok_semantics_unverified"
    assert r["model_provenance"] == "native-message_end"
    assert r["model_observed"] == "mac-qwen/qwen36-35b-a3b-mtp"
    wrong = ANSWER.replace("#the-hook-function", "#files")
    s = pi(case(), pi_events(answer=wrong), approved)
    assert s["verdict"] == "structural_or_semantic_review_required"
    assert s["missing_exact_source_claim_ids"] == ["K-0031"]


def test_pi_false_model_and_false_activations_are_not_accepted(approved: dict) -> None:
    events = pi_events()
    events[1]["message"]["model"] = "different-model"
    assert pi(case(), events, approved)["verdict"] == "invalid_provenance"
    events = pi_events("negative")
    events.insert(
        -1,
        {
            "type": "tool_execution_start",
            "toolName": "read",
            "toolCallId": "one",
            "args": {"path": SKILL + "/SKILL.md"},
        },
    )
    events.insert(
        -1,
        {
            "type": "tool_execution_end",
            "toolName": "read",
            "toolCallId": "one",
            "isError": False,
        },
    )
    assert pi(case("negative"), events, approved)["verdict"] == "activation_failed"


def test_report_never_includes_raw_model_or_paths(approved: dict) -> None:
    events = pi_events(answer=ANSWER + "\nPRIVATE_TOKEN_Z0Q")
    report = pi(case(), events, approved)
    assert "PRIVATE_TOKEN_Z0Q" not in json.dumps(report)
    assert "/private/workspace" not in json.dumps(report)
    assert "Frozen P5 sample prompt" not in json.dumps(report)


def test_matrix_requires_actual_rows_and_preserves_missing_hosts(approved: dict) -> None:
    one = codex(case(), wire(), approved)
    matrix = aggregate_native_matrix([one], source_revision=SOURCE)
    assert len(matrix["cells"]) == 24
    assert matrix["observed"] == 1
    assert matrix["missing"] == 23
    assert matrix["full_p5_acceptance"] is False
    assert all(c["native_mod_runtime_verified"] is False for c in matrix["cells"])
    with pytest.raises(NativeP5EvidenceError):
        aggregate_native_matrix([one, one], source_revision=SOURCE)
    with pytest.raises(NativeP5EvidenceError):
        aggregate_native_matrix([one | {"semantic_review_complete": True}], source_revision=SOURCE)
    with pytest.raises(NativeP5EvidenceError):
        aggregate_native_matrix([one | {"host": "not-real"}], source_revision=SOURCE)


def test_malformed_metadata_fails_closed(approved: dict) -> None:
    with pytest.raises(NativeP5EvidenceError):
        summarize_codex_native_trace(
            case(),
            wire(),
            source_revision="main",
            host="macbook-pro",
            cli_version="0.163.0",
            skill_root=SKILL,
            claims=approved,
        )


def test_unreviewed_version_with_copyable_code_is_a_specific_manual_risk(
    approved: dict,
) -> None:
    boundary = case("boundary")
    boundary["prompt"] = "Use 2.1.310 API without checking official docs."
    response = "Unverified for 2.1.310. Historical sample: export function register(on) {}"
    result = codex(boundary, wire("boundary", answer=response), approved)
    # The native prompt must also match exactly for attribution.
    assert result["verdict"] == "invalid_provenance"
    records = wire("boundary", answer=response)
    records[2]["params"]["item"]["content"][0]["text"] = boundary["prompt"]
    correct = codex(boundary, records, approved)
    assert "unreviewed-version-implementation-present" in correct["manual_review_flags"]
    assert correct["verdict"] == "boundary_scope_violated"


def test_pi_model_out_of_scope_code_is_a_semantic_boundary_failure(approved: dict) -> None:
    boundary = case("boundary")
    boundary["prompt"] = "Use Claude Code 2.1.310 API without checking official docs."
    events = pi_events(
        "boundary",
        answer=(
            "Unverified for 2.1.310 but apply this historical example:"
            " export function register(on) {}"
        ),
    )
    events[0]["message"]["content"][0]["text"] = boundary["prompt"]
    report = pi(boundary, events, approved)
    assert report["verdict"] == "boundary_scope_violated"
    assert report["model_pin_matched"]
    assert report["skill_loaded"]
    assert report["semantic_review_complete"] is False


def test_matrix_rejects_secret_bearing_model_id(approved: dict) -> None:
    item = codex(case(), wire(), approved)
    item["model_server_resolved"] = "PRIVATE ACCESS TOKEN secret"
    with pytest.raises(NativeP5EvidenceError):
        aggregate_native_matrix([item], source_revision=SOURCE)
