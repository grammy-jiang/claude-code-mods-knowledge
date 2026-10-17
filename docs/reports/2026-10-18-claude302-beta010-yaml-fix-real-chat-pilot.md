# P4: beta048 automatic routing regression root cause and beta010 real pilot

## What changed from 30/30 to 0/30?

The frozen, pre-existing beta047 full 46-case ChatGPT ordinary Chat Mode run
actually loaded the personal Plugin's reviewed Skill plus topic references for
all 30 positive Mods tasks. It missed precise approved URLs in one answer,
and none of eight boundary questions loaded the Skill (separate defect).

At beta048 the generated frontmatter line was changed from a valid plain
YAML description into an invalid plain scalar containing an *unquoted*
internal colon and space: the phrase "Claude Code Mods: hooks". The exact
same defect persisted at beta049. This breaks YAML grammar: Mac Ruby/Psych
and Raspberry Pi PyYAML both reject beta048 and beta049 at line 3,
column 55, while accepting the original beta047. The historical ZIP
validator used a substring/regex check, not a real YAML parse, so the
invalid YAML survived package checks and personal account installation.

The original natural Chat Mode test prompts did not change except for
unique task IDs. Both 46-case cohorts used GPT-6 Thinking, standard
effort, ordinary Chat Mode, no user-selected Plugin composer entry, and
no requested search. The genuine completed outcomes were 30/30 positive
Plugin resource reads for beta047 versus 0/30 for beta048.

At beta049 a delayed natural positive still failed to read the Plugin
after around 70 minutes, whereas an explicit Skill-named same-family
positive read two matching Plugin resources. This shows that the Plugin
could still be accessed with an explicit instruction; the regression
involves automatic discovery/selection.

The minimal beta010 fix (merged PR #81) uses a JSON-quoted scalar for the
same description wording and adds an actual safe YAML parse to the ZIP
validator. Both old invalid beta048/beta049 archives are now correctly
rejected, while valid beta047 is accepted. No approved Claim facts or
reference pages were changed to repair this.

## Real current Chat Mode post-fix test

Installed personal Plugin beta010 from exact merged source
b9ea3063393e33259298ddcac02104b16c42b208 and verified its
11/11 normalized downloaded source files. Three independent local
builds (MacBook Pro, Raspberry Pi, sextant) yielded identical hashes
for all 53 compiled artifacts, including the common Skill and Plugin ZIP.
Local agents' already-installed copies were safely upgraded, preserving
the old version as an on-host rollback directory; no running agents
or sessions were restarted.

Four new independent ordinary Chat Mode conversations were sent using
the original test prompts with only new unique task ID markers:

| Predeclared test | Actual matching Plugin resource read | Strict outcome |
| --- | --- | --- |
| POS-E-01, tool.call observer | Skill entrypoint and topic references, 2 read_resource events | Positive exact source/Claim structure PASS |
| POS-U-01, Pane/AbovePrompt UI | Skill entrypoint and topic references, 2 read_resource events | Positive exact source/Claim structure PASS |
| NEG-HVAC, unrelated task | No Skill resource read | Negative nonactivation PASS |
| BOUND-VERSION-NEW, unsupported future version | No Skill resource read | Boundary automatic activation FAIL |

Each original send and full final reply has a separately checked
conversation/answer SHA256; source reference use comes from genuine
ChatGPT tool event metadata, not text-only self-claims. No raw private
model answer or account ID is committed.

**Conclusion:** The invalid YAML entrypoint was a directly proven
package defect and the before/after genuine-model observations
strongly support it as the primary cause of the beta048/beta049
automatic positive routing collapse. This is not proof of the
internal platform routing algorithm, nor a guarantee of 100%
reproducibility across all topics.

The independent, pre-existing unsupported-version/boundary activation
problem remains (beta047 0/8, beta048 0/8, beta049 0/8,
beta010 post-fix 0/1). Correcting YAML does **not** solve that scope.

P4 full 46-case current-bundle repeatability, native Claude/Pi answer
source integrity, version-safety semantics and P6 account rollback
and publication audit remain gated. STABLE_RELEASE_BLOCKED.
