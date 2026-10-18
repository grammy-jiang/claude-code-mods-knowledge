"""Command-line interface for the initial, explicitly unverified source knowledge registry."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from collections import Counter
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from .account_archive import verify_account_download
from .answer_lint import lint_mods_answer
from .chat_mode_compare import ComparisonError, compare_chat_versions
from .chat_mode_report import ChatReportError, aggregate_chat_mode_results
from .claims import approved_claims, load_claims
from .collector import fetch_document
from .compiler import CompilerError, build_artifacts
from .decisions import transition_claim
from .errors import ClaimError, CollectionError, RegistryError
from .evaluator import EvaluationError, evaluate_suite
from .personal_marketplace import MarketplaceError, stage_personal_plugin
from .registry import OFFICIAL_LAYERS, eligible_official_sources, load_registry
from .release_builder import ReleaseBuildError, build_release, verify_release
from .release_validation import (
    MAX_ARCHIVE_SIZE,
    ReleaseValidationError,
    validate_compiled_skill_format,
    validate_dist,
)
from .stable_gate import StableGateError, assess_stable_release
from .storage import record_observation, verify_snapshot_store
from .task_evidence import EvidenceSelectionError, render_evidence_pack, select_task_evidence

DEFAULT_ROOT = Path(__file__).resolve().parents[2]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mods-knowledge",
        description="Read-only validation and explicit official documentation fingerprints",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=DEFAULT_ROOT,
        help="Repository checkout directory (default: this checkout)",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser(
        "validate", help="Validate 91 sources and their provenance without network access"
    )
    listed = sub.add_parser("list", help="List source IDs, trust layers, titles and URLs")
    listed.add_argument("--layer", choices=("L0", "L1", "L2", "R", "C", "H"), default=None)
    sub.add_parser("verify", help="Verify local captured-metadata hashes without network access")
    collect = sub.add_parser(
        "collect", help="Explicitly fetch and fingerprint first-party docs only"
    )
    selection = collect.add_mutually_exclusive_group(required=True)
    selection.add_argument("--source", action="append", metavar="M001")
    selection.add_argument("--all-official", action="store_true")
    collect.add_argument("--limit", type=int, metavar="N")
    collect.add_argument("--timeout", type=float, default=12.0)
    collect.add_argument("--max-bytes", type=int, default=2_000_000)

    claims = sub.add_parser("claims", help="Audit atomic, source-bound knowledge Claims")
    actions = claims.add_subparsers(dest="claims_command", required=True)
    actions.add_parser("validate", help="Validate Claim schema, evidence and decisions offline")
    actions.add_parser("list", help="List all Claim states, including unapproved candidates")
    show = actions.add_parser("show", help="Inspect one Claim without promoting it")
    show.add_argument("claim_id")
    query = actions.add_parser("query", help="Return only approved compatible current Claims")
    query.add_argument("--version", required=True)
    query.add_argument("--surface", choices=("cli", "desktop", "vscode", "headless"), required=True)
    transition = actions.add_parser("transition", help="Record an explicit audited state decision")
    transition.add_argument("claim_id")
    transition.add_argument(
        "--to", choices=("reviewed", "approved", "rejected", "deprecated"), required=True
    )
    transition.add_argument("--actor", required=True)
    transition.add_argument("--reason", required=True)

    build = sub.add_parser(
        "build", help="Compile approved version-scoped knowledge to four offline Skill packages"
    )
    build.add_argument("--api-version", required=True)
    build.add_argument("--surface", choices=("cli", "desktop", "vscode", "headless"), required=True)
    build.add_argument("--knowledge-version", default="0.1.0")
    build.add_argument("--package-version", default="0.1.0")
    build.add_argument("--source-revision", default=None)
    eval_parser = sub.add_parser(
        "eval", help="Run offline P4 resource coverage; never claim model/ChatGPT host pass"
    )
    eval_parser.add_argument("--suite", default="evals/p4_cases.json")
    eval_parser.add_argument("--report", type=Path, default=None)
    report_parser = sub.add_parser(
        "chat-report", help="Aggregate sanitized real Chat-mode QA; never invent a model pass"
    )
    report_parser.add_argument("--suite", type=Path, default=None)
    report_parser.add_argument("--records", type=Path, required=True)
    report_parser.add_argument("--manual-reviews", type=Path, default=None)
    report_parser.add_argument("--blocked", action="append", default=[])
    report_parser.add_argument("--plugin-version", required=True)
    report_parser.add_argument("--source-revision", required=True)
    report_parser.add_argument("--out", type=Path, required=True)
    comparison = sub.add_parser(
        "chat-compare", help="Compare two sanitized real Chat-mode version tests"
    )
    comparison.add_argument("--before", type=Path, required=True)
    comparison.add_argument("--after", type=Path, required=True)
    comparison.add_argument("--before-version", required=True)
    comparison.add_argument("--after-version", required=True)
    comparison.add_argument("--out", type=Path, required=True)
    evidence = sub.add_parser(
        "evidence-select",
        help="Select approved task-specific evidence from SSOT; no LLM or HTTP calls",
    )
    evidence.add_argument("--prompt-file", type=Path, required=True)
    evidence.add_argument("--out", type=Path, required=True)
    evidence.add_argument("--version", default="2.1.302")
    evidence.add_argument(
        "--surface", default="cli", choices=("cli", "desktop", "vscode", "headless")
    )

    answer_lint = sub.add_parser(
        "answer-lint", help="Extract only known Mods code risks from a private reply"
    )
    answer_lint.add_argument("--answer-file", type=Path, required=True)
    answer_lint.add_argument("--case-id", required=True)
    answer_lint.add_argument("--out", type=Path, required=True)
    package_check = sub.add_parser(
        "package-check",
        help="Verify SHA-256, ZIP structure and references without loading any model",
    )
    package_check.add_argument("--dist", type=Path, required=True)
    skills_lint = sub.add_parser(
        "skills-lint",
        help="Fail-closed real YAML parsing of all generated host Skills and both ZIPs",
    )
    skills_lint.add_argument("--dist", type=Path, required=True)
    marketplace = sub.add_parser(
        "marketplace-stage",
        help="Prepare a ChatGPT Desktop personal marketplace; dry-run unless --apply",
    )
    marketplace.add_argument("--dist", type=Path, required=True)
    marketplace.add_argument("--home", type=Path, default=Path.home())
    marketplace.add_argument("--apply", action="store_true")
    release = sub.add_parser("release", help="Prepare a provenance-bound private release candidate")
    release.add_argument("--dist", type=Path, required=True)
    release.add_argument("--out", type=Path, required=True)
    release.add_argument("--source-revision", required=True)
    release.add_argument("--tag", required=True)
    release.add_argument("--host-matrix", type=Path, required=True)
    release_check = sub.add_parser("release-verify", help="Offline verify release ZIP and SHA-256")
    release_check.add_argument("--dir", type=Path, required=True)
    account_archive = sub.add_parser(
        "account-archive-check",
        help="Compare reviewed Plugin ZIP with an account-downloaded normalized ZIP offline",
    )
    account_archive.add_argument("--uploaded", type=Path, required=True)
    account_archive.add_argument("--downloaded", type=Path, required=True)
    account_archive.add_argument("--out", type=Path)
    readiness = sub.add_parser(
        "stable-readiness",
        help="Fail-closed P4/P5/P6 report; never releases or runs models",
    )
    readiness.add_argument("--dist", type=Path, required=True)
    readiness.add_argument("--chat-report", type=Path)
    readiness.add_argument("--agent-report", type=Path)
    readiness.add_argument("--account-report", type=Path)
    readiness.add_argument(
        "--account-download-zip",
        type=Path,
        help="Private ChatGPT-normalized account ZIP; must match the reviewed dist Plugin bytes",
    )
    readiness.add_argument("--out", type=Path, required=True)
    readiness.add_argument("--require-ready", action="store_true")
    return parser


def _print_json(data: object) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "account-archive-check":
            try:
                uploaded = args.uploaded.read_bytes()
                downloaded = args.downloaded.read_bytes()
            except OSError as exc:
                raise ReleaseValidationError("Unable to read supplied Plugin ZIP files") from exc
            report = verify_account_download(uploaded, downloaded)
            if args.out is not None:
                args.out.parent.mkdir(parents=True, exist_ok=True)
                args.out.write_text(
                    json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                    encoding="utf-8",
                )
            _print_json(report)
            return 0
        if args.command == "stable-readiness":

            def load_optional(path: Path | None) -> dict | None:
                if path is None:
                    return None
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, ValueError) as exc:
                    raise StableGateError("Invalid or missing release-gate evidence file") from exc
                if not isinstance(data, dict):
                    raise StableGateError("Release-gate evidence must be a JSON object")
                return data

            account_zip = None
            if args.account_download_zip is not None:
                try:
                    length = args.account_download_zip.stat().st_size
                    if not 0 < length <= MAX_ARCHIVE_SIZE:
                        raise StableGateError("Unsupported account download size")
                    account_zip = args.account_download_zip.read_bytes()
                except OSError as exc:
                    raise StableGateError("Account download file not readable") from exc
            report = assess_stable_release(
                args.root,
                args.dist,
                chat=load_optional(args.chat_report),
                agents=load_optional(args.agent_report),
                account=load_optional(args.account_report),
                account_download_zip=account_zip,
            )
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(
                json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                encoding="utf-8",
            )
            _print_json(report)
            return 3 if args.require_ready and not report["eligible_for_stable_release"] else 0
        if args.command == "evidence-select":
            if not args.prompt_file.is_file() or args.prompt_file.is_symlink():
                raise EvidenceSelectionError("Required private prompt file missing or unsafe")
            if args.prompt_file.stat().st_size > 48_000:
                raise EvidenceSelectionError("Unbounded task prompt file")
            if args.out.is_symlink() or args.out.exists():
                raise EvidenceSelectionError("Refusing to overwrite or follow output file")
            try:
                content = args.prompt_file.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                raise EvidenceSelectionError("Unreadable or invalid private task prompt") from exc
            reg = load_registry(args.root / "sources/registry.json")
            catalog = load_claims(
                args.root / "claims",
                reg,
                args.root / "sources/snapshots",
                args.root / "decisions",
            )
            pack = select_task_evidence(
                content, catalog, version=args.version, surface=args.surface
            )
            if not pack["ready"]:
                _print_json(
                    {
                        "status": "withheld",
                        "reason": pack["reason"],
                        "intent": pack["intent"],
                        "inference_requested": False,
                        "exact_source_claims_selected": 0,
                    }
                )
                return 3
            rendered = render_evidence_pack(pack).encode("utf-8")
            args.out.parent.mkdir(parents=True, exist_ok=True)
            # Exclusive creation and owner-only data, never replace a prior
            # audit or leak private prompts through a subprocess argument.
            descriptor = os.open(str(args.out), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(descriptor, "wb") as output:
                output.write(rendered)
            _print_json(
                {
                    "status": "selected",
                    "intent": "mods",
                    "approved_claim_ids": [c["claim_id"] for c in pack["claims"]],
                    "approved_source_sha256": hashlib.sha256(rendered).hexdigest(),
                    "inference_requested": False,
                    "semantic_correctness_verified": False,
                }
            )
            return 0
        if args.command == "answer-lint":
            try:
                content = args.answer_file.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                raise ValueError("Could not read a UTF-8 reply for quality lint") from exc
            try:
                report = lint_mods_answer(content, case_id=args.case_id)
            except ValueError as exc:
                raise ValueError("Invalid Mods answer evidence: " + str(exc)) from exc
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(
                json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                encoding="utf-8",
            )
            _print_json(report)
            return 0
        if args.command == "chat-compare":
            try:
                before = json.loads(args.before.read_text(encoding="utf-8"))
                after = json.loads(args.after.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                raise ComparisonError("Missing/invalid Chat-mode A/B input") from exc
            report = compare_chat_versions(
                before,
                after,
                before_version=args.before_version,
                after_version=args.after_version,
            )
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(
                json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                encoding="utf-8",
            )
            _print_json(
                {
                    "cases_both_observed": report["cases_both_observed"],
                    "recovered": len(report["structurally_recovered"]),
                    "regressed": len(report["structurally_regressed"]),
                    "persistently_failed": len(report["persistently_failed"]),
                    "answer_semantics_verified": False,
                }
            )
            return 0
        if args.command == "chat-report":
            path = args.suite or args.root / "evals/p4_cases.json"
            try:
                suite = json.loads(path.read_text(encoding="utf-8"))
                records = json.loads(args.records.read_text(encoding="utf-8"))
                manual = (
                    json.loads(args.manual_reviews.read_text(encoding="utf-8"))
                    if args.manual_reviews
                    else None
                )
            except (OSError, ValueError) as exc:
                raise ChatReportError("Invalid or unavailable Chat-mode QA input") from exc
            result = aggregate_chat_mode_results(
                suite,
                records,
                plugin_version=args.plugin_version,
                source_revision=args.source_revision,
                manual_reviews=manual,
                blocked_case_ids=set(args.blocked),
            )
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(
                json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            _print_json(
                {
                    "status": result["status"],
                    "total": result["summary"]["total"],
                    "observed": result["summary"]["observed"],
                    "passed": result["summary"]["passed"],
                    "failed": result["summary"]["failed"],
                    "inconclusive": result["summary"]["inconclusive"],
                    "blocked": result["summary"]["blocked"],
                    "not_run": result["summary"]["not_run"],
                    "full_qa_pass": result["summary"]["full_qa_pass"],
                }
            )
            return 0
        if args.command == "release-verify":
            _print_json(verify_release(args.dir))
            return 0
        if args.command == "release":
            try:
                matrix = json.loads(args.host_matrix.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                raise ReleaseBuildError("Unable to read P5 host matrix") from exc
            result = build_release(
                args.root,
                args.dist,
                args.out,
                source_revision=args.source_revision,
                tag=args.tag,
                host_matrix=matrix,
            )
            _print_json(result)
            return 0
        if args.command == "marketplace-stage":
            _print_json(stage_personal_plugin(args.dist, args.home, apply=args.apply))
            return 0
        if args.command == "skills-lint":
            _print_json(validate_compiled_skill_format(args.dist))
            return 0
        if args.command == "package-check":
            _print_json(validate_dist(args.dist))
            return 0
        if args.command == "eval":
            suite_path = Path(args.suite)
            if not suite_path.is_absolute():
                suite_path = args.root / suite_path
            report = evaluate_suite(args.root, suite_path)
            if args.report is not None:
                args.report.parent.mkdir(parents=True, exist_ok=True)
                args.report.write_text(
                    json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                    encoding="utf-8",
                )
            _print_json(
                {
                    "status": report["status"],
                    "cases_total": report["cases_total"],
                    "resource_checks_passed": report["resource_checks_passed"],
                    "host_runtime_cases_pending": report["host_runtime_cases_pending"],
                    "host_runtime_cases_passed": report["host_runtime_cases_passed"],
                    "report": str(args.report) if args.report else None,
                }
            )
            return 0
        if args.command == "build":
            revision = args.source_revision
            if revision is None:
                git_path = shutil.which("git")
                if git_path:
                    # Git is discovered locally; no shell, credentials, or network required.
                    probe = subprocess.run(  # noqa: S603
                        [git_path, "-C", str(args.root), "rev-parse", "HEAD"],
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    revision = probe.stdout.strip() if probe.returncode == 0 else "working-tree"
                else:
                    revision = "working-tree"
            result = build_artifacts(
                args.root,
                args.root / "dist",
                api_version=args.api_version,
                surface=args.surface,
                package_version=args.package_version,
                knowledge_version=args.knowledge_version,
                source_revision=revision,
            )
            _print_json(
                {
                    "output": str(args.root / "dist"),
                    "approved_claims": result["approved_claims"],
                    "target": result["target"],
                    "package_version": result["package_version"],
                    "source_revision": result["source_revision"],
                    "files": len(result["artifact_sha256"]),
                }
            )
            return 0
        registry = load_registry(args.root / "sources/registry.json")
        if args.command in ("validate", "claims"):
            all_claims = load_claims(
                args.root / "claims",
                registry,
                args.root / "sources/snapshots",
                args.root / "decisions",
            )
        if args.command == "validate":
            _print_json(
                {
                    "sources": len(registry),
                    "claims": len(all_claims),
                    "layers": dict(
                        sorted(Counter(x["trust_layer"] for x in registry.values()).items())
                    ),
                    "eligible_official_documents": len(eligible_official_sources(registry)),
                    "approval_status": "UNVERIFIED_MIGRATION_SEED",
                    "approved_claims": sum(
                        c["lifecycle"] == "approved" for c in all_claims.values()
                    ),
                }
            )
            return 0
        if args.command == "list":
            for source_id, source in sorted(registry.items()):
                if args.layer is None or source["trust_layer"] == args.layer:
                    print(
                        f"{source_id}\t{source['trust_layer']}\t{source['title']}\t{source['url']}"
                    )
            return 0
        if args.command == "claims":
            if args.claims_command == "validate":
                _print_json(
                    {
                        "total": len(all_claims),
                        "approved": sum(c["lifecycle"] == "approved" for c in all_claims.values()),
                        "lifecycles": dict(
                            sorted(Counter(c["lifecycle"] for c in all_claims.values()).items())
                        ),
                        "areas": dict(
                            sorted(
                                Counter(
                                    area
                                    for c in all_claims.values()
                                    for area in c["areas"]["primary"]
                                ).items()
                            )
                        ),
                    }
                )
            elif args.claims_command == "list":
                for cid, claim in sorted(all_claims.items()):
                    print(
                        f"{cid}	{claim['lifecycle']}	"
                        f"{','.join(claim['areas']['primary'])}	{claim['subject']}"
                    )
            elif args.claims_command == "show":
                if args.claim_id not in all_claims:
                    raise ClaimError(f"Unknown Claim {args.claim_id}")
                _print_json(all_claims[args.claim_id])
            elif args.claims_command == "query":
                matching = approved_claims(all_claims, args.version, args.surface)
                _print_json(
                    {
                        "version": args.version,
                        "surface": args.surface,
                        "count": len(matching),
                        "claims": matching,
                    }
                )
            elif args.claims_command == "transition":
                result = transition_claim(
                    args.root,
                    args.claim_id,
                    args.to,
                    args.actor,
                    args.reason,
                    datetime.now(UTC),
                )
                _print_json({"claim_id": result["claim_id"], "lifecycle": result["lifecycle"]})
            return 0
        snapshots = args.root / "sources/snapshots"
        if args.command == "verify":
            problems = verify_snapshot_store(snapshots)
            if problems:
                for problem in problems:
                    print(f"ERROR: {problem}", file=sys.stderr)
                return 2
            load_claims(
                args.root / "claims",
                registry,
                snapshots,
                args.root / "decisions",
            )
            print("verified: local snapshot metadata, Claim evidence and decisions are coherent")
            return 0
        if args.command == "collect":
            if args.limit is not None and (args.limit < 1 or not args.all_official):
                raise CollectionError("--limit requires --all-official and a positive N")
            if args.all_official:
                sources = eligible_official_sources(registry)
                if args.limit:
                    sources = sources[: args.limit]
            else:
                sources = []
                for source_id in args.source:
                    source = registry.get(source_id)
                    if not source or source["trust_layer"] not in OFFICIAL_LAYERS:
                        raise CollectionError(
                            f"Source {source_id} is unknown or not current official documentation"
                        )
                    sources.append(source)
            if problems := verify_snapshot_store(snapshots):
                raise CollectionError("Existing metadata store is invalid: " + "; ".join(problems))
            successes = []
            failures = []
            for source in sources:
                try:
                    result = fetch_document(
                        source["url"], timeout=args.timeout, max_bytes=args.max_bytes
                    )
                    change = record_observation(snapshots, source, result, datetime.now(UTC))
                    successes.append(asdict(change))
                except (CollectionError, OSError) as exc:
                    failures.append({"source_id": source["source_id"], "error": str(exc)})
            _print_json({"collected": successes, "failures": failures})
            return 2 if failures else 0
    except (
        RegistryError,
        CollectionError,
        ClaimError,
        CompilerError,
        EvaluationError,
        ReleaseValidationError,
        MarketplaceError,
        ReleaseBuildError,
        StableGateError,
        ChatReportError,
        ComparisonError,
        EvidenceSelectionError,
        ValueError,
    ) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    raise AssertionError("Unexpected CLI command")


if __name__ == "__main__":
    sys.exit(main())
