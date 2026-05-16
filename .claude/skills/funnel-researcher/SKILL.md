---
name: funnel-researcher
description: When a developer-facing API has a funnel showing dropoff at a specific step, run funnel-researcher to produce hypotheses about why developers stall at that step. Each hypothesis cites a specific location in the product's docs, SDK, or error catalog and proposes a structured edit. Thin wrapper around the installed funnel-researcher CLI; the CLI does the diagnosis.
when_to_use: The user has a developer-API onboarding funnel (defined as YAML), dropoff data per step, and a directory of product artifacts (docs, SDK source, error catalog), and wants to know why developers fall off at a target step.
---

# funnel-researcher

Shells out to the installed `funnel-researcher` CLI to diagnose developer dropoff at a funnel step. It reads the funnel definition, the per-step dropoff data, and the product's artifacts, then produces a markdown report of 2–3 structurally distinct hypotheses. Each hypothesis is assigned to one layer (Funnel definition, API/SDK surface, Docs/Context, Workflow/Sequence), grounded in both a specific dropoff signal and a `file:line` citation into the product surface, and ships an applyable structured edit. No diagnostic logic lives in this skill — `runner.py` validates inputs and invokes the CLI.

## Prerequisites

- The `funnel-researcher` CLI on PATH. Install from a clone of <https://github.com/ivaylogb/funnel-researcher>:
  ```bash
  pip install -e .
  export ANTHROPIC_API_KEY=sk-ant-...
  ```
- `ANTHROPIC_API_KEY` set — `diagnose` spends model tokens.

## Inputs

| Input | Flag | Required | Notes |
|---|---|---|---|
| Funnel definition | `--funnel` | yes | YAML defining the funnel steps. |
| Dropoff data | `--dropoff` | yes | JSON with per-step dropoff numbers. |
| Product artifact directory | `--product` | yes | Docs, SDK source, error catalog. |
| Extra artifact file | `--extra-file` | no | Repeatable; pulls in a file outside the product dir. |
| Model | `--model` | no | Claude model override. |
| Max tokens | `--max-tokens` | no | Output token cap. |
| Output path | `--output-file` | no | Defaults to `./funnel-hypotheses.md`. |

## Outputs

A markdown hypotheses report written to `--output-file` (default `./funnel-hypotheses.md`). The runner prints the path on success. Read that file back and surface the hypotheses to the user.

## Invocation

The user says something like *"developers are dropping off at the first-API-call step of the activation funnel — run funnel-researcher against the product docs."* Claude Code runs:

```bash
python3 ${CLAUDE_SKILL_DIR}/runner.py \
    --funnel ./funnel.yaml \
    --dropoff ./dropoff_data.json \
    --product ./product_artifacts \
    --output-file ./funnel-hypotheses.md
```

Then read `./funnel-hypotheses.md` and present each hypothesis with its layer, the dropoff signal it explains, its `file:line` citation, and the proposed edit.

See [examples/usage.md](examples/usage.md) for a worked example.

## What this skill does not do

- It does not apply edits or run `iterate`. Those are CLI subcommands; not wrapped here.
- It does not invent hypotheses itself — it relays what the CLI produced.
- It does not decide which hypothesis is correct. A human picks what to apply.
