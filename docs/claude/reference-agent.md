# Reference Agent: `issue-triage`

The gold standard. `compare-agents` diffs candidates against this. `review-agent-pr` checks changes against the conventions established here.

## What `issue-triage` does

Given a new GitHub issue, classifies it, gathers context, and either resolves it directly (in-scope and confident) or routes it with structured handoff context to a human (out-of-scope or low confidence).

**In-scope:**

- `bug` — verify reproduction, label, suggest assignee from CODEOWNERS
- `feature` — check duplicates, route to feature-request workflow
- `docs` — search docs, answer with reference, or flag as docs gap

**Out-of-scope (route, do not handle):**

- `security` — route to maintainer DM with templated acknowledgment. Do not analyze.
- `paid_support` — route to billing.
- `code_review` — out of triage scope; route to PR review process.

## Why this is the reference

Not because it's ambitious — because it has the patterns every production agent needs, in their cleanest form.

### 1. Calibrated routing

Classification returns intent + confidence. Below `routing.confidence_threshold` (0.7), the agent routes to `unknown` rather than guessing. Agents that guess on classification cause the most expensive failures.

### 2. Graceful degradation

When tools fail, the agent surfaces the failure with what it *was* able to determine. Never silently degrades.

### 3. Visible reasoning

The agent's reasoning lives in observable surfaces — message text alongside tool calls, structured fields in the final response, the contents of the handoff. The runner additionally captures an execution trace for debugging.

A "scratchpad" the model writes to but no one reads is a fiction. Reasoning that matters belongs in observable surfaces.

### 4. Structured handoff

Every escalation produces: original message, classification + confidence, what the agent attempted, why it escalated, suggested next step. The receiving human gets context, not a forwarded message.

### 5. Eval coverage

- **Routing accuracy** — golden set of issues with ground-truth classifications. Threshold: 0.90.
- **Quality** — LLM-as-judge with calibrated rubric. Currently `not_measured`.
- **Regression** — pinned cases for previously-shipped bugs. Append-only. Currently `not_measured`.

### 6. Clean tool design

Every tool passes `tool-description-audit`:

- Description states what the tool does, when to use, when *not* to use.
- Parameters have docstrings explaining valid values and edge cases.
- Output shape is structured where possible.
- Error modes documented in the description.

## Repo conventions

Apply to all agents in this kit. Skills check for them.

### Prompt structure

```
prompts/
  system.j2          # Top-level orchestrator
  classification.j2  # Routing
  bug_flow.j2        # Bug-specific reasoning
  feature_flow.j2
  docs_flow.j2
  handoff.j2         # Structured escalation
```

Component versioning: each `.j2` has a `{# version: N #}` comment at the top. Changing a component bumps the version. `version-diff` reads these.

### Tool config

Tools live in `tools/<name>.py` with `definition` (dict) and `call` (function) at module level. Separation lets `tool-description-audit` read definitions without executing tools.

### Eval config

```
evals/
  routing/      # pytest-shaped, golden set
  quality/      # LLM-as-judge with calibrated rubric
  regression/   # pinned cases, append-only
```

### Versioning

```yaml
agent: issue-triage
version: 1
prompts:
  system: 1
  classification: 1
  bug_flow: 1
  feature_flow: 1
  docs_flow: 1
  handoff: 1
tools:
  - name: github_issues
    version: 1
```

`version-diff` reads this for semantic deltas.

## Production-ready checklist

A new agent is production-ready when:

- [ ] Routes calibrated, with explicit out-of-scope handling
- [ ] Graceful degradation on every tool failure path
- [ ] Visible reasoning (no hidden-state pretense)
- [ ] Structured handoff for every escalation
- [ ] Routing eval ≥ 0.90 on golden set
- [ ] Quality eval Kappa ≥ 0.7 (when implemented)
- [ ] Tool descriptions pass `tool-description-audit`
- [ ] At least one regression test for any previously-shipped bug
- [ ] `agent.yaml` versioned and current

`compare-agents` checks all of these.

## Spec, not framework

This is a spec, not a base class to inherit from. Frameworks couple your agent to a lifecycle. Specs let your agent evolve while keeping production properties stable.

Skills treat this document as ground truth. When the spec changes, skill behavior changes — without code changes to the skills.
