# Broken candidate: `issue-helper`

A second agent in the same domain as the reference, with deliberate flaws baked in. Used by `compare-agents` and `tool-description-audit` to demonstrate what the skills find.

This is a **teaching artifact**, not a real broken agent in the wild. The flaws are realistic but the package is curated — a real partner dev's v0 would be messier in different ways.

## The flaws

1. **`security` in `intents.in_scope`** (`agent.yaml`). Agent engages with security disclosures instead of escalating. Production-grade safety failure.
2. **No `routing.confidence_threshold`** (`agent.yaml`). Agent dispatches on whatever the classifier returns, no calibration.
3. **Sparse tool descriptions** (`tools/*.py`). No "when not to use" guidance. No output shape documentation.
4. **No graceful degradation** (`prompts/*.j2`). Flow prompts assume tools always succeed.
5. **No eval coverage** (`agent.yaml`). Routing eval `not_implemented`.
6. **Manifest version drift** (`agent.yaml` ↔ `prompts/system.j2`). Manifest claims `system: 1`; actual file says version 2.

Each flaw maps to a finding `compare-agents` produces. See [`../outputs/compare-agents-output.md`](../outputs/compare-agents-output.md) for the full audit.

## Run it (optional)

The candidate has a working runner so the broken behavior can be observed directly:

```bash
python -m examples.broken_candidate.runner --issue 104   # security disclosure — agent will engage instead of escalate
python -m examples.broken_candidate.runner --issue 101   # bug — agent will respond with no graceful degradation
```

Compare the output to running the same issues against `reference_agent.runner`.

## Why the flaws are commented in `agent.yaml`

A real broken candidate wouldn't have helpful comments saying "FLAW 1." The comments are for readers of this kit. Real audits don't get this hint.
