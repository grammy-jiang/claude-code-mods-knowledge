"""Fail-closed release readiness gate based on real Chat and host evidence.

This assesses eligibility; it never publishes, changes a GitHub Release, or
asserts that a fabricated local fixture represents a real model observation.
Every required category must have independent, version-matched observations.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from .evaluator import validate_suite
from .release_validation import ReleaseValidationError, validate_dist

HEX64 = re.compile(r"[a-f0-9]{64}\Z")
HEX40 = re.compile(r"[a-f0-9]{40}\Z")
REQUIRED_AGENTS = ("claude_code", "codex", "pi_agent")
REQUIRED_HOST_CASES = ("positive", "negative", "boundary")
PLUGIN_RESOURCE_PREFIX = "skills://plugins/claude-code-mods-knowledge/"


class StableGateError(ValueError):
    """Compiler or QA input is invalid; no release assessment can be trusted."""


def _hashed(value: object) -> bool:
    return isinstance(value, str) and bool(HEX64.fullmatch(value))


def _validate_chat_evidence(
    chat: object, suite: dict, expected_version: str, source_revision: str
) -> tuple[bool, str]:
    if not isinstance(chat, dict):
        return False, "CHAT_REPORT_MISSING"
    if chat.get("mode") != "chat":
        return False, "CHAT_MODE_NOT_CONFIRMED"
    if (
        chat.get("plugin_version") != expected_version
        or chat.get("source_revision") != source_revision
    ):
        return False, "CHAT_VERSION_OR_SOURCE_MISMATCH"
    summary = chat.get("summary")
    rows = chat.get("items")
    known = {x["id"]: x for x in suite["cases"]}
    if not isinstance(rows, list) or not isinstance(summary, dict):
        return False, "CHAT_46_CASE_REPORT_MISSING"
    if len(rows) != len(known) or len(known) != 46:
        return False, "CHAT_46_CASE_COVERAGE_INCOMPLETE"
    identifiers: set[str] = set()
    conversations: set[str] = set()
    instance_ids: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            return False, "CHAT_ROW_MALFORMED"
        cid = row.get("id")
        if not isinstance(cid, str) or cid not in known or cid in identifiers:
            return False, "CHAT_ROW_ID_MISSING_DUPLICATED_OR_UNKNOWN"
        identifiers.add(cid)
        expected = known[cid]
        positive = expected["expected_activation"]
        if (
            row.get("category") != expected["category"]
            or row.get("expected_activation") is not positive
            or row.get("received") is not True
            or row.get("final_verdict") != "passed"
        ):
            return False, "CHAT_CASE_FAILED_OR_UNREVIEWED"
        convo = row.get("conversation_sha256")
        response = row.get("response_sha256")
        if not _hashed(convo) or not _hashed(response) or convo in conversations:
            return False, "CHAT_CONVERSATION_EVIDENCE_INVALID_OR_DUPLICATED"
        conversations.add(convo)
        loaded = row.get("skill_loaded")
        if loaded is not positive or row.get("invocation_mode") != "automatic":
            return False, "CHAT_ACTIVATION_NOT_AS_EXPECTED"
        resource_uris = row.get("resource_uris")
        if (
            not isinstance(resource_uris, list)
            or not all(isinstance(uri, str) for uri in resource_uris)
            or len(set(resource_uris)) != len(resource_uris)
        ):
            return False, "CHAT_RESOURCES_NOT_VERIFIED"
        if positive:
            pid = row.get("plugin_id_sha256")
            if not _hashed(pid):
                return False, "CHAT_PLUGIN_INSTANCE_NOT_VERIFIED"
            instance_ids.add(pid)
            if not resource_uris or not all(
                isinstance(url, str) and url.startswith(PLUGIN_RESOURCE_PREFIX)
                for url in resource_uris
            ):
                return False, "CHAT_RESOURCE_READ_WRONG_PLUGIN"
            review = row.get("semantic_review")
            if not isinstance(review, dict) or review.get("verdict") != "pass":
                return False, "CHAT_INDEPENDENT_SEMANTIC_REVIEW_MISSING"
            if not _hashed(review.get("rationale_sha256")):
                return False, "CHAT_SEMANTIC_REVIEW_NOT_TRACEABLE"
        else:
            if resource_uris or row.get("plugin_id_sha256") is not None:
                return False, "CHAT_UNRELATED_TASK_FALSE_ACTIVATION"
    if len(instance_ids) != 1:
        return False, "CHAT_TESTED_MULTIPLE_PLUGIN_INSTANCES"
    if (
        summary.get("total") != len(known)
        or summary.get("observed") != len(known)
        or summary.get("passed") != len(known)
        or summary.get("full_qa_pass") is not True
    ):
        return False, "CHAT_SUMMARY_NOT_FULLY_PASSING"
    if any(
        type(summary.get(key)) is not int or summary[key] != 0
        for key in ("failed", "blocked", "inconclusive", "not_run")
    ):
        return False, "CHAT_NON_PASSING_SUMMARY_ITEMS"
    return True, "PASS"


def _validate_host_evidence(
    agents: object, source_revision: str, target: dict, suite: dict
) -> tuple[bool, str]:
    if not isinstance(agents, dict):
        return False, "P5_REAL_HOST_MODEL_EVIDENCE_MISSING"
    if agents.get("source_revision") != source_revision or agents.get("target") != target:
        return False, "P5_SOURCE_OR_TARGET_MISMATCH"
    hosts = agents.get("hosts")
    if not isinstance(hosts, dict) or set(hosts) != set(REQUIRED_AGENTS):
        return False, "P5_HOST_COVERAGE_INCOMPLETE"
    case_ids = {x["id"]: x for x in suite["cases"]}
    seen_host_evidence: set[str] = set()
    for name in REQUIRED_AGENTS:
        row = hosts[name]
        if not isinstance(row, dict):
            return False, f"P5_{name.upper()}_EVIDENCE_MISSING"
        version = row.get("agent_version")
        if not isinstance(version, str) or not re.fullmatch(
            r"[0-9]+\.[0-9]+\.[0-9]+(?:[-+][A-Za-z0-9._-]+)?", version
        ):
            return False, f"P5_{name.upper()}_INSTALLED_VERSION_NOT_RECORDED"
        if name == "claude_code" and version != target["api_version"]:
            return False, "P5_CLAUDE_CODE_TARGET_VERSION_NOT_MATCHED"
        if row.get("native_discovery") != "pass" or row.get("model_inference_status") != "pass":
            return False, f"P5_{name.upper()}_REAL_MODEL_TEST_NOT_PASSED"
        tests = row.get("tests")
        if not isinstance(tests, list) or len(tests) < 3:
            return False, f"P5_{name.upper()}_REAL_MODEL_SCENARIOS_INCOMPLETE"
        seen: set[str] = set()
        categories: set[str] = set()
        for item in tests:
            if not isinstance(item, dict) or item.get("category") not in REQUIRED_HOST_CASES:
                return False, f"P5_{name.upper()}_MODEL_TEST_MALFORMED"
            category = item["category"]
            cid = item.get("case_id")
            if (
                not isinstance(cid, str)
                or cid not in case_ids
                or case_ids[cid]["category"] != category
            ):
                return False, f"P5_{name.upper()}_MODEL_CASE_SCOPE_INVALID"
            if cid in seen:
                return False, f"P5_{name.upper()}_DUPLICATE_MODEL_CASE"
            seen.add(cid)
            categories.add(category)
            digest = item.get("evidence_sha256")
            if (
                item.get("real_inference") is not True
                or item.get("answer_verdict") != "pass"
                or item.get("skill_loaded") is not (category != "negative")
                or not _hashed(digest)
                or digest in seen_host_evidence
            ):
                return False, f"P5_{name.upper()}_MODEL_TEST_FAILED_OR_UNVERIFIED"
            seen_host_evidence.add(digest)
        if categories != set(REQUIRED_HOST_CASES):
            return False, f"P5_{name.upper()}_MISSING_POSITIVE_NEGATIVE_OR_BOUNDARY"
    return True, "PASS"


def _validate_account(account: object, version: str, zip_hash: str) -> tuple[bool, str]:
    if not isinstance(account, dict):
        return False, "CHATGPT_ACCOUNT_INSTALL_NOT_VERIFIED"
    if account.get("installed_plugin_version") != version:
        return False, "CHATGPT_INSTALLED_VERSION_MISMATCH"
    if account.get("chat_surface") != "chat":
        return False, "CHATGPT_NOT_TESTED_IN_ORDINARY_CHAT"
    if account.get("installed_enabled") is not True or account.get("skill_enabled") is not True:
        return False, "CHATGPT_ACCOUNT_PLUGIN_DISABLED_OR_MISSING"
    if account.get("installed_bundle_sha256") != zip_hash:
        return False, "CHATGPT_ACCOUNT_BUNDLE_CHECKSUM_MISMATCH"
    if account.get("rollback_verified") is not True or not _hashed(account.get("evidence_sha256")):
        return False, "CHATGPT_ROLLBACK_OR_ACCOUNT_AUDIT_UNVERIFIED"
    return True, "PASS"


def assess_stable_release(
    root: Path,
    dist: Path,
    *,
    chat: dict | None,
    agents: dict | None,
    account: dict | None,
) -> dict:
    """Return a minimal non-sensitive gate with actionable blocker codes."""
    root = Path(root)
    try:
        suite = json.loads((root / "evals/p4_cases.json").read_text(encoding="utf-8"))
        validate_suite(suite)
        package = validate_dist(Path(dist))
        manifest = json.loads(
            (Path(dist) / "manifests/build-manifest.json").read_text(encoding="utf-8")
        )
    except (OSError, ValueError, ReleaseValidationError) as exc:
        raise StableGateError(f"Invalid build or P4 evaluation package: {exc}") from exc
    target = manifest.get("target")
    expected = {
        "api_version": suite["target"]["claude_code_version"],
        "surface": suite["target"]["surface"],
    }
    if target != expected or manifest.get("approved_claims", 0) < 1:
        raise StableGateError("Release build is not scoped to approved P4 target knowledge")
    source = manifest.get("source_revision")
    if not isinstance(source, str) or not HEX40.fullmatch(source):
        raise StableGateError("Exact full Git source revision is required")
    version = manifest["package_version"]
    zip_hash = package["plugin_zip_sha256"]
    quality = [
        ("chat_46_case_quality", _validate_chat_evidence(chat, suite, version, source)),
        ("three_agent_model_validation", _validate_host_evidence(agents, source, target, suite)),
        ("account_install_rollback", _validate_account(account, version, zip_hash)),
    ]
    checks = {"package_integrity": "pass"}
    blockers = []
    for key, (good, reason) in quality:
        checks[key] = "pass" if good else "fail"
        if not good:
            blockers.append(reason)
    eligible = not blockers
    return {
        "schema_version": 1,
        "status": "READY_FOR_STABLE_RELEASE" if eligible else "STABLE_RELEASE_BLOCKED",
        "eligible_for_stable_release": eligible,
        "target": target,
        "package_version": version,
        "source_revision": source,
        "plugin_zip_sha256": zip_hash,
        "checks": checks,
        "blockers": blockers,
        "note": (
            "Eligibility assesses supplied evidence. It neither invokes models nor "
            "publishes a release; externally fabricated evidence cannot be "
            "proven authentic by an offline report alone."
        ),
    }
