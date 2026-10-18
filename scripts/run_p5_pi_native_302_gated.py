#!/usr/bin/env python3
"""Pi Agent 1.3.0 native CLI 2.1.302 test runner, mandatory buffered gates.

P5 research only. Never streams model answers, runs generated code, changes
global Pi configuration, starts/stops model servers, or alters ChatGPT.
Read-only Pi tools, no MCP/extensions, isolated per-case agent configuration.
The original full native trace remains in a private chmod 0600 local file.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import selectors
import shutil
import signal
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

from mods_knowledge.claims import load_claims
from mods_knowledge.pi_delivery_gate import postflight_mods_case, preflight_mods_case
from mods_knowledge.pi_loop_evidence import NativeRepeatGuard
from mods_knowledge.registry import load_registry
from mods_knowledge.release_validation import validate_dist

ROOT = Path(__file__).resolve().parents[1]
CASE_IDS = frozenset(("POS-E-01", "POS-Q-01", "NEG-TYPESCRIPT", "BOUND-VERSION-NEW"))
MODEL = "qwen36-35b-a3b-mtp"
PROVIDER = "mac-qwen"
MODEL_URL = "http://127.0.0.1:18081/v1"
MODEL_TIMEOUT_MIN = 30
MODEL_TIMEOUT_MAX = 180
MAX_WIRE_BYTES = 12_000_000
MAX_EVENTS = 8000
SOURCE_TARGET = "2.1.302"


class PiNative302Blocked(ValueError):
    """Reviewed native host, package, or test-case requirements failed."""


def _sha(data: bytes | str) -> str:
    return hashlib.sha256(data.encode() if isinstance(data, str) else data).hexdigest()


def _write_private(path: Path, data: dict) -> None:
    if path.exists() or path.is_symlink():
        raise PiNative302Blocked("Do not overwrite an original private QA result")
    with path.open("x") as out:
        json.dump(data, out, ensure_ascii=False, sort_keys=True, indent=2)
        out.write("\n")
    path.chmod(0o600)


def _git_head(root: Path) -> str:
    exe = shutil.which("git")
    if exe is None:
        raise PiNative302Blocked("Git command unavailable to verify source")
    result = subprocess.run(  # noqa: S603 - read-only verified local Git path
        [exe, "-C", str(root), "rev-parse", "HEAD"],
        text=True,
        capture_output=True,
        timeout=8,
        check=True,
    )
    return result.stdout.strip()


def _version_info(binary: str) -> str:
    exe = shutil.which(binary)
    if exe is None:
        raise PiNative302Blocked("Required native agent binary unavailable")
    result = subprocess.run(  # noqa: S603 - resolved native binary, version flag only
        [exe, "--version"],
        text=True,
        capture_output=True,
        timeout=8,
        check=True,
    )
    return result.stdout.strip()


def _attest(
    *,
    root: Path,
    dist: Path,
    skill_root: Path,
    observed_claude_version: str,
    observed_pi_version: str,
) -> tuple[str, str]:
    """Check Git, actual built ZIPs and EVERY native on-host reference file."""
    if observed_claude_version != "2.1.302 (Claude Code)" or observed_pi_version != "1.3.0":
        raise PiNative302Blocked("Installed CLI/Pi versions are not the reviewed pair")
    package = validate_dist(dist)
    if (
        package.get("target") != {"api_version": "2.1.302", "surface": "cli"}
        or package.get("artifacts_verified") != 53
        or package.get("skill_format_status") != "SKILL_FORMAT_VALID"
    ):
        raise PiNative302Blocked("Reviewed compiled package failed actual offline QA")
    manifest = json.loads((dist / "manifests/build-manifest.json").read_text())
    sha = manifest.get("source_revision")
    if not isinstance(sha, str) or not re.fullmatch(r"[a-f0-9]{40}", sha):
        raise PiNative302Blocked("Missing reviewed build SHA")
    if sha != _git_head(root):
        raise PiNative302Blocked("Source Git revision and built artifacts are inconsistent")
    source = dist / "common/claude-code-mods-development"
    if not skill_root.is_dir() or skill_root.is_symlink():
        raise PiNative302Blocked("Installed native Pi Skill is missing or symlinked")
    expected = {str(f.relative_to(source)) for f in source.rglob("*") if f.is_file()}
    observed = {str(f.relative_to(skill_root)) for f in skill_root.rglob("*") if f.is_file()}
    if not expected or expected != observed:
        raise PiNative302Blocked("Native Pi installed Skill/reference files differ")
    for relative in expected:
        dest = skill_root / relative
        if dest.is_symlink() or (source / relative).read_bytes() != dest.read_bytes():
            raise PiNative302Blocked("Native Pi Skill/reference byte identity mismatch")
    return sha, _sha((skill_root / "SKILL.md").read_bytes())


def _get_case(root: Path, case_id: str) -> dict:
    if case_id not in CASE_IDS:
        raise PiNative302Blocked("Only frozen CLI302 P5 native QA tasks permitted")
    cases = json.loads((root / "evals/p4_cases_cli_2_1_302.json").read_text())["cases"]
    selected = [c for c in cases if c.get("id") == case_id]
    if len(selected) != 1 or selected[0].get("category") not in {
        "positive",
        "negative",
        "boundary",
    }:
        raise PiNative302Blocked("P5 QA case missing from frozen reviewed matrix")
    return selected[0].copy()


def _health_check() -> None:
    """Only probe an already-running loopback forwarded server after preflight."""
    req = urllib.request.Request(  # noqa: S310 - immutable local loopback URL
        MODEL_URL + "/models", method="GET"
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as response:  # noqa: S310 - fixed loopback
            if response.status != 200:
                raise PiNative302Blocked("Pinned model endpoint is not healthy")
            payload = json.loads(response.read(160_000))
    except (OSError, ValueError, urllib.error.URLError) as exc:
        raise PiNative302Blocked("Pinned local Qwen backend is offline") from exc
    if MODEL not in [item.get("id") for item in payload.get("data", []) if isinstance(item, dict)]:
        raise PiNative302Blocked("Requested real local model is not the running model")


def _isolated_agent_config(private_root: Path) -> Path:
    d = private_root / "isolated-native-agent"
    d.mkdir(mode=0o700)
    models = {
        "providers": {
            PROVIDER: {
                "baseUrl": MODEL_URL,
                "api": "openai-completions",
                "apiKey": "LOCALHOST_QA_ONLY_NOT_AN_ACCOUNT_KEY",
                "compat": {"supportsDeveloperRole": False, "supportsReasoningEffort": False},
                "models": [
                    {
                        "id": MODEL,
                        "name": "Local isolated P5 Qwen",
                        "reasoning": False,
                        "input": ["text"],
                        "contextWindow": 16384,
                        "maxTokens": 4096,
                    }
                ],
            }
        }
    }
    _write_private(d / "models.json", models)
    _write_private(
        d / "settings.json",
        {
            "defaultProvider": PROVIDER,
            "defaultModel": MODEL,
            "defaultThinkingLevel": "off",
        },
    )
    return d


def _terminate_process_group(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        proc.wait(timeout=4)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait(timeout=4)


def _pi_argv(executable: str, case: dict, skill_root: Path) -> list[str]:
    """Build a single native Pi CLI command with no write/bash/MCP extension."""
    if not executable or not Path(executable).is_absolute():
        raise PiNative302Blocked("Native Pi binary must be a resolved absolute path")
    if not isinstance(case.get("prompt"), str) or not case["prompt"].strip():
        raise PiNative302Blocked("Cannot send unknown or empty native case")
    return [
        executable,
        "-p",
        "--provider",
        PROVIDER,
        "--model",
        MODEL,
        "--thinking",
        "off",
        "--no-session",
        "--no-mcp",
        "--no-extensions",
        "--no-context-files",
        "--no-prompt-templates",
        "--no-approve",
        "--offline",
        "--tools",
        "read",
        "--skill",
        str(skill_root),
        "--mode",
        "json",
        case["prompt"],
    ]


def _run_native(
    case: dict,
    skill_root: Path,
    private_root: Path,
    *,
    timeout: int,
) -> tuple[list[dict], int, bool, bool, str]:
    """Capture the complete native Pi JSON stream before ANY response delivery."""
    executable = shutil.which("pi")
    if not executable:
        raise PiNative302Blocked("Pi native CLI unavailable")
    agent = _isolated_agent_config(private_root)
    workspace = private_root / "workspace"
    workspace.mkdir(mode=0o700)
    argv = _pi_argv(executable, case, skill_root)
    env = os.environ.copy()
    env["PI_CODING_AGENT_DIR"] = str(agent)
    env["PI_OFFLINE"] = "1"
    for variable in (
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_AUTH_TOKEN",
        "ANTHROPIC_OAUTH_TOKEN",
        "OPENAI_API_KEY",
        "GEMINI_API_KEY",
        "OPENROUTER_API_KEY",
    ):
        env.pop(variable, None)

    events: list[dict] = []
    pending = bytearray()
    guard = NativeRepeatGuard(repeat_limit=5, total_tool_limit=36)
    bytes_seen = 0
    timed_out = False
    aborted = False
    wire = private_root / "native-events.private.jsonl"
    err = private_root / "native-stderr.private.log"
    deadline = time.monotonic() + timeout
    with wire.open("xb") as output, err.open("xb") as errors:
        wire.chmod(0o600)
        err.chmod(0o600)
        proc = subprocess.Popen(  # noqa: S603 - resolved native Pi with strict flags
            argv,
            cwd=workspace,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=errors,
            env=env,
            start_new_session=True,
            bufsize=0,
        )
        assert proc.stdout is not None
        selector = selectors.DefaultSelector()
        try:
            selector.register(proc.stdout, selectors.EVENT_READ)
            while True:
                if time.monotonic() >= deadline:
                    timed_out = True
                    break
                ready = selector.select(timeout=0.5)
                if not ready:
                    if proc.poll() is not None:
                        break
                    continue
                block = os.read(proc.stdout.fileno(), 65_536)
                if not block:
                    break
                bytes_seen += len(block)
                if bytes_seen > MAX_WIRE_BYTES:
                    aborted = True
                    break
                output.write(block)
                pending.extend(block)
                while b"\n" in pending:
                    line, _, tail = pending.partition(b"\n")
                    pending = bytearray(tail)
                    if not line.strip():
                        continue
                    try:
                        event = json.loads(line)
                    except (UnicodeError, ValueError):
                        aborted = True
                        break
                    if not isinstance(event, dict):
                        aborted = True
                        break
                    events.append(event)
                    if len(events) > MAX_EVENTS:
                        aborted = True
                        break
                    if event.get("type") == "tool_execution_start":
                        if event.get("toolName") != "read":
                            aborted = True
                            break
                    if guard.observe(event):
                        aborted = True
                        break
                if aborted:
                    break
            if timed_out or aborted:
                _terminate_process_group(proc)
            else:
                try:
                    proc.wait(timeout=4)
                except subprocess.TimeoutExpired:
                    timed_out = True
                    _terminate_process_group(proc)
        finally:
            selector.close()
            if proc.poll() is None:
                _terminate_process_group(proc)
    return (
        events,
        proc.returncode if proc.returncode is not None else 124,
        timed_out,
        aborted,
        _sha(wire.read_bytes()),
    )


def run_case(
    case_id: str,
    *,
    root: Path,
    dist: Path,
    skill_root: Path,
    evidence_dir: Path,
    run_model: bool = False,
    observed_claude_version: str | None = None,
    observed_pi_version: str | None = None,
    health_check=None,
    model_runner=None,
    timeout: int = 120,
) -> dict:
    """Preflight ALWAYS runs before health/network/model operations."""
    if type(run_model) is not bool or not MODEL_TIMEOUT_MIN <= timeout <= MODEL_TIMEOUT_MAX:
        raise PiNative302Blocked("Invalid bounded Pi runtime controls")
    if evidence_dir.exists() or evidence_dir.is_symlink():
        raise PiNative302Blocked("Refusing a second run into existing evidence")
    root, dist, skill_root = Path(root), Path(dist), Path(skill_root)
    revision, installed_sha = _attest(
        root=root,
        dist=dist,
        skill_root=skill_root,
        observed_claude_version=(
            observed_claude_version
            if observed_claude_version is not None
            else _version_info("claude")
        ),
        observed_pi_version=(
            observed_pi_version if observed_pi_version is not None else _version_info("pi")
        ),
    )
    case = _get_case(root, case_id)
    gate = preflight_mods_case(case, target_version=SOURCE_TARGET)
    if gate.get("source_target") != "Claude Code CLI 2.1.302":
        raise PiNative302Blocked("Version mismatch in mandatory native preflight")
    evidence_dir.mkdir(mode=0o700, parents=True)
    basic = {
        "schema_version": 1,
        "source_revision": revision,
        "skill_sha256": installed_sha,
        "target_cli": SOURCE_TARGET,
        "pi_native_version": "1.3.0",
        "case_id": case_id,
        "case_category": case["category"],
        "native_model": f"{PROVIDER}/{MODEL}",
        "original_prompt_sha256": _sha(case["prompt"]),
        "raw_model_output_delivered": False,
        "semantic_correctness_verified": False,
        "stable_release_authorized": False,
    }
    if gate["action"] == "abstain_before_model":
        report = {
            **basic,
            "action": "abstain_before_model",
            "preflight_reason": gate["reason"],
            "safe_refusal_sha256": _sha(gate["safe_reply"]),
            "model_requests_performed": 0,
            "native_model_inference_completed": False,
        }
        _write_private(evidence_dir / "report.private.json", report)
        return report
    if gate["action"] != "run_scoped_model":
        raise PiNative302Blocked("Mandatory Pi preflight did not authorize the task")
    if not run_model:
        report = {
            **basic,
            "action": "model_backend_required_after_preflight",
            "model_requests_performed": 0,
            "native_model_inference_completed": False,
        }
        _write_private(evidence_dir / "report.private.json", report)
        return report

    check = health_check or _health_check
    engine = model_runner or _run_native
    try:
        check()
    except Exception as exc:
        report = {
            **basic,
            "action": "blocked_model_backend_unavailable",
            "model_requests_performed": 0,
            "backend_error_class": type(exc).__name__,
            "native_model_inference_completed": False,
        }
        _write_private(evidence_dir / "report.private.json", report)
        return report

    try:
        if engine is _run_native:
            events, code, timed_out, aborted, wire_sha = engine(
                case, skill_root, evidence_dir, timeout=timeout
            )
        else:
            events, code, timed_out, aborted, wire_sha = engine(case, skill_root, evidence_dir)
        # Model-origin read operations outside the approved workspace/Skill
        # are a QA privacy failure, never a production delivery pass.
        outside_scope = False
        for event in events:
            if event.get("type") != "tool_execution_start":
                continue
            args = event.get("args") or {}
            raw_path = args.get("path") if isinstance(args, dict) else None
            if not isinstance(raw_path, str):
                outside_scope = True
                break
            resolved = Path(raw_path).resolve(strict=False)
            if not (
                resolved.is_relative_to(skill_root.resolve())
                or resolved.is_relative_to((evidence_dir / "workspace").resolve())
            ):
                outside_scope = True
                break
        claims = load_claims(
            root / "claims",
            load_registry(root / "sources/registry.json"),
            root / "sources/snapshots",
            root / "decisions",
        )
        review = postflight_mods_case(
            case,
            events,
            claims=claims,
            skill_root=str(skill_root),
            source_revision=revision,
            provider=PROVIDER,
            model=MODEL,
            pi_version="1.3.0",
            native_exit_code=code,
            timed_out=timed_out,
            terminated_for_repeat=aborted,
            enforce_task_evidence=False,
            target_version=SOURCE_TARGET,
            native_host="raspberry-pi",
        )
        reasons = list(review.get("reason_codes") or [])
        if outside_scope:
            reasons.append("tool_read_outside_isolated_skill_or_workspace")
        report = {
            **basic,
            "action": "native_buffered_review_completed",
            "gate_action": (
                "block_candidate" if outside_scope else review.get("action", "block_candidate")
            ),
            "gate_reason_codes": sorted(set(reasons)),
            "native_model_inference_completed": bool(
                code == 0 and not timed_out and not aborted and review.get("native_exit_ok", False)
            ),
            "native_exit_ok": code == 0 and not timed_out,
            "actual_skill_read_observed": review.get("skill_read_observed"),
            "claim_source_verdict": review.get("source_verdict"),
            "native_tool_calls": review.get("native_tool_calls"),
            "original_private_wire_sha256": wire_sha,
            "native_pi_process_invocations": 1,
            # Pi may internally retry its OpenAI-compatible model request.
            # Do not invent an exact upstream HTTP request count from
            # one terminal CLI process invocation.
            "model_requests_performed": None,
            "model_http_request_count_independently_verified": False,
            # A structural pass is NOT execution of generated code or a
            # verified semantic pass. This runner never releases raw text.
            "raw_model_output_delivered": False,
            "semantic_correctness_verified": False,
        }
    except Exception as exc:
        report = {
            **basic,
            "action": "blocked_native_execution_or_review_error",
            "error_class": type(exc).__name__,
            "model_requests_performed": None,
            "model_http_request_count_independently_verified": False,
            "native_pi_process_invocation_attempted": True,
            "native_model_inference_completed": False,
        }
    _write_private(evidence_dir / "report.private.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=sorted(CASE_IDS), required=True)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--dist", type=Path, default=ROOT / "dist")
    parser.add_argument(
        "--skill-root",
        type=Path,
        default=Path.home() / ".agents/skills/claude-code-mods-development",
    )
    parser.add_argument("--evidence-dir", required=True, type=Path)
    parser.add_argument("--run-model", action="store_true")
    parser.add_argument("--timeout", type=int, default=120)
    args = parser.parse_args()
    result = run_case(
        args.case,
        root=args.root,
        dist=args.dist,
        skill_root=args.skill_root,
        evidence_dir=args.evidence_dir,
        run_model=args.run_model,
        timeout=args.timeout,
    )
    # Everything shown is bounded status metadata. No private raw model
    # answer, prompt or tool result is ever printed.
    safe = {
        key: result.get(key)
        for key in (
            "case_id",
            "action",
            "gate_action",
            "gate_reason_codes",
            "native_model_inference_completed",
            "model_requests_performed",
            "raw_model_output_delivered",
            "stable_release_authorized",
        )
    }
    print(json.dumps(safe, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
