"""
codeowners_lookup — identify suggested assignees for a file or component.

Reads a CODEOWNERS-style file from fixtures and matches by component name or
file path prefix.
"""

from pathlib import Path
from typing import Any

definition: dict[str, Any] = {
    "name": "codeowners_lookup",
    "description": (
        "Look up the suggested code owner(s) for a given component name or "
        "file path. Returns a list of GitHub usernames responsible for that "
        "area of the codebase.\n\n"
        "Use this tool when:\n"
        "- You've identified the component affected by a bug and want to "
        "suggest an assignee in the handoff.\n"
        "- You're routing a feature request and need a component owner.\n\n"
        "Do NOT use this tool when:\n"
        "- You cannot identify a specific component — guessing here causes "
        "wrong-assignee escalations, which damage maintainer trust. Return "
        "'no specific owner' instead.\n"
        "- You only need general repository information.\n\n"
        "Output: a list of usernames, or an empty list if no owner is "
        "configured for that path. An empty list is a valid result, not a "
        "tool failure."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "path_or_component": {
                "type": "string",
                "description": (
                    "Either a file path (e.g., 'src/parser/lexer.py') or a "
                    "component name (e.g., 'parser', 'cli'). Component names "
                    "are matched against directory prefixes."
                ),
            },
        },
        "required": ["path_or_component"],
    },
}


def call(path_or_component: str) -> list[str]:
    """Look up owners. Reads fixtures/codeowners.txt."""
    fixture_path = Path(__file__).parent.parent / "fixtures" / "codeowners.txt"
    if not fixture_path.exists():
        return []

    target = path_or_component.lower().strip("/")
    matches: list[str] = []

    with fixture_path.open() as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            pattern = parts[0].lower().lstrip("/").rstrip("/*")
            owners = [p for p in parts[1:] if p.startswith("@")]
            if target.startswith(pattern) or pattern in target:
                matches.extend(o.lstrip("@") for o in owners)

    # Dedupe while preserving order
    seen = set()
    unique = []
    for m in matches:
        if m not in seen:
            seen.add(m)
            unique.append(m)
    return unique
