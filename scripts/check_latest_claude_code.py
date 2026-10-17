#!/usr/bin/env python3
"""Online, fail-closed Claude Code latest-channel gate for P6 publishing.

Run immediately before compiling/publishing after reviewed SSOT validation.
Offline deterministic builds remain offline; this separate online check is
required in the release procedure. It never installs or executes a plugin.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import urllib.request
from pathlib import Path

REGISTRY_DIST_TAGS_URL = (
    "https://registry.npmjs.org/-/package/%40anthropic-ai%2Fclaude-code/dist-tags"
)
VERSION = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
MAX_RESPONSE = 16_384


class LatestVersionGateError(ValueError):
    """Fail-closed target/current host/approved material freshness error."""


def official_latest(*, timeout: int = 12) -> str:
    """Retrieve npm's latest dist-tag from a fixed HTTPS official package endpoint."""
    if not isinstance(timeout, int) or not 1 <= timeout <= 30:
        raise LatestVersionGateError("Invalid bounded registry timeout")
    request = urllib.request.Request(REGISTRY_DIST_TAGS_URL, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 -- fixed HTTPS official registry URL
            data = response.read(MAX_RESPONSE + 1)
            if not 0 < len(data) <= MAX_RESPONSE:
                raise LatestVersionGateError("Official registry response is empty or oversized")
            document = json.loads(data)
    except (OSError, ValueError, TypeError) as exc:
        raise LatestVersionGateError("Official npm latest could not be verified") from exc
    observed = document.get("latest") if isinstance(document, dict) else None
    if not isinstance(observed, str) or not VERSION.fullmatch(observed):
        raise LatestVersionGateError("Official npm latest tag has an unexpected format")
    return observed


def checked_target(target: str, latest: str, installed: str | None = None) -> None:
    """Never accept old-version build inputs or incorrectly updated local machines."""
    if not VERSION.fullmatch(target) or not VERSION.fullmatch(latest):
        raise LatestVersionGateError("Target and latest must be exact three-part versions")
    if target != latest:
        raise LatestVersionGateError(
            f"Stale build target {target}; official latest is {latest}; refresh SSOT first"
        )
    if installed is not None and installed != latest:
        raise LatestVersionGateError(
            "Local Claude Code CLI is not the latest release; update it before native QA"
        )


def local_cli_version() -> str:
    exe = shutil.which("claude")
    if not exe or not Path(exe).is_absolute():
        raise LatestVersionGateError("Unable to resolve installed Claude Code CLI")
    try:
        completed = subprocess.run(  # noqa: S603 -- resolved CLI with fixed --version only
            [exe, "--version"],
            capture_output=True,
            text=True,
            timeout=12,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise LatestVersionGateError("Unable to verify installed Claude Code CLI") from exc
    if completed.returncode or not completed.stdout:
        raise LatestVersionGateError("Unable to verify installed Claude Code CLI")
    installed = completed.stdout.split()[0]
    if not VERSION.fullmatch(installed):
        raise LatestVersionGateError("Unexpected installed Claude Code version format")
    return installed


def approved_current_claims(root: Path, version: str) -> int:
    """Release must have approved exact-version knowledge, not fallback old Claims."""
    from mods_knowledge.claims import approved_claims, load_claims
    from mods_knowledge.registry import load_registry

    registry = load_registry(root / "sources/registry.json")
    claims = load_claims(
        root / "claims",
        registry,
        root / "sources/snapshots",
        root / "decisions",
    )
    return len(approved_claims(claims, version, "cli"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-version", required=True)
    parser.add_argument("--require-installed", action="store_true")
    parser.add_argument("--require-approved", action="store_true")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    try:
        latest = official_latest()
        installed = local_cli_version() if args.require_installed else None
        checked_target(args.target_version, latest, installed)
        claims = approved_current_claims(args.root, latest) if args.require_approved else None
        if args.require_approved and not claims:
            raise LatestVersionGateError(
                "No approved exact-version SSOT Claims; block Skills/ChatGPT Plugin publish"
            )
    except LatestVersionGateError as exc:
        print(f"BLOCKED: {exc}")
        return 2
    print(
        json.dumps(
            {
                "status": "latest_version_preflight_pass",
                "official_npm_latest": latest,
                "requested_target_version": args.target_version,
                "local_cli_version": installed,
                "approved_exact_version_claims": claims,
                "publication_authorized": False,
                "note": (
                    "Version preflight alone is not evidence of semantic, native, "
                    "or ChatGPT Chat-mode acceptance"
                ),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
