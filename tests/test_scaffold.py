"""Tests for the scaffolding behavior of `llm-wiki init`."""

from __future__ import annotations

import datetime
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from wiki_cli import _okf, _scaffold, _skills, _upgrade, _workspace, app


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
    monkeypatch.setattr(_upgrade, "package_version", lambda: "0.6.0")
    result = CliRunner().invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.output.strip() == "0.6.0"


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
        if str(relative) == "CLAUDE.md":
            continue
        assert (target / relative).read_bytes() == content
    assert (target / "CLAUDE.md").read_bytes() == (
        _upgrade._entrypoint("CLAUDE.md")
    )
    assert "CLAUDE.md" in first.updated
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


def test_upgrade_preserves_diverged_legacy_claude_file(tmp_path):
    target = tmp_path / "legacy"
    _legacy_wiki(target)
    (target / "WIKI.md").write_text("# Independently edited schema\n", encoding="utf-8")

    result = _upgrade.upgrade(target)
    assert "CLAUDE.md" in result.conflicts
    assert (target / "CLAUDE.md").read_text() == "# Customized schema\n"
    assert (target / "WIKI.md").read_text() == "# Independently edited schema\n"


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


def test_workspace_init_creates_root_integrations_without_wiki(tmp_path):
    root = tmp_path / "workspace"
    result = CliRunner().invoke(app, ["workspace", "init", str(root)])

    assert result.exit_code == 0, result.output
    manifest = json.loads((root / ".llm-wiki-workspace.json").read_text())
    assert manifest["wikis"] == []
    assert (root / "AGENTS.md").exists()
    assert (root / ".gitignore").read_bytes() == (Path(__file__).parents[1] / "src" / "wiki_cli" / "template" / ".gitignore").read_bytes()
    assert (root / "insights" / ".gitkeep").exists()
    assert (root / "research" / ".gitkeep").exists()
    assert (root / "wikis" / ".gitkeep").exists()
    assert (root / ".agents" / "skills" / "select-wiki" / "SKILL.md").exists()
    assert (root / ".agents" / "skills" / "research-project" / "SKILL.md").exists()
    assert (root / ".claude" / "commands" / "research-project.md").exists()
    assert not (root / "TOPIC.md").exists()


def test_workspace_init_merges_existing_gitignore(tmp_path):
    root = tmp_path / "workspace"
    root.mkdir()
    (root / ".gitignore").write_text("node_modules/\n", encoding="utf-8")

    _workspace.init(root)

    text = (root / ".gitignore").read_text()
    assert "node_modules/" in text
    assert "**/.obsidian/workspace.json" in text


def test_workspace_research_init_scaffolds_slugged_project_and_status(tmp_path):
    root = tmp_path / "workspace"
    _workspace.init(root)

    result = CliRunner().invoke(app, [
        "workspace", "research", "init", "Compare Local-First Note Apps!", "--workspace", str(root),
    ])

    project = root / "research" / "compare-local-first-note-apps"
    assert result.exit_code == 0, result.output
    assert (project / "BRIEF.md").is_file()
    assert (project / "REPORT.md").is_file()
    assert (project / "SOURCES.md").is_file()
    assert "## References" in (project / "REPORT.md").read_text()
    assert _workspace.research_status(root) == [
        _workspace.ResearchStatus("compare-local-first-note-apps", "ready")
    ]


def test_workspace_research_rejects_collisions_and_reports_incomplete_projects(tmp_path):
    root = tmp_path / "workspace"
    _workspace.init(root)
    _workspace.init_research_project(root, "A Question")

    duplicate = CliRunner().invoke(app, ["workspace", "research", "init", "a question", "--workspace", str(root)])
    (root / "research" / "a-question" / "SOURCES.md").unlink()
    status = CliRunner().invoke(app, ["workspace", "research", "status", str(root)])

    assert duplicate.exit_code != 0
    assert "already exists" in duplicate.output
    assert status.exit_code == 0, status.output
    assert "a-question: incomplete (missing SOURCES.md)" in status.output


def test_workspace_research_requires_valid_workspace(tmp_path):
    result = CliRunner().invoke(app, ["workspace", "research", "init", "Question", "--workspace", str(tmp_path)])

    assert result.exit_code != 0
    assert "No valid workspace manifest" in result.output


def test_workspace_import_rejects_research_directory_name(tmp_path):
    root = tmp_path / "workspace"
    _workspace.init(root)
    source = tmp_path / "source-wiki"
    CliRunner().invoke(app, ["init", str(source)])

    result = CliRunner().invoke(app, ["workspace", "import", str(source), "research", "--workspace", str(root)])

    assert result.exit_code != 0
    assert "reserved" in result.output


def test_workspace_import_excludes_git_and_registers_wiki(tmp_path):
    root = tmp_path / "workspace"
    _workspace.init(root)
    source = tmp_path / "source-wiki"
    CliRunner().invoke(app, ["init", str(source)])
    (source / ".git").mkdir()
    (source / ".git" / "config").write_text("private", encoding="utf-8")

    result = CliRunner().invoke(app, ["workspace", "import", str(source), "knowledge", "--workspace", str(root)])

    assert result.exit_code == 0, result.output
    assert (root / "wikis" / "knowledge" / "TOPIC.md").exists()
    assert not (root / "wikis" / "knowledge" / ".git").exists()
    assert not (root / "wikis" / "knowledge" / ".codex" / "hooks.json").exists()
    assert json.loads((root / ".llm-wiki-workspace.json").read_text())["wikis"] == ["wikis/knowledge"]
    assert _workspace.status(root)[0].state == "ready"


def test_workspace_upgrade_moves_legacy_root_wikis_into_wikis_directory(tmp_path):
    root = tmp_path / "workspace"
    _workspace.init(root)
    legacy = root / "knowledge"
    CliRunner().invoke(app, ["init", str(legacy)])
    manifest_path = root / ".llm-wiki-workspace.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["wikis"] = ["knowledge"]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    preview = CliRunner().invoke(app, ["workspace", "upgrade", str(root), "--wiki", "knowledge"])

    assert preview.exit_code == 0, preview.output
    assert legacy.exists()
    assert "will move into" in preview.output
    assert "wikis/)" in preview.output

    result = CliRunner().invoke(app, ["workspace", "upgrade", str(root), "--wiki", "knowledge", "--apply"])

    destination = root / "wikis" / "knowledge"
    assert result.exit_code == 0, result.output
    assert not legacy.exists()
    assert (destination / "TOPIC.md").exists()
    assert json.loads(manifest_path.read_text())["wikis"] == ["wikis/knowledge"]


def test_workspace_upgrade_does_not_move_any_wiki_when_layout_destination_conflicts(tmp_path):
    root = tmp_path / "workspace"
    _workspace.init(root)
    legacy = root / "knowledge"
    destination = root / "wikis" / "knowledge"
    CliRunner().invoke(app, ["init", str(legacy)])
    CliRunner().invoke(app, ["init", str(destination)])
    manifest_path = root / ".llm-wiki-workspace.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["wikis"] = ["knowledge"]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    result = CliRunner().invoke(app, ["workspace", "upgrade", str(root), "--apply"])

    assert result.exit_code == 1
    assert legacy.exists()
    assert destination.exists()
    assert json.loads(manifest_path.read_text())["wikis"] == ["knowledge"]


def test_workspace_upgrade_is_read_only_until_apply_and_preflights_all(tmp_path):
    root = tmp_path / "workspace"
    _workspace.init(root)
    for name in ("one", "two"):
        wiki = root / name
        CliRunner().invoke(app, ["init", str(wiki)])
    manifest = json.loads((root / ".llm-wiki-workspace.json").read_text())
    manifest["wikis"] = ["one", "two"]
    (root / ".llm-wiki-workspace.json").write_text(json.dumps(manifest), encoding="utf-8")
    original = (root / "one" / "AGENTS.md").read_bytes()
    (root / "two" / "AGENTS.md").write_text("custom", encoding="utf-8")

    result = CliRunner().invoke(app, ["workspace", "upgrade", str(root), "--apply"])

    assert result.exit_code == 1
    assert (root / "one" / "AGENTS.md").read_bytes() == original
    assert "two: conflict" in result.output


def test_workspace_upgrade_adds_insights_to_existing_workspace(tmp_path):
    root = tmp_path / "workspace"
    _workspace.init(root)
    insights = root / "insights" / ".gitkeep"
    insights.unlink()
    insights.parent.rmdir()
    manifest_path = root / ".llm-wiki-workspace.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["managed_files"].pop("insights/.gitkeep")
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    preview = CliRunner().invoke(app, ["workspace", "upgrade", str(root)])

    assert preview.exit_code == 0, preview.output
    assert not insights.exists()
    assert "workspace: ready" in preview.output

    result = CliRunner().invoke(app, ["workspace", "upgrade", str(root), "--apply"])

    assert result.exit_code == 0, result.output
    assert insights.exists()
    assert "insights/.gitkeep" in json.loads(manifest_path.read_text())["managed_files"]


def test_workspace_upgrade_adds_research_directory_to_existing_workspace(tmp_path):
    root = tmp_path / "workspace"
    _workspace.init(root)
    research = root / "research" / ".gitkeep"
    research.unlink()
    research.parent.rmdir()
    manifest_path = root / ".llm-wiki-workspace.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["managed_files"].pop("research/.gitkeep")
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    result = CliRunner().invoke(app, ["workspace", "upgrade", str(root), "--workspace-only", "--apply"])

    assert result.exit_code == 0, result.output
    assert research.exists()
    assert "research/.gitkeep" in json.loads(manifest_path.read_text())["managed_files"]


def test_workspace_upgrade_workspace_only_skips_registered_wikis(tmp_path):
    root = tmp_path / "workspace"
    _workspace.init(root)
    wiki = root / "knowledge"
    CliRunner().invoke(app, ["init", str(wiki)])
    manifest_path = root / ".llm-wiki-workspace.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["wikis"] = ["knowledge"]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    original = (wiki / "AGENTS.md").read_bytes()
    (wiki / "AGENTS.md").write_text("custom", encoding="utf-8")

    result = CliRunner().invoke(app, ["workspace", "upgrade", str(root), "--workspace-only", "--apply"])

    assert result.exit_code == 0, result.output
    assert (wiki / "AGENTS.md").read_bytes() != original
    assert "research:" not in result.output


def test_workspace_rejects_unregistered_selection(tmp_path):
    root = tmp_path / "workspace"
    _workspace.init(root)

    result = CliRunner().invoke(app, ["workspace", "upgrade", str(root), "--wiki", "missing"])

    assert result.exit_code != 0
    assert "Unregistered wiki" in result.output


def test_workspace_upgrade_migrates_unmodified_schema_and_removes_duplicates(tmp_path):
    root = tmp_path / "workspace"
    _workspace.init(root)
    source = tmp_path / "legacy-wiki"
    CliRunner().invoke(app, ["init", str(source)])
    schema = source / "WIKI.md"
    schema.write_bytes(_workspace._legacy_schema())
    _workspace.import_wiki(root, source, "knowledge")

    target = root / "wikis" / "knowledge"
    assert _workspace.WORKSPACE_PROSE_REFERENCE in (target / "WIKI.md").read_text()
    assert not (target / ".agents" / "skills" / "prose-voice" / "SKILL.md").exists()
    assert not (target / ".codex" / "hooks.json").exists()
    assert (target / ".agents" / "skills" / "define-topic" / "SKILL.md").exists()


def test_workspace_upgrade_recognizes_claude_only_legacy_schema(tmp_path):
    root = tmp_path / "workspace"
    _workspace.init(root)
    source = tmp_path / "claude-only-wiki"
    CliRunner().invoke(app, ["init", str(source)])
    (source / "WIKI.md").write_bytes(_workspace._legacy_schema(_workspace.LEGACY_PROSE_REFERENCES[1]))

    _workspace.import_wiki(root, source, "claude-only")

    target = root / "wikis" / "claude-only"
    assert _workspace.WORKSPACE_PROSE_REFERENCE in (target / "WIKI.md").read_text()
    assert not (target / ".claude" / "skills" / "prose-voice" / "SKILL.md").exists()


def test_workspace_upgrade_preserves_duplicates_for_custom_schema(tmp_path):
    root = tmp_path / "workspace"
    _workspace.init(root)
    source = tmp_path / "custom-wiki"
    CliRunner().invoke(app, ["init", str(source)])
    (source / "WIKI.md").write_text("# Custom schema\n", encoding="utf-8")
    _workspace.import_wiki(root, source, "custom")

    result = CliRunner().invoke(app, ["workspace", "upgrade", str(root), "--apply"])

    assert result.exit_code == 0, result.output
    assert (root / "wikis" / "custom" / ".agents" / "skills" / "prose-voice" / "SKILL.md").exists()


def test_okf_migration_previews_then_converts_links_sources_and_sections(tmp_path):
    root = tmp_path / "workspace"
    _workspace.init(root)
    wiki = root / "knowledge"
    CliRunner().invoke(app, ["init", str(wiki)])
    concepts = wiki / "wiki" / "concepts"
    sources = wiki / "wiki" / "sources"
    concepts.mkdir(exist_ok=True)
    sources.mkdir(exist_ok=True)
    (wiki / "raw" / "notes.pdf").write_text("source", encoding="utf-8")
    (sources / "reference.md").write_text(
        "---\ntitle: Reference\ntype: source-summary\ntags: [x]\nsources:\n  - \"[Web](https://example.com)\"\nrelated: []\n---\n\nSource body.\n",
        encoding="utf-8",
    )
    page = concepts / "topic.md"
    original = """---
title: Topic
type: concept
tags: [x]
sources:
  - "[[reference|Reference]]"
  - "[[notes.pdf]]"
related:
  - "[[reference|Reference]]"
created: 2026-01-01
updated: 2026-01-02
---

See [[reference|the reference]].

## Citations

Existing citation prose.
"""
    page.write_text(original, encoding="utf-8")
    manifest = json.loads((root / ".llm-wiki-workspace.json").read_text())
    manifest["wikis"] = ["knowledge"]
    (root / ".llm-wiki-workspace.json").write_text(json.dumps(manifest), encoding="utf-8")

    preview = CliRunner().invoke(app, ["workspace", "migrate-okf", str(root), "--wiki", "knowledge"])
    assert preview.exit_code == 0, preview.output
    assert page.read_text() == original
    applied = CliRunner().invoke(app, ["workspace", "migrate-okf", str(root), "--wiki", "knowledge", "--apply"])

    converted = page.read_text()
    assert applied.exit_code == 0, applied.output
    assert "type: Concept" in converted
    assert "sources:" not in converted
    assert "[notes.pdf](../../raw/notes.pdf)" in converted
    assert "[Reference](../sources/reference.md)" in converted
    assert "## Related Concepts" in converted
    assert "Existing citation prose." in converted
    assert 'okf_version: "0.2"' in (wiki / "wiki" / "index.md").read_text()
    assert _workspace.OKF_OVERRIDE_START in (wiki / "WIKI.md").read_text()

    page.write_text(converted.replace("../sources/reference.md", "/sources/reference.md"), encoding="utf-8")
    repaired = CliRunner().invoke(app, ["workspace", "migrate-okf", str(root), "--wiki", "knowledge", "--apply"])
    assert repaired.exit_code == 0, repaired.output
    assert "[Reference](../sources/reference.md)" in page.read_text()


def test_okf_migration_blocks_all_selected_wikis_on_unresolved_link(tmp_path):
    root = tmp_path / "workspace"
    _workspace.init(root)
    wiki = root / "broken"
    CliRunner().invoke(app, ["init", str(wiki)])
    page = wiki / "wiki" / "concepts" / "broken.md"
    page.write_text("---\ntype: concept\nsources: [\"[[missing]]\"]\n---\n", encoding="utf-8")
    manifest = json.loads((root / ".llm-wiki-workspace.json").read_text())
    manifest["wikis"] = ["broken"]
    (root / ".llm-wiki-workspace.json").write_text(json.dumps(manifest), encoding="utf-8")

    result = CliRunner().invoke(app, ["workspace", "migrate-okf", str(root), "--apply"])

    assert result.exit_code == 1
    assert page.read_text() == "---\ntype: concept\nsources: [\"[[missing]]\"]\n---\n"


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
                    "content": "See [[slug|Title]].",
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
        "+See [[slug|Title]].\n*** End Patch"
    )
    result = _run_codex_hook(tmp_path, patch)
    assert result.returncode == 2
    assert "Obsidian" in result.stderr


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
        "+See [Title](/concepts/slug.md).\n*** End Patch"
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
