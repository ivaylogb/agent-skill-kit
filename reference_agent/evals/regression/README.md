# Regression eval (not yet implemented)

This directory is the slot for the regression eval, referenced by `agent.yaml` (`evals.regression.status: not_measured`).

## What goes here when it's built

A regression eval pins specific cases that previously broke and verifies they stay fixed. The pattern:

- `cases.jsonl` — one case per line, each containing the issue input, the bug it caught, and the expected agent behavior.
- Cases are **append-only**. Never delete a case; only add. If a case becomes obsolete, mark it as such, do not remove.
- The runner re-runs every case on every change and fails CI if any previously-passing case now fails.

## What goes in a case

```json
{
  "id": "regression-001",
  "added_on": "2026-04-23",
  "bug_summary": "Agent classified ambiguous docs/bug as bug with high confidence",
  "input_issue_number": 107,
  "expected_intent": "unknown",
  "expected_min_confidence_threshold_held": true,
  "notes": "Issue 107 has mixed docs/bug signals. Agent must escalate."
}
```

## Why this matters

Routing accuracy on the golden set tells you the agent works on average. Regression cases tell you the agent doesn't *re-break* in ways it has broken before. They're the second axis of correctness.
