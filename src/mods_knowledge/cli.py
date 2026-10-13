"""Command-line interface for the initial, explicitly unverified source knowledge registry."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from .collector import fetch_document
from .errors import CollectionError, RegistryError
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
    return parser


def _print_json(data: object) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        registry = load_registry(args.root / "sources/registry.json")
        if args.command == "validate":
            _print_json(
                {
                    "sources": len(registry),
                    "layers": dict(
                        sorted(Counter(x["trust_layer"] for x in registry.values()).items())
                    ),
                    "eligible_official_documents": len(eligible_official_sources(registry)),
                    "approval_status": "UNVERIFIED_MIGRATION_SEED",
                    "approved_claims": 0,
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
        snapshots = args.root / "sources/snapshots"
        if args.command == "verify":
            problems = verify_snapshot_store(snapshots)
            if problems:
                for problem in problems:
                    print(f"ERROR: {problem}", file=sys.stderr)
                return 2
            print("verified: local snapshot metadata and current-hash index are coherent")
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
    except (RegistryError, CollectionError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    raise AssertionError("Unexpected CLI command")


if __name__ == "__main__":
    sys.exit(main())
