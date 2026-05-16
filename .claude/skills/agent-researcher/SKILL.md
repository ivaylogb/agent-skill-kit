---
name: agent-researcher
description: When an agent eval fails on one or more scenarios, run agent-researcher to produce structured hypotheses about why each failure happened. Each hypothesis proposes a file:line citation, a structured edit, and a verification step. Thin wrapper around the installed agent-researcher CLI; the CLI does the diagnosis.
when_to_use: A scenario in an eval suite is failing, the user wants to understand why, and the eval output is available as a JSON file (e.g., from Braintrust, LangSmith, or a custom harness).
---

# agent-researcher

Shells out to the installed `agent-researcher` CLI to diagnose one failing eval scenario. It reads the target agent's source and the failing scenario, then produces a markdown report of 2–3 structurally distinct hypotheses. Each hypothesis is assigned to one agent-engineering layer (Evaluation, Tools, Context, Workflow), cites specific `file:line` evidence in the target agent, ships an applyable structured edit, and names a verification step. No diagnostic logic lives in this skill — `runner.py` validates inputs and invokes the CLI.

## Prerequisites

- The `agent-researcher` CLI on PATH. Install from a clone of <https://github.com/ivaylogb/agent-researcher>:
  ```bash
  pip install -e .
  export ANTHROPIC_API_KEY=sk-ant-...
  ```
- `ANTHROPIC_API_KEY` set — `diagnose` spends model tokens.

## Inputs

| Input | Flag | Required | Notes |
|---|---|---|---|
| Target agent directory | `--target-agent` | yes | The agent under diagnosis (manifest, prompts, tools). |
| Eval result JSON | `--eval-result` | yes | The harness output containing the failure. |
| Scenario id | `--scenario-id` | no | Which failure to investigate; defaults to the first. |
| Scenario input | `--scenario-input` / `--scenario-input-file` | no | The user message for the failing scenario. Strongly improves the report. |
| Model | `--model` | no | Claude model override. |
| Output path | `--output-file` | no | Defaults to `./hypotheses.md`. |

## Outputs

A markdown hypotheses report written to `--output-file` (default `./hypotheses.md`). The runner prints the path on success. Read that file back and surface the hypotheses to the user.

## Invocation

The user says something like *"the routing eval is failing on scenario 107, run agent-researcher on it."* Claude Code runs:

```bash
python3 ${CLAUDE_SKILL_DIR}/runner.py \
    --target-agent ./reference_agent \
    --eval-result ./reference_agent/evals/routing/last_run.json \
    --scenario-id 107 \
    --scenario-input-file ./scenario_107.txt \
    --output-file ./hypotheses_107.md
```

Then read `./hypotheses_107.md` and present the hypotheses, each with its layer, `file:line` citation, proposed edit, and verification step.

See [examples/usage.md](examples/usage.md) for a worked example.

## What this skill does not do

- It does not apply edits or re-run the eval. That is the CLI's `apply` / `iterate`; not wrapped here.
- It does not invent hypotheses itself — it relays what the CLI produced.
- It does not choose which hypothesis is correct. A human decides what to apply.
