"""Bubblewrap pre-tool filesystem containment of actual native Pi CLI.

Pi's builtin read tool otherwise sees arbitrary host files before a
postflight check can block a leaked answer. Tests must ensure that no
host Home, SSH data, model weights or project root is mounted.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "scripts/run_p5_pi_native_302_gated.py"


def runner_module():
    spec = importlib.util.spec_from_file_location("p5_pi_native_fs", MODULE)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def fake_pi(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    runtime = tmp_path / "node-v24.19.0"
    node = runtime / "bin/node"
    node.parent.mkdir(parents=True)
    node.write_text("fake, never executed")
    node.chmod(0o755)
    bundle = runtime / "lib/node_modules/@earendil-works/pi-coding-agent/dist/bundle/cli.js"
    bundle.parent.mkdir(parents=True)
    bundle.write_text("fake, never executed")
    skill = tmp_path / "installed" / "claude-code-mods-development"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: claude-code-mods-development\n---\n")
    sandbox = tmp_path / "private"
    sandbox.mkdir()
    (sandbox / "isolated-native-agent").mkdir()
    (sandbox / "isolated-native-agent/models.json").write_text('{"providers":{}}')
    (sandbox / "workspace").mkdir()
    return bundle, skill, sandbox, node


def test_native_model_can_only_run_through_explicit_bwrap_os_boundary(
    tmp_path: Path,
) -> None:
    mod = runner_module()
    pi, skill, private, node = fake_pi(tmp_path)
    args = mod._sandbox_pi_argv(
        "/usr/bin/bwrap",
        str(pi),
        {"prompt": "Original source-bound question"},
        skill,
        private,
    )
    assert args[0] == "/usr/bin/bwrap"
    assert "--unshare-all" in args
    assert "--share-net" in args
    assert "--die-with-parent" in args
    assert "--clearenv" in args
    assert "--proc" in args and "--dev" in args
    assert "--tmpfs" in args
    assert ["/usr", "/usr"] == args[args.index("--ro-bind") + 1 : args.index("--ro-bind") + 3]
    assert args[args.index("--skill") + 1] == "/skill"
    assert args[-1] == "Original source-bound question"
    assert args[args.index("--tools") + 1] == "read"
    assert args[args.index("--chdir") + 1] == "/work"
    assert args[args.index("--setenv") + 1 : args.index("--setenv") + 3] == [
        "HOME",
        "/home/qa",
    ]
    mounts = [
        args[i + 1 : i + 3] for i, arg in enumerate(args[:-2]) if arg in {"--ro-bind", "--bind"}
    ]
    assert ["/usr", "/usr"] in mounts
    assert [str(skill.resolve()), "/skill"] in mounts
    assert [str(private / "workspace"), "/work"] in mounts
    assert [str(private / "isolated-native-agent"), "/agent"] in mounts
    assert [str(pi.parents[6]), "/runtime"] in mounts
    assert not any(src == "/" for src, _ in mounts)
    forbidden_prefixes = tuple("/" + x for x in ("home", "root", "etc", "tmp", "mnt"))
    assert not any(src in forbidden_prefixes for src, _ in mounts)
    assert args[args.index("--") + 1] == "/runtime/bin/node"
    assert args[args.index("--") + 2].endswith(
        "/lib/node_modules/@earendil-works/pi-coding-agent/dist/bundle/cli.js"
    )
    assert "--no-mcp" in args and "--no-extensions" in args
    assert "--no-approve" in args and "--offline" in args


@pytest.mark.parametrize(
    "corruption",
    ("missing_runtime_binary", "unreviewed_cli_path", "writable_pi_package", "missing_skill"),
)
def test_corrupt_or_unreviewed_native_runtime_fails_before_model(
    tmp_path: Path,
    corruption: str,
) -> None:
    mod = runner_module()
    pi, skill, private, node = fake_pi(tmp_path)
    if corruption == "missing_runtime_binary":
        node.unlink()
    elif corruption == "unreviewed_cli_path":
        pi = tmp_path / "unknown-pi.js"
        pi.write_text("bad")
    elif corruption == "writable_pi_package":
        # Source package must not be writable by model under the sandbox.
        # The --ro-bind is mandatory, even if host package is writable.
        pass
    else:
        (skill / "SKILL.md").unlink()
    if corruption == "writable_pi_package":
        cmd = mod._sandbox_pi_argv("/usr/bin/bwrap", str(pi), {"prompt": "p"}, skill, private)
        assert ["--ro-bind", str(pi.parents[6]), "/runtime"] == cmd[
            cmd.index(str(pi.parents[6])) - 1 : cmd.index(str(pi.parents[6])) + 2
        ]
    else:
        with pytest.raises(ValueError):
            mod._sandbox_pi_argv("/usr/bin/bwrap", str(pi), {"prompt": "p"}, skill, private)


def test_real_native_wrapper_does_not_use_unconfined_pi_execution():
    script = MODULE.read_text()
    assert "_sandbox_pi_argv(" in script
    assert "bwrap" in script
    assert "_run_native" in script
    assert "filesystem_isolation" in script


def test_only_synthetic_test_model_does_not_claim_a_real_fs_namespace():
    # The injected fake backend tests exercise logical behavior only.
    script = MODULE.read_text()
    assert "filesystem_isolation" in script
    assert "synthetic" in script


def test_actual_native_process_fails_closed_without_bubblewrap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mod = runner_module()
    pi, skill, private, _ = fake_pi(tmp_path)

    # Only the reviewed native Pi binary exists; Linux namespace tool is
    # missing. No unconfined pi subprocess may be created.
    def no_bwrap(name: str):
        return str(pi) if name == "pi" else None

    monkeypatch.setattr(mod.shutil, "which", no_bwrap)
    with pytest.raises(mod.PiNative302Blocked, match="mandatory"):
        mod._run_native(
            {"prompt": "Reviewed synthetic text"},
            skill,
            private,
            timeout=30,
        )
    assert not (private / "native-events.private.jsonl").exists()


def test_one_shared_network_namespace_is_not_a_network_firewall() -> None:
    mod = runner_module()
    assert mod.MODEL_URL.startswith("http://127.0.0.1:")
    assert mod.MODEL_URL.endswith("/v1")
    # Bubblewrap shares the network only so that the already authenticated
    # local SSH forward can be reached. Do not claim arbitrary egress blocked.
    source = MODULE.read_text()
    assert "--share-net" in source
    assert "not all network egress" in source or "not all network egress" in source.lower()


def test_sandbox_argv_does_not_inherit_host_tokens(tmp_path: Path) -> None:
    mod = runner_module()
    pi, skill, private, _ = fake_pi(tmp_path)
    args = mod._sandbox_pi_argv(
        "/usr/bin/bwrap",
        str(pi),
        {"prompt": "Reviewed case"},
        skill,
        private,
    )
    assert "--clearenv" in args
    assert "ANTHROPIC_API_KEY" not in args
    assert "OPENAI_API_KEY" not in args
    assert "HOME" in args
    assert "PI_CODING_AGENT_DIR" in args
    assert "/agent" in args
    assert "/work" in args
    assert "--offline" in args
