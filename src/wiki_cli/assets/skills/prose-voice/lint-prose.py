#!/usr/bin/env python3
# Advisory prose linter for client-facing deliverables.
# Detects 8 mechanical LLM-speak tells from the prose-voice skill's voice guide.
# Always exits 0 — it is never a blocking hook. Run on demand or from the skill.
#
# Usage:
#   python3 lint-prose.py                        # scans analysis/ in cwd
#   python3 lint-prose.py file.md
#   python3 lint-prose.py file1.md file2.md
#   python3 lint-prose.py --dir deliverables/
#
# Checks (heuristic; false positives are acceptable because nothing blocks):
#   dash          — em/en dash connectors (U+2014, U+2013)
#   bold-density  — >2 bold spans on one line
#   bold-phrase   — bold span > ~4 words
#   comma-list    — >=4 commas on a line (list crammed into prose)
#   semicolons    — >=2 semicolons on a line
#   not-x-but-y   — staged contrast tics such as "not X; it is Y" or "is X, not Y"
#   times-symbol  — × (U+00D7) instead of plain x multiplier
#   ask-noun      — "ask" used as a noun (the ask, a reasonable ask, etc.)
#   colon-lead    — colon used after a setup clause instead of direct syntax
#   heading-*     — Title Case, <=6 words, no comma flourish, no trailing period
#
# YAML frontmatter and fenced code blocks are skipped. The frontmatter title:
# field gets the heading-style check; all other frontmatter is ignored.

import argparse
import pathlib
import re
import sys
from itertools import groupby

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError, OSError):
    pass

EM_DASH = "—"
EN_DASH = "–"
TIMES   = "×"

HEADING_STOPWORDS = {
    "a", "an", "the", "and", "but", "or", "nor", "for", "of", "to", "in",
    "on", "at", "by", "vs", "with", "as", "is", "per", "via",
}

HINTS = {
    "dash":             "em/en dash as connector -> use commas, periods, or parentheses",
    "bold-density":     "too many bold spans on one line -> bold only key terms",
    "bold-phrase":      "bold span longer than a term -> bold the key word, not the phrase",
    "comma-list":       "4+ commas -> likely a list crammed into prose; use a real bulleted list",
    "semicolons":       "2+ semicolons -> split into separate sentences",
    "not-x-but-y":      "staged contrast tic -> state the point plainly",
    "times-symbol":     f"math {TIMES} symbol -> write 2x, 3x, 4x with a plain letter x",
    "heading-flourish": "comma/subtitle flourish in heading -> keep it short and plain",
    "heading-case":     "heading not in Title Case (or ends with period) -> use short Title Case",
    "heading-long":     "heading longer than 6 words -> shorten it",
    "ask-noun":         '"ask" used as a noun -> replace with request, requirement, or expectation',
    "colon-lead":       "colon-led setup phrase -> fold the relationship into a direct sentence",
}


def clear_heading(s):
    """Strip markup so heading style checks see only words."""
    s = re.sub(r"\[\[[^\]]*\]\]", "", s)            # [[wiki links]]
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)  # [text](url) -> text
    s = re.sub(r"`[^`]*`", "", s)                    # `inline code`
    s = re.sub(r"\([^)]*\)", "", s)                  # (parentheticals)
    s = s.replace("**", "").replace("*", "").replace("_", "")
    return s.strip()


def check_heading(cleaned):
    issues = []
    if not cleaned.strip():
        return issues
    if "," in cleaned:
        issues.append("heading-flourish")
    if cleaned.endswith("."):
        if "heading-case" not in issues:
            issues.append("heading-case")
    words = cleaned.split()
    if len(words) > 6:
        issues.append("heading-long")
    for i, w in enumerate(words):
        if not re.match(r"^[A-Za-z]", w):
            continue
        if w[0].islower():
            is_stop = w.lower() in HEADING_STOPWORDS
            is_interior = 0 < i < len(words) - 1
            if not (is_stop and is_interior):
                if "heading-case" not in issues:
                    issues.append("heading-case")
    return issues


def colon_lead(line):
    """Catch common colon-as-hinge constructions without flagging syntax labels."""
    if ":" not in line:
        return False

    stripped = line.strip()
    if stripped.startswith("#") or stripped.startswith("|"):
        return False

    colon_at = line.find(":")
    if colon_at == -1:
        return False
    if line[colon_at:colon_at + 3] == "://":
        return False
    if colon_at > 0 and colon_at + 1 < len(line):
        if line[colon_at - 1].isdigit() and line[colon_at + 1].isdigit():
            return False

    prefix = line[:colon_at].strip()
    suffix = line[colon_at + 1:].strip()
    if not prefix or not suffix:
        return False

    prefix = re.sub(r"^\s*(?:[-*+]|\d+\.)\s+", "", prefix)
    if re.match(r"^\*\*[^*]+:\*\*$", prefix + ":"):
        return False

    words = re.findall(r"[A-Za-z0-9']+", prefix)
    if len(words) < 2 or len(words) > 12 or len(prefix) > 90:
        return False

    count_words = "one|two|three|four|five|six|seven|eight|nine|ten|\\d+"
    if re.search(
        rf"(?i)^({count_words})\s+\w+.*\b(is|are|remain|remains|were|was|still)\b",
        prefix,
    ):
        return True

    thesis_nouns = "finding|findings|point|lesson|takeaway|conclusion|claim|argument"
    if re.search(rf"(?i)(?:'s|s')\s+(?:central\s+)?(?:{thesis_nouns})$", prefix):
        return True

    hinge_verbs = (
        "inverts?|means|shows|reveals|creates|turns|makes|becomes|signals|"
        "reflects|drives|anchors|frames"
    )
    if re.search(rf"(?i)\b({hinge_verbs})\b", prefix):
        return True

    return False


def contrast_tic(line):
    """Catch staged contrast patterns that should be rewritten directly."""
    if re.search(r"(?i)\bnot\b[^;.]*;\s*it\s+is\b", line):
        return True
    if re.search(r"(?i)\bit\s+is\s+not\b[^.]*\bit\s+is\b", line):
        return True
    if re.search(
        r"(?i)\b(?:it|this|that|[A-Z][A-Za-z0-9'/-]*(?:\s+[A-Z][A-Za-z0-9'/-]*){0,5})"
        r"\s+(?:is|are|was|were)\s+[^,.;!?]{1,80},\s+not\s+[^.;!?]{1,80}",
        line,
    ):
        return True
    return False


def lint_file(path):
    text = path.read_text(encoding="utf-8")
    raw_lines = text.splitlines()
    findings = []  # (lineno, check, count, text)

    # Frontmatter title: heading-style check only
    if raw_lines and raw_lines[0].strip() == "---":
        for fi, fl in enumerate(raw_lines[1:], start=1):
            if fl.strip() == "---":
                break
            m = re.match(r"^\s*title:\s*(.+?)\s*$", fl)
            if m:
                tv = m.group(1).strip().strip('"').strip("'")
                for iss in check_heading(clear_heading(tv)):
                    findings.append((fi + 1, iss, 1, f"title: {tv}"))

    in_frontmatter = False
    frontmatter_done = False
    in_code_fence = False

    for i, line in enumerate(raw_lines):
        lineno = i + 1
        trimmed = line.strip()

        # --- frontmatter skip ---
        if not frontmatter_done:
            if lineno == 1 and trimmed == "---":
                in_frontmatter = True
                continue
            if in_frontmatter:
                if trimmed == "---":
                    in_frontmatter = False
                    frontmatter_done = True
                continue
            if trimmed:
                frontmatter_done = True

        # --- fenced code block skip ---
        if re.match(r"^(```|~~~)", trimmed):
            in_code_fence = not in_code_fence
            continue
        if in_code_fence:
            continue

        if not trimmed:
            continue

        sample = trimmed[:110] + "..." if len(trimmed) > 110 else trimmed

        # dash
        hits = len(re.findall(f"[{EM_DASH}{EN_DASH}]", line))
        if hits:
            findings.append((lineno, "dash", hits, sample))

        # bold checks
        bold_spans = re.findall(r"\*\*([^*]+)\*\*", line)
        if len(bold_spans) > 2:
            findings.append((lineno, "bold-density", len(bold_spans), sample))
        for span in bold_spans:
            wc = len(span.strip().split())
            if wc > 4:
                display = span.strip()[:70] + ("..." if len(span.strip()) > 70 else "")
                findings.append((lineno, "bold-phrase", wc, f"**{display}**"))

        # comma-list
        cc = line.count(",")
        if cc >= 4:
            findings.append((lineno, "comma-list", cc, sample))

        # semicolons + staged contrast tics
        sc = line.count(";")
        if sc >= 2:
            findings.append((lineno, "semicolons", sc, sample))
        if contrast_tic(line):
            findings.append((lineno, "not-x-but-y", 1, sample))

        # times symbol
        tc = line.count(TIMES)
        if tc:
            findings.append((lineno, "times-symbol", tc, sample))

        # heading style
        m = re.match(r"^#{1,6}\s+(.*)$", trimmed)
        if m:
            for iss in check_heading(clear_heading(m.group(1))):
                findings.append((lineno, iss, 1, trimmed))

        # ask-noun
        if re.search(
            r"(?i)\b(the|an?|our|your|this|that|one|core|reasonable|key|big|main|simple|only|real)\s+ask\b",
            line,
        ) or re.search(r"(?i)\bask\b[.,;!?]", line):
            findings.append((lineno, "ask-noun", 1, sample))

        # colon-led setup phrase
        if colon_lead(line):
            findings.append((lineno, "colon-lead", 1, sample))

    return findings


def main():
    parser = argparse.ArgumentParser(
        description="Advisory prose linter for consultant-voice deliverables."
    )
    parser.add_argument("paths", nargs="*", help="Files or directories to lint")
    parser.add_argument(
        "--dir",
        default=None,
        help="Directory to scan when no positional paths given (default: analysis/ in cwd)",
    )
    args = parser.parse_args()

    targets = []
    if args.paths:
        for p in args.paths:
            pp = pathlib.Path(p)
            if pp.is_dir():
                targets.extend(sorted(pp.glob("*.md")))
            elif pp.is_file():
                targets.append(pp)
            else:
                print(f"skip (not found): {p}")
    else:
        scan_dir = pathlib.Path(args.dir) if args.dir else pathlib.Path("analysis")
        if scan_dir.is_dir():
            targets = sorted(scan_dir.glob("*.md"))
        else:
            print(
                f"No target directory found ({scan_dir}). "
                "Pass a file/directory as an argument or use --dir."
            )
            sys.exit(0)

    if not targets:
        print("No .md files to lint.")
        sys.exit(0)

    grand_total = 0
    for fpath in targets:
        findings = lint_file(fpath)
        if not findings:
            continue

        try:
            rel = fpath.relative_to(pathlib.Path.cwd())
        except ValueError:
            rel = fpath

        print(f"\n=== {rel} ({len(findings)} finding(s)) ===")

        findings.sort(key=lambda x: (x[1], x[0]))
        for check, grp in groupby(findings, key=lambda x: x[1]):
            hint = HINTS.get(check, "")
            print(f"  [{check}] {hint}")
            for lineno, _, count, text in grp:
                print(f"    L{lineno} (x{count}): {text}")

        grand_total += len(findings)

    print(f"\nTotal findings: {grand_total} (advisory; nothing was blocked)")
    sys.exit(0)


if __name__ == "__main__":
    main()
