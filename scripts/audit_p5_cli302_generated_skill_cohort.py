#!/usr/bin/env python3
"""Audit actual CLI302 approved Mods Skill versus no-Skill and CLI309 mismatch.

Private original native JSONL, personal paths and model replies NEVER go to Git.
The report pins genuine host/tool/Skill source, per-Claim exact official URLs
and a stronger opening Evidence section check. This is structural/case-specific
quality evidence, not semantic code acceptance or new CLI309 approval.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from mods_knowledge.answer_lint import lint_mods_answer
from mods_knowledge.claim_source_link_coverage import (
    audit_claim_evidence_section,
    audit_claim_source_links,
)
from mods_knowledge.claims import approved_claims, load_claims
from mods_knowledge.registry import load_registry

TARGET = "2.1.302"
MISMATCH = "2.1.309"
INSTALLED_302_NATIVE_SHA = "2bd4f4e5ed5cb09955b490098f745321cb5491e7ea8c752ba1e3bb010cdadb10"
EXACT_309_NATIVE_SHA = "9796dd26899337f687739a0b39a7353b639f062a3436a7b941fcf19a1b757a9b"
GENERATED_SKILL_SHA = "619787ebd651b572fc8014526d4b283501db882528f56d76920ddda5a92ca42a"
REFERENCES = {
    "events.md": "2a6effcd8d93f8d078b84051a90e506067b304c19b5372fd9f492b7b95a710c1",
    "claim-evidence.md": "d80e52c39fe68cea88acee597f7ec985352cda68c185a8459465bfd7305575e7",
}
SOURCE_REVISION = "814bbdaf385feac5d8f022ff8615991a42038ff7"
ARMS = ("skill302", "baseline302", "mismatch309")


class NativeQualityBlocked(ValueError):
    """Cannot independently support a genuine version-matched quality fact."""


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise NativeQualityBlocked(reason)


def sha(path: Path, *, limit: int = 350_000_000) -> str:
    require(
        path.is_file() and not path.is_symlink() and 0 < path.stat().st_size <= limit,
        "MISSING_OR_UNSAFE_PRIVATE_QA_FILE",
    )
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def _rows(path: Path) -> list[dict]:
    require(path.stat().st_size <= 5_000_000, "OVERSIZE_ORIGINAL_NATIVE_WIRE")
    try:
        rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    except (UnicodeError, ValueError) as exc:
        raise NativeQualityBlocked("INVALID_ORIGINAL_NATIVE_EVENTS") from exc
    require(rows and all(isinstance(x, dict) for x in rows), "NO_REAL_NATIVE_EVENTS")
    return rows


def _native(qa: Path, arm: str) -> tuple[dict, str]:
    wire = qa / "private" / f"{arm}-wire.private.jsonl"
    stderr = qa / "private" / f"{arm}-stderr.private.log"
    debug = qa / "private" / f"{arm}-debug.private.log"
    require(stderr.is_file() and stderr.stat().st_size == 0, "NONZERO_NATIVE_STDERR")
    events = _rows(wire)
    init = [x for x in events if x.get("type") == "system" and x.get("subtype") == "init"]
    target = MISMATCH if arm == "mismatch309" else TARGET
    require(
        len(init) == 1 and init[0].get("claude_code_version") == target,
        "ORIGINAL_CLAUDE_HOST_VERSION_MISMATCH",
    )
    end = [x for x in events if x.get("type") == "result"]
    require(
        len(end) == 1
        and end[0].get("subtype") == "success"
        and end[0].get("is_error") is False
        and set(end[0].get("modelUsage") or {}) == {"claude-sonnet-5-5"},
        "AUTHENTICATED_SONNET_OR_COMPLETED_TURN_MISSING",
    )
    answer = end[0].get("result")
    require(isinstance(answer, str) and 100 < len(answer) < 70_000, "EMPTY_OR_OVERSIZED_ANSWER")
    tools = [
        c
        for x in events
        if x.get("type") == "assistant"
        for c in (x.get("message") or {}).get("content", [])
        if isinstance(c, dict) and c.get("type") == "tool_use"
    ]
    failures = [
        c
        for x in events
        if x.get("type") == "user"
        for c in (x.get("message") or {}).get("content", [])
        if isinstance(c, dict) and c.get("type") == "tool_result" and c.get("is_error") is True
    ]
    if arm == "baseline302":
        # The no-Skill control attempted to read unavailable local evidence.
        # Preserve this negative fact; it limits a perfectly matched A/B claim.
        require(
            len(failures) == 1 and len(tools) == 1 and tools[0].get("name") == "Read",
            "BASELINE_READ_ERROR_DID_NOT_MATCH_ORIGINAL",
        )
    else:
        require(not failures, "SKILL_OR_MISMATCH_REFERENCE_READ_FAILED")
    seen = [x.get("name") for x in tools]
    if arm in ("skill302", "mismatch309"):
        require(
            seen[0] == "Skill"
            and (tools[0].get("input") or {}).get("skill") == "claude-code-mods-development"
            and len([x for x in tools if x.get("name") == "Skill"]) == 1,
            "ACTUAL_GENERATED_MODS_SKILL_NOT_INVOKED",
        )
        read_paths = [
            (x.get("input") or {}).get("file_path") for x in tools if x.get("name") == "Read"
        ]
        require(
            all(isinstance(p, str) and str(qa / "project/") in p for p in read_paths)
            and any(p.endswith("/references/events.md") for p in read_paths)
            and any(p.endswith("/references/claim-evidence.md") for p in read_paths),
            "CLAIM_AND_EVENTS_LOCAL_REFERENCES_NOT_ACTUALLY_READ",
        )
    else:
        require("Skill" not in seen, "NO_SKILL_BASELINE_CONTAMINATED")
    return (
        {
            "case": arm,
            "observed_native_cli_version": target,
            "observed_real_model": "claude-sonnet-5-5",
            "source_private_original_wire_sha256": sha(wire),
            "source_private_debug_sha256": sha(debug),
            "native_result_turns": end[0].get("num_turns"),
            "actual_tool_names": seen,
            "native_tool_error_count": len(failures),
            "native_skill_tool_called": "Skill" in seen,
            "read_events_reference": any(
                (x.get("input") or {}).get("file_path", "").endswith("/references/events.md")
                for x in tools
                if x.get("name") == "Read"
            ),
            "read_claim_evidence_reference": any(
                (x.get("input") or {})
                .get("file_path", "")
                .endswith("/references/claim-evidence.md")
                for x in tools
                if x.get("name") == "Read"
            ),
            "original_model_answer_sha256": hashlib.sha256(answer.encode()).hexdigest(),
            "original_model_answer_character_count": len(answer),
        },
        answer,
    )


def audit(root: Path, trusted: Path, cli302: Path, cli309: Path) -> dict:
    require(root.is_dir() and not root.is_symlink(), "NO_PRIVATE_QA_ROOT")
    require(trusted.is_dir() and not trusted.is_symlink(), "NO_SCOPED_VALIDATED_SSOT")
    require(sha(cli302) == INSTALLED_302_NATIVE_SHA, "WRONG_INSTALLED_302_BINARY")
    require(sha(cli309) == EXACT_309_NATIVE_SHA, "WRONG_DISPOSABLE_309_BINARY")
    skill = root / "project/.claude/skills/claude-code-mods-development"
    require(sha(skill / "SKILL.md") == GENERATED_SKILL_SHA, "CURRENT_GENERATED_SKILL_MISMATCH")
    for name, digest in REFERENCES.items():
        require(sha(skill / "references" / name) == digest, "APPROVED_SKILL_REFERENCE_DRIFT")
    manifest = json.loads((root / "private/build-manifest.json").read_text())
    require(
        manifest.get("target") == {"api_version": TARGET, "surface": "cli"}
        and manifest.get("source_revision") == SOURCE_REVISION,
        "NOT_CURRENT_SOURCE_REVISION_VERSION_SCOPED_BUILD",
    )
    registry = load_registry(trusted / "sources/registry.json")
    claims = load_claims(
        trusted / "claims",
        registry,
        trusted / "sources/snapshots",
        trusted / "decisions",
    )
    require(
        len(approved_claims(claims, TARGET, "cli")) == 31
        and not approved_claims(claims, MISMATCH, "cli"),
        "UNEXPECTED_TARGET_CLAIM_APPROVALS",
    )
    cases = {}
    outputs = {}
    for arm in ARMS:
        cases[arm], outputs[arm] = _native(root, arm)
    expected_prompt = sha(root / "private/prompt.private.txt")
    # User prompt source was the same operator-owned private file for the two
    # CLI302 arms. Native stream-json does NOT by itself attest this fact.
    for arm in ("skill302", "baseline302"):
        cases[arm]["operator_prompt_file_sha256"] = expected_prompt
    cases["mismatch309"]["operator_prompt_file_sha256"] = sha(
        root / "private/mismatch309-prompt.private.txt"
    )
    for arm in ("skill302", "baseline302"):
        text = outputs[arm]
        ordinary = audit_claim_source_links(text, claims, version=TARGET, surface="cli")
        strict = audit_claim_evidence_section(text, claims, version=TARGET, surface="cli")
        lint = lint_mods_answer(text, case_id="POS-E-01", target_version=TARGET)
        cases[arm].update(
            cited_claim_ids=ordinary["cited_claim_ids"],
            exact_approved_claim_urls_observed=ordinary["official_source_links_observed"],
            official_url_anywhere_structural_verdict=ordinary["structural_verdict"],
            opening_evidence_per_claim_verdict=strict["structural_verdict"],
            evidence_exact_locators_attested=strict[
                "evidence_claim_ids_with_exact_approved_locator"
            ],
            missing_opening_evidence_claim_ids=strict[
                "cited_claim_ids_missing_exact_evidence_line"
            ],
            answer_code_risk_flags=lint["risk_flags"],
            answer_manual_review_flags=lint["requires_manual_review"],
        )
    passed = cases["skill302"]
    control = cases["baseline302"]
    require(
        passed["native_skill_tool_called"]
        and passed["read_events_reference"]
        and passed["read_claim_evidence_reference"]
        and passed["official_url_anywhere_structural_verdict"] == "pass"
        and passed["opening_evidence_per_claim_verdict"] == "fail"
        and passed["missing_opening_evidence_claim_ids"] == ["K-0041", "K-0067"]
        and len(passed["cited_claim_ids"]) == 8
        and not passed["answer_code_risk_flags"]
        and not passed["answer_manual_review_flags"],
        "GENUINE_MODEL_302_EVIDENCE_LINTER_CONTRADICTS_ORIGINAL",
    )
    require(
        not control["native_skill_tool_called"]
        and not control["cited_claim_ids"]
        and control["official_url_anywhere_structural_verdict"] == "fail"
        and control["opening_evidence_per_claim_verdict"] == "fail",
        "NO_SKILL_BASELINE_SOURCE_EVIDENCE_CONTAMINATED",
    )
    mismatch = outputs["mismatch309"]
    require(
        cases["mismatch309"]["native_skill_tool_called"]
        and cases["mismatch309"]["read_events_reference"]
        and "2.1.302" in mismatch
        and "2.1.309" in mismatch
        and "version mismatch" in mismatch.lower()
        and "i abstain" in mismatch.lower()
        and "can't guarantee" in mismatch.lower()
        and "```" not in mismatch,
        "HISTORICAL_CLI302_SKILL_WRONGLY_PROMOTED_AS_309",
    )
    cases["mismatch309"].update(
        explicitly_warned_old_version_scope=True,
        explicitly_abstained_from_309_guarantee=True,
        no_309_executable_code_claim=True,
        zero_309_approved_claims=True,
    )
    return {
        "schema_version": 1,
        "scope": "original P5 target-specific generated Claude Code Mods SSOT Skill model QA",
        "approved_cli302_claims": 31,
        "approved_cli309_claims": 0,
        "compiled_source_revision": SOURCE_REVISION,
        "generated_skill_sha256": GENERATED_SKILL_SHA,
        "reference_sha256": REFERENCES,
        "build_manifest_sha256": sha(root / "private/build-manifest.json"),
        "auditor_source_sha256": sha(Path(__file__)),
        "original_cli302_executable_sha256": INSTALLED_302_NATIVE_SHA,
        "original_cli309_executable_sha256": EXACT_309_NATIVE_SHA,
        "cases": cases,
        "actual_native_model_output_improved_source_coverage": True,
        "skill_cohort_evidence_section_completeness_pass": False,
        "no_skill_baseline_official_evidence_pass": False,
        "historical_skill_applied_to_309_without_scope_warning": False,
        "same_prompt_reported_for_302_arms_from_operator_private_file": True,
        "native_wires_independently_attest_identical_prompt_text": False,
        "no_skill_control_had_one_failed_read_and_is_not_a_perfectly_equivalent_source_arm": True,
        "actual_generated_mods_code_typechecked_in_this_cohort": False,
        "source_link_structure_is_not_semantic_correctness": True,
        "full_agent_quality_acceptance": False,
        "new_309_claims_approved": 0,
        "new_production_skills_or_plugin_published": False,
        "stable_release_authorized": False,
        "original_model_text_and_session_ids_not_committed": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-root", required=True, type=Path)
    parser.add_argument("--scoped-ssot", required=True, type=Path)
    parser.add_argument("--cli302", required=True, type=Path)
    parser.add_argument("--cli309", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    if args.out.exists() or args.out.is_symlink():
        raise SystemExit("REFUSED: original QA output already exists")
    try:
        result = audit(args.private_root, args.scoped_ssot, args.cli302, args.cli309)
    except (OSError, ValueError, KeyError, TypeError, NativeQualityBlocked):
        raise SystemExit("BLOCKED: private native Mods Skill quality evidence incomplete") from None
    args.out.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(
        json.dumps(
            {
                "actual_model_cases": 3,
                "scope": "302 approved only",
                "full_quality_pass": False,
                "stable_release_authorized": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
