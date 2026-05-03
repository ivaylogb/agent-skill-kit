# Extending the kit

How to add a new agent, a new skill, or a new convention.

## Add a new agent

Agents in this kit live in their own top-level directory and share the same shape:

```
your_agent/
├── README.md
├── agent.yaml          # Manifest. Skills read this.
├── runner.py           # Agent loop.
├── prompts/            # Jinja2 templates with version comments.
├── tools/              # One module per tool, exposing `definition` + `call`.
├── evals/
│   ├── routing/
│   ├── quality/
│   └── regression/
└── fixtures/           # Test data.
```

### Steps

1. **Copy the reference agent's shape.** `cp -r reference_agent/ your_agent/`. Then strip the issue-triage-specific content out.

2. **Update `agent.yaml`.** Set `agent`, `version: 1`, your model, your in-scope and out-of-scope intents. Keep `routing.confidence_threshold: 0.7` unless you have a calibrated reason to change it.

3. **Write your prompts.** Each `.j2` file starts with `{# version: 1 #}`. Bump the version when you edit. Match the structure of the reference's prompts: classification returns intent + confidence, flow prompts handle one intent each, handoff produces structured escalation.

4. **Write your tools.** Each `tools/<name>.py` exposes a `definition` dict and a `call` function. Keep them separated so `tool-description-audit` can read definitions without executing tools.

5. **Build a routing eval first.** Create `evals/routing/golden.jsonl` with 10–50 examples covering in-scope, out-of-scope, and ambiguous cases. Aim for the threshold in your manifest (0.90 by default).

6. **Run `compare-agents`** against your new agent. Fix what it finds. Iterate.

7. **Run `tool-description-audit`** on `your_agent/tools/`. Fix what it finds.

The first agent takes the longest. Once the shape is in your hands, subsequent agents are mostly content.

## Add a new skill

Skills live in `.claude/skills/<name>/SKILL.md`. One file per skill.

### Anatomy of a skill

```markdown
# <skill-name>

<One-paragraph description.>

## When to invoke
<Concrete triggers.>

## Goal
<What success looks like.>

## How to do this
<Numbered steps. Each step is goal-oriented, not prescriptive.>

## Output format
<Structured output spec.>

## Self-check before completing
<Checklist Claude runs against its own output.>

## What this skill does not do
<Out of scope.>

## Common failure modes for this skill
<Things that go wrong.>
```

### Rules

- **70–130 lines.** If yours is longer, the skill is doing too much. Split it.
- **Goal-oriented, not prescriptive.** Pin to outcomes, not line numbers. Files move; outcomes don't.
- **Read shared docs on demand.** If your skill needs to reference a convention, link it in `docs/claude/*.md` and have the skill read it. Don't inline.
- **Self-reference checks are mandatory.** Every skill ends with a checklist that catches the "looked thorough but missed the obvious" failure.

## Add a new convention

If multiple skills need to reference the same rule, the rule belongs in `docs/claude/<name>.md`. Skills read it on demand.

When you're tempted to copy a paragraph between two skills, write it once in `docs/claude/` and have both skills read it instead.

## When to promote

If you find yourself running the same Claude Code prompt three times, promote it to a skill.

If you find yourself referencing the same convention in three skills, promote it to a `docs/claude/` doc.

If you find yourself building the same eval scaffolding in three agents, promote it to a `helpers/` template that `scaffold-eval` (when built) can stamp out.
