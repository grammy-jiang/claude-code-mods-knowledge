# Real Pi Agent 1.3.0 OS filesystem sandbox smoke — P5

Date: 2026-10-18 Sydney/AEDT.
Target: genuine Raspberry Pi 5, native Pi 1.3.0 and Claude CLI 2.1.302.
Candidate source revision: 81cbb6a, P5 mandatory Bubblewrap patch.

The previous native P5 runner could detect an out-of-scope read only
AFTER the read tool had already accessed the host filesystem.
Such a postflight check cannot prevent secrets entering model context.

The revised runner now requires Linux Bubblewrap to contain every
real native Pi inference process BEFORE any model-origin file read.
There is no fallback to an unrestricted Pi subprocess if namespaces,
runtime files, reviewed Skill, or Bubblewrap are unavailable.

## Actual original on-device evidence

- Linux Bubblewrap 0.12.0 with user/PID/mount namespaces successfully
  executed on the Raspberry Pi, without sudo or user setting changes.
- The native Pi Node runtime and reviewed Skill were mounted read-only;
  isolated agent/workspace were writable and temporary storage was
  a private tmpfs. No host Home filesystem was mounted.
- Inside that sandbox, the installed Skill and isolated models.json
  were readable. Host SSH, project tree and user Pi profiles were
  absent.
- Pi Agent itself answered the native --version command from inside
  the sandbox with observed version 1.3.0.
- The isolated Pi local offline model catalog listed the expected
  qwen36-35b-a3b-mtp alias. No inference or HTTP model request occurred.
- 21/21 targeted native runner and filesystem tests passed on Pi.
- Previous complete Mac offline repository suite for this change:
  985 passed, 11 older-reviewed-target test skips.

No actual Qwen model was started. The forwarded Pi SSH model endpoint
was offline, and the most recent measured Mac Swap remained above the
existing local Qwen supervisor resource safety limit.

## Scope and limitations

- The sandbox permits only read-only system /usr, pinned native Node+Pi
  runtime, read-only approved Skill/reference files, writable private
  agent/workspace folders and tmpfs. Host Home/SSH/Projects are
  deliberately unavailable to the model's read tool.
- Pi built-in read is the only enabled tool. Shell/write/edit,
  extensions, MCP, persistent sessions and context files are disabled.
- Completed model events still require mandatory fully buffered
  CLI302-specific model/source/tool-scope postflight checks.
- The network namespace remains SHARED to access the existing local
  SSH-forwarded Qwen backend. This is file isolation, NOT a general
  outbound network firewall. Pi startup uses offline mode, but
  arbitrary third-party native runtime networking is not proven blocked.
- The smoke proves only OS file visibility, process startup and
  provider-model catalog loading. It does NOT prove Qwen answer quality,
  generated code safety or 46-case Chat Mode compatibility.
- The original complete model traces must remain private. No generated
  artifacts or account secrets are exported by this report.

Stable Release remains HOLD; P5 true Qwen model inference and
semantic QA are still pending safe resource conditions. Agent
Communication is a separate project.
