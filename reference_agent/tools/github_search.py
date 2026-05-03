"""
github_search — search for issues matching a query.

Backed by a simple substring/keyword search over the local fixture for demos.
In production this would proxy to the GitHub search API.
"""

import json
from pathlib import Path
from typing import Any

definition: dict[str, Any] = {
    "name": "github_search",
    "description": (
        "Search for GitHub issues matching a free-text query within the current "
        "repository. Returns up to 10 issues ranked by relevance, including "
        "title, number, state (open/closed), and a short snippet.\n\n"
        "Use this tool when:\n"
        "- Checking whether a new issue is a duplicate.\n"
        "- Finding related issues for context.\n"
        "- Looking up whether a previously-fixed bug has regressed (search for "
        "the bug, then check the state of any matching closed issues).\n\n"
        "Do NOT use this tool when:\n"
        "- You already know the issue number — use `github_issues` instead.\n"
        "- You're looking for code (this searches issues only).\n\n"
        "Output: a list of search hits. An empty list is a valid result and "
        "means no matches were found — it does not mean the search failed."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": (
                    "Free-text search query. Use 3-7 keywords. Avoid quotes "
                    "and operators — they often hurt recall on issue search."
                ),
            },
            "state": {
                "type": "string",
                "enum": ["open", "closed", "all"],
                "description": (
                    "Filter by issue state. Use 'all' when checking for "
                    "regressions; 'open' when checking for active duplicates."
                ),
                "default": "all",
            },
        },
        "required": ["query"],
    },
}


def call(query: str, state: str = "all") -> list[dict[str, Any]]:
    """Search the fixture for matching issues. Simple substring match for demo."""
    fixture_path = Path(__file__).parent.parent / "fixtures" / "issues.json"
    if not fixture_path.exists():
        return []

    with fixture_path.open() as f:
        issues = json.load(f)

    query_terms = [t.lower() for t in query.split() if len(t) > 2]
    results = []

    for issue in issues:
        if state != "all" and issue.get("state") != state:
            continue
        haystack = (issue["title"] + " " + issue["body"]).lower()
        score = sum(1 for term in query_terms if term in haystack)
        if score > 0:
            results.append({
                "number": issue["number"],
                "title": issue["title"],
                "state": issue.get("state", "open"),
                "snippet": issue["body"][:200],
                "_score": score,
            })

    results.sort(key=lambda r: r["_score"], reverse=True)
    # Strip the internal sort key — the model doesn't need it and it adds noise.
    for r in results:
        r.pop("_score", None)
    return results[:10]
