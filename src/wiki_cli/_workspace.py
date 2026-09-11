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

from . import _okf, _scaffold, _skills, _upgrade

MANIFEST_NAME = ".llm-wiki-workspace.json"
SCHEMA_VERSION = 1
RESEARCH_DIRECTORY = "research"
RESEARCH_FILES = ("BRIEF.md", "REPORT.md", "SOURCES.md")
WIKIS_DIRECTORY = "wikis"
RESERVED_WORKSPACE_DIRECTORIES = {"insights", RESEARCH_DIRECTORY, WIKIS_DIRECTORY}
LEGACY_PROSE_REFERENCES = (
    "Follow the `prose-voice` skill (`.claude/skills/prose-voice/SKILL.md` in Claude Code or `.agents/skills/prose-voice/SKILL.md` in Codex).",
    "Follow the `prose-voice` skill (`.claude/skills/prose-voice/SKILL.md`).",
)
WORKSPACE_PROSE_REFERENCE = "Follow the active `prose-voice` skill for this wiki. In a workspace, select the wiki before applying the shared root skill."
LEGACY_OBSIDIAN_SCHEMA_MARKERS = (
    "## Frontmatter Schema\n",
    "**Formatting rule — `sources:` and `related:` MUST use a block list",
    "**Internal links** (between wiki files): Obsidian wiki syntax",
    "## index.md Format\n",
    "## log.md Format\n",
)
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
    files_to_write = _skills.workspace_rendered_files()
    files_to_write[".gitignore"] = (
        (files("wiki_cli") / "template" / ".gitignore").read_bytes(),
        False,
    )
    return files_to_write


def _workspace_upgrade_files() -> dict[str, tuple[bytes, bool]]:
    """Wiki-local entrypoints retained when a wiki joins a workspace."""
    desired = _upgrade._desired_upgrade_files()
    return {key: value for key, value in desired.items() if key in {"AGENTS.md", "CLAUDE.md"}}


def _legacy_schema(reference: str = LEGACY_PROSE_REFERENCES[0]) -> bytes:
    """The pre-workspace template, reconstructed from the current schema."""
    current = (files("wiki_cli") / "template" / "WIKI.md").read_text(encoding="utf-8")
    return current.replace(WORKSPACE_PROSE_REFERENCE, reference).encode()


def _is_legacy_schema(content: bytes) -> bool:
    if content in {_legacy_schema(reference) for reference in LEGACY_PROSE_REFERENCES}:
        return True

    # Before workspace support, generated wikis used an Obsidian-specific
    # schema. Some versions also included project boilerplate, example log
    # entries, or minor formatting variations. Those are template history,
    # not user customization, so recognize the family rather than requiring a
    # byte-for-byte match. Requiring all structural markers and the old skill
    # reference keeps an unrelated custom schema out of this migration path.
    text = content.decode("utf-8", errors="replace")
    return (
        WORKSPACE_PROSE_REFERENCE not in text
        and any(reference in text for reference in LEGACY_PROSE_REFERENCES)
        and all(marker in text for marker in LEGACY_OBSIDIAN_SCHEMA_MARKERS)
    )


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
    if relative in RESERVED_WORKSPACE_DIRECTORIES:
        raise typer.BadParameter(f"Workspace wiki path is reserved: {relative}")
    path = _root_path(root, relative)
    parts = Path(relative).parts
    is_legacy = len(parts) == 1
    is_canonical = len(parts) == 2 and parts[0] == WIKIS_DIRECTORY
    if not (is_legacy or is_canonical):
        raise typer.BadParameter(f"Workspace wiki must be a direct child of {WIKIS_DIRECTORY}/: {relative}")
    expected_parent = root if is_legacy else root / WIKIS_DIRECTORY
    if path.parent != expected_parent:
        raise typer.BadParameter(f"Unsafe workspace wiki path: {relative}")
    _upgrade._validate_wiki(path)
    return path


def _canonical_wiki_path(name: str) -> str:
    return f"{WIKIS_DIRECTORY}/{name}"


def _is_legacy_wiki_path(relative: str) -> bool:
    return len(Path(relative).parts) == 1 and relative not in RESERVED_WORKSPACE_DIRECTORIES


def init(root: Path) -> None:
    root = root.expanduser().resolve()
    if _manifest_path(root).exists():
        raise typer.BadParameter(f"Workspace already exists at {root}.")
    root.mkdir(parents=True, exist_ok=True)
    desired = _root_files()
    for relative in desired:
        destination = root / relative
        if destination.exists() and relative != ".gitignore":
            raise typer.BadParameter(f"Refusing to replace existing workspace file: {destination}")
    managed: dict[str, str] = {}
    for relative, (content, executable) in desired.items():
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if relative == ".gitignore" and destination.exists():
            content = _merge_gitignore(destination.read_bytes(), content)
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


def _merge_gitignore(existing: bytes, required: bytes) -> bytes:
    """Append only missing bundled ignore lines, preserving a repository's rules."""
    existing_text = existing.decode("utf-8")
    required_text = required.decode("utf-8")
    existing_lines = set(existing_text.splitlines())
    missing = [line for line in required_text.splitlines() if line not in existing_lines]
    if not missing:
        return existing
    return (existing_text.rstrip() + "\n" + "\n".join(missing) + "\n").encode()


@dataclass
class WikiStatus:
    name: str
    state: str
    detail: str = ""


@dataclass
class ResearchStatus:
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
            notes = conflicts or _migration_notes(target)
            if _is_legacy_wiki_path(relative):
                notes = [*notes, f"will move to {_canonical_wiki_path(relative)}"]
            detail = ", ".join(notes)
            result.append(WikiStatus(relative, "conflict" if conflicts else "ready", detail))
        except typer.BadParameter as exc:
            result.append(WikiStatus(relative, "invalid", str(exc)))
    return result


def _research_slug(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    if not slug:
        raise typer.BadParameter("NAME must contain at least one letter or number.")
    return slug


def _research_path(root: Path, slug: str) -> Path:
    return _root_path(root, f"{RESEARCH_DIRECTORY}/{slug}")


def _research_templates(name: str) -> dict[str, str]:
    return {
        "BRIEF.md": f"""# {name}\n\n## Research question\n\n<!-- What do you want to understand? -->\n\n## Context and constraints\n\n<!-- Audience, scope, constraints, and relevant prior knowledge. -->\n\n## Definition of done\n\n<!-- What would let you confidently conclude this project? -->\n""",
        "REPORT.md": f"""# {name}\n\n## Current answer\n\n<!-- Refine this answer as the research develops. -->\n\n## Findings\n\n<!-- Evidence-backed findings in clear language. -->\n\n## Open questions\n\n<!-- Important uncertainty or next questions. -->\n\n## References\n\n<!-- Use standard Markdown links for cited sources. -->\n""",
        "SOURCES.md": f"""# {name} Source Ledger\n\n<!-- Record useful sources, their relevance, and any notes for later verification. -->\n""",
    }


def init_research_project(root: Path, name: str) -> str:
    """Create a lightweight research project in a validated workspace."""
    root = root.expanduser().resolve()
    _read_manifest(root)
    slug = _research_slug(name)
    destination = _research_path(root, slug)
    if destination.exists() or destination.is_symlink():
        raise typer.BadParameter(f"Research project already exists: {destination}")
    destination.mkdir(parents=True)
    for relative, content in _research_templates(name).items():
        (destination / relative).write_text(content, encoding="utf-8")
    return slug


def research_status(root: Path) -> list[ResearchStatus]:
    """List direct-child research projects and their required-file status."""
    root = root.expanduser().resolve()
    _read_manifest(root)
    directory = _root_path(root, RESEARCH_DIRECTORY)
    if not directory.exists():
        return []
    if directory.is_symlink() or not directory.is_dir():
        raise typer.BadParameter(f"Invalid research directory: {directory}")
    result: list[ResearchStatus] = []
    for project in sorted(directory.iterdir(), key=lambda item: item.name):
        if not project.is_dir() or project.is_symlink():
            continue
        missing = [name for name in RESEARCH_FILES if not (project / name).is_file()]
        result.append(ResearchStatus(
            project.name,
            "ready" if not missing else "incomplete",
            "" if not missing else f"missing {', '.join(missing)}",
        ))
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
    aliases = {Path(relative).name: relative for relative in registered}
    requested = registered if names is None else names
    chosen = [aliases.get(name, name) for name in requested]
    unknown = sorted(set(chosen) - set(registered))
    if unknown:
        raise typer.BadParameter(f"Unregistered wiki: {', '.join(unknown)}")
    return [(relative, _validate_wiki_path(root, relative)) for relative in chosen]


def _layout_moves(root: Path, selected: list[tuple[str, Path]]) -> tuple[list[tuple[str, Path, Path]], list[str]]:
    """Preflight legacy root-wiki moves without changing the workspace."""
    moves: list[tuple[str, Path, Path]] = []
    conflicts: list[str] = []
    wiki_directory = root / WIKIS_DIRECTORY
    if wiki_directory.is_symlink() or (wiki_directory.exists() and not wiki_directory.is_dir()):
        return moves, [WIKIS_DIRECTORY]
    for relative, source in selected:
        if not _is_legacy_wiki_path(relative):
            continue
        destination = wiki_directory / relative
        if destination.exists() or destination.is_symlink():
            conflicts.append(f"{relative} -> {_canonical_wiki_path(relative)}")
        else:
            moves.append((relative, source, destination))
    return moves, conflicts


def _apply_layout_moves(root: Path, moves: list[tuple[str, Path, Path]]) -> dict[str, Path]:
    """Move preflighted legacy wikis and register their canonical paths."""
    relocated: dict[str, Path] = {}
    for relative, source, destination in moves:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(destination))
        relocated[relative] = destination
    if relocated:
        manifest = _read_manifest(root)
        manifest["wikis"] = sorted(
            _canonical_wiki_path(relative) if relative in relocated else relative
            for relative in manifest["wikis"]
        )
        _write_manifest(root, manifest)
    return relocated


def _root_upgrade_plan(root: Path) -> tuple[dict[str, tuple[bytes, bool]], list[str]]:
    """Return safe root-managed updates and conflicts without writing anything."""
    manifest = _read_manifest(root)
    managed = dict(manifest["managed_files"])
    updates: dict[str, tuple[bytes, bool]] = {}
    conflicts: list[str] = []
    for relative, (desired, executable) in _root_files().items():
        destination = root / relative
        if destination.is_symlink() or (destination.exists() and not destination.is_file()):
            conflicts.append(relative)
            continue
        if relative == ".gitignore" and destination.is_file():
            merged = _merge_gitignore(destination.read_bytes(), desired)
            if merged != destination.read_bytes() or managed.get(relative) != _digest(merged):
                updates[relative] = (merged, executable)
            continue
        if not destination.exists():
            updates[relative] = (desired, executable)
            continue
        current = destination.read_bytes()
        recorded = managed.get(relative)
        if recorded is None and current != desired:
            conflicts.append(relative)
        elif recorded is not None and _digest(current) != recorded:
            conflicts.append(relative)
        elif current != desired or recorded != _digest(desired):
            updates[relative] = (desired, executable)
    return updates, conflicts


def _apply_root_upgrade(root: Path, updates: dict[str, tuple[bytes, bool]]) -> None:
    manifest = _read_manifest(root)
    managed = dict(manifest["managed_files"])
    for relative, (content, executable) in updates.items():
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
        if executable:
            destination.chmod(destination.stat().st_mode | 0o111)
    for relative, (content, _executable) in _root_files().items():
        destination = root / relative
        if destination.is_file() and not destination.is_symlink():
            managed[relative] = _digest(destination.read_bytes())
    manifest["managed_files"] = dict(sorted(managed.items()))
    manifest["template_version"] = _upgrade.package_version()
    _write_manifest(root, manifest)


def upgrade(root: Path, *, names: list[str] | None, apply: bool) -> list[WikiStatus]:
    root = root.expanduser().resolve()
    root_updates, root_conflicts = _root_upgrade_plan(root)
    selected = selected_wikis(root, names)
    moves, move_conflicts = _layout_moves(root, selected)
    statuses: list[WikiStatus] = [
        WikiStatus(
            "workspace",
            "conflict" if root_conflicts or move_conflicts else "ready",
            ", ".join(root_conflicts + move_conflicts) if root_conflicts or move_conflicts else (
                f"{len(root_updates)} root-managed file(s) will update"
                + (f"; {len(moves)} wiki(s) will move into {WIKIS_DIRECTORY}/" if moves else "")
                if root_updates or moves else "already up to date"
            ),
        )
    ]
    for name, target in selected:
        conflicts = _upgrade_conflicts(target)
        statuses.append(WikiStatus(name, "conflict" if conflicts else "ready", ", ".join(conflicts or _migration_notes(target))))
    if not apply or any(item.state != "ready" for item in statuses):
        return statuses
    _apply_root_upgrade(root, root_updates)
    relocated = _apply_layout_moves(root, moves)
    return [
        WikiStatus("workspace", "upgraded", f"{len(root_updates)} root-managed file(s) updated; {len(moves)} wiki(s) moved into {WIKIS_DIRECTORY}/"),
        *[WikiStatus(name, "upgraded", _workspace_upgrade(relocated.get(name, target))) for name, target in selected],
    ]


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
        schema.write_text(text, encoding="utf-8")
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
    if destination_name in RESERVED_WORKSPACE_DIRECTORIES:
        raise typer.BadParameter(f"NAME is reserved by the workspace: {destination_name}")
    destination_name = _canonical_wiki_path(destination_name)
    destination = root / destination_name
    if destination.exists():
        raise typer.BadParameter(f"Destination already exists: {destination}")
    if destination_name in manifest["wikis"] or Path(destination_name).name in manifest["wikis"]:
        raise typer.BadParameter(f"Wiki already registered: {destination_name}")
    shutil.copytree(source, destination, ignore=shutil.ignore_patterns(".git"))
    _workspace_upgrade(destination)
    manifest["wikis"].append(destination_name)
    manifest["wikis"].sort()
    _write_manifest(root, manifest)
    return destination_name


def create_wiki(root: Path, name: str) -> str:
    """Create and register a fresh wiki in the workspace's canonical location."""
    root = root.expanduser().resolve()
    manifest = _read_manifest(root)
    if Path(name).name != name or name in {"", ".", ".."}:
        raise typer.BadParameter("NAME must be a simple wiki directory name.")
    if name in RESERVED_WORKSPACE_DIRECTORIES:
        raise typer.BadParameter(f"NAME is reserved by the workspace: {name}")
    relative = _canonical_wiki_path(name)
    destination = root / relative
    if destination.exists() or destination.is_symlink():
        raise typer.BadParameter(f"Destination already exists: {destination}")
    if relative in manifest["wikis"] or name in manifest["wikis"]:
        raise typer.BadParameter(f"Wiki already registered: {name}")
    _scaffold.copy_template(destination)
    _skills.install(destination)
    _upgrade.record_fresh_install(destination, include_integrations=True)
    _workspace_upgrade(destination)
    manifest["wikis"].append(relative)
    manifest["wikis"].sort()
    _write_manifest(root, manifest)
    return relative
