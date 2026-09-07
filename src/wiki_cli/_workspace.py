"""Manifest-backed multi-wiki workspace operations."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path

import typer

from . import _okf, _skills, _upgrade

MANIFEST_NAME = ".llm-wiki-workspace.json"
SCHEMA_VERSION = 1
LEGACY_PROSE_REFERENCES = (
    "Follow the `prose-voice` skill (`.claude/skills/prose-voice/SKILL.md` in Claude Code or `.agents/skills/prose-voice/SKILL.md` in Codex).",
    "Follow the `prose-voice` skill (`.claude/skills/prose-voice/SKILL.md`).",
)
WORKSPACE_PROSE_REFERENCE = "Follow the active `prose-voice` skill for this wiki. In a workspace, select the wiki before applying the shared root skill."
DUPLICATE_INTEGRATIONS = (
    ".claude/settings.json",
    ".claude/hooks/guard-blank-edits.py",
    ".claude/hooks/guard-immutable-dirs.py",
    ".claude/hooks/guard-wiki-links.py",
    ".claude/skills/prose-voice/SKILL.md",
    ".claude/skills/prose-voice/lint-prose.py",
    ".agents/skills/prose-voice/SKILL.md",
    ".agents/skills/prose-voice/lint-prose.py",
    ".codex/hooks.json",
    ".codex/hooks/guard-edits.py",
)
OKF_OVERRIDE_START = "<!-- llm-wiki:okf-format:start -->"
OKF_OVERRIDE_END = "<!-- llm-wiki:okf-format:end -->"
OKF_OVERRIDE = f"""{OKF_OVERRIDE_START}
## OKF Format Override

For every document in `wiki/`, use parseable YAML frontmatter with a non-empty OKF `type`. Use relative standard Markdown links, not Obsidian `[[wiki links]]` or bundle-root paths. Record external web provenance in structured `sources:` entries and mirror it in a terminal `## Citations` section. Put internal concept links in a terminal `## Related Concepts` section. Do not put legacy link strings in frontmatter `sources` or `related` fields. This override takes precedence over earlier format instructions.
{OKF_OVERRIDE_END}
"""


def _digest(content: bytes) -> str:
    return "sha256:" + hashlib.sha256(content).hexdigest()


def _root_files() -> dict[str, tuple[bytes, bool]]:
    return _skills.workspace_rendered_files()


def _workspace_upgrade_files() -> dict[str, tuple[bytes, bool]]:
    """Wiki-local entrypoints retained when a wiki joins a workspace."""
    desired = _upgrade._desired_upgrade_files()
    return {key: value for key, value in desired.items() if key in {"AGENTS.md", "CLAUDE.md"}}


def _legacy_schema(reference: str = LEGACY_PROSE_REFERENCES[0]) -> bytes:
    """The pre-workspace template, reconstructed from the current schema."""
    current = (files("wiki_cli") / "template" / "WIKI.md").read_text(encoding="utf-8")
    return current.replace(WORKSPACE_PROSE_REFERENCE, reference).encode()


def _is_legacy_schema(content: bytes) -> bool:
    return content in {_legacy_schema(reference) for reference in LEGACY_PROSE_REFERENCES}


def _manifest_path(root: Path) -> Path:
    return root / MANIFEST_NAME


def _read_manifest(root: Path) -> dict[str, object]:
    path = _manifest_path(root)
    if not path.is_file() or path.is_symlink():
        raise typer.BadParameter(f"No valid workspace manifest at {path}.")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        wikis = value.get("wikis")
        managed = value.get("managed_files")
        if value.get("schema_version") != SCHEMA_VERSION:
            raise ValueError("unsupported schema_version")
        if not isinstance(wikis, list) or not all(isinstance(item, str) for item in wikis):
            raise ValueError("wikis must be a list of paths")
        if not isinstance(managed, dict) or not all(
            isinstance(key, str) and isinstance(item, str) for key, item in managed.items()
        ):
            raise ValueError("managed_files must map paths to hashes")
        return value
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise typer.BadParameter(f"Invalid {path}: {exc}") from exc


def _write_manifest(root: Path, manifest: dict[str, object]) -> None:
    _manifest_path(root).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def _root_path(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if path.parent != root and root not in path.parents:
        raise typer.BadParameter(f"Unsafe workspace path: {relative}")
    return path


def _validate_wiki_path(root: Path, relative: str) -> Path:
    path = _root_path(root, relative)
    if path.parent != root:
        raise typer.BadParameter(f"Workspace wiki must be a top-level directory: {relative}")
    _upgrade._validate_wiki(path)
    return path


def init(root: Path) -> None:
    root = root.expanduser().resolve()
    if _manifest_path(root).exists():
        raise typer.BadParameter(f"Workspace already exists at {root}.")
    root.mkdir(parents=True, exist_ok=True)
    desired = _root_files()
    for relative in desired:
        destination = root / relative
        if destination.exists():
            raise typer.BadParameter(f"Refusing to replace existing workspace file: {destination}")
    managed: dict[str, str] = {}
    for relative, (content, executable) in desired.items():
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
        if executable:
            destination.chmod(destination.stat().st_mode | 0o111)
        managed[relative] = _digest(content)
    _write_manifest(root, {
        "schema_version": SCHEMA_VERSION,
        "template_version": _upgrade.package_version(),
        "managed_files": dict(sorted(managed.items())),
        "wikis": [],
    })


@dataclass
class WikiStatus:
    name: str
    state: str
    detail: str = ""


def status(root: Path) -> list[WikiStatus]:
    root = root.expanduser().resolve()
    manifest = _read_manifest(root)
    result: list[WikiStatus] = []
    for relative in manifest["wikis"]:
        try:
            target = _validate_wiki_path(root, relative)
            conflicts = _upgrade_conflicts(target)
            detail = ", ".join(conflicts or _migration_notes(target))
            result.append(WikiStatus(relative, "conflict" if conflicts else "ready", detail))
        except typer.BadParameter as exc:
            result.append(WikiStatus(relative, "invalid", str(exc)))
    return result


def _upgrade_conflicts(target: Path) -> list[str]:
    """Mirror upgrade's write-conflict checks without changing the wiki."""
    manifest = _upgrade._read_manifest(target)
    managed = dict(manifest["managed_files"])
    conflicts: list[str] = []
    schema = target / "WIKI.md"
    if not schema.exists() and not (target / "CLAUDE.md").is_file():
        return ["WIKI.md"]
    for relative, (desired, _executable) in _workspace_upgrade_files().items():
        destination = target / relative
        if destination.is_symlink() or (destination.exists() and not destination.is_file()):
            conflicts.append(relative)
        elif destination.is_file():
            current = destination.read_bytes()
            recorded = managed.get(relative)
            if recorded is None and current != desired:
                if not (relative == "CLAUDE.md" and schema.is_file() and schema.read_bytes() == current):
                    conflicts.append(relative)
            elif recorded is not None and _digest(current) != recorded:
                conflicts.append(relative)
    return conflicts


def _migration_notes(target: Path) -> list[str]:
    schema = target / "WIKI.md"
    if not schema.is_file():
        return []
    current = schema.read_bytes()
    if _is_legacy_schema(current):
        return ["will migrate WIKI.md and remove duplicate integrations"]
    if WORKSPACE_PROSE_REFERENCE not in current.decode("utf-8", errors="replace"):
        return ["retaining local integrations because WIKI.md is customized"]
    return []


def selected_wikis(root: Path, names: list[str] | None = None) -> list[tuple[str, Path]]:
    root = root.expanduser().resolve()
    manifest = _read_manifest(root)
    registered = list(manifest["wikis"])
    chosen = names or registered
    unknown = sorted(set(chosen) - set(registered))
    if unknown:
        raise typer.BadParameter(f"Unregistered wiki: {', '.join(unknown)}")
    return [(relative, _validate_wiki_path(root, relative)) for relative in chosen]


def upgrade(root: Path, *, names: list[str] | None, apply: bool) -> list[WikiStatus]:
    selected = selected_wikis(root, names)
    statuses: list[WikiStatus] = []
    for name, target in selected:
        conflicts = _upgrade_conflicts(target)
        statuses.append(WikiStatus(name, "conflict" if conflicts else "ready", ", ".join(conflicts or _migration_notes(target))))
    if not apply or any(item.state != "ready" for item in statuses):
        return statuses
    return [WikiStatus(name, "upgraded", _workspace_upgrade(target)) for name, target in selected]


def migrate_okf(root: Path, *, names: list[str] | None, apply: bool) -> list[WikiStatus]:
    """Preview or apply an all-or-nothing OKF migration for selected wikis."""
    selected = selected_wikis(root, names)
    plans: list[tuple[str, Path, _okf.MigrationPlan]] = []
    statuses: list[WikiStatus] = []
    for name, target in selected:
        plan = _okf.build_plan(target / "wiki")
        plans.append((name, target, plan))
        if plan.issues:
            statuses.append(WikiStatus(name, "blocked", "; ".join(plan.issues)))
        else:
            statuses.append(WikiStatus(name, "ready", f"{len(plan.changes)} corpus file(s) will change"))
    if not apply or any(status.state == "blocked" for status in statuses):
        return statuses
    for name, target, plan in plans:
        for path, content in plan.changes.items():
            path.write_text(content, encoding="utf-8")
        _append_okf_override(target / "WIKI.md")
    return [WikiStatus(name, "migrated", f"{len(plan.changes)} corpus file(s) updated") for name, _target, plan in plans]


def _append_okf_override(schema: Path) -> None:
    text = schema.read_text(encoding="utf-8")
    pattern = re.compile(rf"\n?{re.escape(OKF_OVERRIDE_START)}.*?{re.escape(OKF_OVERRIDE_END)}\n?", re.DOTALL)
    text = pattern.sub("\n", text).rstrip() + "\n\n" + OKF_OVERRIDE
    schema.write_text(text, encoding="utf-8")


def _workspace_upgrade(target: Path) -> str:
    """Refresh entrypoints and retire only safe duplicate local integrations."""
    manifest = _upgrade._read_manifest(target)
    managed = dict(manifest["managed_files"])
    changes: list[str] = []
    schema = target / "WIKI.md"
    if not schema.exists():
        schema.write_bytes((target / "CLAUDE.md").read_bytes())
        changes.append("WIKI.md")

    for relative, (desired, _executable) in _workspace_upgrade_files().items():
        destination = target / relative
        if destination.is_file():
            current = destination.read_bytes()
            recorded = managed.get(relative)
            if recorded is None and current == desired:
                changes.append(f"adopted {relative}")
            elif current != desired:
                destination.write_bytes(desired)
                changes.append(relative)
            managed[relative] = _digest(desired)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(desired)
            managed[relative] = _digest(desired)
            changes.append(relative)

    if _is_legacy_schema(schema.read_bytes()):
        text = schema.read_text(encoding="utf-8")
        for reference in LEGACY_PROSE_REFERENCES:
            text = text.replace(reference, WORKSPACE_PROSE_REFERENCE)
        schema.write_text(
            text,
            encoding="utf-8",
        )
        changes.append("migrated WIKI.md")

    if WORKSPACE_PROSE_REFERENCE in schema.read_text(encoding="utf-8", errors="replace"):
        for relative in DUPLICATE_INTEGRATIONS:
            destination = target / relative
            recorded = managed.get(relative)
            if destination.is_file() and recorded == _digest(destination.read_bytes()):
                destination.unlink()
                managed.pop(relative, None)
                changes.append(f"removed {relative}")

    _upgrade._write_manifest(target, managed)
    return ", ".join(changes) if changes else "already up to date"


def import_wiki(root: Path, source: Path, name: str | None = None) -> str:
    root = root.expanduser().resolve()
    manifest = _read_manifest(root)
    source = source.expanduser().resolve()
    _upgrade._validate_wiki(source)
    destination_name = name or source.name
    if Path(destination_name).name != destination_name or destination_name in {"", ".", ".."}:
        raise typer.BadParameter("NAME must be a simple top-level directory name.")
    destination = root / destination_name
    if destination.exists():
        raise typer.BadParameter(f"Destination already exists: {destination}")
    if destination_name in manifest["wikis"]:
        raise typer.BadParameter(f"Wiki already registered: {destination_name}")
    shutil.copytree(source, destination, ignore=shutil.ignore_patterns(".git"))
    _workspace_upgrade(destination)
    manifest["wikis"].append(destination_name)
    manifest["wikis"].sort()
    _write_manifest(root, manifest)
    return destination_name
