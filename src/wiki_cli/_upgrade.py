"""Safe, manifest-backed upgrades for generated LLM wiki directories."""

from __future__ import annotations

import hashlib
import json
import stat
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from importlib.resources import files
from pathlib import Path

import typer

from . import _skills

MANIFEST_NAME = ".llm-wiki.json"
SCHEMA_VERSION = 1


def package_version() -> str:
    try:
        return version("llm-wiki-cli")
    except PackageNotFoundError:
        return "0.7.3"


def _digest(content: bytes) -> str:
    return "sha256:" + hashlib.sha256(content).hexdigest()


def _entrypoint(name: str) -> bytes:
    return (files("wiki_cli") / "template" / name).read_bytes()


def _desired_upgrade_files() -> dict[str, tuple[bytes, bool]]:
    desired = _skills.rendered_files()
    desired["AGENTS.md"] = (_entrypoint("AGENTS.md"), False)
    desired["CLAUDE.md"] = (_entrypoint("CLAUDE.md"), False)
    return desired


def _read_manifest(target: Path) -> dict[str, object]:
    path = target / MANIFEST_NAME
    if not path.exists():
        return {"schema_version": SCHEMA_VERSION, "managed_files": {}}
    if path.is_symlink() or not path.is_file():
        raise typer.BadParameter(f"Invalid {path}: expected a regular file")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if value.get("schema_version") != SCHEMA_VERSION:
            raise ValueError("unsupported schema_version")
        managed = value.get("managed_files")
        if not isinstance(managed, dict) or not all(
            isinstance(key, str) and isinstance(item, str)
            for key, item in managed.items()
        ):
            raise ValueError("managed_files must map paths to hashes")
        return value
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise typer.BadParameter(f"Invalid {path}: {exc}") from exc


def _validate_wiki(target: Path) -> None:
    required = (target / "TOPIC.md", target / "wiki" / "index.md")
    if not target.is_dir() or not all(path.is_file() for path in required):
        raise typer.BadParameter(
            f"{target} does not look like an LLM wiki (expected TOPIC.md and wiki/index.md)."
        )
    if not (target / "WIKI.md").is_file() and not (target / "CLAUDE.md").is_file():
        raise typer.BadParameter(f"{target} has neither WIKI.md nor legacy CLAUDE.md.")


def _make_executable(path: Path) -> None:
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _write_manifest(target: Path, managed: dict[str, str]) -> None:
    value = {
        "schema_version": SCHEMA_VERSION,
        "template_version": package_version(),
        "managed_files": dict(sorted(managed.items())),
    }
    (target / MANIFEST_NAME).write_text(
        json.dumps(value, indent=2) + "\n", encoding="utf-8"
    )


def record_fresh_install(target: Path, *, include_integrations: bool) -> None:
    """Create the managed-file manifest for a newly scaffolded wiki."""
    relatives = ["AGENTS.md", "CLAUDE.md"]
    if include_integrations:
        relatives.extend(_skills.rendered_files())
    managed = {
        relative: _digest((target / relative).read_bytes())
        for relative in relatives
        if (target / relative).is_file()
    }
    _write_manifest(target, managed)


@dataclass
class UpgradeResult:
    created: list[str]
    updated: list[str]
    adopted: list[str]
    conflicts: list[str]


def upgrade(target: Path) -> UpgradeResult:
    """Upgrade one wiki, preserving files changed outside CLI management."""
    target = target.expanduser().resolve()
    _validate_wiki(target)
    manifest = _read_manifest(target)  # Validate before performing any writes.
    managed = dict(manifest["managed_files"])
    result = UpgradeResult([], [], [], [])

    wiki_schema = target / "WIKI.md"
    if not wiki_schema.exists():
        wiki_schema.write_bytes((target / "CLAUDE.md").read_bytes())
        result.created.append("WIKI.md")

    for relative, (desired, executable) in _desired_upgrade_files().items():
        destination = target / relative
        if destination.is_symlink() or (
            destination.exists() and not destination.is_file()
        ):
            result.conflicts.append(relative)
            continue

        if destination.is_file():
            current = destination.read_bytes()
            recorded = managed.get(relative)
            if recorded is None:
                if current == desired:
                    managed[relative] = _digest(current)
                    result.adopted.append(relative)
                    if executable:
                        _make_executable(destination)
                elif (
                    relative == "CLAUDE.md"
                    and not wiki_schema.is_symlink()
                    and wiki_schema.is_file()
                    and wiki_schema.read_bytes() == current
                ):
                    # The legacy schema has been preserved byte-for-byte in
                    # WIKI.md, so it is safe to turn CLAUDE.md into an entrypoint.
                    destination.write_bytes(desired)
                    managed[relative] = _digest(desired)
                    result.updated.append(relative)
                else:
                    result.conflicts.append(relative)
                continue
            if _digest(current) != recorded:
                result.conflicts.append(relative)
                continue
            if current != desired:
                destination.write_bytes(desired)
                result.updated.append(relative)
            if executable:
                _make_executable(destination)
            managed[relative] = _digest(desired)
            continue

        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(desired)
        if executable:
            _make_executable(destination)
        managed[relative] = _digest(desired)
        result.created.append(relative)

    _write_manifest(target, managed)
    return result
