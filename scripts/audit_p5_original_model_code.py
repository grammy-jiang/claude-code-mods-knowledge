#!/usr/bin/env python3
"""Hash-pin exact native Codex/Sonnet answer code and stage WITHOUT execution.

Only the five inspected, non-network observer snippets from actual completed
CLI302 native model traces are permitted. Sonnet's two bare hook fragments
require a clearly labeled synthetic register(on) wrapper. The separate
Sonnet Bash documentation example is NEVER treated as executable Mod code.

Actual code execution is the responsibility of a separate Linux Bubblewrap
runner with no host Home mount and no network; this script only writes files.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "evals/fixtures/p5-native-model-code-302"
CODE_FILES = {
    "codex/01.mjs",
    "codex/02.mjs",
    "sonnet/01-fragment.js",
    "sonnet/02-fragment.js",
    "sonnet/03-module.js",
}
EXPECTED = {
    "codex/01.mjs": "50a7d802386832da143ea488aa135dab5370b6d212a2bfab28a371740f4670d1",
    "codex/02.mjs": "0323e52088fd786510cef77b8d302aa6543637f6195ad30758c74ee118298633",
    "sonnet/01-fragment.js": "d4f98022545244eaf5ade30d2bd6099bc00c21fc1ff2ee145a506e5ddee30202",
    "sonnet/02-fragment.js": "a9462aca5cde33fd2e0503e0e84412fe9c63179365987de3580fb2d13045af8f",
    "sonnet/03-module.js": "8961117ce40da1efc4d848be91c9a2105d0704fe617727107e5c13698ac956df",
}
FORBIDDEN = re.compile(
    r"\b(?:require|import|process|fetch|WebSocket|"
    r"XMLHttpRequest|child_process|globalThis|document|window|Bun|Deno)\b"
    r"|__proto__|https?://|file://|(?:\.\./|/home/|/Users/)",
    re.I,
)
CANDIDATE_FILENAMES = {
    "codex/01.mjs": "codex-01.mjs",
    "codex/02.mjs": "codex-02.mjs",
    "sonnet/01-fragment.js": "sonnet-01.mjs",
    "sonnet/02-fragment.js": "sonnet-02.mjs",
    "sonnet/03-module.js": "sonnet-03.mjs",
}


class ModelCodeEvidenceBlocked(ValueError):
    """Unreviewed, altered, or unsafe code cannot reach the test sandbox."""


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def validate_manifest(root: Path = FIXTURES) -> dict:
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise ModelCodeEvidenceBlocked("Missing original reviewed code manifest")
    data = json.loads(manifest_path.read_text())
    sources = data.get("model_candidate_sources")
    if (
        data.get("schema_version") != 1
        or data.get("reviewed_claude_cli") != "2.1.302"
        or data.get("tests_do_not_grant_actual_claude_mods_host_acceptance") is not True
        or not isinstance(sources, list)
        or len(sources) != 3
    ):
        raise ModelCodeEvidenceBlocked("Wrong model source/CLI/provenance manifest")
    codex, sonnet, doc = sources
    if (
        codex.get("original_full_reply_sha256")
        != "691e6d36376b0118ea319c279375f51828d585d15d14956a384b791ee6f6bd2e"
        or codex.get("native_wire_sha256")
        != "e2114bc10f10091352c3b7291d194daf4f38f8ea60deb7a9b374b7bbe1e1d135"
        or codex.get("requested_model") != "gpt-6.1-sol"
        or sonnet.get("case_id") != "POS-E-01"
        or sonnet.get("source", {}).get("answer_sha256")
        != "5383f45f79bb4a301c49c99319a551ec738e419f770ac64beda465774e05beb7"
        or doc.get("case_id") != "POS-Q-01"
        or doc.get("source", {}).get("answer_sha256")
        != "de666504c2aa3c4517e7b9928ceda64319151c5307c73b62832e6dd176a8f8b5"
    ):
        raise ModelCodeEvidenceBlocked("Original model wire or reply identity changed")
    if doc["source"]["blocks"] != [
        {
            "ordinal": 1,
            "language": "bash",
            "code_sha256": "161c150f1bdc26adc623e39f20ea4f4ab54ee77bfb6053bb86760a5ccc4c1df3",
            "code_length": 27,
            "fixture_path": None,
            "module_self_contained": False,
            "is_shell_command_not_mod_code": True,
        }
    ]:
        raise ModelCodeEvidenceBlocked("Sonnet documentation shell example changed")
    cases = {
        **{x["path"]: x["code_sha256"] for x in codex["fixtures"]},
        **{x["fixture_path"]: x["code_sha256"] for x in sonnet["source"]["blocks"]},
    }
    if cases != EXPECTED:
        raise ModelCodeEvidenceBlocked("Code block SHA/identity registry changed")
    actual_files = {
        str(path.relative_to(root))
        for path in root.rglob("*")
        if path.is_file()
        and path.suffix in (".js", ".mjs")
        and path.name != "observer-contract.test.mjs"
    }
    if actual_files != CODE_FILES:
        raise ModelCodeEvidenceBlocked("Missing or unexpected model-origin code file")
    for relative, expected_hash in EXPECTED.items():
        path = root / relative
        if not path.is_file() or path.is_symlink() or path.stat().st_size > 512:
            raise ModelCodeEvidenceBlocked("Model-origin code fixture is untrusted")
        raw = path.read_bytes()
        if sha(raw) != expected_hash:
            raise ModelCodeEvidenceBlocked(f"Code block mutated: {relative}")
        text = raw.decode("utf-8")
        if FORBIDDEN.search(text) or re.search(r"\b(?:eval|Function)\s*\(", text):
            raise ModelCodeEvidenceBlocked("Unreviewed network/file/process API in model code")
        if not (
            "on(" in text
            and "tool.call" in text
            and "next(e)" in text
            and "async ($, e, next)" in text
        ):
            raise ModelCodeEvidenceBlocked("Not the approved 3-argument tool.call observer")
        is_fragment = "fragment" in relative
        if is_fragment and "export function register(" in text:
            raise ModelCodeEvidenceBlocked("Fragment was relabeled as a complete module")
        if not is_fragment and not text.lstrip().startswith("export function register(on)"):
            raise ModelCodeEvidenceBlocked("Missing complete on-register exported entrypoint")
    return data


def stage(original_root: Path, destination: Path) -> dict:
    validate_manifest(original_root)
    if destination.exists() or destination.is_symlink():
        raise ModelCodeEvidenceBlocked("Refuse to replace original model test staging directory")
    destination.mkdir(parents=True, mode=0o700)
    candidates = destination / "candidates"
    candidates.mkdir(mode=0o700)
    rows = []
    for name, fixture in CANDIDATE_FILENAMES.items():
        original = (original_root / name).read_bytes()
        text = original.decode("utf-8")
        fragment = "fragment" in name
        if fragment:
            adapted = "export function register(on) {\n" + text + "\n}"
        else:
            adapted = text
        path = candidates / fixture
        path.write_text(adapted)
        path.chmod(0o600)
        rows.append(
            {
                "model_code_fixture": name,
                "source_code_sha256": sha(original),
                "sandbox_module_sha256": sha(adapted.encode()),
                "sandbox_module_name": fixture,
                "requires_test_only_register_wrapper": fragment,
                "syntax_checked_only_not_type_or_production_certified": True,
            }
        )
    result = {
        "schema_version": 1,
        "original_reviewed_source_files": len(rows),
        "full_module_candidates": 3,
        "synthetic_fragment_wrapper_candidates": 2,
        "shell_documentation_examples_not_executed": 1,
        "actual_claude_mod_host_runtime_tested": False,
        "model_code_run_on_host_without_sandbox": False,
        "per_case": rows,
    }
    report = destination / "stage-manifest.json"
    report.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    report.chmod(0o600)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = stage(FIXTURES, args.out)
    print(
        {
            "original_code_sha_pinned": result["original_reviewed_source_files"],
            "self_contained_modules": result["full_module_candidates"],
            "wrapped_fragments_not_installable_directly": result[
                "synthetic_fragment_wrapper_candidates"
            ],
            "no_model_code_executed": True,
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
