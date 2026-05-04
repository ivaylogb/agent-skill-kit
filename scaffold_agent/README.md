# scaffold_agent

Generates a new agent from a one-line description. Asks clarifying questions, validates the spec, writes a complete agent directory matching the methodology in this kit.

## Run

```bash
python -m scaffold_agent describe "An agent that triages incoming sales leads by qualification stage" \
    --output ./generated
```

The meta-agent will ask 1-3 clarifying questions, then produce an agent into `./generated/<agent_name>/`.

## Bypass the conversation

For testing or for inputs you've already structured, generate from a JSON spec file:

```bash
python -m scaffold_agent from-spec scaffold_agent/tests/sample_spec_lead_triage.json \
    --output ./generated
```

The schema for the spec file is in `scaffold_agent/spec.py` (`AgentSpec` dataclass).

## What gets generated

```
<agent_name>/
├── README.md
├── agent.yaml          # Manifest. Audit skills read this.
├── runner.py           # Agent loop, built on the Anthropic SDK.
├── prompts/
│   ├── system.j2
│   ├── classification.j2
│   ├── handoff.j2
│   └── <intent>_flow.j2  × one per in-scope intent
├── tools/
│   ├── __init__.py
│   └── <tool_name>.py  × one per tool, with `definition` and `call()`
└── evals/
    └── routing/
        └── golden.jsonl  # Starter golden set
```

The generated tools have stub `call()` functions. To make the agent useful, fill them in with your actual backend integrations.

## Architecture

The scaffolder is itself an agent. It has two tools:

- `ask_user_question` — for clarifying questions. Capped at 3 to avoid over-asking.
- `submit_spec` — forced via `tool_choice` so the model can't drift from the schema.

The conversation loop runs against the Anthropic SDK directly. No framework wrapper. The same patterns this kit teaches.

## Limitations

- The scaffolder relies on the user's domain knowledge. Vague descriptions ("an agent for sales") will yield generic specs even with clarifying questions.
- Generated tool descriptions are good but not domain-perfect. Expect to refine them after running `tool-description-audit` on the generated tools.
- The scaffolder does not run `compare-agents` on its own output. Run it manually as a follow-up step to surface gaps before deploying.

## Verify the generated agent

After generation, run the audit skills against the new agent:

```bash
# Via Claude Code in the repo:
# Invoke `compare-agents` against ./generated/<agent_name>/
# Invoke `tool-description-audit` on ./generated/<agent_name>/tools/
```

This is the methodology in motion: scaffold → audit → fix.
