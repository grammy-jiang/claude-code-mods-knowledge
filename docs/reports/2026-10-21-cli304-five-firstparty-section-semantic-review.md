# Claude Code CLI 2.1.304: five exact current official section reviews

**Review time:** 2026-10-21 AEDT. **Release status:** HOLD, no CLI304 Claim approval.

The five existing high-risk Claim **candidates** K-0070 through K-0074 were evaluated against the original captured first-party HTML and independently obtained Markdown from 2026-10-20. All raw official documents are retained **privately**; no upstream Markdown/HTML was committed or reproduced into the public repository. The original approved 302 source Registry pins and all Claim/decision records remain unchanged.

Three official source revision review records were created under `sources/reviews/revisions/M003`, `M004` and `M006`, keyed by the exact newly observed source HTML SHA256. Each contains the matching Markdown SHA256, the current official HTML anchor, exact Markdown heading, inclusive line start/end, a SHA256 of the exact section bytes, a declared reviewer label and a timezone-aware review timestamp. This is an auditable *section-review attestation*, **not** a cryptographic reviewer signature, new semantic API guarantee or real user permission test. All five section fingerprints were independently recomputed from the private current first-party source text and checked against original captured bytes.

## Claim-by-Claim semantic review

| Candidate | Current first-party section | What it directly proves | What it does **not** prove |
| --- | --- | --- | --- |
| **K-0070**, human-only `decider: 'person'` | Events, `#approve-or-refuse-a-tool-call-before-the-user-is-asked` | `tool.check` runs after prior permission rules/hooks, can return `allow`/`ask`/`deny`, and `next(e)` yields the earlier decision | That a real 304 host routes `person` to a human, handles unattended calls or resolves managed overrides. The new person detail is found in the 304 release note, not that document section. |
| **K-0071**, optional `e.isReadOnly` | Reference, `#events` | General `tool.check` event, agent/organization fields and event result semantics | Actual read-only metadata classification. The new flag comes from 304 release notes and pinned 304 core type; mock Read without explicitly supplied metadata observed `undefined`. |
| **K-0072**, skipped-Hook transcript diagnostics | Events, `#the-order-mods-run-in` | Hook middleware order, dependencies, managed settings and `PreToolUse` ordering | Genuine preceding-plugin skip behavior and transcript readback. The new transcript line is documented in the 304 release note only. |
| **K-0073**, failed-reload recovery | Interface, `#keep-state` | Module-variable, session state and store persistence/reload-related distinctions | Real failed reload preserving the previously loaded Mod version's tool and command availability. The fix itself is in the 304 release note. |
| **K-0074**, `tool.check` error recovery | Events, `#handle-a-hook-that-fails` | Directly documents hook registration `.catch`, recovery semantics using `next.called`, and `tool.check` refusal via `{ decision: 'deny' }` even after `next` resolves | Real host-managed permissions, interactive human callbacks, actual tool execution or full runtime-generated type compatibility. Only six native synthetic permissions were already verified. |

**Finding:** K-0074 has direct source support for a narrow Hook-error-handling recommendation; the other four have only relevant background sections and must not be treated as if those sections proved the 304 release-specific deltas. Even K-0074 is not yet ready to be published as a newly approved Claim without explicit lifecycle review and the required runtime gates.

## Reproducibility and fail-closed boundaries

The complete SHA-linked findings are at `docs/reports/2026-10-21-cli304-five-reviewed-firstparty-sections.json`. The corresponding separate source-review files are in `sources/reviews/revisions/` and linked by exact digest in the findings. The private read-only source verifier is `scripts/review_cli304_exact_official_sections.py`; it refuses unrecognized source digests, changed/missing HTML anchors, Markdown heading mismatches, altered old candidate hashes, or missing technical semantics.

Recompute the expected evidence *without modifying the repository*, from a checkout of the same source revision and the original private first-party capture. The recorded `--reviewed-at` ensures stable output:

```sh
uv run --offline --group dev python - <<'PY'
from pathlib import Path
from datetime import datetime
import json
from scripts.review_cli304_exact_official_sections import audit
root = Path('/tmp/mods-cli304-firstparty-31claim-20261020')
record = json.loads(Path('docs/reports/2026-10-21-cli304-five-reviewed-firstparty-sections.json').read_text())
replayed, _ = audit(root, time=datetime.fromisoformat(record['reviewed_at'].replace('Z', '+00:00')))
assert replayed == record, 'Review provenance drift'
print('PASS: Five first-party source section records reproduce byte-equivalently')
PY
```

No candidate Claim `lifecycle`, `verification` or `evidence.role` was changed; all five remain `candidate/indexed/context`, original old-version approved Claims remain scoped to their respective versions, and `approved_claims(..., '2.1.304', 'cli')` still returns an empty list.

## Required next milestone

An independently recorded K-0074 `candidate → reviewed` lifecycle transition may now be proposed using its exact SHA-attested source section. That transition must not silently become `approved`; it requires explicit review rationale and decision ledger. For K-0070–K-0073, a new first-party **release-specific** support source or equivalent narrow target review and real host tests must be established first. Only after such approvals and complete host/native acceptance can any 2.1.304 Skill be built or deployed.

The P4 Chat Mode 46-case qualification, P5 full host/model acceptance and Stable release remain HOLD. Agent Communication is a separate excluded project.
