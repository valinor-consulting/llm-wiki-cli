"""Tests for the scaffolding behavior of `llm-wiki init`."""

from __future__ import annotations

import datetime
import json
import os

import pytest
import typer

from wiki_cli import _scaffold, _skills


def test_copy_template_into_empty_dir(tmp_path):
    target = tmp_path / "demo"
    resolved = _scaffold.resolve_target(str(target), force=False)
    _scaffold.copy_template(resolved)

    assert (resolved / "README.md").exists()
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


def test_skills_install_rewrites_plugin_root(tmp_path):
    target = tmp_path / "wiki"
    target.mkdir()
    _skills.install(target)

    skill = (target / ".claude" / "skills" / "prose-voice" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    assert "${CLAUDE_PLUGIN_ROOT}" not in skill
    assert "${CLAUDE_PROJECT_DIR}/.claude/skills/prose-voice/lint-prose.py" in skill


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
