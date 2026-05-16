# funnel-researcher — worked example

## What the user says

> Our activation funnel shows 70% of developers who create an API key never
> make a successful first API call. The funnel and dropoff numbers are in
> `./funnel.yaml` and `./dropoff_data.json`; the product docs and SDK are
> under `./product_artifacts`. Run funnel-researcher on the first-call step.

## What Claude Code does

```bash
python3 ${CLAUDE_SKILL_DIR}/runner.py \
    --funnel ./funnel.yaml \
    --dropoff ./dropoff_data.json \
    --product ./product_artifacts \
    --output-file ./funnel-hypotheses.md
```

The runner validates the two files and the product directory exist and that
`funnel-researcher` is on PATH, then shells out to `funnel-researcher
diagnose`. On success it prints:

```
./funnel-hypotheses.md
```

## What Claude Code shows back

Claude Code reads `./funnel-hypotheses.md` and summarizes:

> `funnel-researcher` produced 3 hypotheses for the create-key → first-call
> dropoff (70%):
>
> 1. **[Docs/Context]** `docs/quickstart.md:48` — the quickstart's first
>    `curl` example uses `agent_id=YOUR_AGENT_ID` as a literal placeholder
>    with no preceding step that creates an agent, so copy-paste returns
>    `MISSING_AGENT_ID`. This is the 70% step. Proposed edit: insert the
>    create-agent call before the first request.
> 2. **[API/SDK surface]** `errors/catalog.md:23` — `MISSING_AGENT_ID` is
>    documented only in the error catalog, not linked from the quickstart, so
>    a developer who hits it has no recovery path. Proposed edit: add a
>    remediation pointer.
> 3. **[Workflow/Sequence]** `sdk/client.py:112` — the SDK constructor accepts
>    a key but defers agent resolution to first call, so the failure surfaces
>    late and far from the cause. Proposed edit: validate agent on init.
>
> Full report with structured edits at `./funnel-hypotheses.md`. Nothing has
> been applied.
