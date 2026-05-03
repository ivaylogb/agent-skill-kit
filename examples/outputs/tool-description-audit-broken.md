# Tool description audit: examples/broken_candidate/tools/

> Output of running `tool-description-audit` against the broken candidate's tools directory. Captured 2026-05-03.

## Summary

**2 tools audited. 0 Pass / 0 Concern / 2 Fail.** Both tools fail on the most consequential dimension — "When NOT to use" — and both have parameter descriptions that state only the type, with no guidance on edge cases. The shared failure across both tools indicates a convention gap, not isolated quality issues.

## github_issues

**File:** `examples/broken_candidate/tools/github_issues.py:7-19`
**Overall:** Fail

| Dimension | Grade | Note |
|-----------|-------|------|
| What it does | ✅ | "Fetches details about a GitHub issue given its number" — clear and action-oriented. |
| When to use | ❌ | Absent. No positive use cases described. |
| When NOT to use | ❌ | Absent. Critical gap. |
| Output shape | ⚠️ | "Returns the issue data" — names the success case, omits error and not-found cases. |
| Parameter docs | ❌ | `issue_number`'s description is "The issue number." — no guidance on valid values, no warning against passing URLs or "#123" strings. |

### Findings

**When NOT to use (Fail).** The description does not tell the model when to prefer another tool. The agent has both `github_issues` and `github_search` available; without explicit "Do NOT use this tool when you only need to search across issues — use `github_search` instead," the model has no signal for tool selection beyond intuition. Concrete fix: add a "Do NOT use this tool when:" section enumerating cases where `github_search` is the right choice, where `codeowners_lookup` is the right choice, and where the agent should ask the user for the issue number rather than guess.

**Output shape (Concern).** The description doesn't describe the not-found case. The implementation returns `{}` on missing issues (line 27), which the model then has to reason about with no documentation. Concrete fix: state explicitly "If the issue does not exist or is private, the tool returns an empty dict. Surface this explicitly — do not pretend the issue exists." (Note: an empty dict is also a weaker error signal than the reference's `{"error": "not_found", "issue_number": N}`.)

**Parameter docs (Fail).** `issue_number` description is 4 words. Concrete fix: "The issue number within the repository. Must be a positive integer. Do not pass URL strings or '#123' — just the number." This is approximately what the reference provides.

## github_search

**File:** `examples/broken_candidate/tools/github_search.py:7-19`
**Overall:** Fail

| Dimension | Grade | Note |
|-----------|-------|------|
| What it does | ⚠️ | "Searches GitHub issues for a query string." — clear but generic. |
| When to use | ❌ | Absent. |
| When NOT to use | ❌ | Absent. |
| Output shape | ❌ | No description of return value. The model has no idea whether empty results are a failure or a valid "no matches" result. |
| Parameter docs | ❌ | `query` description is "Search query." — no guidance on length, operators, quoting, or recall expectations. |

### Findings

**When NOT to use (Fail).** Same gap as `github_issues`. The model needs to know: do not call this tool when the issue number is already known (`github_issues` is direct). Do not call this tool when looking for code (this searches issues only). Do not call this tool with quoted queries or operators (often hurts recall).

**Output shape (Fail).** The implementation returns a list of search hits. An empty list is a valid result meaning "no matches found" — but the description never says so. The model is likely to treat empty results as a tool failure and either retry with a different query (wasting tokens) or escalate. Concrete fix: "Output: a list of search hits. An empty list is a valid result and means no matches were found — it does not mean the search failed."

**Parameter docs (Fail).** `query` description is 2 words. The implementation does substring matching with a 3+ character minimum, which is non-obvious from outside. Concrete fix: "Free-text search query. Use 3-7 keywords. Avoid quotes and operators — they often hurt recall on issue search."

**Filter parameter missing.** The reference's `github_search` accepts a `state` parameter (open / closed / all) that the candidate's version omits. Not strictly a description issue, but worth flagging.

## Cross-tool patterns

Both tools fail "When NOT to use" and "Parameter docs." This is a convention gap, not isolated quality issues. The team that built this candidate likely treats tool descriptions like Python docstrings (concise, for human readers) rather than as prompts (detailed, for the model). The single highest-leverage fix would be to adopt a tool-description template that requires every tool to include four sections: purpose, when to use, when NOT to use, output shape — and a parameter-description rule that requires more than a type restatement.

The reference agent's tools (`reference_agent/tools/`) follow this template. Diffing the two `github_issues.py` files side-by-side is the fastest way to internalize the difference.
