# pluma-cross — worked example

`pluma cross` runs the applicable tools through its input-hash cache. The
two patterns below differ only in whether those tools were already run on the
same inputs.

## Pattern 1 — fresh full run

### What the user says

> I have funnel/dropoff data and a trace cohort for the same API. I haven't
> diagnosed either yet. Run both and show me where they agree.

### What Claude Code does

```bash
python3 ${CLAUDE_SKILL_DIR}/runner.py \
    --product ./product_artifacts \
    --funnel ./funnel.yaml \
    --dropoff ./dropoff_data.json \
    --traces ./traces.jsonl \
    --cohort ./cohort.yaml \
    --output-file ./pluma-cross.md
```

The runner confirms two complete tool input sets (funnel-researcher,
integration-watcher), validates every path, and shells out to `pluma cross`.
Nothing is cached, so both tools run and spend model tokens. On success it
prints:

```
./pluma-cross.md
```

## Pattern 2 — re-run after the individual tools already ran

### What the user says

> I already ran funnel-researcher and integration-watcher on these exact
> inputs earlier. Now show me the convergence report.

### What Claude Code does

The invocation is identical:

```bash
python3 ${CLAUDE_SKILL_DIR}/runner.py \
    --product ./product_artifacts \
    --funnel ./funnel.yaml \
    --dropoff ./dropoff_data.json \
    --traces ./traces.jsonl \
    --cohort ./cohort.yaml \
    --output-file ./pluma-cross.md
```

Because the inputs hash-match the earlier runs, `pluma cross` reports both
tools as cache hits on stderr and only runs the cross-match step — near-zero
cost, no model spend. (Pass `--force` to re-run anyway, or `--no-cache` to
bypass the cache entirely.)

## What Claude Code shows back

Claude Code reads `./pluma-cross.md` and summarizes:

> `pluma cross` ran funnel-researcher and integration-watcher against
> `./product_artifacts` (both cache hits in pattern 2) and found **2
> cross-tool findings** — places both tools independently flagged:
>
> 1. `docs/quickstart.md:48` — funnel-researcher's create-key→first-call
>    dropoff hypothesis and integration-watcher's `MISSING_AGENT_ID` cluster
>    both cite the same placeholder-without-create-step defect (mechanical
>    match, overlapping line range).
> 2. **Docs/Context layer, `docs/streaming.md`** — both tools land on the
>    streaming option being undiscoverable (categorical match: shared layer +
>    product file).
>
> Plus the correlation matrix and each tool's unique findings. Full report at
> `./pluma-cross.md`. Nothing has been applied.
