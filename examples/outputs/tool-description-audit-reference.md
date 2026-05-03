# Tool description audit: reference_agent/tools/

> Output of running `tool-description-audit` against the reference agent's tools directory. Captured 2026-05-03.

## Summary

**3 tools audited. 3 Pass / 0 Concern / 0 Fail.** All three tools pass every dimension. This is the convention the broken candidate's tools fail to meet — see `tool-description-audit-broken.md` for the contrast.

## github_issues

**File:** `reference_agent/tools/github_issues.py:18-44`
**Overall:** Pass

| Dimension | Grade | Note |
|-----------|-------|------|
| What it does | ✅ | First sentence states purpose specifically: "Fetch full details for a single GitHub issue, including title, body, labels, author, comments, and metadata." |
| When to use | ✅ | Three explicit positive cases listed under "Use this tool when:". |
| When NOT to use | ✅ | Two explicit negative cases listed under "Do NOT use this tool when:" — directs to `github_search` and `codeowners_lookup` for those cases. |
| Output shape | ✅ | Documents both success and error cases. The not-found case is named explicitly ("returns `{\"error\": \"not_found\"}`") with guidance on how to surface it. |
| Parameter docs | ✅ | `issue_number` description includes type, valid values, and what NOT to pass: "Must be a positive integer. Do not pass URL strings or '#123' — just the number." |

No findings.

## github_search

**File:** `reference_agent/tools/github_search.py:13-41`
**Overall:** Pass

| Dimension | Grade | Note |
|-----------|-------|------|
| What it does | ✅ | "Search for GitHub issues matching a free-text query within the current repository. Returns up to 10 issues ranked by relevance, including title, number, state (open/closed), and a short snippet." — specific, action-oriented, names the output shape inline. |
| When to use | ✅ | Three positive cases including the non-obvious "Looking up whether a previously-fixed bug has regressed (search for the bug, then check the state of any matching closed issues)." |
| When NOT to use | ✅ | Two explicit negative cases. |
| Output shape | ✅ | Empty results are explicitly named as a *valid* result, not a failure: "An empty list is a valid result and means no matches were found — it does not mean the search failed." This is the failure mode the broken candidate's tool fails to document. |
| Parameter docs | ✅ | Both `query` and `state` have descriptions covering valid values, edge cases ("Avoid quotes and operators — they often hurt recall on issue search"), and use guidance ("Use 'all' when checking for regressions; 'open' when checking for active duplicates."). |

No findings.

## codeowners_lookup

**File:** `reference_agent/tools/codeowners_lookup.py:8-37`
**Overall:** Pass

| Dimension | Grade | Note |
|-----------|-------|------|
| What it does | ✅ | "Look up the suggested code owner(s) for a given component name or file path. Returns a list of GitHub usernames responsible for that area of the codebase." |
| When to use | ✅ | Two positive cases covering bug-handling and feature-routing scenarios. |
| When NOT to use | ✅ | Two negative cases including the consequential one: "You cannot identify a specific component — guessing here causes wrong-assignee escalations, which damage maintainer trust. Return 'no specific owner' instead." This actively *prevents* the model from guessing. |
| Output shape | ✅ | Empty list explicitly named as a valid result: "An empty list is a valid result, not a tool failure." |
| Parameter docs | ✅ | `path_or_component` description covers both formats with examples. |

No findings.

## Cross-tool patterns

The three tools share a common template: purpose / when to use / when NOT to use / output shape, with parameter docs that go beyond type restatement. This is the convention the broken candidate fails to follow. The audit's clean pass on all three is what production-ready tool design looks like.
