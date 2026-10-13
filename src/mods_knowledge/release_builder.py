"""Deterministic private, pre-release assembly with explicit model-runtime caveats.

This is not a public Plugins Directory submission or a verified ChatGPT Chat mode run.
No LLM or network access is performed here.
"""

from __future__ import annotations

import hashlib
import json
import re
import tempfile
from pathlib import Path

from .claims import approved_claims, load_claims
from .compiler import CompilerError, compile_knowledge
from .errors import ClaimError, RegistryError
from .evaluator import EvaluationError, evaluate_suite
from .registry import load_registry
from .release_validation import (
    ReleaseValidationError,
    validate_bundle,
    validate_dist,
)

TAG_PATTERN = re.compile(r"v[0-9]+\.[0-9]+\.[0-9]+-rc\.[0-9]+\Z")
SHA_PATTERN = re.compile(r"[a-f0-9]{40}\Z")


class ReleaseBuildError(ValueError):
    """A private release candidate is incomplete, ambiguous or unverifiable."""


def _serialized(payload: object) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode(
        "utf-8"
    )


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _validate_matrix(data: dict) -> dict:
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ReleaseBuildError("P5 host matrix version is missing/unsupported")
    platforms = data.get("platforms")
    if not isinstance(platforms, dict) or set(platforms) != {"macbook", "raspberrypi", "sextant"}:
        raise ReleaseBuildError("Three independent host entries are required")
    for device, report in platforms.items():
        if not isinstance(report, dict):
            raise ReleaseBuildError(f"Invalid P5 host report for {device}")
        if report.get("static_tests") not in ("pass", "not_run", "failed"):
            raise ReleaseBuildError(f"Invalid static P5 result for {device}")
        if report.get("token_based_agent_test") != "not_run":
            raise ReleaseBuildError("Token-based Claude/Codex/host agent tests were not run")
    chatgpt = data.get("chatgpt")
    if not isinstance(chatgpt, dict):
        raise ReleaseBuildError("P5 ChatGPT evidence is missing")
    activation = chatgpt.get("chat_skill_activation")
    answer = chatgpt.get("chat_answer_evaluation")
    if activation not in ("not_run", "pass", "fail", "inconclusive"):
        raise ReleaseBuildError("Unrecognized Chat mode activation status")
    if answer not in ("not_run", "partial", "pass", "fail", "inconclusive"):
        raise ReleaseBuildError("Unrecognized Chat mode answer evaluation")
    cases = chatgpt.get("chat_cases", [])
    if not isinstance(cases, list):
        raise ReleaseBuildError("Chat mode evidence cases must be a list")
    if activation == "not_run":
        if cases or answer != "not_run":
            raise ReleaseBuildError("Unobserved Chat mode cannot claim answer/activation evidence")
    else:
        if not cases:
            raise ReleaseBuildError("Chat mode activation requires actual case evidence")
        seen = set()
        for case in cases:
            if not isinstance(case, dict):
                raise ReleaseBuildError("Malformed Chat mode case evidence")
            cid = case.get("case_id")
            if (
                not isinstance(cid, str)
                or cid in seen
                or not re.fullmatch(r"[A-Z][A-Z0-9_-]{3,60}", cid)
            ):
                raise ReleaseBuildError("Invalid/duplicate Chat mode case identifier")
            seen.add(cid)
            for key in ("conversation_sha256", "response_sha256"):
                if not isinstance(case.get(key), str) or not re.fullmatch(
                    r"[a-f0-9]{64}", case[key]
                ):
                    raise ReleaseBuildError(
                        "Chat mode evidence requires hashed conversation/response"
                    )
            if not isinstance(case.get("plugin_version"), str):
                raise ReleaseBuildError("Missing Chat mode plugin version")
            if case.get("answer_quality") not in (
                "pass",
                "fail",
                "partial",
                "not_run",
                "inconclusive",
            ):
                raise ReleaseBuildError("Invalid Chat mode answer quality result")
            if not isinstance(case.get("notes"), str):
                raise ReleaseBuildError("Missing Chat mode review note")
            resources = case.get("resource_uris")
            if not isinstance(resources, list) or len(resources) != len(set(resources)):
                raise ReleaseBuildError("Malformed Chat mode resource read list")
            if any(
                not isinstance(uri, str)
                or not uri.startswith(
                    "skills://plugins/claude-code-mods-knowledge/claude-code-mods-development"
                )
                for uri in resources
            ):
                raise ReleaseBuildError("Chat mode resource points to another plugin")
            if case.get("skill_loaded") is True and not resources:
                raise ReleaseBuildError("Claimed Skill activation has no read-resource trace")
        if activation == "pass" and not any(c.get("skill_loaded") for c in cases):
            raise ReleaseBuildError(
                "Chat mode activation PASS requires a Skill read_resource trace"
            )
        if answer == "pass" and (
            len(cases) < 46 or not all(c.get("answer_quality") == "pass" for c in cases)
        ):
            raise ReleaseBuildError("Full Chat mode answer PASS requires all 46 P4 cases verified")
    if chatgpt.get("marketplace_source") not in ("not_prepared", "prepared", "installed_cache"):
        raise ReleaseBuildError("Unknown local ChatGPT marketplace status")
    if chatgpt.get("local_package_cache") not in ("not_verified", "installed_cache"):
        raise ReleaseBuildError("Unknown ChatGPT plugin cache status")
    return data


def _source_sbom(root: Path, approved: list[dict]) -> dict:
    sources = load_registry(root / "sources/registry.json")
    used: dict[str, dict] = {}
    for claim in approved:
        for item in claim["evidence"]:
            original = sources[item["source_id"]]
            if original["trust_layer"] not in ("L0", "L1"):
                raise ReleaseBuildError("Non-official sources cannot establish release knowledge")
            used[item["source_id"]] = {
                "source_id": original["source_id"],
                "url": original["url"],
                "trust_layer": original["trust_layer"],
                "html_sha256": original["snapshot"]["sha256"],
                "review_status": original["review_state"],
            }
    return {
        "schema_version": 1,
        "purpose": "Source-provenance inventory for an offline Skills-only plugin",
        "approved_claim_count": len(approved),
        "approved_claim_ids": sorted(c["claim_id"] for c in approved),
        "sources": sorted(used.values(), key=lambda item: item["source_id"]),
    }


def _validate_release_inputs(
    root: Path, dist: Path, source_revision: str, tag: str, host_matrix: dict
) -> tuple[dict, dict, list[dict], dict[str, bytes]]:
    if not SHA_PATTERN.fullmatch(source_revision):
        raise ReleaseBuildError("Release source revision must be a full lowercase Git SHA")
    if not TAG_PATTERN.fullmatch(tag):
        raise ReleaseBuildError(
            "Unverified ChatGPT runtime requires an explicit -rc.N prerelease tag"
        )
    _validate_matrix(host_matrix)
    try:
        dist_meta = validate_dist(dist)
        manifest = json.loads((dist / "manifests/build-manifest.json").read_text())
    except (ReleaseValidationError, OSError, ValueError) as exc:
        raise ReleaseBuildError(f"Cannot verify release compiler output: {exc}") from exc
    version = tag.removeprefix("v")
    if manifest["package_version"] != version:
        raise ReleaseBuildError("Git release version must match the packaged plugin version")
    if manifest["source_revision"] != source_revision:
        raise ReleaseBuildError("Release source revision differs from compiler manifest revision")
    for case in host_matrix["chatgpt"].get("chat_cases", []):
        if case["plugin_version"] != version:
            raise ReleaseBuildError(
                "Chat mode tested plugin version differs from the release version"
            )
    try:
        suite = json.loads((root / "evals/p4_cases.json").read_text(encoding="utf-8"))
        suite_target = suite["target"]
        expected_target = {
            "api_version": suite_target["claude_code_version"],
            "surface": suite_target["surface"],
        }
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise ReleaseBuildError("Cannot verify target against the P4 evaluated suite") from exc
    if manifest.get("target") != expected_target:
        raise ReleaseBuildError("Release target must match the explicitly evaluated P4 scope")
    try:
        fresh = compile_knowledge(
            root,
            api_version=expected_target["api_version"],
            surface=expected_target["surface"],
            package_version=version,
            knowledge_version=manifest["knowledge_version"],
            source_revision=source_revision,
        )
        registry = load_registry(root / "sources/registry.json")
        claims = load_claims(
            root / "claims", registry, root / "sources/snapshots", root / "decisions"
        )
        approved = approved_claims(
            claims, expected_target["api_version"], expected_target["surface"]
        )
    except (CompilerError, ClaimError, RegistryError, OSError, ValueError) as exc:
        raise ReleaseBuildError(f"Cannot verify release against SSOT inputs: {exc}") from exc
    for file_name, content in fresh.items():
        if not (dist / file_name).is_file() or (dist / file_name).read_bytes() != content:
            raise ReleaseBuildError("Dist cannot be reproduced from reviewed SSOT source inputs")
    return dist_meta, manifest, approved, fresh


def build_release(
    root: Path, dist: Path, destination: Path, *, source_revision: str, tag: str, host_matrix: dict
) -> dict:
    """Produce idempotent, versioned private release files without host-pass fiction."""
    root, dist, destination = Path(root), Path(dist), Path(destination)
    dist_info, manifest, approved, _ = _validate_release_inputs(
        root, dist, source_revision, tag, host_matrix
    )
    try:
        p4 = evaluate_suite(root, root / "evals/p4_cases.json")
    except (EvaluationError, OSError) as exc:
        raise ReleaseBuildError(f"P4 offline resource evaluation failed: {exc}") from exc
    if p4["resource_checks_passed"] != 46 or p4["host_runtime_cases_passed"] != 0:
        raise ReleaseBuildError("Unexpected P4 resource or ChatGPT runtime grading status")
    version = tag.removeprefix("v")
    files: dict[str, bytes] = {
        f"claude-code-mods-knowledge-{version}.zip": (
            dist / f"packages/claude-code-mods-knowledge-{version}.zip"
        ).read_bytes(),
        f"claude-code-mods-development-{version}.zip": (
            dist / f"packages/claude-code-mods-development-{version}.zip"
        ).read_bytes(),
        "SOURCE-SBOM.json": _serialized(_source_sbom(root, approved)),
        "P4-STATIC.json": _serialized(p4),
        "P5-HOST-MATRIX.json": _serialized(host_matrix),
    }
    release = {
        "schema_version": 1,
        "tag": tag,
        "version": version,
        "status": "prerelease_host_runtime_unverified",
        "source_revision": source_revision,
        "target": manifest["target"],
        "approved_claims": len(approved),
        "excluded_candidates": manifest["candidate_claims_excluded"],
        "p4": {
            "cases_total": p4["cases_total"],
            "resource_checks_passed": p4["resource_checks_passed"],
            "host_runtime_cases_passed": p4["host_runtime_cases_passed"],
            "host_runtime_cases_pending": p4["host_runtime_cases_pending"],
        },
        "p5": host_matrix,
        "compiler": {
            "compiler_version": manifest["compiler_version"],
            "knowledge_version": manifest["knowledge_version"],
            "package_version": manifest["package_version"],
            "input_count": len(manifest["input_sha256"]),
            "artifact_count": dist_info["artifacts_verified"],
        },
        "component_sha256": {name: _sha(raw) for name, raw in sorted(files.items())},
        "limits": (
            "Local package tests alone do not prove ChatGPT Chat mode behavior; "
            "individual Chat read_resource traces and response checks are recorded "
            "separately in P5 case evidence, and untested P4 cases remain pending. "
            "No Claude/Codex model was called while local quotas were unavailable."
        ),
    }
    files["RELEASE.json"] = _serialized(release)
    files["SHA256SUMS"] = "".join(
        f"{_sha(raw)}  {name}\n" for name, raw in sorted(files.items())
    ).encode("utf-8")
    if destination.is_symlink():
        raise ReleaseBuildError("Cannot write private release through symlink output path")
    if destination.exists():
        existing = {p.name: p.read_bytes() for p in destination.iterdir() if p.is_file()}
        if existing == files:
            return release
        raise ReleaseBuildError("Existing different release cannot be overwritten")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".mods-release-", dir=destination.parent) as tmp:
        stage = Path(tmp) / "release"
        stage.mkdir()
        for name, content in files.items():
            (stage / name).write_bytes(content)
        stage.rename(destination)
    verify_release(destination)
    return release


def verify_release(destination: Path) -> dict:
    """Offline release-level checksum, metadata and package integrity checks."""
    destination = Path(destination)
    if not destination.is_dir() or destination.is_symlink():
        raise ReleaseBuildError("Release directory does not exist or is unsafe")
    checks = destination / "SHA256SUMS"
    meta = destination / "RELEASE.json"
    if not checks.is_file() or not meta.is_file():
        raise ReleaseBuildError("Release checksums/manifest are missing")
    actual = {p.name: p for p in destination.iterdir() if p.is_file() or p.is_symlink()}
    checksum_lines = checks.read_text(encoding="utf-8").splitlines()
    parsed = {}
    for line in checksum_lines:
        match = re.fullmatch(r"([a-f0-9]{64})  ([a-zA-Z0-9._-]+)", line)
        if not match or match.group(2) in parsed:
            raise ReleaseBuildError("Invalid or duplicate SHA256SUMS entries")
        parsed[match.group(2)] = match.group(1)
    if set(actual) != set(parsed) | {"SHA256SUMS"}:
        raise ReleaseBuildError("Unexpected or missing private release files")
    for name, expected in parsed.items():
        file = actual[name]
        if file.is_symlink() or _sha(file.read_bytes()) != expected:
            raise ReleaseBuildError(f"Release checksum/SHA mismatch for {name}")
    try:
        release = json.loads(meta.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise ReleaseBuildError("Invalid RELEASE.json") from exc
    if release.get("status") != "prerelease_host_runtime_unverified":
        raise ReleaseBuildError("Missing required runtime-unverified prerelease status")
    _validate_matrix(release.get("p5"))
    matrix_raw = actual["P5-HOST-MATRIX.json"].read_bytes()
    if _serialized(release["p5"]) != matrix_raw:
        raise ReleaseBuildError("Chat mode P5 host matrix differs from embedded release metadata")
    for name, hash_ in release.get("component_sha256", {}).items():
        if name not in actual or _sha(actual[name].read_bytes()) != hash_:
            raise ReleaseBuildError("Release component SHA mismatch")
    version = release["version"]
    try:
        sbom = json.loads(actual["SOURCE-SBOM.json"].read_text(encoding="utf-8"))
    except (KeyError, OSError, ValueError) as exc:
        raise ReleaseBuildError("Missing or invalid release source SBOM") from exc
    claim_ids = sbom.get("approved_claim_ids")
    if not isinstance(claim_ids, list) or len(set(claim_ids)) != len(claim_ids):
        raise ReleaseBuildError("Invalid approved Claim IDs in source SBOM")
    if len(claim_ids) != release.get("approved_claims"):
        raise ReleaseBuildError("Release/source SBOM approved claim count mismatch")
    allowed_claim_ids = set(claim_ids)
    for prefix in ("claude-code-mods-knowledge", "claude-code-mods-development"):
        name = f"{prefix}-{version}.zip"
        if name not in actual:
            raise ReleaseBuildError(f"Missing release ZIP: {name}")
        validate_bundle(
            actual[name].read_bytes(),
            allowed_claim_ids=allowed_claim_ids,
            target=release.get("target"),
        )
    return release
