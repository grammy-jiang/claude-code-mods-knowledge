#!/usr/bin/env bash
# Token-free SSOT and package regression checks.
set -euo pipefail
cd "$(dirname "$0")/.."
VERSION="${MODS_PYTHON_VERSION:-3.14}"
uv sync --locked --python "$VERSION" --quiet
uv run --python "$VERSION" --locked ruff check .
uv run --python "$VERSION" --locked ruff format --check .
uv run --python "$VERSION" --locked pytest -q
uv run --python "$VERSION" --locked mods-knowledge validate
uv run --python "$VERSION" --locked mods-knowledge verify
uv run --python "$VERSION" --locked mods-knowledge claims validate
if command -v sha256sum >/dev/null 2>&1; then sha256sum -c docs/SOURCE_IMPORT_SHA256.txt; else shasum -a 256 -c docs/SOURCE_IMPORT_SHA256.txt; fi
uv run --python "$VERSION" --locked mods-knowledge eval --report /tmp/mods-p4-static-ci.json
REV="$(git rev-parse HEAD)"
uv run --python "$VERSION" --locked mods-knowledge build --api-version 2.1.296 --surface cli --package-version 0.2.0-beta.1 --source-revision "$REV"
uv run --python "$VERSION" --locked mods-knowledge skills-lint --dist dist
uv run --python "$VERSION" --locked mods-knowledge package-check --dist dist
if command -v sha256sum >/dev/null 2>&1; then (cd dist && sha256sum -c manifests/checksums.sha256); else (cd dist && shasum -a 256 -c manifests/checksums.sha256); fi
echo "CI_OFFLINE_PASS Python=$VERSION Git=$REV"
