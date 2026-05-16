---
name: integration-watcher
description: When a cohort of developer integrations against an API is producing traces, run integration-watcher to find patterns in how the integrations are getting stuck. Each finding cites trace evidence, product-surface evidence, and proposes a structured edit. Thin wrapper around the installed integration-watcher CLI; the CLI does the analysis.
when_to_use: The user has API call traces (JSONL), a cohort definition (YAML) with a watch question, and a directory of product artifacts (docs, SDK source, error catalog), and wants the patterns in how that cohort's integrations get stuck.
---

# integration-watcher

Shells out to the installed `integration-watcher` CLI to find patterns across a cohort's integration traces. It reads the trace stream, the cohort definition (including the watch question), and the product's artifacts, then produces a markdown findings report of 2–3 structurally distinct findings. Each finding is assigned to one layer (Trace definition, API/SDK surface, Docs/Context, Integration sequence), grounded in both trace evidence (`developer_id` + call sequence) and product evidence (`file:line`), and ships an applyable structured edit. No analysis logic lives in this skill — `runner.py` validates inputs and invokes the CLI.

## Prerequisites

- The `integration-watcher` CLI on PATH. Install from a clone of <https://github.com/ivaylogb/integration-watcher>:
  ```bash
  pip install -e .
  export ANTHROPIC_API_KEY=sk-ant-...
  ```
- `ANTHROPIC_API_KEY` set — `watch` spends model tokens.

## Inputs

| Input | Flag | Required | Notes |
|---|---|---|---|
| Trace stream | `--traces` | yes | JSONL of API-call traces across the cohort. |
| Cohort definition | `--cohort` | yes | YAML; includes the watch question. |
| Product artifact directory | `--product` | yes | Docs, SDK source, error catalog. |
| Extra artifact file | `--extra-file` | no | Repeatable; pulls in a file outside the product dir. |
| Model | `--model` | no | Claude model override. |
| Max tokens | `--max-tokens` | no | Output token cap. |
| Output path | `--output-file` | no | Defaults to `./integration-findings.md`. |

## Outputs

A markdown findings report written to `--output-file` (default `./integration-findings.md`). The runner prints the path on success. Read that file back and surface the findings to the user.

## Invocation

The user says something like *"the traces from our beta cohort are in `traces.jsonl` — run integration-watcher and tell me why so many integrations stall after the first call."* Claude Code runs:

```bash
python3 ${CLAUDE_SKILL_DIR}/runner.py \
    --traces ./traces.jsonl \
    --cohort ./cohort.yaml \
    --product ./product_artifacts \
    --output-file ./integration-findings.md
```

Then read `./integration-findings.md` and present each finding with its layer, the trace evidence (`developer_id` + call sequence), the `file:line` citation, and the proposed edit.

See [examples/usage.md](examples/usage.md) for a worked example.

## What this skill does not do

- It does not apply edits or run `iterate`. Those are CLI subcommands; not wrapped here.
- It does not find patterns itself — it relays what the CLI produced.
- It is not analytics, telemetry, or session replay. It surfaces structural patterns and traces them to product artifacts.
