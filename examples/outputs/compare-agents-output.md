# Comparison: issue-helper vs. issue-triage

## Summary

The single most serious finding is that `security` appears in `intents.in_scope`, meaning the agent will engage with and analyze security disclosures instead of routing them — a production safety failure that must be fixed before any other work. There are **2 Critical findings**, **5 Important findings**, and **6 Nits**; shared gaps with the reference (quality and regression evals) are in their own section.

---

## Critical findings

### 1. `security` listed as an in-scope intent

**Where:** `examples/broken_candidate/agent.yaml:19`

**What:** `security` is listed under `intents.in_scope` alongside `bug`, `feature`, and `docs`. It is absent from `intents.out_of_scope`. There is no `security_flow.j2` to handle it, so the `system.j2` "do your best" fallback (line 8–9) kicks in when a security issue arrives. The classification prompt (`classification.j2:8`) correctly identifies the `security` intent — the agent will classify it and then attempt to handle it in-line.

**Why it matters:** A vulnerability report processed as in-scope will be analyzed, summarized, and potentially posted to a public comment thread before a maintainer can coordinate responsible disclosure. This is the canonical way security disclosures leak via automated triage tooling.

**Reference behavior:** `reference_agent/agent.yaml:24` places `security` in `out_of_scope`. `reference_agent/prompts/system.j2:11–12` makes it a hard rule: "Out-of-scope intents are escalated, not handled." `reference_agent/prompts/handoff.j2:35–38` provides a templated acknowledgment that avoids summarizing the disclosure content.

---

### 2. No `routing.confidence_threshold`

**Where:** `examples/broken_candidate/agent.yaml:28–29` (comment acknowledges absence; key is never set)

**What:** The manifest has no `routing` block. The agent dispatches on whatever confidence the classifier returns — including sub-50% guesses on ambiguous issues. `system.j2:17–21` defines a dispatch loop with no branch for low-confidence classification; the loop goes directly from "Classify" to "Dispatch to the appropriate flow" with no threshold check.

**Why it matters:** Without a threshold, ambiguous issues get dispatched as confident classifications. A docs question at 0.52 confidence gets handled as `docs` rather than escalated. More dangerously, a security disclosure at 0.61 confidence — slightly below the reference's threshold — would be dispatched rather than routed to the `unknown` escalation path.

**Reference behavior:** `reference_agent/agent.yaml:30` sets `confidence_threshold: 0.7`. `reference_agent/prompts/system.j2:8` makes the rule explicit: "If your classification confidence is below 0.7, route to `unknown` and escalate. Do not guess."

---

## Important findings

### 3. `handoff.j2` prompt is missing entirely

**Where:** `examples/broken_candidate/agent.yaml:39` (comment: "No handoff prompt"); `examples/broken_candidate/prompts/` (file not present); manifest `prompts` block has no `handoff` key

**What:** There is no prompt to produce structured escalation context. The `out_of_scope` intents (`paid_support`, `code_review`) have no defined escalation path, and the missing `confidence_threshold` (Critical #2) means there is also no low-confidence escalation path. Any escalation the agent attempts produces unstructured output. The manifest does not declare `handoff` in the `prompts` block at all.

**Why it matters:** A handoff is the contract with the receiving human. Without one, escalation produces a forwarded message rather than structured context — original message, classification, what was attempted, why it was escalated, suggested next step. The human receiving the escalation has to start triage from scratch.

**Reference behavior:** `reference_agent/prompts/handoff.j2` defines a five-part structured JSON output and specializes it for out-of-scope, low-confidence, and tool-failure escalation cases. `reference_agent/agent.yaml:40` declares `handoff: 1` in the `prompts` block.

---

### 4. `system.j2` "always be helpful" instruction overrides out-of-scope policy

**Where:** `examples/broken_candidate/prompts/system.j2:8–9`

**What:** The system prompt instructs: "Always provide a useful response. Every issue deserves engagement. If you don't know how to handle something, do your best — partial information is better than none." This is a direct override of any escalation policy. Even if `security` were correctly placed in `out_of_scope`, this top-level instruction would still push the agent to engage with the content. The dispatch loop (lines 14–26) has no branch for out-of-scope intents and no "What you do not do" section constraining behavior at boundaries.

**Why it matters:** System prompt instructions are highest priority. A "do your best" directive at that level defeats routing rules defined in the manifest. The reference's design principle — "Classify before you act" and "Out-of-scope intents are escalated, not handled" — requires the opposite instruction in the system prompt.

**Reference behavior:** `reference_agent/prompts/system.j2:11–12` states the hard rule. Lines 41–45 provide a "What you do not do" section listing prohibited actions (close issues, assign issues, comment on the issue, edit the issue body).

---

### 5. No working routing eval — agent is unmeasured

**Where:** `examples/broken_candidate/agent.yaml:52` (`routing.status: not_implemented`); `examples/broken_candidate/` has no `evals/` directory

**What:** The candidate declares `routing.status: not_implemented` with no golden set and no pass threshold. No `evals/routing/` directory exists. This is a candidate-specific gap: the reference has a working routing eval; the candidate does not.

**Why it matters:** Routing accuracy is the primary measurable property of a triage agent. Without an eval, every prompt change is unverified, model upgrades are high-risk with no before/after signal, and there is no way to assert the agent meets the 90% threshold required for production readiness. Quality and regression evals being absent is a shared gap (see below); routing being absent is the candidate's own gap.

**Reference behavior:** `reference_agent/agent.yaml:54–56` declares `golden_set: evals/routing/golden.jsonl` and `pass_threshold: 0.90`. `reference_agent/evals/routing/golden.jsonl` and `reference_agent/evals/routing/run_eval.py` exist and are runnable.

---

### 6. `codeowners_lookup` tool missing entirely

**Where:** `examples/broken_candidate/tools/` (no `codeowners_lookup.py`); `examples/broken_candidate/agent.yaml:41–48` (tools list has only `github_issues` and `github_search`)

**What:** The reference uses `codeowners_lookup` to suggest assignees in bug triage and feature routing. The candidate declares no such tool and the bug flow (`bug_flow.j2:8`) has no step for component identification or assignee suggestion. There is no mechanism to populate a `suggested_assignee` in the output.

**Why it matters:** Bug triage without assignee suggestion produces handoffs a human must manually re-triage. The reference's structured `triage_decision` schema includes `suggested_assignee` as a required field; the candidate's schema has no equivalent.

**Reference behavior:** `reference_agent/tools/codeowners_lookup.py` defines the tool with a full description, when-not-to-use guidance ("guessing here causes wrong-assignee escalations, which damage maintainer trust"), and empty-list semantics. `reference_agent/prompts/bug_flow.j2:26–30` calls it after identifying a component.

---

## Nits

### 7. `system.j2` version drift: file is v2, manifest claims v1

**Where:** `examples/broken_candidate/prompts/system.j2:1` (`{# version: 2 — edited 2026-04-30 #}`); `examples/broken_candidate/agent.yaml:32` (`system: 1`)

**What:** The file header was bumped to version 2 on 2026-04-30, but the manifest was not updated. Skills that read the manifest to compute version deltas (`version-diff`, `review-agent-pr`) will report a false "no change" for the system prompt.

---

### 8. `github_issues` tool description is 79 chars with no when-not-to-use and no error-case docs

**Where:** `examples/broken_candidate/tools/github_issues.py:9`

**What:** Description is "Fetches details about a GitHub issue given its number. Returns the issue data." — 79 characters. No when-not-to-use guidance, no documentation of the error shape when an issue is not found. The implementation returns `{}` on not-found (line 35) rather than a structured error, so the model cannot distinguish "found but empty" from "not found."

**Reference behavior:** `reference_agent/tools/github_issues.py:22–36` has a 400+ character multi-section description and returns `{"error": "not_found"}` on miss (line 71) matching the documented error shape.

---

### 9. `github_search` tool description is 42 chars, missing `state` parameter, leaks `_score`

**Where:** `examples/broken_candidate/tools/github_search.py:9` (description), `:40` (missing `state` in `input_schema`), `:41` (`_score` included in results)

**What:** Three issues in one tool: (a) description is "Searches GitHub issues for a query string." — 42 chars, no when-not-to-use, no note that empty results are valid not-failure; (b) no `state` parameter, so the model cannot filter open vs. closed when distinguishing duplicates from regressions; (c) `_score` is included in every result, leaking an internal sort key as data. The comment on line 41 acknowledges the anti-pattern.

**Reference behavior:** `reference_agent/tools/github_search.py` has a 400+ char description, adds `state` with enum and per-value guidance (line 40–47), and strips `_score` before returning (line 83).

---

### 10. Flow prompts missing tool failure handling and "what this flow does not do" sections

**Where:** `examples/broken_candidate/prompts/bug_flow.j2` (no failure modes section); `examples/broken_candidate/prompts/feature_flow.j2` (same); `examples/broken_candidate/prompts/docs_flow.j2` (same)

**What:** All three flow prompts omit: (a) explicit tool failure modes the agent should expect and handle gracefully, and (b) a "What this flow does not do" section constraining behavior at the boundary. Without failure mode guidance, the model either hallucinates results or silently drops tool steps when tools fail.

**Reference behavior:** `reference_agent/prompts/bug_flow.j2:57–68` enumerates failure modes for both `github_search` and `codeowners_lookup`. Lines 63–68 define the "What this flow does not do" section with three concrete prohibitions.

---

### 11. Flow prompts do not inject classification data

**Where:** `examples/broken_candidate/prompts/bug_flow.j2:19–20`; `examples/broken_candidate/prompts/feature_flow.j2:8–10`; `examples/broken_candidate/prompts/docs_flow.j2:8–10`

**What:** All three flow prompts render `{{ issue.title }}` and `{{ issue.body }}` but not `{{ classification.intent }}` or `{{ classification.confidence }}`. The flow cannot include the classification decision or confidence in its structured output or handoff context.

**Reference behavior:** `reference_agent/prompts/bug_flow.j2:75` renders `Issue #{{ issue.number }} — classified as {{ classification.intent }} (confidence {{ classification.confidence }})` in the issue header, which flows into the structured `triage_decision` output.

---

### 12. `feature_flow.j2` has no structured output schema

**Where:** `examples/broken_candidate/prompts/feature_flow.j2:13`

**What:** The prompt instructs: "Produce a response thanking the user and indicating whether the feature is reasonable." No JSON schema, no field definitions. The caller receives a free-text response with no defined structure to parse.

**Reference behavior:** `reference_agent/prompts/feature_flow.j2:24–34` defines a structured JSON output schema with six named fields (`decision`, `intent`, `scope`, `component`, `suggested_assignee`, `handoff_context`).

---

### 13. `docs_flow.j2` answers from model knowledge instead of searching docs

**Where:** `examples/broken_candidate/prompts/docs_flow.j2:5`

**What:** The prompt instructs: "Try to answer it directly using your knowledge." The reference explicitly searches via `github_search` scoped to the docs directory and decides between three structured outcomes (answer with reference, route to discussions, flag docs gap). Answering from model knowledge bypasses the actual documentation corpus.

**Reference behavior:** `reference_agent/prompts/docs_flow.j2:10–11`: "Search via `github_search` scoped to the docs directory. If you find a doc page that addresses the question → output `answer_with_reference` and include the doc URL." Answering from knowledge alone is not an option the reference flow offers.

---

## Shared gaps with the reference

**Quality eval — both not measured.**
`reference_agent/agent.yaml:57` sets `quality.status: not_measured`. The candidate sets `quality.status: not_implemented`. Neither has an LLM-as-judge eval with a calibrated rubric. This is not a candidate-specific gap; the reference sets the standard here as "not yet implemented."

**Regression eval — both not measured.**
`reference_agent/agent.yaml:61` sets `regression.status: not_measured`. The candidate sets `regression.status: not_implemented`. Neither has pinned regression cases. Same situation as quality.

---

## What I read

1. `docs/claude/reference-agent.md` — reference spec and production-ready checklist
2. `reference_agent/agent.yaml` — reference manifest (structural baseline)
3. `examples/broken_candidate/agent.yaml` — candidate manifest
4. `examples/broken_candidate/prompts/system.j2`
5. `examples/broken_candidate/prompts/classification.j2`
6. `examples/broken_candidate/prompts/bug_flow.j2`
7. `examples/broken_candidate/prompts/feature_flow.j2`
8. `examples/broken_candidate/prompts/docs_flow.j2`
9. `examples/broken_candidate/tools/github_issues.py`
10. `examples/broken_candidate/tools/github_search.py`
11. `reference_agent/prompts/system.j2`
12. `reference_agent/prompts/bug_flow.j2`
13. `reference_agent/prompts/feature_flow.j2`
14. `reference_agent/prompts/docs_flow.j2`
15. `reference_agent/prompts/handoff.j2`
16. `reference_agent/tools/github_issues.py`
17. `reference_agent/tools/github_search.py`
18. `reference_agent/tools/codeowners_lookup.py`
