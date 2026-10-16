#!/usr/bin/env python3
"""Safely validate only eligible native Codex model-origin observer code.

The target version is the retained real Claude Code CLI 2.1.296 binary.
Results are *native strict+harmless mock*, NOT unmocked production
downstream tool event semantics or arbitrary JS sandbox certification.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from run_p5_codex_paired import MODEL, PRIVATE, ROOT

CLIVERSION = Path.home() / ".local/share/claude/versions/2.1.296"
FIXTURE = ROOT / "tests/fixtures/mods-async-observer"
CODE = re.compile(
    chr(96) * 3 + r"(?:js|javascript|ts|typescript)?\s*\n(.*?)" + chr(96) * 3,
    re.I | re.S,
)
NAMED = re.compile(r"^\s*export\s+function\s+register\s*\(\s*on\s*\)", re.M)
RISK = re.compile(
    r"\b(?:import|require|fetch|eval|Function|exec|spawn|process|fs|https|http)\s*\(",
    re.I,
)


def main() -> int:
    version = subprocess.run(  # noqa: S603 - original verified CLI binary
        [str(CLIVERSION), "--version"],
        capture_output=True,
        text=True,
        timeout=8,
        check=True,
    ).stdout.strip()
    if "2.1.296" not in version or not FIXTURE.is_dir():
        raise RuntimeError("Reviewed target CLI or safe Mod fixture missing")
    candidates = []
    for trial in (1, 2, 3):
        wire = PRIVATE / "paired" / MODEL / "POS-E-01" / f"trial-{trial}/native-wire.jsonl"
        if not wire.exists():
            continue
        answers = []
        for line in wire.read_text(errors="replace").splitlines():
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if event.get("method") == "item/completed":
                item = event.get("params", {}).get("item")
                if isinstance(item, dict) and item.get("type") == "agentMessage":
                    if isinstance(item.get("text"), str):
                        answers.append(item["text"])
        final = "\n".join(answers)
        for idx, source in enumerate(CODE.findall(final)):
            safe = (
                len(source) < 3500
                and bool(NAMED.search(source))
                and "tool.call" in source
                and "next(e)" in source
                and not RISK.search(source)
            )
            record = {
                "case_id": "POS-E-01",
                "trial": trial,
                "block": idx,
                "code_sha256": hashlib.sha256(source.encode()).hexdigest(),
                "named_register": bool(NAMED.search(source)),
                "eligible_safe_fixture": safe,
                "strict_exit": None,
                "native_test_exit": None,
                "native_mock_passed": False,
            }
            if safe:
                owned = PRIVATE / "observer_native_model_origin" / f"trial-{trial}-block-{idx}"
                owned.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                if owned.exists():
                    raise RuntimeError("Refuse to overwrite an existing private fixture")
                shutil.copytree(FIXTURE, owned)
                (owned / "hooks/register.js").write_text(source)
                env = os.environ.copy()
                for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY"):
                    env.pop(k, None)
                try:
                    validation = subprocess.run(  # noqa: S603 - literal native CLI, scoped test fixture
                        [str(CLIVERSION), "plugin", "validate", "--strict", str(owned)],
                        capture_output=True,
                        text=True,
                        timeout=25,
                        env=env,
                    )
                    test = subprocess.run(  # noqa: S603 - literal native CLI, offline fixtures only
                        [str(CLIVERSION), "plugin", "test", str(owned)],
                        capture_output=True,
                        text=True,
                        timeout=35,
                        env=env,
                    )
                    record["strict_exit"] = validation.returncode
                    record["native_test_exit"] = test.returncode
                    record["native_mock_passed"] = (
                        validation.returncode == 0
                        and test.returncode == 0
                        and "1 pass" in (test.stdout + test.stderr)
                    )
                except subprocess.TimeoutExpired:
                    record["native_mock_timeout"] = True
            candidates.append(record)
    result = {
        "reviewed_native_target": "Claude Code CLI 2.1.296",
        "original_case": "POS-E-01",
        "candidate_code_blocks": len(candidates),
        "complete_named_register_candidates": sum(x["eligible_safe_fixture"] for x in candidates),
        "native_strict_and_mock_passed": sum(x["native_mock_passed"] for x in candidates),
        "results": candidates,
        "real_downstream_event_identity_verified": False,
        "production_qualified": False,
        "no_model_answer_text_public": True,
    }
    private = PRIVATE / "observer_model_origin_results.json"
    if private.exists():
        raise RuntimeError("Cannot overwrite prior immutable model-origin QA")
    private.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    private.chmod(0o600)
    print(
        json.dumps(
            {
                "blocks": result["candidate_code_blocks"],
                "eligible": result["complete_named_register_candidates"],
                "native_strict_and_mock_passed": result["native_strict_and_mock_passed"],
                "real_downstream_event_identity_verified": False,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
