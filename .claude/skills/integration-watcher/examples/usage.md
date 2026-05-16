# integration-watcher — worked example

## What the user says

> I exported API traces from our beta cohort to `traces.jsonl`. The cohort
> definition and watch question are in `cohort.yaml` ("why do integrations
> stall after the first successful call?"). Product docs and SDK are under
> `./product_artifacts`. Run integration-watcher.

## What Claude Code does

```bash
python3 ${CLAUDE_SKILL_DIR}/runner.py \
    --traces ./traces.jsonl \
    --cohort ./cohort.yaml \
    --product ./product_artifacts \
    --output-file ./integration-findings.md
```

The runner validates the traces file, cohort YAML, and product directory
exist and that `integration-watcher` is on PATH, then shells out to
`integration-watcher watch`. On success it prints:

```
./integration-findings.md
```

## What Claude Code shows back

Claude Code reads `./integration-findings.md` and summarizes:

> `integration-watcher` produced 2 findings for the beta cohort:
>
> 1. **[Docs/Context]** `docs/streaming.md` — across 14 of 22 developers
>    (`dev_03`, `dev_07`, `dev_11`, …) the call sequence is: first call OK,
>    then a poll loop on `GET /runs/{id}` that never flips to streaming. The
>    streaming option is buried in an SDK docstring (`sdk/client.py:204`) and
>    absent from `docs/streaming.md`. Proposed edit: document `stream=True`
>    in the streaming page.
> 2. **[API/SDK surface]** `errors/catalog.md:51` — 9 developers retry the
>    same request after a `409 RUN_IN_PROGRESS` with no backoff and identical
>    params; the error body carries no `retry_after`. Proposed edit: add
>    `retry_after` to the 409 payload and document it.
>
> Full report with trace references and structured edits at
> `./integration-findings.md`. Nothing has been applied.
