# Strict validation: optional author metadata becomes a fatal warning

**Observation date:** 2026-10-14. **Tested host:** Claude Code CLI 2.1.296 on macOS. **Scope:** isolated, disposable Mod fixture; no real agent/model execution.

The official Mods [reference file-layout section](https://code.claude.com/docs/en/plugins/mods/reference#files) points to the Claude plugin manifest specification and the [creation guide's static validation step](https://code.claude.com/docs/en/plugins/mods/create#check-what-claude-code-reads-from-your-mod). The manifest does not generally require author metadata, but the installed CLI's strict validation can reject an otherwise valid fixture because it treats an author warning as a failure.

## Reproduced variants

| Fixture | Command | CLI exit | success | Manifest warnings |
|---|---|---:|---|---|
| No author | `claude plugin validate <dir> --json` | 0 | true | 1, author attribution |
| No author | `claude plugin validate --strict <dir> --json` | 1 | false | 1, author attribution |
| `"author":{"name":"Mods QA"}` | `claude plugin validate --strict <dir> --json` | 0 | true | None |

These were run on the same disposable plugin layout with named `register(on)`, pass-through `tool.call` and `hooks/hooks.json` pointing to the module. Only the author field and strict flag differed. The reported reason in the strict failure was an author attribution *warning*, not a manifest schema error. The exact result in the repository is [the sanitized structured evidence](2026-10-14-strict-author-validation.json).

**K-0034** is the approved source-bound guidance Claim, scoped to Claude Code CLI **[2.1.296, 2.1.297)**. This is not a declaration that all later versions will behave identically or that author is mandatory in non-strict mode. A fully runnable example that tells the reader to run strict validation should include an author object and explain the difference between warnings/errors.

The problem was first found by independently running an explicit ChatGPT Chat-mode answer from temporary candidate v0.2.0-beta.5. That reply correctly cited K-0031/K-0032, used the named register entrypoint and three handler arguments, **but omitted author from its displayed plugin.json while suggesting strict validation**. This is precisely why successful Skill loading is not sufficient to claim generated code is fully usable.

The central Knowledge Compiler now propagates K-0034 to all four generated Skills, rather than changing per-platform files. The candidate SSOT update is not yet an accepted new public Release; the user's actual ChatGPT account was returned to the published v0.2.0-beta.1.
