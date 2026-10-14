# ChatGPT ordinary Chat-mode: full 46-case two-Skill preview routing regression

**2026-10-14. Preview v0.2.0-preview.1, Git 93b4a722982c310a021f47f582393c4cdc29670a.**

This is the **exact generated** optional two-Skill preview, separately verified
against the installed account's 15 ZIP member contents. The personal account
showed it installed and both Skills enabled before this test. Forty-six
unchanged P4 questions were submitted through authenticated standard **Chat**
composer in deterministically interleaved order, each with its own confirmed
conversation ID. All 46 final replies and sampled tool invocation histories
were recovered. This is not Work mode.

| P4 group | Observed | Actual Plugin read_resource | Strict structural PASS |
| --- | ---: | ---: | ---: |
| Positive Mods development | 30 | **0/30** | 0 |
| Boundary version/security | 8 | **0/8** | 0 |
| Unrelated tasks | 8 | **0/8** (correct nonactivation) | 8 |
| Total | **46** | **0** | **8** |

**This is an outright failure of Plugin automatic activation** on the in-scope
requests in this run. Sampled real conversation tool histories showed ordinary
web.run calls, not api_tool.read_resource from this Plugin. A generic model
response is not a Plugin success.

The *older, different-time* Beta.1 46-case run recorded 27/30 positive
auto-loads and 0/8 boundary loads. A separate contemporary 48-conversation
A/B experiment with a **hand-built, different two-Skill ZIP** saw 7/16
boundary loads against 3/16 Beta.1 control. Neither can be assumed to
causally predict this exact generated preview: model routing is server-side,
variable and the experiments were not randomized across all cohorts. No
per-turn installed-package identity snapshot exists in the model transcripts,
so do not make a stronger claim than the observed 0 Plugin resource reads
for these conversations.

The user account has since been restored to the last published
`v0.2.0-beta.1`, enabled. No public GitHub release was created from this
preview, and Draft PR #15 remains intentionally unmerged.

## Quality, security and storage

The sanitized [complete per-case JSON](2026-10-14-preview-full-chat-mode-qa.json)
contains case IDs, prompt and response hashes, observed Claim IDs and
activation flags only. Raw ChatGPT replies, conversation IDs, cookies,
personal account IDs and browser profiles remain on Raspberry Pi's private
local QA workspace, not in this public repository.

The P4 auto-routing gate does **not** pass, and semantic correctness is
unverified because no Skill was loaded. **Issue #1 cannot honestly be closed
as 'fixed'.** The only currently demonstrated reliable approach for users
needing the reviewed guidance is to explicitly select
`@claude-code-mods-knowledge` in ordinary Chat mode, and still validate
runnable examples. See Issues #1, #2, #3 and #4 for remaining host and
model-quality gates.

The file-content security gate from PR #17 prevents this preview from being
packaged as a normal release without a separate, reviewed multi-Skill
provenance and policy.
