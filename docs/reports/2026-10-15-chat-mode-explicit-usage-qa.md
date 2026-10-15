# ChatGPT ordinary Chat Mode — direct plugin mention vs selected `@` plugin

**Date:** 2026-10-15, Australia/Sydney. **Only Chat Mode was tested** (not ChatGPT Work, Codex-hosted tasks or a Work cloud browser). The installed personal `claude-code-mods-knowledge` Plugin remained **`0.2.0-beta.1`**, enabled with its single `claude-code-mods-development` Skill. Its reviewed knowledge target is Claude Code **2.1.296 / CLI**; this published Beta contains 26 approved Claims rather than all 29 in current source `main`. No plugin package or account setting was changed by this experiment. The before/after account inspection verified the same installed version/Plugin instance with the Skill enabled.

## Official Chat Mode behavior and capability boundary

OpenAI's [Plugins in ChatGPT](https://help.openai.com/en/articles/20001256-plugins-in-chatgpt) states that users can select an installed Plugin in the Chat composer with `@` or the `+`/Plugins menu, depending on surface. The [Skills](https://developers.openai.com/plugins/concepts/skills) docs state that a Skill's metadata is initially available to the model and instructions are loaded when the request matches **or the user invokes it directly**. The [ChatGPT connection/test guide](https://developers.openai.com/plugins/deploy/connect-chatgpt) explicitly permits **Skills-only** packages in new Chat conversations, and recommends verifying actual resource use, completing steps and evaluating positive/negative/boundary requests. We intentionally did **not** follow the separate plugin quickstart's Work Mode test route.

This Plugin contains reviewed text instructions and reference documents **but no MCP tool server**, hence successful loading can help explain APIs, draft Mod code and review user-provided snippets. **The Skill cannot by itself run local `claude plugin test`, inspect the user's real Claude Code installation, edit files or access an account.** Such operations require separately available, authorized tools and their own execution evidence. A model can still produce technically wrong code despite reading correct references.

## Twelve verified real Chat Mode conversations

We used four **pairs of identical user prompt text**, changing only whether the installed Plugin was selected through the composer system hint, plus four extra direct selected-Plugin cases. In each pair the prompt text *explicitly asked* ChatGPT to use `claude-code-mods-knowledge`, consult its Skill and references, and cite approved Claims plus first-party Mods sources. Plain text alone carried **no `system_hints` value**, while the other side used the exact personal installed Plugin system hint. The extra cases used unmodified original P4 prompts with explicit UI Plugin selection. Each of 12 separate new Chat conversations completed successfully under **GPT-6 Thinking / Standard**; a genuine `api_tool.read_resource` tool trace confirmed correct Plugin Skill access **12/12**.

| Test | Real canonical Skill reads | Positive responses meeting source/Claim structural checks | Limit |
| --- | ---: | ---: | --- |
| Text prompt explicitly says to use installed Plugin and Skill, **without UI selection** | **4/4** | **3/3** | One additional unsupported-new-version boundary requires manual review |
| Plugin explicitly selected with `@` / composer hint | **8/8** | **6/6** | Two boundaries require manual review |
| **Combined** | **12/12** | **9/9** | **Three positive answers still include native-invalid recommended examples** |

Original P4 case categories represented: transparent `tool.call` middleware, offline `.test.ts` testing, Pane/AbovePrompt UI matching, `/clear`/`/resume` state persistence, static hook discovery, sandbox/secret permissions, unverified Claude Code 2.1.310 API and an attempt to override security from an unofficial blog. In the latter boundary test the model declined to upload secrets or discard official documentation; both new-version answers withheld a blanket 2.1.310 compatibility guarantee. One version-boundary answer, however, included an independently invalid 2.1.296 example.

**Scope of conclusion:** An explicit, natural-language request to use the installed Plugin may itself be enough to trigger a real Skill read; *typing the bare plugin name without that instruction* was not tested. Selecting via `@` produced a canonical read in every sampled conversation. **Neither mode guarantees universal activation in future runs**; this is a small, nonrandomized, same-account observation, not an automatic-routing P4 pass. The 4 paired prompts are semantically identical within each pair, but system-hint selection is not the only possible time-sensitive model-context difference.

## Correcting a Chat Mode answer-collection defect

**11/12** newly sampled Chat replies used more than one sequential user-visible assistant text message: nine contained two segments, two contained three, and only one contained a single text segment. A reply might have short introductory narration, several thousand characters of main reasoning/reference/code guidance, and a final section. The older browser client's `latest_reply(conv)` returns **only the final visible assistant message**, which can be just a small fraction of the actual answer. For one explicit `tool.call` case, the assistant text segment lengths were **81 + 5,537 + 873 characters**, while the old collector scored **873 characters**. It falsely treated approved Claim IDs and a correct callback example from the earlier segment as missing.

The new pure `mods_knowledge.chat_visible_reply.collect_latest_visible_reply(cc.chain(conv))` selects all visible assistant text after the last user message, preserving their original order. It excludes prior user turns, tool messages, non-user-facing recipients and incomplete responses. The returned **full** reply must then be sent into `chat_mode_evidence.summarize_chat_mode_case` and independently reviewed. Raw assistant text is stored only in private local QA directories; the [case-level sanitized report](2026-10-15-chat-mode-explicit-usage-qa.json) publishes hashes, segment counts, Claim IDs, trusted resource URI values and conservative quality statuses, **not** private conversation IDs, replies, cookies or account plugin identifiers. Previous QA based on `latest_reply` may have **under-counted Claim/source coverage for multi-message turns**; no past published failure is silently reclassified without independent readback. Six earlier explicit controls were independently rescored and each happened to contain just one visible segment; their five structural passes and one structural failure remain structurally consistent.

## Independent CLI 2.1.296 correctness findings

**Passing a source/Claim structural check does not mean a runnable recommendation is valid.** Three of the **nine positive answers** included a materially incorrect command or entry point that could mislead a user copying its primary/example code, independently reproduced on the target CLI:

| Real answer cases | Problematic *recommended* pattern | Native Claude Code CLI 2.1.296 |
| --- | --- | --- |
| Text-mention `POS-E-01` and UI-selected `POS-E-01` | `export default function register({ on })` described as correct | `claude plugin validate --strict` **exit 1**; synthetic `.test.ts` **exit 1**. Later examples in the same answers used a valid named export, but that does not validate the first example |
| UI-selected `POS-Q-01` | `claude plugin test ./path/to/your-mod.test.ts` presented as the core command | **exit 1**, not a plugin folder. `claude plugin test .` from the Mod root **exit 0** with one synthetic test passing |

A fourth known-risk example occurred in a **boundary** response: the plain-text `BOUND-VERSION-NEW` answer correctly refused to guarantee new 2.1.310 API compatibility, yet included the same invalid default/destructured `register` shape as an example purportedly scoped to older CLI 2.1.296.

Additional bounded native checks passed: `export function register(on)` with a transparent `($, e, next)` observer passed strict validation plus one safe mocked test; the response's statically imported helper and named `register(on)` pattern for `POS-T-03` passed strict validation and discovered `tool.call`. The UI matcher behavior, exact per-user reactive-state lifecycle, and user-specific security environment have **not** been executed/verified merely by reading Skill material. `POS-P-01` and `BOUND-INJECTION` gave appropriate security guidance without accessing secrets. The absence of automatic code-risk flags is not an independent semantic PASS.

A related regression fix strengthens `mods_knowledge.answer_lint`: previously it detected an unsupported `export default function register({ on })` but **missed** `export function register({ on })`, which the same CLI strict validator also rejects. New red-first tests and the `unsupported-named-register-destructuring` flag cover the named destructured form, while clearly labeled wrong examples remain manual-review-only.

## Operational conclusion

For current personal Chat Mode users, the most reproducible route is to **type `@` and choose the actual installed Plugin**, then ask for exact CLI/version scope, approved K-Claims and direct first-party references. The text-only prompt "Please use the installed `claude-code-mods-knowledge` Plugin and its Skill..." also loaded the actual Skill in every one of four sampled Chat conversations. **Still run `claude plugin validate --strict` and safe `.test.ts` tests before trusting or shipping generated Mod code**; any actions on real files, systems or accounts require separate authorization and appropriate tools.

Keep P4 automatic activation, full independent semantic quality, all three native Agents and P6 stable-release readiness **open / blocked**. Do not infer Work Mode behavior from this Chat-only study or publish a new Plugin version solely because the model read a Skill.
