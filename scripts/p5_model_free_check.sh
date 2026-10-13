#!/usr/bin/env bash
# P5 token-free static tests only, no Claude Code/Codex/Pi model execution.
set -euo pipefail
if [ "$#" -lt 1 ]; then echo "Usage: bash scripts/p5_model_free_check.sh macbook|raspberrypi|sextant [outdir]" >&2; exit 2; fi
cd "$(dirname "$0")/.."
HOST_ID="$1"
case "$HOST_ID" in
  macbook|raspberrypi|sextant) ;;
  *) echo "Invalid host identifier" >&2; exit 2 ;;
esac
P5_PACKAGE_VERSION="${P5_PACKAGE_VERSION:-0.1.0-rc.1}"
OUTDIR="/tmp/mods-p5-$HOST_ID"
if [ "$#" -ge 2 ]; then OUTDIR="$2"; fi
mkdir -p "$OUTDIR"
BASE="$(pwd -P)"
SHA="$(git rev-parse HEAD)"
echo "Host=$HOST_ID checkout=$BASE Git=$SHA"
uv sync --locked --quiet
uv run pytest -q >"$OUTDIR/pytest.log" 2>&1
uv run ruff check . >"$OUTDIR/ruff.log" 2>&1
uv run ruff format --check . >>"$OUTDIR/ruff.log" 2>&1
uv run mods-knowledge validate >"$OUTDIR/registry.json"
uv run mods-knowledge verify >"$OUTDIR/source-integrity.log"
uv run mods-knowledge claims validate >"$OUTDIR/claims.json"
uv run mods-knowledge eval --report "$OUTDIR/p4.json" >"$OUTDIR/p4-summary.json"
uv run mods-knowledge build --api-version 2.1.296 --surface cli \
  --package-version "$P5_PACKAGE_VERSION" --source-revision "$SHA" >"$OUTDIR/build.json"
uv run mods-knowledge package-check --dist dist >"$OUTDIR/package-check.json"
export P5_HOST_ID="$HOST_ID" P5_OUTDIR="$OUTDIR" P5_GIT_SHA="$SHA"
uv run python - <<'PY'
import json
import os
import platform
import re
from pathlib import Path
out = Path(os.environ["P5_OUTDIR"])
host = os.environ["P5_HOST_ID"]
revision = os.environ["P5_GIT_SHA"]
testing = (out / "pytest.log").read_text(encoding="utf-8")
matches = re.findall(r"(\d+) passed", testing)
assert matches, testing[-400:]
assert "failed" not in testing[-90:].lower(), testing[-400:]
p4 = json.loads((out / "p4.json").read_text())
built = json.loads((out / "build.json").read_text())
checked = json.loads((out / "package-check.json").read_text())
assert p4["resource_checks_passed"] == 46 and p4["host_runtime_cases_passed"] == 0
assert built["source_revision"] == revision
assert checked["source_revision"] == revision
assert checked["artifacts_verified"] == 48
assert checked["approved_claims"] == built["approved_claims"]
item = {
    "schema_version": 1,
    "host_id": host,
    "hostname": platform.node(),
    "os": platform.system().lower(),
    "architecture": platform.machine(),
    "python": platform.python_version(),
    "source_revision": revision,
    "package_version": built["package_version"],
    "static_tests": "pass",
    "pytest_passed": int(matches[-1]),
    "ruff": "pass",
    "resource_checks": 46,
    "plugin_bundle_sha256": checked["plugin_zip_sha256"],
    "skill_bundle_sha256": checked["skill_zip_sha256"],
    "files_verified": checked["artifacts_verified"],
    "token_based_agent_test": "not_run",
    "chatgpt_chat_runtime": "not_run",
    "status": "package_verified_host_runtime_not_run",
}
path = out / f"P5-{host}.json"
path.write_text(json.dumps(item, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
print(json.dumps(item, ensure_ascii=False, sort_keys=True, indent=2))
PY
echo "P5 static cross-host verification complete; no model quota consumed."
