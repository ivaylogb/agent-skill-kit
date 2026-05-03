# Quality eval (not yet implemented)

This directory is the slot for the LLM-as-judge quality eval, which is referenced by `agent.yaml` (`evals.quality.status: not_measured`).

## What goes here when it's built

A quality eval scores the agent's *output* (handoff quality, response helpfulness, tone) using an LLM-as-judge with a calibrated rubric. The flow:

1. **Golden set** — `golden.jsonl` with issue inputs and expert-written ideal handoffs.
2. **Judge prompt** — `judge.j2` that scores agent output against the ideal on dimensions like: handoff completeness, classification correctness, tone, no information loss.
3. **Calibration** — pairs of human-rated examples used to compute Cohen's Kappa between the LLM judge and human raters. Target Kappa ≥ 0.7 before the eval is trustworthy.
4. **Runner** — `run_eval.py` that scores agent outputs against the rubric and reports pass rate.

## Why it isn't here yet

Calibrating an LLM judge requires human-rated examples to compare against. That's a deliberate process, not something to fake. The repo holds the slot honestly until real calibration happens.

## What `compare-agents` should check about this

When a candidate agent has `evals.quality.status: not_measured` AND is being compared to the reference, `compare-agents` should flag this as a *gap shared with the reference* — not as a gap unique to the candidate. The reference is honest about its own incompleteness; the comparison should reflect that.
