"""github_issues — fetches issue details."""

import json
from pathlib import Path
from typing import Any

definition: dict[str, Any] = {
    "name": "github_issues",
    "description": "Fetches details about a GitHub issue given its number. Returns the issue data.",
    "input_schema": {
        "type": "object",
        "properties": {
            "issue_number": {
                "type": "integer",
                "description": "The issue number.",
            },
        },
        "required": ["issue_number"],
    },
}


def call(issue_number: int) -> dict[str, Any]:
    fixture_path = Path(__file__).parent.parent / "fixtures" / "issues.json"
    if not fixture_path.exists():
        return {}

    with fixture_path.open() as f:
        issues = json.load(f)

    for issue in issues:
        if issue["number"] == issue_number:
            return issue

    return {}
