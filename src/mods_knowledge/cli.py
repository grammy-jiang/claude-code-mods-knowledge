"""Command-line interface for the initial, explicitly unverified source knowledge registry."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from collections import Counter
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from .claims import approved_claims, load_claims
from .collector import fetch_document
from .compiler import CompilerError, build_artifacts
from .decisions import transition_claim
from .errors import ClaimError, CollectionError, RegistryError
from .registry import OFFICIAL_LAYERS, eligible_official_sources, load_registry
from .storage import record_observation, verify_snapshot_store

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
    return parser


def _print_json(data: object) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
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
    except (RegistryError, CollectionError, ClaimError, CompilerError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    raise AssertionError("Unexpected CLI command")


if __name__ == "__main__":
    sys.exit(main())
