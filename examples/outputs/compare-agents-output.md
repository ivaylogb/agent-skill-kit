# Comparison: issue-helper vs. issue-triage

> Output of running `compare-agents` against `examples/broken_candidate/` with `reference_agent/` as the baseline. Captured 2026-05-03.

## Summary

The candidate (`issue-helper`) has **two Critical** findings, **five Important** findings, and **one Nit**, in addition to **two shared gaps** with the reference. The most consequential finding is that `intents.in_scope` includes `security`, which means the agent will engage with security disclosures rather than escalate them. This is a production-grade safety failure and should be fixed before any other work.

## Critical findings

### 1. Security disclosures are in_scope

**Where:** `examples/broken_candidate/agent.yaml` line 14

**What:** The candidate's manifest lists `security` under `intents.in_scope`, alongside `bug`, `feature`, and `docs`. Combined with the runner's `flow_map["security"] = "bug_flow"` (line 105 of `runner.py`), the agent will dispatch security disclosures to the bug-handling flow and treat them as ordinary bug reports.

**Why it matters:** A vulnerability report with a working proof of concept will be processed through the same path as a bug report — including duplicate search, public component lookup, and a public-facing handoff. This is exactly the pattern that ships exploits to public review queues.

**Reference behavior:** `issue-triage` lists `security` under `intents.out_of_scope` and produces a templated handoff that does not analyze the disclosure content. Verified on issue 104 (RCE disclosure): classified as `security` with 0.99 confidence, escalation reason `out_of_scope`, no analysis of the vulnerability.

### 2. No confidence threshold in routing

**Where:** `examples/broken_candidate/agent.yaml` — `routing.confidence_threshold` is absent.

**What:** The candidate's manifest has no `routing` section. The runner (line 96 of `runner.py`) reads `intent = classification.get("intent", "unknown")` directly with no confidence check. Whatever the classifier returns gets dispatched.

**Why it matters:** On ambiguous issues, the classifier returns *something* with low confidence — but the agent has no way to escalate. It guesses. Routing accuracy on the easy cases doesn't tell you anything about how the agent behaves at the boundary.

**Reference behavior:** `issue-triage` enforces `routing.confidence_threshold: 0.7` at runtime (line 169 of `reference_agent/runner.py`). Below threshold, the intent is replaced with `unknown` and the agent escalates to a structured handoff regardless of the original classification.

## Important findings

### 3. Tool descriptions are sparse and missing "when not to use" guidance

**Where:**
- `examples/broken_candidate/tools/github_issues.py` line 9 (description is 11 words)
- `examples/broken_candidate/tools/github_search.py` line 9 (description is 8 words)

**What:** Both tools' descriptions state what the tool does but do not describe when not to use it, what the output shape looks like in error cases, or how the tool interacts with similar tools in the registry.

**Why it matters:** Tool descriptions are prompts. The model uses them to decide *which* tool to call and *whether* to call any at all. A description that says "Searches GitHub issues for a query string" gives the model no signal about when search is the wrong move (e.g., when the issue number is already known and `github_issues` would be the right call).

**Reference behavior:** Each reference tool has a description that is multi-section: what it does, when to use it (positive), when NOT to use it (negative), and what the output shape includes. See `reference_agent/tools/github_issues.py` for the canonical shape.

### 4. No graceful degradation in flow prompts

**Where:** `examples/broken_candidate/prompts/bug_flow.j2`, `feature_flow.j2`, `docs_flow.j2`

**What:** None of the flow prompts describe what to do when a tool call fails. `bug_flow.j2` line 7 instructs the model to "Search for similar issues with `github_search`" with no guidance on what to do if the search returns an error or empty results.

**Why it matters:** Tools fail. When they do, the model either fakes a result, hallucinates, or silently drops the search step. All three produce wrong outputs. Explicit failure-mode guidance in the prompt is what prevents this.

**Reference behavior:** `reference_agent/prompts/bug_flow.j2` lines 57-61 explicitly enumerate the tool failure modes and the correct response to each. Empty results are not failures; tool exceptions must be surfaced; missing CODEOWNERS means "no specific owner," not a guess.

### 5. No handoff prompt

**Where:** `examples/broken_candidate/prompts/` — `handoff.j2` does not exist.

**What:** The candidate has flow prompts for in-scope intents but no prompt for producing structured escalation context. When the candidate encounters an out-of-scope intent (`paid_support`, `code_review`) the runner returns `decision: no_flow` with a one-line message, not a structured handoff.

**Why it matters:** A handoff is a contract with the receiving human. Without a structured one, escalation produces no context, no classification confidence, no actions-taken summary. The receiving human starts triage from scratch.

**Reference behavior:** `reference_agent/prompts/handoff.j2` produces a structured handoff with summary, classification, actions taken, escalation reason, and suggested next step. Used for both out-of-scope and low-confidence cases.

### 6. Manifest version drift

**Where:** `examples/broken_candidate/agent.yaml` line 28 declares `system: 1` but `examples/broken_candidate/prompts/system.j2` line 1 says `version: 2 — edited 2026-04-30, manifest still claims version 1`.

**What:** The manifest's record of prompt versions is inconsistent with the actual prompt file. The prompt has been edited since the manifest was last updated.

**Why it matters:** `version-diff` and `review-agent-pr` rely on the manifest as the source of truth for what changed. Drift here invalidates downstream skills' analyses. If a reviewer asks "what changed in v2?", the manifest cannot answer.

**Reference behavior:** `reference_agent/agent.yaml` prompt versions match each prompt file's header comment exactly.

### 7. No routing eval

**Where:** `examples/broken_candidate/agent.yaml` line 41 declares `evals.routing.status: not_implemented`. No `evals/routing/` directory exists.

**What:** The candidate has no routing accuracy measurement at all. Classification could be 50% accurate or 95% accurate; nobody knows.

**Why it matters:** Routing accuracy is the most consequential property of a triage agent. Without an eval, every prompt change is unverified. Drift goes undetected. Model upgrades become high-risk events because there's no signal to compare before-and-after on. This is *not* a shared gap — the reference has a working routing eval with 7 golden examples and a 6/7 pass rate.

**Reference behavior:** `reference_agent/evals/routing/golden.jsonl` defines 7 ground-truth cases. `reference_agent/evals/routing/run_eval.py` scores classification against them. Threshold is 0.90 (currently failing at 0.857, surfaced honestly in `last_run.json`).

## Nits

### 8. `_score` field leaks to the model

**Where:** `examples/broken_candidate/tools/github_search.py` line 31.

**What:** The internal sort key `_score` is included in the tool's return value. The model sees it but has no use for it.

**Why it matters:** Noise in tool outputs costs context budget and gives the model spurious signals to reason about. Cosmetic, but cheap to fix.

**Reference behavior:** `reference_agent/tools/github_search.py` strips `_score` before returning (line 84-86, comment: "Strip the internal sort key — the model doesn't need it and it adds noise.").

## Shared gaps with the reference

These are gaps in the candidate that are also gaps in the reference. Surfaced for completeness but not chargeable to the candidate.

### S1. Quality eval not implemented

Both agents declare `evals.quality.status: not_measured`. Building a calibrated LLM-as-judge eval is non-trivial and the reference is honest about not having one yet. The candidate inherits this gap; it's not a candidate-specific issue until the reference ships one.

### S2. Regression eval not implemented

Both agents declare `evals.regression.status: not_measured`. Same reasoning as S1.

## What I read

1. `docs/claude/reference-agent.md`
2. `reference_agent/agent.yaml`
3. `examples/broken_candidate/agent.yaml`
4. `examples/broken_candidate/prompts/system.j2`
5. `examples/broken_candidate/prompts/classification.j2`
6. `examples/broken_candidate/prompts/bug_flow.j2`
7. `examples/broken_candidate/prompts/feature_flow.j2`
8. `examples/broken_candidate/prompts/docs_flow.j2`
9. `examples/broken_candidate/tools/github_issues.py`
10. `examples/broken_candidate/tools/github_search.py`
11. `examples/broken_candidate/runner.py`
12. `reference_agent/prompts/bug_flow.j2` (for cross-reference on graceful degradation pattern)
13. `reference_agent/tools/github_search.py` (for cross-reference on _score handling)
14. `reference_agent/runner.py` (for cross-reference on confidence threshold enforcement)
