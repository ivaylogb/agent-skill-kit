# Tool description audit: examples/broken_candidate/tools/

## Summary

Both tools fail the audit overall (0 Pass, 0 Concern, 2 Fail). The most consequential shared weakness is a complete absence of "When NOT to use" guidance on every tool — the model has no signal to distinguish between the two tools and will routinely call the wrong one. Secondary failures on output shape and parameter docs compound the risk: neither tool documents what it returns or covers edge cases in parameter descriptions.

---

## github_issues

**File:** `examples/broken_candidate/tools/github_issues.py:7–20`
**Overall:** Fail

| Dimension | Grade | Note |
|-----------|-------|------|
| What it does | ⚠️ | States the purpose but "Returns the issue data" is too vague to convey what fields are in the response |
| When to use | ❌ | No positive use case enumerated; usage is left entirely to inference |
| When NOT to use | ❌ | Completely absent; no guidance to prefer `github_search` when only a title or keyword is known |
| Output shape | ❌ | "Returns the issue data" names no fields; empty-dict return on missing issue is undocumented |
| Parameter docs | ⚠️ | `issue_number` says only "The issue number." — no range, no behavior on nonexistent numbers |

### Findings

**When NOT to use (line 9) — Fail**
The description contains zero negative guidance. The model has no way to know it should NOT call `github_issues` when it has a keyword or title instead of an issue number — `github_search` is the right tool in that case. It also has no warning against calling this tool in a loop to simulate search. A production-ready description would include:

> "Do NOT use this tool if you only have a keyword or title — use `github_search` instead. Do NOT call this in a loop to browse issues; use `github_search` for discovery."

**Output shape (line 9) — Fail**
"Returns the issue data" tells the model nothing about what fields are present or what happens when the issue doesn't exist. The implementation returns an empty dict `{}` for both a missing issue (`github_issues.py:35`) and a missing fixture file (`github_issues.py:26`) — the model cannot handle or communicate these error states without knowing about them. A good description states:

> "Returns a dict with keys `number`, `title`, `body`, `state`, `labels`, `assignees`, and `created_at`. Returns an empty dict `{}` if the issue number is not found."

**Parameter docs — `issue_number` (line 15–16) — Concern**
"The issue number." conveys only the semantic role. It omits: valid range (positive integers), what happens on an invalid or nonexistent number (empty dict returned, no exception), and the fact that issue numbers — not URLs — are required. A good description:

> "Positive integer identifying the issue (e.g., 42). Passing an issue number that does not exist returns an empty dict rather than raising an error."

---

## github_search

**File:** `examples/broken_candidate/tools/github_search.py:7–19`
**Overall:** Fail

| Dimension | Grade | Note |
|-----------|-------|------|
| What it does | ❌ | One sentence names the action but omits what is searched (title + body), what is returned, and the 10-result cap |
| When to use | ❌ | No positive use case enumerated |
| When NOT to use | ❌ | Completely absent; no guidance to prefer `github_issues` when the issue number is already known |
| Output shape | ❌ | No description of returned fields, result count, or empty-list case |
| Parameter docs | ❌ | `query` says only "Search query." — no guidance on syntax, 3-character minimum, or multi-term behavior |

### Findings

**What it does (line 9) — Fail**
"Searches GitHub issues for a query string." omits critical facts about how the search works: it matches against issue title and body text, terms shorter than 3 characters are silently ignored (`github_search.py:31`), ranking is additive-OR (more matched terms = higher score), and results are capped at 10. A model that doesn't know about the 3-character minimum will pass single-letter tokens and get unexpectedly empty results. A good description:

> "Searches GitHub issues by keyword match against issue title and body text. Returns up to 10 results ranked by term frequency. Terms shorter than 3 characters are ignored."

**When NOT to use (line 9) — Fail**
No negative guidance exists. The model has no signal to avoid calling `github_search` when it already has an issue number — `github_issues` is faster and more precise in that case. It also has no warning that this is keyword-only and should not be used as a substitute for semantic or structured queries. A good description addition:

> "Do NOT use this tool when you already have an issue number — use `github_issues` instead. Do NOT rely on this tool for exact-match lookups; it uses keyword scoring, not exact string matching."

**Output shape (line 9) — Fail**
The description says nothing about what the tool returns. The implementation returns a list of dicts with `number`, `title`, `snippet` (first 200 chars of body), and `_score` fields — and an empty list `[]` when nothing matches (`github_search.py:35`, `github_search.py:45`). The model cannot reason about downstream steps (e.g., extracting `number` to pass to `github_issues`) without knowing what keys exist. A good description:

> "Returns a list of up to 10 dicts, each with keys `number` (int), `title` (str), and `snippet` (first 200 characters of body). Returns an empty list if no issues match. The `_score` field is an internal relevance rank and should be ignored."

**Parameter docs — `query` (line 14–15) — Fail**
"Search query." is the minimum possible documentation. It omits: that terms under 3 characters are dropped (`github_search.py:31`), that multiple terms are scored independently (OR semantics, not AND), and that GitHub search operators like `is:open` or `label:bug` are not supported. A good description:

> "Free-text keyword query matched against issue title and body. Multiple space-separated terms are scored independently — all matching terms increase relevance, but no single term is required. Terms shorter than 3 characters are silently ignored. GitHub search operators (e.g. `is:open`, `label:`) are not supported."

---

## Cross-tool patterns

**Pattern 1 — "When NOT to use" is absent on every tool (github_issues.py:9, github_search.py:9)**
Neither tool references the other as the preferred alternative in its domain. `github_issues` should tell the model to use `github_search` for keyword-based discovery; `github_search` should tell the model to use `github_issues` when an issue number is already in hand. When two tools have overlapping domains, each must explicitly point away from itself in the cases where the other is better. This is the highest-impact gap in both files and the most common production failure mode.

**Pattern 2 — Output shape undocumented on every tool (github_issues.py:9, github_search.py:9)**
Neither description states what the tool returns — not the field names, not the empty/error cases, nothing. This forces the model to guess the output schema, leading to brittle downstream tool chaining (e.g., attempting to access a `comments` field that isn't present, or failing to extract `number` from search results to pass to `github_issues`). A team convention of always documenting return shape in the description would fix this across both tools.

**Pattern 3 — Parameter docs name type only, not behavior (github_issues.py:15, github_search.py:14)**
Both tools have parameter descriptions that state only the semantic role ("The issue number.", "Search query.") but omit valid values, edge cases, and what NOT to pass. This is a shared convention gap: the team appears to treat parameter descriptions as labels rather than prompts. Establishing a template — valid values / edge cases / what NOT to pass — and applying it consistently would resolve this pattern across the entire codebase.
