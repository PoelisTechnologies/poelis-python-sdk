#!/usr/bin/env python3
"""
Regenerate CLAUDE.md from .cursor/rules/*.mdc files.

Usage:
  python3 scripts/sync_claude_rules.py              # always regenerate
  python3 scripts/sync_claude_rules.py --check-stdin # only if stdin says an .mdc was touched
"""

import json
import sys
from pathlib import Path


def parse_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    end = text.find("---", 3)
    if end == -1:
        return {}, text
    fm_text = text[3:end].strip()
    body = text[end + 3 :].strip()
    fm: dict = {}
    for line in fm_text.splitlines():
        if ":" in line:
            key, _, raw = line.partition(":")
            key = key.strip()
            raw = raw.strip()
            if raw.lower() == "true":
                fm[key] = True
            elif raw.lower() == "false":
                fm[key] = False
            else:
                fm[key] = raw
    return fm, body


def generate(repo_root: Path) -> str:
    rules_dir = repo_root / ".cursor" / "rules"
    if not rules_dir.exists():
        return ""

    always: list[dict] = []
    conditional: list[dict] = []

    for path in sorted(rules_dir.glob("*.mdc")):
        text = path.read_text(encoding="utf-8")
        fm, body = parse_frontmatter(text)
        entry = {"name": path.stem, "fm": fm, "body": body}
        if fm.get("alwaysApply") is True:
            always.append(entry)
        else:
            conditional.append(entry)

    lines = [
        "<!-- AUTO-GENERATED — do not edit manually. Source: .cursor/rules/*.mdc -->",
        "<!-- Regenerate: python3 scripts/sync_claude_rules.py -->",
        "",
        "# Claude Code Rules",
        "",
        "> Auto-generated from `.cursor/rules/`. Edit the `.mdc` source files — **not this file**.",
        "",
    ]

    def render(entries: list[dict]) -> None:
        for e in entries:
            title = e["name"].replace("-", " ").title()
            lines.append(f"### {title}")
            lines.append("")
            desc = e["fm"].get("description", "")
            if desc:
                lines.append(f"_{desc}_")
                lines.append("")
            globs = e["fm"].get("globs", "")
            if globs:
                lines.append(f"**Applies when editing:** `{globs}`")
                lines.append("")
            lines.append(e["body"])
            lines.append("")

    if always:
        lines.append("## Always-Apply Rules")
        lines.append("")
        lines.append("These rules apply to **every** task in this project.")
        lines.append("")
        render(always)

    if conditional:
        lines.append("## Conditional Rules")
        lines.append("")
        lines.append(
            "Apply these rules when the task touches files matching the listed globs."
        )
        lines.append("")
        render(conditional)

    return "\n".join(lines)


def main() -> None:
    check_stdin = "--check-stdin" in sys.argv

    repo_root = Path(__file__).resolve().parent.parent

    if check_stdin:
        try:
            data = json.loads(sys.stdin.read() or "{}")
            file_path = data.get("tool_input", {}).get("file_path", "")
            if ".cursor/rules/" not in file_path or not file_path.endswith(".mdc"):
                sys.exit(0)
        except (json.JSONDecodeError, KeyError):
            sys.exit(0)

    content = generate(repo_root)
    if not content:
        print("No .cursor/rules/*.mdc files found.", file=sys.stderr)
        sys.exit(1)

    out = repo_root / "CLAUDE.md"
    out.write_text(content, encoding="utf-8")
    print(f"CLAUDE.md regenerated ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
