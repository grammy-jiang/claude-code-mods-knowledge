# CLI 2.1.302: bounded native verification of original Codex-generated snippets

This follow-up independently audits the **54 original native positive
Codex replies** from the immutable 144-turn experiment, across all A/B/C
arms and both frozen/heldout case sets. Each response and its App Server
wire were checked against existing SHA256 before code-fence inspection.

- **23 original JavaScript snippets** matched exactly two manually
  approved, non-I/O behavior patterns after comments/whitespace and
  innocuous quote-style normalization: nine simple tool.call pass-through
  observers; 14 fail-isolated async logger observers. **Zero unknown JS
  patterns.** These counts classify shapes, not total runnable full Mods.
- **19 original shell code blocks** contained only one of three accepted
  first-party CLI invocation shapes: strict validation in the plugin
  directory, strict validation of a specified Mod directory, or mocked
  plugin testing of the Mod directory. **No generated shell commands
  were executed**. Each equivalent command shape was instead verified
  with an independent, source-controlled benign Mod test fixture on
  genuine CLI 2.1.302, with no actual Bash tool call.
- Two exact original, manually reviewed model-origin JavaScript examples
  were separately embedded in a disposable named register(on) entry,
  subject to first-party CLI 2.1.302 strict validation and native mocked
  success/deny/isError checks (three tests each, all passed). Six
  independent Node tests per pattern passed exact value/exception identity,
  once-only next(e), and both sync and rejected async logger failures.
  Testing only these whitelisted originals did not execute any unknown
  model code.
- Other original snippets were checked for source-shape equivalence, not
  individually executed. Matching patterns and a native test harness do
  **not** certify all model-generated code, UI callbacks, security
  policy semantics, remote hosts or a production Mod; do not use these
  results to unblock unrelated executable replies automatically.

The companion JSON contains only per-case hashes, bounded counts and
review labels. Raw model replies, prompt text, credentials, machine paths,
accounts, transcript URLs and diagnostic output remain private.

The **46 real ChatGPT Chat Mode** cases are independently tracked and do
not inherit any pass from these Codex native results. Release remains
HOLD pending finished Chat Mode quality review and any unresolved code
semantics.
