"""Version-pinned, deterministic Mods task routing and minimal evidence packs.

No model inference, private conversation retention, HTTP fetch or source edits.
All API facts and original official URL fragments come from approved SSOT
Claims; keyword routing rules are *non-authoritative* dispatch metadata.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping
from urllib.parse import urlsplit

from .claims import approved_claims
from .errors import ClaimError

TARGET_VERSION = "2.1.296"
MAX_PROMPT_CHARS = 12000
MAX_EVIDENCE_CLAIMS = 6
_VERSION = re.compile(r"(?<!\d)(\d+\.\d+\.\d+)(?!\d)")
# Never treat a Python/Node/Codex runtime version as the Mods API version.
# Match the IMMEDIATE software label adjacent to each semver, not all
# product names across a long prompt.
_INCIDENTAL_VERSION_PREFIX = re.compile(
    r"\b(?:python|node(?:\.js)?|typescript|codex|pi\s+agent|"
    r"pytest|npm|macos|uv|ruby|rustc|golang|go)\s*(?:v(?:ersion)?\s*)?$",
    re.I,
)
_CURRENT_API = re.compile(
    r"\b(?:latest|newest|up[- ]to[- ]date|today['’]?s|"
    r"currently supported|as of today)\b|"
    r"\bcurrent\s+(?:claude|mods?|api|plugin|official|release|specification|version)\b|"
    r"\b(?:supported|available|released)\s+(?:right\s+)?now\b|"
    r"最新|现行|最新版|当前(?:的)?(?:\s*API|版本|规范|正式版|支持|功能)|"
    r"目前(?:官方|最新|支持|版本)|现在(?:还)?(?:支持|可以|能|有哪些|是什么)",
    re.I,
)
_UNKNOWN_VERSION = re.compile(
    r"\b(?:forgot(?:\s+which)?\s+version|"
    r"(?:don't|do not)\s+know\s+(?:the\s+)?version|"
    r"unknown\s+(?:cli\s+)?version|verify\s+compatibility)\b|"
    r"版本(?:不明|未知)|忘(?:记|了).*版本",
    re.I,
)
_UNREVIEWED_SURFACE = re.compile(
    r"\b(?:vs\s*code|vscode|desktop|headless|jetbrains)\b|桌面(?:版|端)|集成开发环境",
    re.I,
)
_NONCLI_IMPL = re.compile(
    r"\b(?:build|implement|create|generate|write|run|guarantee|"
    r"verified|support(?:ed)?)\b|(?:实现|开发|生成|保证|支持|确保).*(?:界面|集成|桌面|代码)",
    re.I,
)
_UNSAFE_SCOPE = re.compile(
    r"\b(?:ignore\s+official\s+docs|skip\s+permissions|"
    r"bypass\s+permissions|upload\s+(?:environment\s+)?secrets|"
    r"full\s+account\s+control\s+without\s+inspection)\b|"
    r"绕过权限|上传.*(?:密钥|凭据)",
    re.I,
)
_SHORT_MODS = re.compile(
    r"\bmods?\s+(?:observer|middleware|hook|test|event|api|state|ui|pane|"
    r"tool\.call|2\.1\.\d{3,})\b|"
    r"\b(?:test|testing|create|build|implement)\s+(?:a\s+)?mods?\b",
    re.I,
)
_MODS = re.compile(
    r"claude(?:\s+code)?\s+mods?\b|"
    r"claude\s+plugin\s+(?:test|validate)\b|"
    r"\btool\.call\b|\bui\.render\b|"
    r"\$\.(?:state|store|ui)\b|"
    r"\bregister\s*\(\s*on\s*\)|"
    r"\bmod\s+(?:hook|plugin|manifest|test|event|api|offline)\b|"
    r"插件.*(?:mods?|hook)|"
    r"claude\s+(?:code\s+)?mod\b",
    re.I,
)
_UNRELATED = (
    re.compile(r"\bnot\s+mods?\b|\bwithout\s+mods?\b", re.I),
    re.compile(r"\b(?:generic|ordinary)\s+(?:python|typescript|mcp|web)\b", re.I),
)
_HISTORY = re.compile(r"claude_code_enable_function_hooks|old\s+(?:mods?\s+)?preview", re.I)
_REGION = {
    "E": re.compile(
        r"tool\.call|observer|middleware|next\(e\)|事件|观察器|hook\s+callback|tool\s+result", re.I
    ),
    "S": re.compile(
        r"\$\.(?:state|store)|reactive|\/clear|\/resume|\/branch|持久|状态|生命周期", re.I
    ),
    "T": re.compile(
        r"register\s*\(\s*on\s*\)|type(?:script)?\s+(?:api|declaration)|manifest|validate|静态|类型",
        re.I,
    ),
    "Q": re.compile(
        r"\.test\.ts|test|offline|mock|stub|diagnostic|无交互|不联网|测试|不登录", re.I
    ),
    "P": re.compile(
        r"permission|security|sandbox|secret|credential|managed|权限|沙箱|密钥|风险|安全", re.I
    ),
    "U": re.compile(r"pane|above\s*prompt|ui\.render|vscode|vs\s*code|desktop|渲染|界面", re.I),
}
# Dispatch signatures, NOT source facts. Each ID below must be approved and
# in-scope at runtime or selection fails closed. A statement/URL is NEVER
# maintained in this mapping.
_PHRASES = (
    ("K-0007", r"observer|观察器|original.*result|原始工具结果|透传|next\(e\)"),
    ("K-0031", r"tool\.call|register\s*\(\s*on\s*\)|观察器|hook\s+callback"),
    ("K-0037", r"observer|观察器|diagnostic|异常传播|logging"),
    ("K-0008", r"immutable|rewrite|不变|复制.*事件"),
    ("K-0009", r"middleware|order|顺序"),
    ("K-0010", r"deny|replace|拒绝|替代|guard\s+bash"),
    ("K-0011", r"lifecycle|生命周期|module|模块变量"),
    ("K-0012", r"\/clear|\/resume|\/branch|loses.*state|恢复"),
    ("K-0013", r"\$\.store.*(?:race|并发|同时|共享)|race|竞争"),
    ("K-0014", r"\$\.state.*(?:ui|render|invalidate)|反应式"),
    ("K-0015", r"type(?:script)?\s+(?:api|declaration)|声明"),
    ("K-0016", r"plugin\s+validate|static\s+hook|静态"),
    ("K-0017", r"dynamic(?:ally)?\s+import|static\s+discovery|发现"),
    ("K-0018", r"manifest|directory\s+structure|hooks\.json|目录结构"),
    ("K-0019", r"\.test\.ts|offline|不联网|不登录|test.*mod|测试.*mod"),
    ("K-0033", r"\.test\.ts.*(?:命令|command)|plugin\s+test|测试.*命令|什么.*命令"),
    ("K-0020", r"stub|side\s+effects|side-effects|副作用"),
    ("K-0021", r"mock\s+clock|timer|定时器"),
    ("K-0022", r"ui.*test|render.*test|控件.*测试"),
    ("K-0023", r"sandbox|secret|密钥|沙箱|插件.*风险"),
    ("K-0024", r"third.party|third-party|marketplace|第三方"),
    ("K-0025", r"permission|deny.*ask|权限策略"),
    ("K-0026", r"organization|managed|allowmanagedmodsonly|组织"),
    ("K-0027", r"ui\.render|pane|above\s*prompt"),
    ("K-0028", r"ui\.invalidate|invalidate"),
    ("K-0029", r"onpress|onsubmit|onselect|控件"),
    ("K-0030", r"vs\s*code|vscode|desktop|surfaces|宿主"),
    ("K-0034", r"strict.*manifest|author.*validate"),
    ("K-0035", r"plugin\s+validate.*(?:directory|路径|strict)|strict"),
    ("K-0038", r"register\s*\(\s*on\s*\)|hooks\/register"),
)
_AREA_BY_CLAIM = {
    "K-0007": "E",
    "K-0031": "E",
    "K-0037": "E",
    "K-0008": "E",
    "K-0009": "E",
    "K-0010": "E",
    "K-0011": "S",
    "K-0012": "S",
    "K-0013": "S",
    "K-0014": "S",
    "K-0015": "T",
    "K-0016": "T",
    "K-0017": "T",
    "K-0018": "T",
    "K-0019": "Q",
    "K-0033": "Q",
    "K-0020": "Q",
    "K-0021": "Q",
    "K-0022": "Q",
    "K-0023": "P",
    "K-0024": "P",
    "K-0025": "P",
    "K-0026": "P",
    "K-0027": "U",
    "K-0028": "U",
    "K-0029": "U",
    "K-0030": "U",
    "K-0034": "T",
    "K-0035": "T",
    "K-0038": "T",
}


class EvidenceSelectionError(ValueError):
    """Missing, ambiguous or unreviewed input must not be guessed."""


def _mods_target_versions(text: str) -> list[str]:
    """Extract Mod-target semvers, ignoring clearly labeled toolchain versions.

    An unlabeled semver within an in-scope Mod request remains a target:
    treating it as a harmless unrelated version could leak unreviewed APIs.
    """
    targets: set[str] = set()
    for match in _VERSION.finditer(text):
        before = text[max(0, match.start() - 48) : match.start()]
        if _INCIDENTAL_VERSION_PREFIX.search(before):
            continue
        targets.add(match.group(1))
    return sorted(targets)


def route_task(prompt: str) -> dict:
    """Classify a bounded request, with separately scoped version/host checks.

    The regex router is intentionally conservative.  It does NOT prove that
    newer documentation is unavailable, only that this SSOT cannot verify it.
    """
    if not isinstance(prompt, str) or not 0 < len(prompt.strip()) <= MAX_PROMPT_CHARS:
        raise EvidenceSelectionError("Bounded non-empty user prompt required")
    text = unicodedata.normalize("NFKC", prompt)
    versions = _mods_target_versions(text)
    mods_explicit = bool(_MODS.search(text) or _SHORT_MODS.search(text))
    legacy = "settings.json" in text.lower() and "pretooluse" in text.lower()
    if any(pattern.search(text) for pattern in _UNRELATED) or (
        legacy and not re.search(r"\bmod\s+api\b|tool\.call", text, re.I)
    ):
        return {
            "intent": "unrelated",
            "areas": [],
            "versions": [],
            "reason": "explicit_non_mod_or_legacy_control",
            "target": None,
        }
    if _HISTORY.search(text):
        return {
            "intent": "blocked",
            "areas": [],
            "versions": versions,
            "reason": "unreviewed_legacy_preview_api",
            "target": None,
        }
    if not mods_explicit:
        return {
            "intent": "unrelated",
            "areas": [],
            "versions": [],
            "reason": "no_mod_api_signal",
            "target": None,
        }
    # Source version freshness is a separate property from user intent.
    # "latest" must never be silently converted into the pinned 2.1.296.
    if _CURRENT_API.search(text):
        return {
            "intent": "blocked",
            "areas": [],
            "versions": versions,
            "reason": "current_api_requires_first_party_verification",
            "target": None,
        }
    if _UNSAFE_SCOPE.search(text):
        return {
            "intent": "blocked",
            "areas": [],
            "versions": versions,
            "reason": "untrusted_or_unsafe_instruction",
            "target": None,
        }
    if _UNKNOWN_VERSION.search(text) and not versions:
        return {
            "intent": "blocked",
            "areas": [],
            "versions": [],
            "reason": "unknown_target_version",
            "target": None,
        }
    # Pure comparison questions may be answered as "not verified"; commands
    # to implement or guarantee non-CLI behavior must fail before evidence.
    if _UNREVIEWED_SURFACE.search(text) and _NONCLI_IMPL.search(text):
        return {
            "intent": "blocked",
            "areas": [],
            "versions": versions,
            "reason": "unverified_host_surface",
            "target": None,
        }
    if any(v != TARGET_VERSION for v in versions):
        return {
            "intent": "blocked",
            "areas": [],
            "versions": versions,
            "reason": "unreviewed_version",
            "target": None,
        }
    areas = [code for code, pattern in _REGION.items() if pattern.search(text)]
    return {
        "intent": "mods",
        "areas": areas,
        "versions": versions,
        "reason": None,
        "target": TARGET_VERSION,
    }


def _reviewed_url(entry: Mapping) -> str | None:
    if (
        entry.get("role") != "supports"
        or entry.get("kind") != "official-doc"
        or not str(entry.get("source_id", "")).startswith("M")
        or not isinstance(entry.get("locator"), str)
    ):
        return None
    url = entry["locator"]
    try:
        split = urlsplit(url)
    except ValueError:
        return None
    if (
        split.scheme != "https"
        or split.netloc != "code.claude.com"
        or not split.path.startswith("/docs/en/plugins/mods/")
        or not split.fragment
        or split.username
        or split.password
    ):
        return None
    return url


def select_task_evidence(
    prompt: str,
    claims: Mapping[str, dict],
    *,
    version: str = TARGET_VERSION,
    surface: str = "cli",
) -> dict:
    """Return minimal approved Claim/URL pairs, never a guessed citation.

    This does NOT claim the recipient model opened any reference or that
    a source-supported assertion is semantically correct.
    """
    route = route_task(prompt)
    if route["intent"] != "mods":
        return {**route, "claims": [], "ready": False, "reason": route["reason"]}
    if version != TARGET_VERSION or surface != "cli":
        return {
            **route,
            "intent": "blocked",
            "claims": [],
            "ready": False,
            "reason": "unreviewed_target_or_surface",
        }
    if not isinstance(claims, Mapping):
        raise EvidenceSelectionError("Validated SSOT Claim map required")
    try:
        approved = {item["claim_id"]: item for item in approved_claims(claims, version, surface)}
    except (ClaimError, KeyError, TypeError, ValueError) as exc:
        raise EvidenceSelectionError("Unverified or invalid source map") from exc
    normalized = unicodedata.normalize("NFKC", prompt)
    scores: list[tuple[int, str]] = []
    for cid, expression in _PHRASES:
        if not re.search(expression, normalized, re.I):
            continue
        expected_area = _AREA_BY_CLAIM[cid]
        if expected_area not in route["areas"]:
            continue
        if cid not in approved or expected_area not in approved[cid]["areas"]["primary"]:
            raise EvidenceSelectionError(
                "Routing metadata points to an unapproved or unrelated Claim"
            )
        scores.append((2 if re.search(expression, normalized, re.I) else 1, cid))
    # No speculative fallback from an arbitrary area reference to an exact
    # atomic statement. Require a semantically discriminating match.
    if not scores:
        return {**route, "claims": [], "ready": False, "reason": "no_reviewed_semantic_match"}
    ordered = [cid for _score, cid in sorted(set(scores), key=lambda x: (-x[0], x[1]))]
    # The cap makes overflow a refuse rather than an arbitrary truncation.
    if len(ordered) > MAX_EVIDENCE_CLAIMS:
        return {
            **route,
            "claims": [],
            "ready": False,
            "reason": "ambiguous_too_many_possible_claims",
        }
    pack = []
    for cid in ordered:
        claim = approved[cid]
        urls = sorted({u for e in claim["evidence"] if (u := _reviewed_url(e))})
        if not urls:
            raise EvidenceSelectionError(f"Approved Claim {cid} has no first-party pinned URL")
        pack.append(
            {
                "claim_id": cid,
                "area": _AREA_BY_CLAIM[cid],
                "statement": claim["statement"],
                "official_urls": urls,
                "version": version,
                "surface": surface,
            }
        )
    return {**route, "ready": True, "claims": pack, "reason": None}


def render_evidence_pack(selection: Mapping) -> str:
    """Render a privacy-safe candidate sheet, not a fabricated model answer."""
    if not isinstance(selection, Mapping) or selection.get("ready") is not True:
        raise EvidenceSelectionError("Refuse to render unsupported task evidence")
    cards = selection.get("claims")
    if not isinstance(cards, list) or not cards or len(cards) > MAX_EVIDENCE_CLAIMS:
        raise EvidenceSelectionError("Invalid evidence pack cardinality")
    lines = [
        "# Target-scoped selected Mod evidence",
        "",
        f"Target: Claude Code {TARGET_VERSION}, CLI only.",
        "These are approved SSOT facts, not evidence of model reading or live runtime validation.",
        "Use only Claim/URL pairs relevant to the task; preserve exact fragments.",
        "",
    ]
    for entry in cards:
        if not isinstance(entry, Mapping):
            raise EvidenceSelectionError("Invalid evidence item")
        cid = entry.get("claim_id")
        urls = entry.get("official_urls")
        statement = entry.get("statement")
        if not isinstance(cid, str) or not re.fullmatch(r"K-\d{4,}", cid):
            raise EvidenceSelectionError("Invalid atomic Claim ID")
        if (
            not isinstance(urls, list)
            or not urls
            or any(
                not isinstance(u, str)
                or _reviewed_url(
                    {"role": "supports", "kind": "official-doc", "source_id": "M", "locator": u}
                )
                != u
                for u in urls
            )
        ):
            raise EvidenceSelectionError("Unapproved or malformed official URL")
        if not isinstance(statement, str) or len(statement) > 3000:
            raise EvidenceSelectionError("Invalid SSOT assertion")
        lines.extend([f"## {cid}", f"Guidance: {statement}"])
        lines.extend(f"Evidence: {cid} — {url}" for url in urls)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
