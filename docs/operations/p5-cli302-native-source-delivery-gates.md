# P5: current CLI 2.1.302 native host source and version gates

Target: latest reviewed Claude Code CLI 2.1.302, native Claude Code
(Sonnet / Medium), Codex gpt-6.1-sol / Medium and native Pi Agent 1.3.

These source/runtime gates use the single approved SSOT knowledge
revision; historical 2.1.296 defaults and test evidence remain
unchanged, and any runtime model outcome is separately verified.
The Agent Communication project is unrelated and out of scope.

## Exact failures reproduced

Prior genuine Sonnet CLI2.1.302 natural-positive Model answer was
missing the exact approved first-party locator for K-0065.
Another genuine Sonnet/Medium test, using reviewed beta011, invoked
the native Skill, read references/testing.md, but ALSO tried to read
an optional references/selected-evidence.md which was NOT actually
packaged. The native Read returned a file-not-found error, after which
the completed answer included K-0066 and K-0067 without their exact
respective official URLs. Skill tool invocations therefore cannot be
used as proof of complete, actually successful reference reads.

The new compiler stops advertising selected-evidence.md. It directs
agents to load the topic reference AND always-available bundled
references/claim-evidence.md before citing any approved Claim.
The compiler's archive validator rejects a literal local reference
mentioned even in prose or a code span unless that file is actually
present in the reviewed package. Red-first regression tests cover
both normal host Skills and both approved ZIP archive variants.
No optional missing reference can pass the standard pre-install
deterministic format/package gates.

Pi Agent 1.3 / local Qwen 3.6 genuine P5 baseline had two failures:
it cited K-0041 and K-0042 without exact official Source URLs, and
for unreviewed CLI2.1.310 produced executable CLI2.1.302 Mod code
despite its own Skill version guard. The old native Pi deterministic
delivery pre/postflight module was still pinned to historical 2.1.296.
An arbitrary non-buffered native model call never inherited its
safety gate.

## 2.1.302 version-pinned gate

Pi preflight and native Pi source postflight now accept an explicitly
reviewed target_version of 2.1.302 while preserving historical
2.1.296 behavior as the default (never silently treating one
version's approved Claims as another's). Other version inputs
are refused; the unreviewed 2.1.220/2.1.296/2.1.310 and legacy-preview
boundary examples return action=abstain_before_model and
model_requests_needed=0. No model inference or generated code should
be needed to explain that unsupported API behavior is unverified.

For completed *buffered* positive native Pi results, the postflight
requires first-party official URLs for EACH cited Claim, with
fragment and target match. Correct URLs for some Claims do not
erase missing ones. Bad or unverified Mod code is withheld, not
streamed. It is not a complete independent native Mod code test.
A future native runner must invoke the preflight before starting any
model and postflight before delivering model text. An agent that
directly ignores the gate is not inherently safe.

The model-free, native Pi 1.3.0 diagnostic command verifies CLI,
installed Skill SHA, checked-out Git HEAD, complete compiled package
manifest and the frozen 2.1.302 case prompt before returning
the preflight verdict; it never launches Pi model inference:

    uv run --locked mods-knowledge build \
        --api-version 2.1.302 --surface cli \
        --package-version 0.4.12-beta.1 \
        --source-revision "$(git rev-parse HEAD)"

    uv run --locked python scripts/run_p5_pi_cli302_preflight.py \
        --case BOUND-VERSION-NEW \
        --dist dist \
        --out /tmp/mods-p5-pi302-boundary-preflight.json

For a positive case the result only authorizes future model
inference once a genuine backend is available and correctly pinned;
it does not claim inference was performed.

## Original evidence and current limitations

The first Sonnet/Medium beta011 rerun reached a small explicit
USD 0.40 budget cap before a final response and must be classified
as budget-interrupted, neither source pass nor source fail.

A second complete genuine Sonnet/Medium CLI302 P5 run on POS-Q-01
did load the native Skill and testing.md, but also attempted the
missing selected-evidence.md file. It completed with cited K-0066
and K-0067 lacking their exact official URLs. This is recorded
as a true source structural failure, NOT a fully correct answer.
Native untrusted generated code was not executed.

The previous temporary oMLX Pi Agent Qwen backend at the Mac
SSH-forwarded loopback port was stopped after original P5 testing.
The Pi-side forwarding port currently exists, but HTTP requests
reset because no model is listening on the remote Mac target.
Do not claim it is available or count preflight-only metadata as
a real Pi model acceptance result. Further host inference must
use isolated read-only native tools, bounded model usage and
post-buffer inspection, never arbitrary generated code execution.

P5 native Sonnet/Pi, 46-case current Chat Mode and full generated
Mod semantic validation remain HOLD. Stable release is NOT approved.
