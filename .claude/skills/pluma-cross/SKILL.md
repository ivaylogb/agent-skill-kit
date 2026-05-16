---
name: pluma-cross
description: After running two or more of agent-researcher, funnel-researcher, or integration-watcher against the same product surface, run pluma-cross to report where those tools independently converge on the same defect. Thin wrapper around the installed `pluma cross` CLI, which runs the applicable tools (through its cache) and emits a correlation matrix plus the findings that appear in more than one tool.
when_to_use: The user wants to run two or more diagnostic tools against the same product surface and find where they independently agree. If the individual tools have already been run with identical inputs, `pluma cross` hits the cache and only runs the cross-match step at near-zero cost.
---

# pluma-cross

Shells out to the installed `pluma cross` CLI. Given the raw inputs for two or more sister tools — all pointing at the same `--product` — `pluma cross` runs each applicable tool through its input-hash cache, normalizes every report into a unified Finding shape, and emits one report: a correlation matrix (tool × layer), the findings that show up in **more than one** tool (mechanical match on overlapping `file:line`, or categorical match on shared layer + product file), then the findings unique to each tool. The cross-match logic lives in the CLI — `runner.py` only validates inputs and invokes it.

**This wraps the shipped `pluma cross` interface honestly.** It takes raw tool inputs and re-runs the tools; it does not consume pre-generated finding markdown. The cache is what makes re-runs cheap: if the user already ran a tool with the exact same inputs, that tool's run is a cache hit and spends no model tokens — only the tools whose inputs were not previously cached spend.

## Prerequisites

- The `pluma` CLI on PATH, plus the sister tools it routes to. Install from a clone of <https://github.com/ivaylogb/pluma> (and the tool repos it orchestrates):
  ```bash
  pip install -e .
  export ANTHROPIC_API_KEY=sk-ant-...
  ```
- `ANTHROPIC_API_KEY` set — any tool that is **not** a cache hit spends model tokens.

## Inputs

`--product` (required) and `--output-file` are passed through. Provide the input flags for **at least two** tools, all describing the same product:

| Tool | Flags (both required for that tool) |
|---|---|
| funnel-researcher | `--funnel` + `--dropoff` |
| integration-watcher | `--traces` + `--cohort` |
| agent-researcher | `--eval-result` + `--target-agent` |

Optional passthrough: `--model`, `--max-tokens`, `--extra-file` (repeatable), `--no-cache`, `--force`. Output path defaults to `./pluma-cross.md`. The runner refuses to invoke unless at least two complete tool input sets are present.

## Outputs

A markdown cross-tool report written to `--output-file` (default `./pluma-cross.md`). The runner prints the path on success. Read that file back and surface the correlation matrix and the cross-tool findings.

## Invocation

The user says something like *"I have funnel/dropoff data and a trace cohort for the same API — run both diagnostics and show me where they agree."* Claude Code runs:

```bash
python3 ${CLAUDE_SKILL_DIR}/runner.py \
    --product ./product_artifacts \
    --funnel ./funnel.yaml \
    --dropoff ./dropoff_data.json \
    --traces ./traces.jsonl \
    --cohort ./cohort.yaml \
    --output-file ./pluma-cross.md
```

If `funnel-researcher` and `integration-watcher` were already run on these exact inputs (e.g. via the other skills), this run is mostly cache hits — the convergence report comes back at near-zero cost. The two invocation patterns are shown in [examples/usage.md](examples/usage.md).

## What this skill does not do

- It does not consume pre-generated finding files. The shipped `pluma cross` takes raw inputs and runs the tools (cache-backed).
- It does not run `apply` / `iterate`. Those are separate `pluma` subcommands.
- It does not correlate findings itself — the CLI does the matching. The runner is a pure shell-out.
- It does not decide which converged finding to act on. A human decides.
