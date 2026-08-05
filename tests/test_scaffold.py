"""Tests for the scaffolding behavior of `llm-wiki init`."""

from __future__ import annotations

import datetime
import json
import os
import subprocess
import sys

import pytest
import typer
from typer.testing import CliRunner

from wiki_cli import _scaffold, _skills, _upgrade, app


def test_copy_template_into_empty_dir(tmp_path):
    target = tmp_path / "demo"
    resolved = _scaffold.resolve_target(str(target), force=False)
    _scaffold.copy_template(resolved)

    assert (resolved / "README.md").exists()
    assert (resolved / "WIKI.md").exists()
    assert (resolved / "CLAUDE.md").exists()
    assert (resolved / "AGENTS.md").exists()
    # No git is ever created.
    assert not (resolved / ".git").exists()


def test_placeholders_render(tmp_path):
    target = tmp_path / "my-wiki"
    resolved = _scaffold.resolve_target(str(target), force=False)
    _scaffold.copy_template(resolved)

    readme = (resolved / "README.md").read_text(encoding="utf-8")
    assert "<WIKI_NAME>" not in readme
    assert "my-wiki" in readme


def test_index_placeholder_renders_if_present(tmp_path):
    target = tmp_path / "dated"
    resolved = _scaffold.resolve_target(str(target), force=False)
    _scaffold.copy_template(resolved)

    index = resolved / "wiki" / "index.md"
    if index.exists():
        text = index.read_text(encoding="utf-8")
        assert "<YYYY-MM-DD>" not in text
        assert datetime.date.today().isoformat() in text


def test_non_empty_dir_refused_without_force(tmp_path):
    target = tmp_path / "occupied"
    target.mkdir()
    (target / "existing.txt").write_text("hi", encoding="utf-8")

    with pytest.raises(typer.BadParameter):
        _scaffold.resolve_target(str(target), force=False)


def test_force_allows_non_empty_dir(tmp_path):
    target = tmp_path / "occupied"
    target.mkdir()
    (target / "existing.txt").write_text("hi", encoding="utf-8")

    resolved = _scaffold.resolve_target(str(target), force=True)
    _scaffold.copy_template(resolved)

    assert (resolved / "README.md").exists()
    assert (resolved / "existing.txt").exists()
    assert not (resolved / ".git").exists()


def test_skills_install_writes_claude_dir(tmp_path):
    target = tmp_path / "wiki"
    target.mkdir()
    _skills.install(target)

    claude = target / ".claude"
    assert (claude / "skills" / "prose-voice" / "SKILL.md").exists()
    assert (claude / "skills" / "prose-voice" / "lint-prose.py").exists()
    assert (claude / "commands" / "define-topic.md").exists()
    for name in ("guard-blank-edits", "guard-immutable-dirs", "guard-wiki-links"):
        assert (claude / "hooks" / f"{name}.py").exists()

    # The tool must never write settings.local.json.
    assert not (claude / "settings.local.json").exists()

    agents = target / ".agents" / "skills"
    assert (agents / "prose-voice" / "SKILL.md").exists()
    assert (agents / "define-topic" / "SKILL.md").exists()
    assert (target / ".codex" / "hooks.json").exists()
    assert (target / ".codex" / "hooks" / "guard-edits.py").exists()


def test_skills_install_rewrites_plugin_root(tmp_path):
    target = tmp_path / "wiki"
    target.mkdir()
    _skills.install(target)

    skill = (target / ".claude" / "skills" / "prose-voice" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    assert "${CLAUDE_PLUGIN_ROOT}" not in skill
    assert "${CLAUDE_PROJECT_DIR}/.claude/skills/prose-voice/lint-prose.py" in skill

    codex_skill = (
        target / ".agents" / "skills" / "prose-voice" / "SKILL.md"
    ).read_text(encoding="utf-8")
    assert "CLAUDE_PROJECT_DIR" not in codex_skill
    assert ".agents/skills/prose-voice/lint-prose.py" in codex_skill

    define_topic = (
        target / ".agents" / "skills" / "define-topic" / "SKILL.md"
    ).read_text(encoding="utf-8")
    assert "name: define-topic" in define_topic
    assert "`WIKI.md`" in define_topic


def test_skills_install_wires_guard_hooks(tmp_path):
    target = tmp_path / "wiki"
    target.mkdir()
    _skills.install(target)

    settings = json.loads(
        (target / ".claude" / "settings.json").read_text(encoding="utf-8")
    )
    pre = settings["hooks"]["PreToolUse"]
    commands = [h["command"] for h in pre[0]["hooks"]]
    assert len(commands) == 3
    for name in ("guard-blank-edits", "guard-immutable-dirs", "guard-wiki-links"):
        assert any(f"/.claude/hooks/{name}.py" in c for c in commands)
        assert all("${CLAUDE_PLUGIN_ROOT}" not in c for c in commands)


def test_skills_install_hooks_are_executable(tmp_path):
    target = tmp_path / "wiki"
    target.mkdir()
    _skills.install(target)

    hook = target / ".claude" / "hooks" / "guard-blank-edits.py"
    assert os.access(hook, os.X_OK)
    assert os.access(target / ".codex" / "hooks" / "guard-edits.py", os.X_OK)


def test_init_installs_both_agents_and_manifest(tmp_path):
    target = tmp_path / "wiki"
    result = CliRunner().invoke(app, ["init", str(target)])
    assert result.exit_code == 0, result.output
    assert (target / ".claude" / "settings.json").exists()
    assert (target / ".agents" / "skills" / "define-topic" / "SKILL.md").exists()
    assert (target / ".codex" / "hooks.json").exists()
    manifest = json.loads((target / ".llm-wiki.json").read_text())
    assert manifest["schema_version"] == 1
    assert "AGENTS.md" in manifest["managed_files"]
    assert ".codex/hooks.json" in manifest["managed_files"]


def test_init_no_skills_keeps_entrypoints_only(tmp_path):
    target = tmp_path / "wiki"
    result = CliRunner().invoke(app, ["init", str(target), "--no-skills"])
    assert result.exit_code == 0, result.output
    assert (target / "WIKI.md").exists()
    assert (target / "CLAUDE.md").exists()
    assert (target / "AGENTS.md").exists()
    assert not (target / ".claude").exists()
    assert not (target / ".agents").exists()
    assert not (target / ".codex").exists()


def test_version_option(monkeypatch):
    monkeypatch.setattr(_upgrade, "package_version", lambda: "0.2.0")
    result = CliRunner().invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.output.strip() == "0.2.0"


def _legacy_wiki(path):
    (path / "wiki").mkdir(parents=True)
    (path / "wiki" / "index.md").write_text("# Index\n", encoding="utf-8")
    (path / "TOPIC.md").write_text("# Custom Topic\n", encoding="utf-8")
    (path / "CLAUDE.md").write_text("# Customized schema\n", encoding="utf-8")


def test_upgrade_legacy_wiki_preserves_content_and_is_idempotent(tmp_path):
    target = tmp_path / "legacy"
    _legacy_wiki(target)
    original = {
        path.relative_to(target): path.read_bytes()
        for path in target.rglob("*")
        if path.is_file()
    }

    first = _upgrade.upgrade(target)
    assert "WIKI.md" in first.created
    assert (target / "WIKI.md").read_text() == "# Customized schema\n"
    for relative, content in original.items():
        assert (target / relative).read_bytes() == content
    assert (target / "AGENTS.md").exists()
    assert (target / ".codex" / "hooks.json").exists()

    second = _upgrade.upgrade(target)
    assert not second.created
    assert not second.updated
    assert not second.adopted
    assert not second.conflicts


def test_upgrade_preserves_modified_managed_file(tmp_path):
    target = tmp_path / "legacy"
    _legacy_wiki(target)
    _upgrade.upgrade(target)
    agents = target / "AGENTS.md"
    agents.write_text("custom instructions\n", encoding="utf-8")

    result = _upgrade.upgrade(target)
    assert "AGENTS.md" in result.conflicts
    assert agents.read_text() == "custom instructions\n"


def test_upgrade_adopts_identical_untracked_file(tmp_path):
    target = tmp_path / "legacy"
    _legacy_wiki(target)
    desired = _skills.rendered_files()[".codex/hooks.json"][0]
    hooks = target / ".codex" / "hooks.json"
    hooks.parent.mkdir()
    hooks.write_bytes(desired)

    result = _upgrade.upgrade(target)
    assert ".codex/hooks.json" in result.adopted


def test_upgrade_malformed_manifest_aborts_before_writes(tmp_path):
    target = tmp_path / "legacy"
    _legacy_wiki(target)
    (target / ".llm-wiki.json").write_text("not json", encoding="utf-8")

    with pytest.raises(typer.BadParameter):
        _upgrade.upgrade(target)
    assert not (target / "WIKI.md").exists()
    assert not (target / "AGENTS.md").exists()


def test_upgrade_rejects_non_wiki(tmp_path):
    with pytest.raises(typer.BadParameter):
        _upgrade.upgrade(tmp_path)


def _run_codex_hook(tmp_path, patch):
    target = tmp_path / "wiki"
    target.mkdir(exist_ok=True)
    _skills.install(target)
    payload = {
        "tool_name": "apply_patch",
        "tool_input": {"command": patch},
        "cwd": str(target),
    }
    return subprocess.run(
        [sys.executable, str(target / ".codex" / "hooks" / "guard-edits.py")],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
    )


def _run_claude_hook(tmp_path, name, payload):
    target = tmp_path / "claude-wiki"
    target.mkdir(exist_ok=True)
    _skills.install(target)
    return subprocess.run(
        [sys.executable, str(target / ".claude" / "hooks" / f"{name}.py")],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
    )


@pytest.mark.parametrize(
    ("name", "payload"),
    [
        (
            "guard-immutable-dirs",
            {"tool_name": "Edit", "tool_input": {"file_path": "raw/source.md"}},
        ),
        (
            "guard-blank-edits",
            {
                "tool_name": "Edit",
                "tool_input": {"old_string": "\n", "new_string": "\n\n"},
            },
        ),
        (
            "guard-wiki-links",
            {
                "tool_name": "Write",
                "tool_input": {
                    "file_path": "wiki/page.md",
                    "content": "| Topic | [[slug|Title]] |",
                },
            },
        ),
    ],
)
def test_claude_hooks_still_block_invalid_edits(tmp_path, name, payload):
    assert _run_claude_hook(tmp_path, name, payload).returncode == 2


@pytest.mark.parametrize(
    "header",
    [
        "*** Update File: raw/source.md",
        "*** Add File: Clippings/article.md",
        "*** Delete File: raw/source.md",
        "*** Update File: notes.md\n*** Move to: raw/moved.md",
        r"*** Update File: raw\\source.md",
    ],
)
def test_codex_hook_blocks_immutable_paths(tmp_path, header):
    patch = f"*** Begin Patch\n{header}\n@@\n-old\n+new\n*** End Patch"
    result = _run_codex_hook(tmp_path, patch)
    assert result.returncode == 2
    assert "immutable" in result.stderr


def test_codex_hook_blocks_blank_only_patch(tmp_path):
    patch = "*** Begin Patch\n*** Update File: wiki/page.md\n@@\n-\n+  \n*** End Patch"
    result = _run_codex_hook(tmp_path, patch)
    assert result.returncode == 2
    assert "blank" in result.stderr


def test_codex_hook_blocks_bad_table_link(tmp_path):
    patch = (
        "*** Begin Patch\n*** Update File: wiki/page.md\n@@\n"
        "+| Topic | [[slug|Title]] |\n*** End Patch"
    )
    result = _run_codex_hook(tmp_path, patch)
    assert result.returncode == 2
    assert "unescaped" in result.stderr


def test_codex_hook_checks_every_file_in_multi_file_patch(tmp_path):
    patch = (
        "*** Begin Patch\n*** Update File: wiki/page.md\n@@\n-old\n+new\n"
        "*** Update File: raw/source.md\n@@\n-old\n+new\n*** End Patch"
    )
    result = _run_codex_hook(tmp_path, patch)
    assert result.returncode == 2
    assert "raw/source.md" in result.stderr


def test_codex_hook_allows_valid_edit_and_malformed_input(tmp_path):
    patch = (
        "*** Begin Patch\n*** Update File: wiki/page.md\n@@\n-old\n"
        "+| Topic | [[slug\\|Title]] |\n*** End Patch"
    )
    assert _run_codex_hook(tmp_path, patch).returncode == 0

    target = tmp_path / "malformed"
    target.mkdir()
    _skills.install(target)
    result = subprocess.run(
        [sys.executable, str(target / ".codex" / "hooks" / "guard-edits.py")],
        input="not json",
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0
