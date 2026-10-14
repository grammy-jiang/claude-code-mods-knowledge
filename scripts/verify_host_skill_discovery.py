#!/usr/bin/env python3
"""Model-free NATIVE host Skill discovery probes.

Uses Codex app-server skills/list, Pi Agent's own loadSkillsFromDir, and Claude
Code's plugin manifest validator in isolated temporary directories. No agent
turns, no accounts/tokens printed or copied, no global Skill installation.
"""

from __future__ import annotations

import argparse
import json
import os
import selectors
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SKILL_NAME = "claude-code-mods-development"


def _run(
    command: list[str],
    *,
    env: dict | None = None,
    cwd: Path | None = None,
    stdin: str | None = None,
    timeout: float = 18,
) -> subprocess.CompletedProcess:
    return subprocess.run(  # noqa: S603 -- trusted installed CLI, fixed argv, shell disabled.
        command,
        cwd=cwd,
        env=env,
        input=stdin,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def _pi_skill_lookup(dist: Path, workspace: Path) -> dict:
    binary = shutil.which("pi")
    node = shutil.which("node")
    if not binary or not node:
        return {"status": "unavailable", "reason": "pi or node is not installed"}
    import_index = Path(binary).resolve().parents[1] / "index.js"
    if not import_index.is_file():
        return {"status": "unavailable", "reason": "Pi loader module not available"}
    work = workspace / "pi"
    skills = work / ".agents/skills"
    skills.mkdir(parents=True)
    shutil.copytree(dist / "pi/.agents/skills" / SKILL_NAME, skills / SKILL_NAME)
    code = """
import { pathToFileURL } from 'node:url'
const module = await import(pathToFileURL(process.env.MOD_PI_INDEX).href)
const r = module.loadSkillsFromDir({dir: process.env.MOD_SKILL_DIR, source:'mods-skill-smoke'})
const full = module.formatSkillsForPrompt(r.skills)
console.log(JSON.stringify({
  names: r.skills.map(x=>x.name),
  diagnostics: r.diagnostics.map(x=>x.message || String(x)),
  listedInSystemPrompt: full.includes('claude-code-mods-development')
}))
"""
    env = dict(os.environ, MOD_PI_INDEX=str(import_index), MOD_SKILL_DIR=str(skills))
    completed = _run([node, "--input-type=module", "-e", code], cwd=work, env=env)
    if completed.returncode:
        raise RuntimeError("Pi native skill discovery failed: " + completed.stderr[:400])
    data = json.loads(completed.stdout.strip())
    if (
        data["names"].count(SKILL_NAME) != 1
        or data["diagnostics"]
        or not data["listedInSystemPrompt"]
    ):
        raise RuntimeError(f"Pi native Skill loading/diagnostics mismatch: {data}")
    return {
        "status": "pass",
        "skills_loaded": 1,
        "native_loader": "loadSkillsFromDir",
        "skill_prompt_metadata": True,
    }


def _codex_skill_lookup(dist: Path, workspace: Path) -> dict:
    executable = shutil.which("codex")
    if not executable:
        return {"status": "unavailable", "reason": "codex binary is not installed"}
    work = workspace / "codex"
    skills = work / ".agents/skills"
    skills.mkdir(parents=True)
    shutil.copytree(dist / "codex/.agents/skills" / SKILL_NAME, skills / SKILL_NAME)
    codex_home = work / "codex-home"
    codex_home.mkdir()
    env = dict(os.environ, CODEX_HOME=str(codex_home))
    child = subprocess.Popen(  # noqa: S603 -- local Codex app-server, no shell/inference.
        [executable, "app-server", "--stdio", "-c", "analytics.enabled=false"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        cwd=work,
        text=True,
        bufsize=1,
    )

    def send(message: dict) -> None:
        assert child.stdin is not None
        child.stdin.write(json.dumps(message, separators=(",", ":")) + "\n")
        child.stdin.flush()

    def receive(expected_id: int, timeout: float = 18) -> dict:
        assert child.stdout is not None
        selector = selectors.DefaultSelector()
        selector.register(child.stdout, selectors.EVENT_READ)
        until = time.monotonic() + timeout
        while time.monotonic() < until:
            if not selector.select(min(1.0, max(0, until - time.monotonic()))):
                if child.poll() is not None:
                    break
                continue
            row = child.stdout.readline()
            if not row:
                break
            try:
                message = json.loads(row)
            except ValueError:
                continue
            if message.get("id") == expected_id:
                return message
        raise RuntimeError(
            f"Codex app-server did not answer RPC {expected_id} (exit={child.poll()})"
        )

    try:
        send(
            {
                "method": "initialize",
                "id": 1,
                "params": {
                    "clientInfo": {
                        "name": "mods_ssot_qa",
                        "title": "Mods Skill QA",
                        "version": "0.1.0",
                    }
                },
            }
        )
        init = receive(1)
        if "result" not in init:
            raise RuntimeError("Codex app-server refused initialization")
        send({"method": "initialized"})
        send(
            {"method": "skills/list", "id": 2, "params": {"cwds": [str(work)], "forceReload": True}}
        )
        reply = receive(2)
        if "result" not in reply:
            raise RuntimeError("Codex app-server skills/list unavailable")
        entries = reply["result"].get("data", [])
        matches = [
            skill
            for entry in entries
            for skill in entry.get("skills", [])
            if skill.get("name") == SKILL_NAME
        ]
        if len(matches) != 1 or matches[0].get("enabled") is not True:
            raise RuntimeError("Codex native skills/list did not find one enabled Mods Skill")
        return {
            "status": "pass",
            "skills_loaded": 1,
            "native_loader": "app-server skills/list",
            "enabled": True,
        }
    finally:
        child.terminate()
        try:
            child.communicate(timeout=3)
        except subprocess.TimeoutExpired:
            child.kill()
            child.communicate(timeout=3)


def _claude_manifest_check(dist: Path, workspace: Path) -> dict:
    binary = shutil.which("claude")
    if not binary:
        return {"status": "unavailable", "reason": "claude binary is not installed"}
    work = workspace / "claude"
    plugin = work / ".claude-plugin"
    plugin.mkdir(parents=True)
    skills = work / "skills"
    skills.mkdir()
    shutil.copytree(dist / "claude-code/.claude/skills" / SKILL_NAME, skills / SKILL_NAME)
    manifest = {
        "name": "mods-qa-disposable",
        "version": "0.0.0",
        "description": "Disposable offline Skill package QA only",
        "author": {"name": "Mods Knowledge QA"},
    }
    (plugin / "plugin.json").write_text(json.dumps(manifest) + "\n", encoding="utf-8")
    run = _run([binary, "plugin", "validate", "--strict", str(work), "--json"], cwd=work)
    if run.returncode:
        raise RuntimeError(
            "Claude Code official plugin validation failed: " + run.stdout[:550] + run.stderr[:250]
        )
    data = json.loads(run.stdout)
    if data.get("success") is not True:
        raise RuntimeError("Claude Code plugin manifest validation returned no success")
    return {
        "status": "pass",
        "native_validator": "claude plugin validate --strict",
        "manifest_valid": True,
        "real_skill_invocation": "not_run",
        "note": "Plugin manifest validation is NOT proof that the model discovered or invoked the skill",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    dist = args.dist.resolve()
    if not (dist / "manifests/build-manifest.json").is_file():
        parser.error("Missing compiled artifact build manifest")
    manifest = json.loads((dist / "manifests/build-manifest.json").read_text())
    with tempfile.TemporaryDirectory(prefix="mods-host-qa-") as tmp:
        root = Path(tmp)
        records = {
            "pi_agent": _pi_skill_lookup(dist, root),
            "codex": _codex_skill_lookup(dist, root),
            "claude_code": _claude_manifest_check(dist, root),
        }
    output = {
        "schema_version": 1,
        "status": "native_discovery_only_model_turns_not_run",
        "target": manifest["target"],
        "source_revision": manifest["source_revision"],
        "plugin_zip_sha256": manifest["artifact_sha256"][
            next(
                name
                for name in manifest["artifact_sha256"]
                if name.startswith("packages/claude-code-mods-knowledge-")
            )
        ],
        "host_checks": records,
        "all_available_native_checks_pass": all(
            x["status"] == "pass" for x in records.values() if x["status"] != "unavailable"
        ),
        "claude_code_model_invocation": "not_run",
        "codex_model_invocation": "not_run",
        "pi_agent_model_invocation": "not_run",
        "notes": "No model quota consumed. Native discovery/manifest checks do not prove actual AI answer quality.",
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(output, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    print(json.dumps(output, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
