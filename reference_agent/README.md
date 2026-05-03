# reference-agent: `issue-triage`

Open-source library maintainer assistant. Classifies incoming GitHub issues, gathers context via tools, returns a structured triage decision — direct response or structured handoff.

The gold standard. `compare-agents` checks new agents against this one.

## Run it

```bash
pip install -r ../requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...

python -m reference_agent.runner --issue 101 --show-trace   # bug
python -m reference_agent.runner --issue 104 --show-trace   # security — must escalate
python -m reference_agent.runner --issue 107 --show-trace   # ambiguous — must escalate as unknown
```

## Run the routing eval

```bash
python -m reference_agent.evals.routing.run_eval
```

Last measured: 6/7 (0.857). Threshold is 0.90. The seventh case (issue 107) is a real disagreement between policy and behavior — see `evals/routing/golden.jsonl` notes.

## Layout

```
reference_agent/
├── agent.yaml          # Manifest. Skills read this.
├── runner.py           # Agent loop.
├── prompts/            # system, classification, three flow prompts, handoff.
├── tools/              # github_issues, github_search, codeowners_lookup.
├── evals/
│   ├── routing/        # Golden set + runner.
│   ├── quality/        # Stub (not implemented).
│   └── regression/     # Stub (not implemented).
└── fixtures/           # Issues + CODEOWNERS for offline runs.
```

## Patterns

See [`../docs/claude/reference-agent.md`](../docs/claude/reference-agent.md) for the full spec. Short version: calibrated routing, graceful degradation, visible reasoning, structured handoff, eval coverage, clean tool design.
