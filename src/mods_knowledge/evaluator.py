"""P4 offline knowledge-resource evaluation; never infer ChatGPT model success.

Structural coverage proves links and scoped claims exist in generated packages.
Triggering, answer quality, and UI installation require separately recorded
ChatGPT Chat-mode runs and are intentionally reported as NOT_RUN here.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .claims import approved_claims, load_claims
from .compiler import CompilerError, compile_knowledge
from .errors import ClaimError, RegistryError
from .registry import load_registry

_AREA_FILES = {
    "E": "events",
    "S": "state",
    "T": "types",
    "Q": "testing",
    "P": "security",
    "U": "interface",
}
_CATEGORIES = frozenset(("positive", "negative", "boundary"))
_BOUNDARIES = frozenset(
    (
        "abstain_version",
        "ask_version",
        "reject_historical",
        "abstain_surface",
        "reject_untrusted",
        "reject_unsafe",
    )
)
_CLAIM = re.compile(r"K-[0-9]{4,}\Z")
_CASE = re.compile(r"[A-Z][A-Z0-9_-]{3,50}\Z")


class EvaluationError(ValueError):
    """Evaluation suite cannot be verified against the approved knowledge."""


def validate_suite(suite: dict) -> None:
    """Check case inputs but never assume the expected model behavior happened."""
    if not isinstance(suite, dict) or set(suite) != {
        "schema_version",
        "suite_id",
        "target",
        "notes",
        "cases",
    }:
        raise EvaluationError("Unexpected P4 suite structure")
    if suite["schema_version"] != 1 or not isinstance(suite["suite_id"], str):
        raise EvaluationError("Unsupported P4 evaluation suite")
    target = suite["target"]
    if not isinstance(target, dict) or set(target) != {"claude_code_version", "surface"}:
        raise EvaluationError("P4 target requires explicit version and surface")
    cases = suite["cases"]
    if not isinstance(cases, list) or not cases:
        raise EvaluationError("No P4 evaluation cases")
    seen: set[str] = set()
    for case in cases:
        if not isinstance(case, dict) or set(case) != {
            "id",
            "category",
            "prompt",
            "expected_activation",
            "expected_areas",
            "expected_claim_ids",
            "expected_behavior",
            "notes",
        }:
            raise EvaluationError("Malformed P4 evaluation case")
        cid = case["id"]
        if not isinstance(cid, str) or not _CASE.fullmatch(cid) or cid in seen:
            raise EvaluationError(f"Invalid or repeated case ID: {cid!r}")
        seen.add(cid)
        if (
            case["category"] not in _CATEGORIES
            or not isinstance(case["prompt"], str)
            or not case["prompt"].strip()
            or len(case["prompt"]) > 1000
            or type(case["expected_activation"]) is not bool
            or not isinstance(case["expected_areas"], list)
            or not isinstance(case["expected_claim_ids"], list)
            or not isinstance(case["notes"], str)
        ):
            raise EvaluationError(f"{cid}: invalid P4 case metadata")
        areas = case["expected_areas"]
        ids = case["expected_claim_ids"]
        if (
            len(areas) != len(set(areas))
            or not set(areas) <= set(_AREA_FILES)
            or len(ids) != len(set(ids))
            or not all(isinstance(v, str) and _CLAIM.fullmatch(v) for v in ids)
        ):
            raise EvaluationError(f"{cid}: invalid or repeated area/claim reference")
        if case["category"] == "positive":
            if (
                not case["expected_activation"]
                or not areas
                or not ids
                or case["expected_behavior"] != "source_cited"
            ):
                raise EvaluationError(f"{cid}: malformed positive expectation")
        elif case["category"] == "negative":
            if (
                case["expected_activation"]
                or areas
                or ids
                or case["expected_behavior"] != "no_activation"
            ):
                raise EvaluationError(f"{cid}: malformed negative expectation")
        elif (
            not case["expected_activation"]
            or areas
            or ids
            or case["expected_behavior"] not in _BOUNDARIES
        ):
            raise EvaluationError(f"{cid}: malformed boundary expectation")


def _get_suite(suite: Path | dict) -> dict:
    if isinstance(suite, Path):
        try:
            content = json.loads(suite.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise EvaluationError(f"Cannot read P4 suite: {exc}") from exc
    else:
        content = suite
    validate_suite(content)
    return content


def evaluate_suite(root: Path, suite: Path | dict) -> dict[str, Any]:
    """Evaluate offline resource coverage. ChatGPT runtime results remain NOT_RUN."""
    data = _get_suite(suite)
    root = Path(root)
    target = data["target"]
    version = target["claude_code_version"]
    surface = target["surface"]
    try:
        sources = load_registry(root / "sources/registry.json")
        claims = load_claims(
            root / "claims", sources, root / "sources/snapshots", root / "decisions"
        )
        active = {c["claim_id"]: c for c in approved_claims(claims, version, surface)}
        compiled = compile_knowledge(
            root,
            api_version=version,
            surface=surface,
            source_revision="p4-static-evaluation",
        )
    except (ClaimError, CompilerError, RegistryError, OSError, ValueError) as exc:
        raise EvaluationError(
            f"Target version/surface cannot be evaluated with approved Claims: {exc}"
        ) from exc
    base = "common/claude-code-mods-development"
    skill = compiled[f"{base}/SKILL.md"].decode("utf-8")
    head = skill.split("---", 2)[1]
    scoped = (
        "Claude Code Mods" in head
        and "Use when" in head
        and "related plugin security or TypeScript APIs" not in head
    )
    if not scoped:
        raise EvaluationError("Skill activation description is too broad for unrelated topics")
    all_pages = {
        area: compiled[f"{base}/references/{name}.md"].decode("utf-8")
        for area, name in _AREA_FILES.items()
    }
    for word in (
        "unverified",
        "source",
        "target",
        "permission",
        "official",
        "do not activate",
        "untrusted",
        "ask the user",
    ):
        if word not in skill.lower():
            raise EvaluationError(f"Missing required default Skill guard: {word}")
    results = []
    for case in data["cases"]:
        cid = case["id"]
        if case["category"] == "positive":
            claim_set = set(case["expected_claim_ids"])
            missing = claim_set - set(active)
            if missing:
                raise EvaluationError(f"{cid}: unapproved or missing Claim IDs: {sorted(missing)}")
            areas = {
                area for claim_id in claim_set for area in active[claim_id]["areas"]["primary"]
            }
            if areas != set(case["expected_areas"]):
                raise EvaluationError(f"{cid}: source Claims do not match declared resource areas")
            for claim_id in claim_set:
                claim = active[claim_id]
                area = claim["areas"]["primary"][0]
                text = all_pages[area]
                if f"## {claim_id} " not in text:
                    raise EvaluationError(f"{cid}: Claim {claim_id} not in compiled {area} page")
                for evidence in claim["evidence"]:
                    source = sources[evidence["source_id"]]
                    if (
                        evidence["locator"] not in text
                        or source["url"] not in text
                        or source["trust_layer"] not in ("L0", "L1")
                    ):
                        raise EvaluationError(f"{cid}: source traceability incomplete")
        elif case["category"] == "negative":
            if not scoped:
                raise EvaluationError(f"{cid}: the Skill may activate without Mods intent")
        else:
            if "target" not in skill.lower() or "unverified" not in skill.lower():
                raise EvaluationError(f"{cid}: missing version/host abstention guidance")
        results.append(
            {
                "id": cid,
                "category": case["category"],
                "expected_activation": case["expected_activation"],
                "expected_behavior": case["expected_behavior"],
                "static_status": "pass",
                "host_status": "not_run",
            }
        )
    manifest = json.loads(compiled["manifests/build-manifest.json"])
    fingerprints = json.dumps(
        manifest["input_sha256"], sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return {
        "suite_id": data["suite_id"],
        "target": target,
        "source_revision": hashlib.sha256(fingerprints).hexdigest(),
        "approved_claims": len(active),
        "cases_total": len(results),
        "resource_checks_passed": len(results),
        "resource_checks_failed": 0,
        "host_runtime_cases_passed": 0,
        "host_runtime_cases_pending": len(results),
        "activation_accuracy": None,
        "model_response_accuracy": None,
        "model_executed": False,
        "activation_description_scoped": scoped,
        "status": "STATIC_PASS_HOST_NOT_TESTED",
        "host_runtime_caveat": (
            "No ChatGPT Chat-mode plugin installation, auto-activation, or model response "
            "was executed. Offline checks verify source/resource coverage only."
        ),
        "results": results,
    }
