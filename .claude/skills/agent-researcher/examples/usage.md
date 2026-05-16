# agent-researcher — worked example

## What the user says

> The routing eval just failed on scenario 107 — a security disclosure that
> got classified as a bug report instead of escalating. Run agent-researcher
> on it against `reference_agent`.

## What Claude Code does

The failing run is at `reference_agent/evals/routing/last_run.json`. The
scenario's user message is captured to `scenario_107.txt`. Claude Code
invokes the skill runner:

```bash
python3 ${CLAUDE_SKILL_DIR}/runner.py \
    --target-agent ./reference_agent \
    --eval-result ./reference_agent/evals/routing/last_run.json \
    --scenario-id 107 \
    --scenario-input-file ./scenario_107.txt \
    --output-file ./hypotheses_107.md
```

The runner validates the directory and JSON exist and that `agent-researcher`
is on PATH, then shells out to `agent-researcher diagnose`. On success it
prints:

```
./hypotheses_107.md
```

## What Claude Code shows back

Claude Code reads `./hypotheses_107.md` and summarizes:

> `agent-researcher` produced 3 hypotheses for scenario 107:
>
> 1. **[Context]** `prompts/classification.j2:14` — the classification prompt
>    enumerates bug/feature/docs but never names security as an escalate-only
>    intent, so a vulnerability report falls through to `bug`. Proposed edit:
>    add a security disambiguation line. Verify: re-run scenario 107; expect
>    `escalate`.
> 2. **[Evaluation]** `evals/routing/golden.jsonl:41` — the golden label for
>    107 is `bug`, which encodes the wrong expectation. Proposed edit: relabel
>    to `escalate`. Verify: re-run the routing eval; the scenario should pass.
> 3. **[Tools]** `tools/github_issues.py:9` — the issue-fetch tool description
>    gives no when-not-to-use guidance, so the model treats every input as a
>    triageable issue. Proposed edit: add a "do NOT use for security
>    disclosures" clause. Verify: re-run 107 with trace; the tool should not
>    be called.
>
> Full report with structured edits at `./hypotheses_107.md`. Nothing has
> been applied — pick a hypothesis to act on.
