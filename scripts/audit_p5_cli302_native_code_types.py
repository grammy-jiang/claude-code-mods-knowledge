#!/usr/bin/env python3
"""Offline TypeScript check of EXACT original Codex/Sonnet observer snippets.

Obtains core API .d.ts from the real local CLI 2.1.302 executable, with
Mac/Pi identical source fingerprints. Never uses the old 2.1.277 GitHub
types; never publishes 652KB of upstream declaration text.

Typechecking makes a harmless JSDoc param annotation on each private test
copy and wraps two incomplete Sonnet handler fragments. Original byte hashes
remain unchanged. The separate suggested repair replaces only unsupported
console.log diagnostic calls with documented $.ui.log(..., {to:'debug'}).
This is NOT a production Mod code change or native interactive approval.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from audit_p5_original_model_code import CANDIDATE_FILENAMES, EXPECTED, FIXTURES, validate_manifest
from extract_reviewed_cli302_core_types import DECLARATION_SHA256, extract_from_binary

EXPECTED_TYPE_ERRORS = {
    "codex-02.mjs": "TS2584",
    "sonnet-02.mjs": "TS2584",
    "sonnet-03.mjs": "TS2584",
}
TSC_DIAGNOSTIC_RE = re.compile(
    r"^hooks/(?P<file>[\w.-]+)\((?P<line>\d+),(?P<column>\d+)\): "
    r"error (?P<code>TS\d+): (?P<description>.*)$"
)


class CoreTypeAuditBlocked(ValueError):
    """The source, pinned declaration, compiler, or model code did not match."""


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _stage(work: Path, *, declarations: bytes, repair: bool) -> dict:
    validate_manifest()
    work.mkdir(mode=0o700)
    (work / "types").mkdir()
    (work / "hooks").mkdir()
    core = work / "types/claude-code.d.ts"
    core.write_bytes(b"// Written by Claude Code 2.1.302.\n" + declarations)
    core.chmod(0o600)
    rows = []
    for name, output in CANDIDATE_FILENAMES.items():
        file = FIXTURES / name
        raw = file.read_bytes()
        if sha(raw) != EXPECTED[name]:
            raise CoreTypeAuditBlocked("Original model code SHA mismatch")
        code = raw.decode("utf-8")
        wrapped = "fragment" in name
        if wrapped:
            code = "export function register(on) {\n" + code + "\n}"
        modified = False
        if repair and 'console.log("observer done")' in code:
            if code.count('console.log("observer done")') != 1:
                raise CoreTypeAuditBlocked("Multiple unreviewed diagnostic edits")
            code = code.replace(
                'console.log("observer done")',
                '$.ui.log("observer done", { to: "debug" })',
            )
            modified = True
        code = "/** @param {import('claude-code').On} on */\n" + code
        output_file = work / "hooks" / output
        output_file.write_text(code)
        output_file.chmod(0o600)
        rows.append(
            {
                "source_name": name,
                "original_model_code_sha256": sha(raw),
                "private_staged_copy_sha256": sha(code.encode()),
                "fragment_wrapped_for_test_only": wrapped,
                "proposed_diagnostic_uses_ui_log": modified,
            }
        )
    expected_repair_count = 3 if repair else 0
    if sum(row["proposed_diagnostic_uses_ui_log"] for row in rows) != expected_repair_count:
        raise CoreTypeAuditBlocked("Only three source-identified log calls may be replaced")
    # TS harness checks each exported function conforms to the exact Register.
    statements = ["import type { Register } from 'claude-code';"]
    for index, filename in enumerate(sorted(CANDIDATE_FILENAMES.values())):
        statements.extend(
            [
                f"import {{ register as register{index} }} from './hooks/{filename}';",
                f"const check{index}: Register = register{index};",
                f"void check{index};",
            ]
        )
    (work / "register-type-constraints.ts").write_text("\n".join(statements) + "\n")
    tsconfig = {
        "compilerOptions": {
            "target": "es2023",
            "lib": ["es2023"],
            "module": "esnext",
            "moduleResolution": "bundler",
            "strict": True,
            "noUncheckedIndexedAccess": True,
            "allowJs": True,
            "checkJs": True,
            "noEmit": True,
            "skipLibCheck": True,
            "types": [],
            "noErrorTruncation": True,
        },
        "include": [
            "types/*.d.ts",
            "hooks/*.mjs",
            "register-type-constraints.ts",
        ],
    }
    (work / "tsconfig.json").write_text(json.dumps(tsconfig, indent=2) + "\n")
    return {
        "files": rows,
        "tsconfig_sha256": sha((work / "tsconfig.json").read_bytes()),
        "type_source_sha256": sha(declarations),
    }


def parse_diagnostics(text: str) -> list[dict]:
    diagnostics = []
    for line in text.splitlines():
        m = TSC_DIAGNOSTIC_RE.fullmatch(line.strip())
        if not m:
            raise CoreTypeAuditBlocked("Unrecognized compiler diagnostic: no silent pass")
        row = m.groupdict()
        diagnostics.append(
            {
                "file": row["file"],
                "line": int(row["line"]),
                "column": int(row["column"]),
                "code": row["code"],
                "description_signal": (
                    "unknown_console_global"
                    if row["code"] == "TS2584"
                    and "Cannot find name 'console'" in row["description"]
                    else "unreviewed"
                ),
            }
        )
    return diagnostics


def _tsc(work: Path, executable: str) -> tuple[int, list[dict]]:
    node = shutil.which("node")
    if node is None or not Path(node).is_file():
        raise CoreTypeAuditBlocked("Pinned local Node runtime unavailable")
    result = subprocess.run(  # noqa: S603 - native TypeScript CLI, noEmit only
        [executable, "-p", str(work / "tsconfig.json"), "--pretty", "false"],
        cwd=work,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
        env={
            "PATH": str(Path(node).parent) + ":/usr/bin:/bin",
            "LANG": "C.UTF-8",
        },
    )
    if result.returncode not in (0, 2) or result.stderr:
        raise CoreTypeAuditBlocked("Unexpected local TypeScript compiler failure")
    return result.returncode, parse_diagnostics(result.stdout)


def audit(cli_binary: Path) -> dict:
    raw, src = extract_from_binary(cli_binary)
    tsc = shutil.which("tsc")
    if tsc is None:
        raise CoreTypeAuditBlocked("Installed native TypeScript compiler unavailable")
    tsv = subprocess.run(  # noqa: S603 - version only
        [tsc, "--version"],
        capture_output=True,
        text=True,
        timeout=8,
        check=True,
    ).stdout.strip()
    if tsv != "Version 6.0.3":
        raise CoreTypeAuditBlocked("Unreviewed TypeScript compiler version")
    with tempfile.TemporaryDirectory(prefix="mods302-core-typecheck-") as tmp:
        root = Path(tmp)
        original = _stage(root / "original", declarations=raw, repair=False)
        failed_rc, original_errors = _tsc(root / "original", tsc)
        found = {x["file"]: x["code"] for x in original_errors}
        if (
            failed_rc != 2
            or len(original_errors) != 3
            or found != EXPECTED_TYPE_ERRORS
            or any(x["description_signal"] != "unknown_console_global" for x in original_errors)
        ):
            raise CoreTypeAuditBlocked("Original source type errors differ from reproduction")
        amended = _stage(root / "proposed-repair", declarations=raw, repair=True)
        amended_rc, amended_errors = _tsc(root / "proposed-repair", tsc)
        if amended_rc != 0 or amended_errors:
            raise CoreTypeAuditBlocked("Test-only approved API logging changes still fail types")
        candidates = []
        for source in original["files"]:
            name = source["source_name"]
            output = CANDIDATE_FILENAMES[name]
            entry = next(x for x in amended["files"] if x["source_name"] == name)
            candidates.append(
                {
                    "origin": name,
                    "original_sha256": source["original_model_code_sha256"],
                    "original_core_typecheck_pass": output not in found,
                    "original_type_diagnostic": found.get(output),
                    "fragment_has_synthetic_wrapper": source["fragment_wrapped_for_test_only"],
                    "proposed_ui_log_replacement_applied": entry["proposed_diagnostic_uses_ui_log"],
                    "test_only_remediation_core_typecheck_pass": True,
                    "actual_model_generated_code_unchanged_in_git": True,
                }
            )
    return {
        "schema_version": 1,
        "target_claude_cli": "2.1.302",
        "typescript_version": tsv,
        "source": "same embedded official core .d.ts in Mac and Pi CLI2.1.302 binaries",
        "core_declarations_sha256": DECLARATION_SHA256,
        "core_declarations_length": len(raw),
        "source_native_binary_sha256": src["native_binary_sha256"],
        "original_model_snippets_sha256_verified": 5,
        "original_pass": 2,
        "original_fail": 3,
        "original_known_console_type_errors": 3,
        "test_only_ui_log_remediation_typecheck_pass": 5,
        "diagnostic_errors": original_errors,
        "original_cases": candidates,
        "only_local_no_emit_typechecking_used": True,
        "model_or_account_network_requests": 0,
        "original_model_code_executed_during_typecheck": False,
        "runtime_generated_builtin_tool_type_merge_verified": False,
        "real_interactive_mod_host_permission_semantics_verified": False,
        "whole_model_generated_code_semantics_approved": False,
        "stable_release_authorized": False,
        "proprietary_full_declaration_exported_to_public_git": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cli-binary", type=Path, default=Path.home() / ".local/share/claude/versions/2.1.302"
    )
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists() or args.out.is_symlink():
        raise SystemExit("REFUSED: original source-pinned typecheck audit already exists")
    try:
        report = audit(args.cli_binary)
    except (CoreTypeAuditBlocked, OSError, ValueError, subprocess.SubprocessError):
        raise SystemExit("BLOCKED: source/TypeScript/CLI302 audit did not complete") from None
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(
        {
            "original_exact_cli302_core_types_pass": report["original_pass"],
            "original_type_errors": report["original_fail"],
            "test_only_diagnostic_rewrite_typechecks": report[
                "test_only_ui_log_remediation_typecheck_pass"
            ],
            "real_interactive_permissions_verified": False,
            "stable_release_authorized": False,
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
