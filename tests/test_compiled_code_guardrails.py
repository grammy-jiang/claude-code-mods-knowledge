"""New official SSOT fixes must reach every generated host, without manual edits."""

from pathlib import Path

from mods_knowledge.compiler import compile_knowledge

ROOT = Path(__file__).resolve().parents[1]


def test_new_api_guardrail_ids_and_exact_guidance_propagate_into_all_hosts() -> None:
    compiled = compile_knowledge(
        ROOT, api_version="2.1.296", surface="cli", source_revision="guardrail-test"
    )
    for prefix in (
        "common/claude-code-mods-development",
        "claude-code/.claude/skills/claude-code-mods-development",
        "codex/.agents/skills/claude-code-mods-development",
        "pi/.agents/skills/claude-code-mods-development",
        "chatgpt/claude-code-mods-knowledge/skills/claude-code-mods-development",
    ):
        main = compiled[f"{prefix}/SKILL.md"].decode()
        types = compiled[f"{prefix}/references/types.md"].decode()
        testing = compiled[f"{prefix}/references/testing.md"].decode()
        assert "K-0032" in main and "K-0033" in main
        assert "K-0032" in types
        assert "K-0033" in testing
        assert "export default function register({ on })" in main
        assert "claude plugin test ./my-mod" in main
        assert "cli 2.1.296" in main.lower()
        assert "https://code.claude.com/docs/en/plugins/mods/" in types
        assert "https://code.claude.com/docs/en/plugins/mods/" in testing


def test_source_guardrail_does_not_invent_unreviewed_new_versions() -> None:
    compiled = compile_knowledge(
        ROOT, api_version="2.1.296", surface="cli", source_revision="guardrail-test"
    )
    text = compiled["common/claude-code-mods-development/SKILL.md"].decode()
    assert "2.1.296" in text
    assert "2.1.310" not in text or "unverified" in text.lower()


def test_strict_author_guidance_is_compiled_into_all_agent_skill_sources() -> None:
    compiled = compile_knowledge(
        ROOT, api_version="2.1.296", surface="cli", source_revision="strict-author"
    )
    for prefix in (
        "common/claude-code-mods-development",
        "claude-code/.claude/skills/claude-code-mods-development",
        "codex/.agents/skills/claude-code-mods-development",
        "pi/.agents/skills/claude-code-mods-development",
        "chatgpt/claude-code-mods-knowledge/skills/claude-code-mods-development",
    ):
        main = compiled[f"{prefix}/SKILL.md"].decode()
        types = compiled[f"{prefix}/references/types.md"].decode()
        assert "K-0034" in main and "M003" in main
        assert "K-0034" in types
        assert "claude plugin validate --strict" in main
        assert "author" in main


def test_validate_directory_requirement_is_generated_from_approved_claim() -> None:
    import inspect

    from mods_knowledge.compiler import _skill_main

    compiled = compile_knowledge(
        ROOT, api_version="2.1.296", surface="cli", source_revision="validate-path-ssot"
    )
    expected = "claude plugin validate --strict ."
    for prefix in (
        "common/claude-code-mods-development",
        "claude-code/.claude/skills/claude-code-mods-development",
        "codex/.agents/skills/claude-code-mods-development",
        "pi/.agents/skills/claude-code-mods-development",
        "chatgpt/claude-code-mods-knowledge/skills/claude-code-mods-development",
    ):
        body = compiled[f"{prefix}/SKILL.md"].decode()
        ref = compiled[f"{prefix}/references/types.md"].decode()
        assert "K-0035 / M002" in body
        assert expected in body
        assert "## K-0035" in ref
        assert expected in ref
    # The API fact is in one approved Claim, not duplicated as executable
    # literal instructions in the compiler's own code.
    assert expected not in inspect.getsource(_skill_main)


def test_transparent_observer_logging_failure_guardrail_is_generated_from_approved_claim() -> None:
    import inspect

    from mods_knowledge.compiler import _skill_main

    compiled = compile_knowledge(
        ROOT, api_version="2.1.296", surface="cli", source_revision="observer-log-isolation"
    )
    for prefix in (
        "common/claude-code-mods-development",
        "claude-code/.claude/skills/claude-code-mods-development",
        "codex/.agents/skills/claude-code-mods-development",
        "pi/.agents/skills/claude-code-mods-development",
        "chatgpt/claude-code-mods-knowledge/skills/claude-code-mods-development",
    ):
        skill = compiled[f"{prefix}/SKILL.md"].decode()
        reference = compiled[f"{prefix}/references/events.md"].decode()
        assert "K-0037 / M004" in skill
        assert "## K-0037" in reference
        assert "fail-isolated" in skill.lower() or "日志" in skill
        assert "#observe-an-event" in skill
    assert "console.log" not in inspect.getsource(_skill_main)
