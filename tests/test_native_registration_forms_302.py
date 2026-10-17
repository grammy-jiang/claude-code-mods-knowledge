"""Reproducible Mac Claude CLI 2.1.302 named Mod registration loader matrix.

All snippets are fixed assistant-authored synthetic Mod code. No model-origin
artifact, account, network or real file/tool operation is executed. CI hosts
without this exact target binary report SKIP, never a fabricated native pass.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

HOOK = "on('tool.call', async ($, e, next) => next(e))"
FORMS = (
    ("named-function", f"export function register(on) {{ {HOOK} }}", True),
    ("named-arrow-const", f"export const register = (on) => {{ {HOOK} }}", True),
    ("named-async-arrow", f"export const register = async (on) => {{ {HOOK} }}", True),
    ("named-const-function", f"export const register = function(on) {{ {HOOK} }}", True),
    (
        "local-const-export-alias",
        f"const register = (on) => {{ {HOOK} }};\nexport {{ register }};",
        True,
    ),
    (
        "const-destructured-arrow",
        f"export const register = ({{ on }}) => {{ {HOOK} }}",
        False,
    ),
    (
        "const-destructured-function",
        f"export const register = function({{ on }}) {{ {HOOK} }}",
        False,
    ),
    (
        "local-const-destructured-export",
        f"const register = ({{ on }}) => {{ {HOOK} }};\nexport {{ register }};",
        False,
    ),
    (
        "factory-initializer",
        f"function createRegister() {{ return (on) => {{ {HOOK} }} }}\n"
        "export const register = createRegister();",
        False,
    ),
    (
        "indirect-variable-assignment",
        f"const fn = (on) => {{ {HOOK} }};\nexport const register = fn;",
        False,
    ),
)


def _target_cli() -> str:
    executable = shutil.which("claude")
    if not executable:
        pytest.skip("Real Claude Code CLI is unavailable: native loader untested")
    result = subprocess.run(  # noqa: S603 -- fixed installed binary + fixed version arg
        [executable, "--version"], check=False, capture_output=True, text=True, timeout=15
    )
    if result.returncode or "2.1.302" not in result.stdout:
        pytest.skip("Installed Claude CLI version is not reviewed target 2.1.302")
    return executable


@pytest.mark.parametrize(("name", "source", "accepted"), FORMS, ids=[x[0] for x in FORMS])
def test_bounded_target_loader_registration_forms(
    tmp_path: Path, name: str, source: str, accepted: bool
) -> None:
    executable = _target_cli()
    root = tmp_path / name
    (root / ".claude-plugin").mkdir(parents=True)
    (root / "hooks").mkdir()
    (root / "tests").mkdir()
    (root / ".claude-plugin/plugin.json").write_text(
        json.dumps(
            {
                "name": "mods-registration-form-synthetic",
                "version": "0.0.1",
                "description": "Offline source-controlled registration-form probe",
                "author": {"name": "Mods QA"},
            }
        )
    )
    (root / "hooks/hooks.json").write_text(
        json.dumps({"description": "Safe synthetic tool observer", "modules": ["./register.js"]})
    )
    (root / "hooks/register.js").write_text(source + "\n")
    (root / "tests/probe.test.ts").write_text(
        """import { expect, test } from 'claude-code/testing'
test('single safe mocked Read tool passes through observer', async ($, on) => {
  on('tool.call', () => ({ result: 'SAFE_SYNTHETIC_STUB' }))
  const actual = await $.tool.call({ tool: 'Read', file_path: 'NEVER_REAL_FILE' })
  expect(actual.result).toBe('SAFE_SYNTHETIC_STUB')
})
"""
    )
    strict = subprocess.run(  # noqa: S603 -- bounded locally authored files, no network
        [executable, "plugin", "validate", "--strict", str(root)],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    mocked = subprocess.run(  # noqa: S603 -- bounded local disposable mock
        [executable, "plugin", "test", str(root)],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if accepted:
        assert strict.returncode == 0, (strict.stdout + strict.stderr)[-500:]
        assert mocked.returncode == 0, (mocked.stdout + mocked.stderr)[-500:]
        assert "1 pass" in mocked.stdout + mocked.stderr
        assert "0 fail" in mocked.stdout + mocked.stderr
    else:
        assert strict.returncode != 0, f"Unexpected strict acceptance of {name}"
        assert mocked.returncode != 0, f"Unexpected mock acceptance of {name}"
        diagnostic = strict.stdout + strict.stderr
        if "destructured" in name:
            assert "the parameter that receives on is not a plain name" in diagnostic
        else:
            assert "register is exported as something other than a const function" in diagnostic
