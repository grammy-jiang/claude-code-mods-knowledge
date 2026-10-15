"""Deterministic private, pre-release assembly with explicit model-runtime caveats.

This is not a public Plugins Directory submission or a verified ChatGPT Chat mode run.
No LLM or network access is performed here.
"""

from __future__ import annotations

import hashlib
import io
import json
import re
import tempfile
import zipfile
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

TAG_PATTERN = re.compile(r"v[0-9]+\.[0-9]+\.[0-9]+-(?:rc|beta)\.[0-9]+\Z")
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
        if report.get("static_tests") != "pass":
            raise ReleaseBuildError(f"P5 host {device}: static verification must pass for release")
        if report.get("token_based_agent_test") != "not_run":
            raise ReleaseBuildError("Token-based Claude/Codex/host agent tests were not run")
        if not isinstance(report.get("source_revision"), str) or not SHA_PATTERN.fullmatch(
            report["source_revision"]
        ):
            raise ReleaseBuildError(f"P5 host {device}: invalid source revision")
        for field in ("plugin_bundle_sha256", "skill_bundle_sha256"):
            sha = report.get(field)
            if not isinstance(sha, str) or not re.fullmatch(r"[a-f0-9]{64}", sha):
                raise ReleaseBuildError(f"P5 host {device}: missing/invalid {field}")
        if any(
            type(report.get(field)) is not int or report[field] < 1
            for field in ("files_verified", "resource_checks")
        ):
            raise ReleaseBuildError(f"P5 host {device}: incomplete resource/package verification")
        if type(report.get("pytest_passed")) is not int or report["pytest_passed"] < 1:
            raise ReleaseBuildError(f"P5 host {device}: missing test result")
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
            "Incomplete Chat-mode verification requires a -rc.N or -beta.N prerelease tag"
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
    for host_id, report in host_matrix["platforms"].items():
        if report["source_revision"] != source_revision:
            raise ReleaseBuildError(f"P5 host {host_id}: source revision differs from release")
        if report["plugin_bundle_sha256"] != dist_meta["plugin_zip_sha256"]:
            raise ReleaseBuildError(f"P5 host {host_id}: plugin ZIP SHA differs from release")
        if report["skill_bundle_sha256"] != dist_meta["skill_zip_sha256"]:
            raise ReleaseBuildError(f"P5 host {host_id}: Skill ZIP SHA differs from release")
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
    p4_expected = len(suite["cases"])
    for host_id, report in host_matrix["platforms"].items():
        if report["files_verified"] != dist_meta["artifacts_verified"]:
            raise ReleaseBuildError(f"P5 host {host_id}: compiled artifact count differs")
        if report["resource_checks"] != p4_expected:
            raise ReleaseBuildError(f"P5 host {host_id}: evaluated scenario count differs")
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


def _adapter_zip(dist: Path, host: str) -> bytes:
    """Build an installable project-layout adapter archive with fixed ZIP metadata."""
    if host not in ("claude-code", "codex", "pi"):
        raise ReleaseBuildError("Unsupported Agent Skill adapter host")
    relative_root = (
        ".claude/skills/claude-code-mods-development"
        if host == "claude-code"
        else ".agents/skills/claude-code-mods-development"
    )
    source = dist / host / relative_root
    if source.is_symlink() or not source.is_dir():
        raise ReleaseBuildError(f"Missing generated adapter Skill directory: {host}")
    paths = sorted(p for p in source.rglob("*") if p.is_file())
    if len(paths) != 9 or any(p.is_symlink() for p in paths):
        raise ReleaseBuildError(f"Unexpected generated Skill layout for {host}")
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
        for path in paths:
            logical = f"{relative_root}/{path.relative_to(source).as_posix()}"
            info = zipfile.ZipInfo(logical)
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.create_system = 3
            info.external_attr = 0o644 << 16
            info.compress_type = zipfile.ZIP_STORED
            archive.writestr(info, path.read_bytes())
    return output.getvalue()


def _release_notes(tag: str, status: str, matrix: dict, manifest: dict) -> bytes:
    """Human-readable release note; no user conversations or private host data."""
    chat = matrix["chatgpt"]
    items = chat.get("chat_cases", [])
    passed = sum(c.get("answer_quality") == "pass" for c in items)
    failed = sum(c.get("answer_quality") == "fail" for c in items)
    note = f"""# Claude Code Mods Knowledge — {tag} Beta

**Status:** {status}. Private pre-release, **not** a general availability claim.

This release contains a ChatGPT **Chat mode** Skills-only Plugin, the generic
Agent Skill ZIP and separate project-layout Skill ZIPs for Claude Code, Codex
and Pi Agent, all generated from one reviewed Single Source of Truth.

**Target:** Claude Code {manifest["target"]["api_version"]} ({manifest["target"]["surface"]}).
**Approved Claims:** {manifest["approved_claims"]}.
**Candidates not published:** {manifest["candidate_claims_excluded"]}.
**Deprecated Claims not published:** {manifest.get("deprecated_claims_excluded", 0)}.

## ChatGPT Chat mode evidence

- Account plugin activation status: {chat.get("chat_skill_activation", "not_run")}
- Chat-mode answer qualification: {chat.get("chat_answer_evaluation", "not_run")}
- Tested beta-version cases: {len(items)}; structurally passing: {passed}; failing: {failed}
- Full suite: 46 scenarios; only separately observed cases count as tested.
- Negative and historical/unsupported-version scenarios need independent review.
- Installed plugin presence does **not** guarantee automatic triggering on every chat.

## Skill distribution

- `claude-code-mods-knowledge-<version>.zip`: ChatGPT Plugin (`plugin.json` + Skill)
- `claude-code-mods-development-<version>.zip`: standalone portable Skill
- `claude-code-mods-development-claude-code-<version>.zip`: `.claude/skills` layout
- `claude-code-mods-development-codex-<version>.zip`: `.agents/skills` layout
- `claude-code-mods-development-pi-<version>.zip`: `.agents/skills` layout

Verify `SHA256SUMS` before installing. Consult `RELEASE.json`,
`SOURCE-SBOM.json`, `P4-STATIC.json` and `P5-HOST-MATRIX.json` for source
versions, review status, tested platforms and unverified limits.

No Claude Code/Codex model was called while local token quotas were exhausted.
Actual Claude Code, Codex and Pi Agent model loading/answer tests remain pending.
This beta should not be used as proof that unreviewed future Mods APIs are safe.
"""
    return note.encode("utf-8")


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
    if (
        p4["resource_checks_passed"] != p4["cases_total"]
        or p4["cases_total"] < 1
        or p4["host_runtime_cases_passed"] != 0
    ):
        raise ReleaseBuildError("Unexpected P4 resource or ChatGPT runtime grading status")
    version = tag.removeprefix("v")
    status = (
        "beta_chat_mode_partially_verified"
        if host_matrix["chatgpt"].get("chat_cases")
        else "prerelease_host_runtime_unverified"
    )
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
    for host in ("claude-code", "codex", "pi"):
        files[f"claude-code-mods-development-{host}-{version}.zip"] = _adapter_zip(dist, host)
    files["RELEASE-NOTES.md"] = _release_notes(tag, status, host_matrix, manifest)
    release = {
        "schema_version": 1,
        "tag": tag,
        "version": version,
        "status": status,
        "source_revision": source_revision,
        "target": manifest["target"],
        "approved_claims": len(approved),
        "excluded_candidates": manifest["candidate_claims_excluded"],
        "excluded_deprecated": manifest.get("deprecated_claims_excluded", 0),
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
    if release.get("status") not in (
        "prerelease_host_runtime_unverified",
        "beta_chat_mode_partially_verified",
    ):
        raise ReleaseBuildError("Missing safe prerelease/Beta status")
    if (release["status"] == "beta_chat_mode_partially_verified") != bool(
        release.get("p5", {}).get("chatgpt", {}).get("chat_cases")
    ):
        raise ReleaseBuildError("Beta Chat-mode evidence status disagrees with the case matrix")
    _validate_matrix(release.get("p5"))
    try:
        json.loads(actual["SOURCE-SBOM.json"].read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ReleaseBuildError("Missing or unreadable source SBOM") from exc
    version = release.get("version")
    plugin_file = actual.get(f"claude-code-mods-knowledge-{version}.zip")
    skill_file = actual.get(f"claude-code-mods-development-{version}.zip")
    if not plugin_file or not skill_file:
        raise ReleaseBuildError("Missing release version's plugin/skill archives")
    expected_plugin_sha = _sha(plugin_file.read_bytes())
    expected_skill_sha = _sha(skill_file.read_bytes())
    for host_id, report in release["p5"]["platforms"].items():
        if report["files_verified"] != release.get("compiler", {}).get("artifact_count"):
            raise ReleaseBuildError(f"P5 host {host_id}: release artifact count mismatch")
        if report["resource_checks"] != release.get("p4", {}).get("cases_total"):
            raise ReleaseBuildError(f"P5 host {host_id}: release scenario count mismatch")
        if report["source_revision"] != release.get("source_revision"):
            raise ReleaseBuildError(f"P5 host {host_id}: release source SHA mismatch")
        if report["plugin_bundle_sha256"] != expected_plugin_sha:
            raise ReleaseBuildError(f"P5 host {host_id}: release plugin ZIP mismatch")
        if report["skill_bundle_sha256"] != expected_skill_sha:
            raise ReleaseBuildError(f"P5 host {host_id}: release Skill ZIP mismatch")
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
    # Adapter archives must be exact copies of the generic Skill under the
    # intended host path; no scripts, extra files or symlinks can be introduced.
    from .release_validation import _read_checked_archive

    generic = _read_checked_archive(
        actual[f"claude-code-mods-development-{version}.zip"].read_bytes()
    )
    core_prefix = "claude-code-mods-development/"
    common = {
        path[len(core_prefix) :]: raw
        for path, raw in generic.items()
        if path.startswith(core_prefix)
    }
    if len(common) != 9:
        raise ReleaseBuildError("Unexpected generic Skill archive contents")
    for host in ("claude-code", "codex", "pi"):
        archive_name = f"claude-code-mods-development-{host}-{version}.zip"
        if archive_name not in actual:
            raise ReleaseBuildError(f"Missing Agent adapter ZIP: {archive_name}")
        host_root = (
            ".claude/skills/claude-code-mods-development/"
            if host == "claude-code"
            else ".agents/skills/claude-code-mods-development/"
        )
        members = _read_checked_archive(actual[archive_name].read_bytes())
        expected = {host_root + name: data for name, data in common.items()}
        if members != expected:
            raise ReleaseBuildError(f"Agent adapter archive differs from approved Skill: {host}")
    if "Beta" not in actual["RELEASE-NOTES.md"].read_text(encoding="utf-8"):
        raise ReleaseBuildError("Release notes do not identify this as Beta")
    return release
