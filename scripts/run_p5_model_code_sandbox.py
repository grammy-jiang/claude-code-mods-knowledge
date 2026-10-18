#!/usr/bin/env python3
"""Execute reviewed exact Codex/Sonnet observer snippets ONLY in Bubblewrap.

No model calls, provider access, host Home mounts, network namespace, MCP,
Claude execution or generated code execution on the unsandboxed host.
The only untrusted executable bytes are hash-matched original observer code
blocks from verified historical model answers. The harness itself is trusted,
and probes ONLY the limited synthetic next(e) pass-through contract.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from audit_p5_original_model_code import CANDIDATE_FILENAMES, FIXTURES, stage

ROOT = Path(__file__).resolve().parents[1]
HARNESS = FIXTURES / "observer-contract.test.mjs"
NODE_SUFFIX = re.compile(r"node-v[0-9]+[.][0-9]+[.][0-9]+")
MAX_OUTPUT_BYTES = 180_000


class ModelCodeSandboxBlocked(ValueError):
    """Model-origin code must never run outside a proven isolated namespace."""


def _node_runtime() -> Path:
    binary = shutil.which("node")
    if binary is None:
        raise ModelCodeSandboxBlocked("Native Node binary not available")
    resolved = Path(binary).resolve(strict=True)
    if resolved.name != "node" or resolved.parent.name != "bin":
        raise ModelCodeSandboxBlocked("Unreviewed Node binary shape")
    runtime = resolved.parent.parent
    if not NODE_SUFFIX.fullmatch(runtime.name):
        raise ModelCodeSandboxBlocked("Must use pinned local Node v24 runtime")
    if not resolved.is_file() or not os.access(resolved, os.X_OK):
        raise ModelCodeSandboxBlocked("Node executable is inaccessible")
    return runtime


def sandbox_argv(
    bwrap: Path,
    node_runtime: Path,
    work: Path,
    command: list[str],
) -> list[str]:
    if (
        not bwrap.is_absolute()
        or not node_runtime.is_dir()
        or not work.is_dir()
        or not HARNESS.is_file()
        or any(not isinstance(arg, str) for arg in command)
        or command[0] != "/runtime/bin/node"
    ):
        raise ModelCodeSandboxBlocked("Invalid local Node or sandbox scope")
    return [
        str(bwrap),
        "--unshare-all",
        "--die-with-parent",  # Includes an ISOLATED network namespace.
        "--ro-bind",
        "/usr",
        "/usr",
        "--symlink",
        "usr/lib",
        "/lib",
        "--symlink",
        "usr/bin",
        "/bin",
        "--ro-bind",
        str(node_runtime.resolve()),
        "/runtime",
        "--ro-bind",
        str(FIXTURES.resolve()),
        "/tests",
        "--bind",
        str(work.resolve()),
        "/work",
        "--proc",
        "/proc",
        "--dev",
        "/dev",
        "--tmpfs",
        "/tmp",  # noqa: S108 - sandbox-private tmpfs, NOT host /tmp
        "--dir",
        "/home",
        "--dir",
        "/home/qa",
        "--clearenv",
        "--setenv",
        "HOME",
        "/home/qa",
        "--setenv",
        "PATH",
        "/runtime/bin:/usr/bin:/bin",
        "--chdir",
        "/work",
        "--",
        *command,
    ]


def _run(
    argv: list[str],
    *,
    work: Path,
    timeout: int,
) -> tuple[int, str, str]:
    try:
        result = subprocess.run(  # noqa: S603 - reviewed fixed Bubblewrap executable/args
            argv,
            cwd=work,
            input="",
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"},
        )
    except subprocess.TimeoutExpired as exc:
        raise ModelCodeSandboxBlocked("Hard timeout in sandboxed code behavior test") from exc
    if (
        len(result.stdout.encode()) > MAX_OUTPUT_BYTES
        or len(result.stderr.encode()) > MAX_OUTPUT_BYTES
    ):
        raise ModelCodeSandboxBlocked("Sandbox output exceeded fixed cap")
    return result.returncode, result.stdout, result.stderr


def _test_counts(tap: str) -> tuple[int, int, int]:
    def last_number(name: str) -> int:
        matches = re.findall(r"(?m)^# " + re.escape(name) + r" ([0-9]+)\s*$", tap)
        if len(matches) != 1:
            raise ModelCodeSandboxBlocked("Missing or duplicate authoritative TAP result")
        return int(matches[0])

    return last_number("tests"), last_number("pass"), last_number("fail")


def audit(timeout: int = 45) -> dict:
    if not 5 <= timeout <= 90:
        raise ModelCodeSandboxBlocked("Invalid bounded sandbox timeout")
    binary = shutil.which("bwrap")
    if binary is None:
        raise ModelCodeSandboxBlocked("Mandatory Bubblewrap missing: refuse native model code")
    bwrap = Path(binary).resolve(strict=True)
    if not bwrap.is_file():
        raise ModelCodeSandboxBlocked("Missing approved Bubblewrap binary")
    runtime = _node_runtime()
    with tempfile.TemporaryDirectory(prefix="mods-p5-original-code-sandbox-") as temp:
        work = Path(temp) / "work"
        staged = stage(FIXTURES, work)
        # Every Node parse and behavior check executes INSIDE the namespace,
        # NEVER in the unconfined Python host. The raw snippets are not
        # imported by Python and no model/network access is performed.
        syntax_count = 0
        for module in CANDIDATE_FILENAMES.values():
            argv = sandbox_argv(
                bwrap,
                runtime,
                work,
                ["/runtime/bin/node", "--check", "/work/candidates/" + module],
            )
            code, stdout, stderr = _run(argv, work=work, timeout=timeout)
            if code or stderr or stdout:
                raise ModelCodeSandboxBlocked(f"Candidate has JS parser error: {module}")
            syntax_count += 1
        argv = sandbox_argv(
            bwrap,
            runtime,
            work,
            [
                "/runtime/bin/node",
                "--test",
                "--test-reporter=tap",
                "/tests/observer-contract.test.mjs",
            ],
        )
        exit_code, stdout, stderr = _run(argv, work=work, timeout=timeout)
        tested, passed, failed = _test_counts(stdout)
        # 5 groups + 40 shared tests + 3 guarded logger tests = 48.
        if exit_code != 0 or failed != 0 or tested != 48 or passed != 48:
            raise ModelCodeSandboxBlocked(
                "Original candidate failed or skipped a required contract"
            )
        # Negative control: replace only a staged candidate with deliberately
        # incorrect pass-through behavior. No code is executed on the host:
        # the same Bubblewrap network/file boundary applies to this run.
        corrupted = work / "candidates/codex-01.mjs"
        corrupted.write_text(
            "export function register(on) { on('tool.call', async ($,e,next)=>({fake:true}));}"
        )
        neg_code, neg_stdout, _ = _run(argv, work=work, timeout=timeout)
        neg_tests, neg_pass, neg_fail = _test_counts(neg_stdout)
        if neg_code == 0 or neg_fail < 1 or neg_pass == neg_tests:
            raise ModelCodeSandboxBlocked(
                "Intentionally unsafe observer escaped the behavioral gate"
            )
        return {
            "schema_version": 1,
            "target_claude_cli": "2.1.302",
            "execution_surface": "Linux Bubblewrap unprivileged user+PID+mount+network namespaces",
            "actual_host_home_mounted": False,
            "network_namespace_unshared": True,
            "model_network_requests": 0,
            "bubblewrap_only_no_fallback": True,
            "model_code_run_on_unconfined_host": False,
            "model_origin_code_sha256_verified": staged["original_reviewed_source_files"],
            "self_contained_original_modules": staged["full_module_candidates"],
            "synthetically_wrapped_original_fragments": staged[
                "synthetic_fragment_wrapper_candidates"
            ],
            "not_a_mod_js_module_shell_examples_not_executed": staged[
                "shell_documentation_examples_not_executed"
            ],
            "native_node_javascript_syntax_pass": syntax_count,
            "synthetic_observer_contract_test_count": tested,
            "synthetic_observer_contract_tests_passed": passed,
            "synthetic_observer_contract_tests_failed": failed,
            "synthetic_corrupt_downstream_observer_detected": True,
            "synthetic_corrupt_observer_failure_count": neg_fail,
            "whole_claude_code_mod_runtime_semantics_verified": False,
            "official_claude_code_2_1_302_declarations_typechecked": False,
            "actual_claude_mod_host_plugin_test_executed": False,
            "stable_release_authorized": False,
            "raw_native_model_messages_exported": False,
            "original_source_fixture_manifest_sha256": hashlib.sha256(
                (FIXTURES / "manifest.json").read_bytes()
            ).hexdigest(),
            "trusted_behavior_test_sha256": hashlib.sha256(HARNESS.read_bytes()).hexdigest(),
            "node_runtime_major_version": runtime.name.split("-v")[1].split(".")[0],
            "model_generated_code_semantic_scope": "Synthetic event/pass-through only, not real Claude Mod host",
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--timeout", type=int, default=45)
    args = parser.parse_args()
    if args.out.exists() or args.out.is_symlink():
        raise SystemExit("REFUSED: original OS-sandbox semantic result exists")
    try:
        report = audit(args.timeout)
    except (ModelCodeSandboxBlocked, OSError, ValueError, KeyError, subprocess.SubprocessError):
        raise SystemExit("BLOCKED: real OS-isolated native model-code audit failed") from None
    args.out.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    print(
        {
            "reviewed_actual_model_snippets": report["model_origin_code_sha256_verified"],
            "synthetic_behavior_tests_passed": report["synthetic_observer_contract_tests_passed"],
            "network_isolated": True,
            "host_home_exposed": False,
            "whole_claude_mod_runtime_pass": False,
            "stable_release_authorized": False,
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
