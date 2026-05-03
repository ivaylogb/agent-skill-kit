# tool-description-audit

Audit one or more tool definitions for production-readiness. The audit grades each tool's `description`, `input_schema`, and parameter docs against the principle: **tool descriptions are prompts**. The model uses them to decide which tool to call, when to call it, and when not to.

## When to invoke

- A new tool is added to an agent.
- An existing tool's description is modified (often during a model upgrade — descriptions that worked on Sonnet 3.5 may regress on Sonnet 4.5).
- Before opening a PR that adds tools, as a self-check.
- Periodically across all of an agent's tools, to catch drift.

This skill works on any agent. It does not require a reference agent.

## Goal

For each tool examined, produce a structured grade across five dimensions:

1. **What it does** — does the description state the tool's purpose clearly?
2. **When to use** — does the description give positive examples of when to call it?
3. **When NOT to use** — does the description explicitly describe cases where another tool is better, or where the tool should not be called at all?
4. **Output shape** — does the description describe what the tool returns, including error/empty cases?
5. **Parameter docs** — does each parameter in `input_schema` have a description that covers valid values, edge cases, and what NOT to pass?

A tool that fails on dimension 3 ("when NOT to use") is the most common production failure mode. The model will call the tool when it shouldn't, because nothing in the description told it not to.

## How to do this

1. **Identify the tool definition file(s).** Tools in this repo live in `tools/<name>.py` and expose a `definition` dict. The user may pass a single tool path or a directory.

2. **For each tool**, read the file and extract the `definition` dict.

3. **Grade each dimension.** Pass / Concern / Fail. Concrete criteria:
   - **What it does**: must state the purpose in the first sentence. Pass if the first sentence is action-oriented and specific. Fail if it's empty, generic, or too short to convey purpose. (e.g., "Fetches data" → Fail; "Fetches GitHub issue details, comments, and metadata for a single issue" → Pass).
   - **When to use**: must include at least one positive use case. Pass if there's a "Use this tool when:" section or equivalent prose. Concern if implicit. Fail if absent.
   - **When NOT to use**: Pass if there's an explicit "Do NOT use this tool when:" or equivalent. Concern if there's a hint but no enumeration. Fail if absent. *This is the most consequential dimension.*
   - **Output shape**: Pass if the description states what the tool returns and what error / empty results look like. Concern if only success case is described. Fail if no output description.
   - **Parameter docs**: For each parameter, check the `description` field in the schema. Pass if it states valid values / edge cases / what NOT to pass. Concern if it states the type only. Fail if absent.

4. **Cite the file:line for every Concern or Fail.** Vague critique helps no one.

5. **Write the audit using the format below.**

## Output format

```markdown
# Tool description audit: <tool path or directory>

## Summary

<2-3 sentences. Lead with the count of tools by overall grade (Pass/Concern/Fail). Lead the explanation with the most-impactful weakness if any.>

## <tool_name>

**File:** `<path>:<line range>`
**Overall:** Pass | Concern | Fail

| Dimension | Grade | Note |
|-----------|-------|------|
| What it does | ✅ / ⚠️ / ❌ | <brief> |
| When to use | ✅ / ⚠️ / ❌ | <brief> |
| When NOT to use | ✅ / ⚠️ / ❌ | <brief> |
| Output shape | ✅ / ⚠️ / ❌ | <brief> |
| Parameter docs | ✅ / ⚠️ / ❌ | <brief> |

### Findings

<For each Concern or Fail, a paragraph: what's missing, why it matters, and a concrete example of what good would look like for this specific tool.>

(repeat per tool)

## Cross-tool patterns

<If 2+ tools fail the same dimension, surface it as a pattern — usually means the team has a shared convention gap, not a per-tool issue.>
```

## Self-check before completing

Before signaling done, verify:

- [ ] I read each tool file in full, including the `input_schema`.
- [ ] Every Concern or Fail has a `file:line` citation.
- [ ] For every Fail on "When NOT to use," I gave a concrete example of what good would look like for *that specific tool* — not generic advice.
- [ ] If multiple tools fail the same dimension, I added a Cross-tool patterns section.
- [ ] The summary states the count of Pass / Concern / Fail tools.
- [ ] I did not invent failure modes that aren't actually present in the code.

## What this skill does not do

- It does not rewrite the descriptions. It surfaces gaps. (A separate `tool-description-rewrite` skill could do that; not in this kit yet.)
- It does not test the tool's behavior. It audits the description only.
- It does not check whether the tool is *actually used correctly* by the agent — that's an integration concern, audited at the prompt level.

## Common failure modes for this skill

- **Grading too leniently on "When NOT to use."** This is the most consequential dimension. If the description doesn't enumerate cases where the tool should not be called, that's a Fail. A vague hint like "use carefully" is not enough.
- **Vague feedback.** "Description could be more detailed" is not actionable. Always cite the specific dimension and what specifically is missing.
- **Treating short descriptions as automatic Fails.** Length alone is not the criterion — clarity is. A 200-character description that hits all five dimensions beats a 1000-character one that doesn't.
- **Forgetting parameter docs.** Easy to focus on the top-level `description` and skip the `input_schema.properties`. The parameter docs are equally part of the prompt.
