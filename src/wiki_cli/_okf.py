"""Previewable migration of an LLM wiki corpus to the OKF v0.2 profile."""

from __future__ import annotations

import re
import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import yaml

# Markdown tables require the label separator in a piped wiki link to be
# escaped (``[[target\|label]]``). Accept that form as well as the ordinary
# ``[[target|label]]`` form, without retaining the escape in the target.
WIKI_LINK = re.compile(r"\[\[([^\]]+?)(?:\\?\|([^\]]+))?\]\]")
ROOT_MARKDOWN_LINK = re.compile(r"(\[[^\]]+\])\((/[^)]+)\)")
FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")


@dataclass
class MigrationPlan:
    changes: dict[Path, str]
    issues: list[str]


def _split_frontmatter(path: Path, text: str) -> tuple[dict[str, object], str]:
    match = FRONTMATTER.match(text)
    if not match:
        raise ValueError(f"{path}: missing YAML frontmatter")
    value = yaml.safe_load(match.group(1))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: frontmatter must be a mapping")
    return value, text[match.end():]


def _dump_frontmatter(value: dict[str, object]) -> str:
    return "---\n" + yaml.safe_dump(value, allow_unicode=True, sort_keys=False).strip() + "\n---\n\n"


def _section(body: str, heading: str, entries: list[str]) -> str:
    """Merge generated bullet links into a terminal level-two section."""
    if not entries:
        return body.rstrip() + "\n"
    pattern = re.compile(rf"(?m)^## {re.escape(heading)}\s*$")
    match = pattern.search(body)
    if match:
        following = re.search(r"(?m)^## ", body[match.end():])
        end = match.end() + following.start() if following else len(body)
        existing = body[match.end():end]
        existing_targets = _section_link_targets(existing)
        additions = [entry for entry in entries if _link_target(entry) not in existing_targets]
        if not additions:
            return body
        inserted = existing.rstrip() + "\n" + "\n".join(f"- {entry}" for entry in additions) + "\n\n"
        return body[:match.end()] + inserted + body[end:].lstrip("\n")
    return body.rstrip() + f"\n\n## {heading}\n\n" + "\n".join(f"- {entry}" for entry in entries) + "\n"


def _link_target(link: str) -> str:
    parsed = _markdown_link(link)
    return parsed[1] if parsed else link


def _markdown_link(value: str) -> tuple[str, str] | None:
    """Parse a complete Markdown link, including balanced URL parentheses."""
    if not value.startswith("[") or not value.endswith(")"):
        return None
    separator = value.find("](")
    if separator < 1:
        return None
    title = value[1:separator]
    destination = value[separator + 2:-1]
    if not destination:
        return None
    depth = 0
    escaped = False
    for character in destination:
        if escaped:
            escaped = False
        elif character == "\\":
            escaped = True
        elif character == "(":
            depth += 1
        elif character == ")":
            if depth == 0:
                return None
            depth -= 1
    if depth or escaped:
        return None
    destination = re.sub(r"\\([()\\])", r"\1", destination)
    return title, destination


def _section_link_targets(value: str) -> set[str]:
    targets: set[str] = set()
    for line in value.splitlines():
        candidate = line.strip()
        if candidate.startswith("- "):
            candidate = candidate[2:].strip()
        parsed = _markdown_link(candidate)
        if parsed:
            targets.add(parsed[1])
    return targets


def _replace_inline_code(line: str, transform: Callable[[str], str]) -> str:
    """Apply a text transformation outside Markdown inline-code spans."""
    parts: list[str] = []
    plain_start = cursor = 0
    while cursor < len(line):
        if line[cursor] != "`":
            cursor += 1
            continue
        run_end = cursor + 1
        while run_end < len(line) and line[run_end] == "`":
            run_end += 1
        marker = line[cursor:run_end]
        closing = line.find(marker, run_end)
        if closing < 0:
            cursor = run_end
            continue
        parts.append(transform(line[plain_start:cursor]))
        parts.append(line[cursor:closing + len(marker)])
        cursor = closing + len(marker)
        plain_start = cursor
    parts.append(transform(line[plain_start:]))
    return "".join(parts)


def _replace_outside_code(text: str, transform: Callable[[str], str]) -> str:
    """Apply a text transformation outside fenced and inline Markdown code."""
    rendered: list[str] = []
    fence_character: str | None = None
    fence_length = 0
    for line in text.splitlines(keepends=True):
        match = FENCE.match(line)
        if fence_character is not None:
            rendered.append(line)
            if (
                match
                and match.group(1)[0] == fence_character
                and len(match.group(1)) >= fence_length
                and not line[match.end():].strip()
            ):
                fence_character = None
                fence_length = 0
            continue
        if match:
            marker = match.group(1)
            fence_character = marker[0]
            fence_length = len(marker)
            rendered.append(line)
            continue
        rendered.append(_replace_inline_code(line, transform))
    return "".join(rendered)


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        key = _link_target(item)
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def _type(value: object) -> object:
    return {"concept": "Concept", "source-summary": "Reference"}.get(value, value)


def build_plan(wiki_root: Path) -> MigrationPlan:
    """Return all corpus transformations and blockers without writing anything."""
    markdown = sorted(wiki_root.rglob("*.md"))
    concept_paths = [path for path in markdown if path.name not in {"index.md", "log.md"}]
    issues: list[str] = []
    slugs: dict[str, Path] = {}
    for path in concept_paths:
        if path.stem in slugs:
            issues.append(f"ambiguous wiki link target '{path.stem}': {slugs[path.stem]} and {path}")
        else:
            slugs[path.stem] = path

    raw_root = wiki_root.parent / "raw"
    raw_paths = list(raw_root.rglob("*")) if raw_root.is_dir() else []
    raw_files = [path for path in raw_paths if path.is_file()]

    def internal_link(target: str, label: str | None, owner: Path) -> str:
        if target in slugs:
            path = slugs[target]
            href = Path(os.path.relpath(path, owner.parent)).as_posix()
            return f"[{label or target}]({href})"
        reserved = {"index": wiki_root / "index.md", "log": wiki_root / "log.md"}
        if target in reserved and reserved[target].is_file():
            href = Path(os.path.relpath(reserved[target], owner.parent)).as_posix()
            return f"[{label or target}]({href})"
        if target in {"TOPIC", "TOPIC.md"} and (wiki_root.parent / "TOPIC.md").is_file():
            href = Path(os.path.relpath(wiki_root.parent / "TOPIC.md", owner.parent)).as_posix()
            return f"[{label or target}]({href})"
        if "." in target:
            candidates = [path for path in raw_files if path.name == target or path.relative_to(raw_root).as_posix() == target]
            if len(candidates) == 1:
                href = Path(os.path.relpath(candidates[0], owner.parent)).as_posix()
                return f"[{label or target}]({href})"
            if len(candidates) > 1:
                issues.append(f"{owner}: ambiguous raw source '{target}'")
            else:
                issues.append(f"{owner}: unresolved raw source '{target}'")
        else:
            issues.append(f"{owner}: unresolved wiki link '{target}'")
        return f"[{label or target}](/{target}.md)"

    def replace_links(text: str, owner: Path) -> str:
        def convert_wiki_links(value: str) -> str:
            return WIKI_LINK.sub(lambda match: internal_link(match.group(1), match.group(2), owner), value)

        def relative_root_link(match: re.Match[str]) -> str:
            destination = match.group(2)
            path_part, separator, fragment = destination.partition("#")
            candidate = wiki_root / path_part.lstrip("/")
            if not candidate.is_file() and path_part.startswith("/raw/"):
                candidate = wiki_root.parent / path_part.lstrip("/")
            if not candidate.is_file() and path_part == "/TOPIC.md":
                candidate = wiki_root.parent / "TOPIC.md"
            if not candidate.is_file():
                return match.group(0)
            href = Path(os.path.relpath(candidate, owner.parent)).as_posix()
            return f"{match.group(1)}({href}{separator}{fragment})"

        return _replace_outside_code(
            text,
            lambda value: ROOT_MARKDOWN_LINK.sub(relative_root_link, convert_wiki_links(value)),
        )

    changes: dict[Path, str] = {}
    for path in markdown:
        text = path.read_text(encoding="utf-8")
        if path.name == "index.md":
            rendered = replace_links(text, path)
            if path == wiki_root / "index.md" and not FRONTMATTER.match(rendered):
                rendered = '---\nokf_version: "0.2"\n---\n\n' + rendered
            if rendered != text:
                changes[path] = rendered
            continue
        if path.name == "log.md":
            rendered = replace_links(text, path)
            if rendered != text:
                changes[path] = rendered
            continue

        try:
            frontmatter, body = _split_frontmatter(path, text)
        except (UnicodeError, yaml.YAMLError, ValueError) as exc:
            issues.append(str(exc))
            continue
        if not isinstance(frontmatter.get("type"), str) or not frontmatter["type"].strip():
            issues.append(f"{path}: missing non-empty type")
            continue

        citations: list[str] = []
        related: list[str] = []
        sources = frontmatter.pop("sources", None)
        legacy_related = frontmatter.pop("related", None)
        structured: list[dict[str, str]] = []
        if sources is not None:
            if not isinstance(sources, list):
                issues.append(f"{path}: legacy sources must be a list")
                continue
            for source in sources:
                if isinstance(source, dict):
                    if isinstance(source.get("resource"), str):
                        normalized = {key: value for key, value in source.items() if key in {"resource", "title"} and isinstance(value, str)}
                        structured.append(normalized)
                        resource = normalized["resource"]
                        if resource.startswith(("https://", "http://")):
                            citations.append(f"[{normalized.get('title', resource)}]({resource})")
                    else:
                        issues.append(f"{path}: structured source lacks resource")
                    continue
                if not isinstance(source, str):
                    issues.append(f"{path}: unsupported source entry")
                    continue
                external = _markdown_link(source)
                if external and external[1].startswith(("https://", "http://")):
                    title, resource = external
                    structured.append({"resource": resource, "title": title})
                    citations.append(f"[{title}]({resource})")
                else:
                    wiki = WIKI_LINK.fullmatch(source)
                    if wiki:
                        target, label = wiki.groups()
                        if target == "TOPIC.md":
                            continue
                        link = internal_link(target, label, path)
                        if target in slugs:
                            related.append(link)
                        else:
                            citations.append(link)
                    else:
                        issues.append(f"{path}: unsupported source '{source}'")
        if legacy_related is not None:
            if not isinstance(legacy_related, list):
                issues.append(f"{path}: legacy related must be a list")
                continue
            for item in legacy_related:
                if not isinstance(item, str) or not (wiki := WIKI_LINK.fullmatch(item)):
                    issues.append(f"{path}: unsupported related entry '{item}'")
                    continue
                target, label = wiki.groups()
                if target == "TOPIC.md":
                    continue
                related.append(internal_link(target, label, path))

        existing_sources = frontmatter.get("sources")
        if structured:
            existing = existing_sources if isinstance(existing_sources, list) else []
            seen_resources = {item.get("resource") for item in existing if isinstance(item, dict)}
            frontmatter["sources"] = existing + [item for item in structured if item["resource"] not in seen_resources]
        frontmatter["type"] = _type(frontmatter["type"])
        rendered = _dump_frontmatter(frontmatter) + replace_links(body, path)
        rendered = _section(rendered, "Citations", _dedupe(citations))
        rendered = _section(rendered, "Related Concepts", _dedupe(related))
        if rendered != text:
            changes[path] = rendered
    return MigrationPlan(changes, issues)
