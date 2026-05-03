"""
github_issues — fetch issue details and existing comments.

This tool follows the repo convention of separating tool *definition* from tool
*implementation*. The definition is a pure dict that audit skills can read
without executing anything. The implementation is the `call` function.

Backed by a local fixture file so demos work without GitHub credentials. In
production, the implementation would call the GitHub API; the definition would
not change.
"""

import json
from pathlib import Path
from typing import Any

# The definition is what the model sees. Audit skills (notably
# tool-description-audit) read this without executing the tool. The
# description is treated as a prompt — clarity matters as much as accuracy.

definition: dict[str, Any] = {
    "name": "github_issues",
    "description": (
        "Fetch full details for a single GitHub issue, including title, body, "
        "labels, author, comments, and metadata.\n\n"
        "Use this tool when:\n"
        "- You need to see the full issue body and existing comments to triage.\n"
        "- You need author metadata (first-time contributor, last activity).\n"
        "- You need to verify an issue exists before referencing it.\n\n"
        "Do NOT use this tool when:\n"
        "- You only need to search across issues — use `github_search` instead.\n"
        "- You need owner/component info — use `codeowners_lookup` instead.\n\n"
        "Output: a structured issue object. If the issue does not exist or is "
        "private, the tool returns `{\"error\": \"not_found\"}`. Surface this "
        "explicitly in your scratchpad — do not pretend the issue exists."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "issue_number": {
                "type": "integer",
                "description": (
                    "The issue number within the repository. Must be a positive "
                    "integer. Do not pass URL strings or '#123' — just the number."
                ),
            },
        },
        "required": ["issue_number"],
    },
}


def call(issue_number: int) -> dict[str, Any]:
    """
    Fetch issue details. Returns structured data or {"error": "not_found"}.

    The fixture path is resolved relative to this file so the tool works from
    any working directory.
    """
    fixture_path = Path(__file__).parent.parent / "fixtures" / "issues.json"
    if not fixture_path.exists():
        return {"error": "fixture_missing", "path": str(fixture_path)}

    with fixture_path.open() as f:
        issues = json.load(f)

    for issue in issues:
        if issue["number"] == issue_number:
            return issue

    return {"error": "not_found", "issue_number": issue_number}
