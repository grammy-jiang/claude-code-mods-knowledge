# Pi Agent 1.3.0: real CLI 2.1.302 buffered P5 acceptance path

This *native Pi Agent* command enforces the current reviewed Claude Code
CLI 2.1.302 preflight and postflight inside the same Pi test process.
It replaces the prior independent-only preflight plus historical
2.1.296-only test driver. It is not a Pi extension or an MCP server,
does not use the Agent Communication project, and does not execute any
code produced by a model.

Source file: scripts/run_p5_pi_native_302_gated.py.

## Safety order, without any manual intervention

1. Verify the local Claude and Pi CLI versions, original Git HEAD,
   full dist/ZIP manifest and 53 artifact hashes, and byte identity of
   every installed native Skill/reference file.
2. Read a frozen CLI 2.1.302 P5 question and invoke the REAL current
   version preflight. Unsupported CLI 2.1.310 requests must be refused
   here, with ZERO model requests and NO endpoint health probe.
3. In-scope questions are allowed only with the explicit --run-model
   testing flag. Otherwise create a private "backend required" result,
   not a fake accepted model result.
4. Probe exactly the already-running local Qwen model endpoint
   127.0.0.1:18081 /v1/models. If unavailable, exit with a private,
   fail-closed report and ZERO model calls. This runner never starts or
   stops local model services.
5. Configure only an isolated, private PI_CODING_AGENT_DIR. Native Pi
   Agent (1.3.0) requires mandatory Linux Bubblewrap OS filesystem
   containment BEFORE any model tool access: a private PID/mount/user
   namespace with only read-only system /usr, the exact reviewed
   Node/Pi runtime at /runtime, the installed Skill at /skill, a
   private /agent and /work writable binding and a tmpfs /tmp.
   The host's Home, SSH keys, projects and original Pi settings are
   NOT mounted. Both the reviewed runtime and Skill are read-only.
   Linux user namespaces must be available; otherwise fail CLOSED,
   never start the old unrestricted direct Pi process.
   The network namespace is shared to reach only the already-approved
   SSH-forwarded local model endpoint; this is NOT a general network
   firewall, although Pi startup runs in offline mode and the only
   available tool is built-in read. No MCP/extensions, no persistent
   session, no shell/write/edit tools, no global configuration.
   The --skill flag exposes the reviewed Skill but never proves
   the model actually read it.
6. Buffer stdout JSON events into private files (0600). Enforce hard
   total bytes, timeout, event count and repeated tool-call bounds.
   Kill only this runner's own native Pi process group on violations.
   For any observed file reads outside the reviewed Skill and
   isolated workspace, block the candidate (a postflight check, NOT
   a kernel-level file sandbox).
7. Before exposing anything, run the SAME current CLI 2.1.302 postflight
   that checks actual model identity, final stop, original question,
   actual Skill tool reads, exact approved first-party Claim+URL pairs
   and version/safety risk signals. Even structural-only passing
   responses are never streamed to the caller by this QA runner.
   Never execute model-generated Mod/JS code.
8. Store only bounded, sanitized status metadata in the report. Keep
   original event wire, model content and stderr in the private
   evidence directory. The runner refuses to overwrite a prior case.
   A single Pi CLI execution can internally retry inference HTTP;
   request counts are UNKNOWN unless separately measured in the
   model server logs. Never equate one Pi process with one HTTP call.

## Native execution examples

For a new exact Git-reviewed local build in the repository, build
with the current checked-out source SHA. Do not reuse a candidate
dist produced by another commit:

    uv run --locked mods-knowledge build \
      --api-version 2.1.302 --surface cli \
      --package-version 0.4.12-p5gate.1 \
      --source-revision "$(git rev-parse HEAD)"
    uv run --locked mods-knowledge skills-lint --dist dist
    uv run --locked mods-knowledge package-check --dist dist

Then on Raspberry Pi, with the approved identical native Skill installed:

    uv run --locked python scripts/run_p5_pi_native_302_gated.py \
      --case BOUND-VERSION-NEW \
      --evidence-dir /tmp/mods-p5-302-boundary-original

This must return preflight abstention with NO model inference or HTTP
health check. For actual positive inference, use a NEW evidence directory,
the real pinned and already healthy local Qwen model service, and explicitly
pass --run-model:

    uv run --locked python scripts/run_p5_pi_native_302_gated.py \
      --case POS-E-01 --run-model --timeout 120 \
      --evidence-dir /tmp/mods-p5-302-positive-original

A source-structure pass can only be reported as
allow_structural_only; runtime Mod semantics remain unverified. Negative
unrelated control NEG-TYPESCRIPT tests no false Skill activation.

## Current environmental blocker

At 17:34 Sydney on 2026-10-18, the remote MacBook Pro had
approximately 6.0 GB swap in use (older Pi model-testing supervisor
requires no more than 512 MiB) and the Qwen endpoint was not running.
All existing user AI service states must be preserved; do not restart
or stop them simply to force the P5 model score. The Pi local SSH
listener is not equivalent to a working model backend.

The runner and its synthetically injected local tests verify the
execution and safety gate sequencing without Qwen inference or
web/account calls. Real native acceptance remains a separate P5
requirement, and the full ChatGPT Plugin 46-case/Stability gates
remain HOLD. No score is downgraded or upgraded because a provider
is offline.
