# Example outputs: using the kit end-to-end

These are real outputs captured by running the skills against the broken candidate at `examples/broken_candidate/` and the reference agent at `reference_agent/`. They're meant to be read as a workflow, not three isolated audits.

## The walkthrough

A new agent has been added to the repo. You want to know: how far is it from production-ready, and what specifically needs work? Three skills, in sequence.

### Step 1 — Structural diff

Run `compare-agents` first. It compares the candidate's manifest, prompts, tools, and evals against the reference and surfaces where the candidate falls short. This is the wide lens.

→ [`compare-agents-output.md`](compare-agents-output.md)

The captured run found **2 Critical, 5 Important, 6 Nits, 2 Shared gaps**. The most consequential — `security` placed in `intents.in_scope` — is a production safety failure that takes precedence over everything else. The second Critical (no confidence threshold) means the agent dispatches on every classification regardless of confidence, including 0.5 guesses on ambiguous issues.

The audit also found things the broken candidate didn't telegraph in its comments: a "do your best" instruction in `system.j2` that overrides the out-of-scope policy, a `docs_flow` that answers from model knowledge instead of searching the docs corpus. Skills that only catch the things the test bench tells them to find aren't useful; this one reads the actual code.

### Step 2 — Zoom in on tool design

`compare-agents` flags tool design issues at a high level (sparse descriptions, missing failure handling). For the depth, run `tool-description-audit` on the candidate's tools.

→ [`tool-description-audit-broken.md`](tool-description-audit-broken.md)

Both tools fail across all five dimensions — what they do, when to use, when NOT to use, output shape, parameter docs. The audit produces concrete, copy-pasteable rewrites for each finding rather than abstract critique. The `Cross-tool patterns` section diagnoses the *systemic* issue: the team's convention treats parameter descriptions as type labels, not as prompts the model reads to decide what to call.

### Step 3 — Compare against the reference's tools

Same skill, different target. Run it on the reference agent's tools to confirm what "good" looks like — and to demonstrate that the audit isn't just looking for failure modes.

→ [`tool-description-audit-reference.md`](tool-description-audit-reference.md)

All three reference tools pass cleanly. The audit identifies *what specifically* makes them good: symmetric cross-tool redirects (each tool points to the right alternative), explicit empty-result-vs-failure semantics, parameter docs that go beyond type to cover behavior. These are the conventions the candidate's tools fail to follow.

## What this composition demonstrates

A new agent gets reviewed in three passes. The first pass surfaces the structural shape of the gap. The second pass quantifies the depth on the dimension that flagged hottest. The third pass anchors the review against a known-good baseline. Each skill alone is useful; together they produce a complete enough picture to decide what to fix first.

The skills don't chain automatically — Claude Code runs each one when invoked. The composition is in the workflow, not the framework.

## Reading the audits as a partner dev

If you're cloning this kit and pointing the skills at your own agent:

1. Start with `compare-agents` against the reference. Read the Critical findings first; they block production. Important findings are real but won't ship a security hole if shipped. Nits are real but fine to leave open while you address higher-priority items.
2. For each finding, the audit cites file and line. Open the file, look at the line, decide.
3. Run `tool-description-audit` on your tools. The Cross-tool patterns section is where systemic gaps show up — those are higher-leverage fixes than any individual finding.
4. Re-run after fixes. Both skills are idempotent and read the actual codebase, so they'll surface different findings as the code changes.

## Captured

| File | Skill | Target | Date |
|------|-------|--------|------|
| `compare-agents-output.md` | `compare-agents` | `examples/broken_candidate/` | 2026-05-03 |
| `tool-description-audit-broken.md` | `tool-description-audit` | `examples/broken_candidate/tools/` | 2026-05-03 |
| `tool-description-audit-reference.md` | `tool-description-audit` | `reference_agent/tools/` | 2026-05-03 |

Real outputs from real runs. Re-running on the same files will produce close-but-not-identical results — file:line citations are accurate, severity grading is consistent, exact wording will vary.
