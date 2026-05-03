"""github_search — search GitHub issues."""

import json
from pathlib import Path
from typing import Any

definition: dict[str, Any] = {
    "name": "github_search",
    "description": "Searches GitHub issues for a query string.",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query.",
            },
        },
        "required": ["query"],
    },
}


def call(query: str) -> list[dict[str, Any]]:
    fixture_path = Path(__file__).parent.parent / "fixtures" / "issues.json"
    if not fixture_path.exists():
        return []

    with fixture_path.open() as f:
        issues = json.load(f)

    query_terms = [t.lower() for t in query.split() if len(t) > 2]
    results = []
    for issue in issues:
        haystack = (issue["title"] + " " + issue["body"]).lower()
        score = sum(1 for term in query_terms if term in haystack)
        if score > 0:
            results.append({
                "number": issue["number"],
                "title": issue["title"],
                "snippet": issue["body"][:200],
                "_score": score,  # Leaking internal field — same anti-pattern
            })

    results.sort(key=lambda r: r["_score"], reverse=True)
    return results[:10]
