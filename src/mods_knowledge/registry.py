"""Validate source identities and enforce the official-document trust firewall."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from jsonschema import Draft202012Validator, FormatChecker

from .errors import RegistryError

SCHEMA_PATH = (
    Path(__file__).resolve().parents[2]
    / "docs/design/mods_ssot_design_v0_1/schemas/source.schema.json"
)

_LAYER_TYPE = {
    "L0": "official-mods",
    "L1": "official-dependency",
    "L2": "official-secondary",
    "R": "official-example",
    "C": "community",
    "H": "historical",
}
OFFICIAL_LAYERS = frozenset(("L0", "L1", "L2"))
OFFICIAL_ORIGIN = "https://code.claude.com"
OFFICIAL_PATH_PREFIX = "/docs/en/"


def _identity(url: str) -> str:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise RegistryError(f"Not a valid HTTPS source URL: {url!r}")
    if parsed.username or parsed.password or parsed.port not in (None, 443):
        raise RegistryError("Source URL must not contain credentials or custom ports")
    if parsed.query and ("token=" in parsed.query.lower() or "key=" in parsed.query.lower()):
        raise RegistryError("Credentials must not be embedded in source URLs")
    path = parsed.path.rstrip("/") or "/"
    return urlunsplit(("https", parsed.hostname.lower(), path, parsed.query, ""))


def _is_official_url(url: str) -> bool:
    parsed = urlsplit(url)
    return (
        parsed.scheme == "https"
        and parsed.netloc == "code.claude.com"
        and (parsed.path.startswith(OFFICIAL_PATH_PREFIX) or parsed.path == "/docs/llms.txt")
        and not parsed.query
        and not parsed.fragment
    )


def validate_registry(data: dict, schema_path: Path = SCHEMA_PATH) -> dict[str, dict]:
    """Validate the 0.1 migration envelope and all source records.

    Importing a source never implies that its API claims are verified.
    """
    if not isinstance(data, dict) or data.get("approval_status") != "UNVERIFIED_MIGRATION_SEED":
        raise RegistryError("Registry must remain UNVERIFIED_MIGRATION_SEED in P0")
    if data.get("schema_version") != "0.1.0" or not isinstance(data.get("sources"), list):
        raise RegistryError("Expected source registry schema_version 0.1.0 with sources list")
    if set(data) != {"schema_version", "generated_from", "approval_status", "sources"}:
        raise RegistryError("Unexpected or missing top-level registry fields")
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        validator.check_schema(schema)
    except (OSError, ValueError) as exc:
        raise RegistryError(f"Cannot load a valid source schema: {exc}") from exc
    seen_ids: set[str] = set()
    identities: dict[str, str] = {}
    registry: dict[str, dict] = {}
    for source in data["sources"]:
        if not isinstance(source, dict):
            raise RegistryError("Source records must be JSON objects")
        errors = sorted(
            validator.iter_errors(source), key=lambda e: (list(map(str, e.path)), e.message)
        )
        if errors:
            raise RegistryError(
                f"Invalid source {source.get('source_id', '?')}: {errors[0].message}"
            )
        identifier = source["source_id"]
        if identifier in seen_ids:
            raise RegistryError(f"Duplicate source ID: {identifier}")
        seen_ids.add(identifier)
        layer = source["trust_layer"]
        if source["source_type"] != _LAYER_TYPE[layer]:
            raise RegistryError(f"Incompatible layer/type for {identifier}")
        if set(source["areas"]["primary"]) & set(source["areas"]["secondary"]):
            raise RegistryError(f"Area assigned to both primary and secondary: {identifier}")
        if layer == "H" and not source.get("historical_reason"):
            raise RegistryError(f"Historical reason required for {identifier}")
        if layer in OFFICIAL_LAYERS and (
            not _is_official_url(source["url"])
            or (source.get("canonical_url") and not _is_official_url(source["canonical_url"]))
        ):
            raise RegistryError(f"Unsupported official documentation origin/path: {identifier}")
        snapshot = source["snapshot"]
        if snapshot["state"] == "unpinned" and (
            snapshot["sha256"] is not None or snapshot["commit_sha"] is not None
        ):
            raise RegistryError(f"Unpinned source contains a digest or commit: {identifier}")
        if source["review_state"] == "pinned" and snapshot["state"] != "pinned":
            raise RegistryError(f"Pinned review without pinned source: {identifier}")
        for value in (source["url"], source.get("canonical_url")):
            if not value:
                continue
            identity = _identity(value)
            previous = identities.get(identity)
            if previous and previous != identifier:
                raise RegistryError(f"Duplicate source URL/alias: {identifier} and {previous}")
            identities[identity] = identifier
        registry[identifier] = source
    for identifier, source in registry.items():
        next_id = source.get("superseded_by")
        visited = {identifier}
        while next_id:
            if next_id not in registry:
                raise RegistryError(f"Unknown superseding source {next_id} for {identifier}")
            if next_id in visited:
                raise RegistryError(f"Cyclic supersession at {identifier}")
            visited.add(next_id)
            next_id = registry[next_id].get("superseded_by")
    return registry


def load_registry(path: Path, schema_path: Path = SCHEMA_PATH) -> dict[str, dict]:
    """Read registry JSON from a path, validating its schema and trust metadata."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RegistryError(f"Cannot read registry {path}: {exc}") from exc
    return validate_registry(data, schema_path)


def eligible_official_sources(registry: Mapping[str, dict]) -> list[dict]:
    """Select official documentation only; never include R, C, or H sources."""
    return [
        source
        for _, source in sorted(registry.items())
        if source["trust_layer"] in OFFICIAL_LAYERS and _is_official_url(source["url"])
    ]
