# agent-skill-kit

Claude Code skills for shipping production-grade agents. A reference agent, a set of audit skills, and the conventions that hold them together.

## What's here

| | |
|---|---|
| **Reference agent** (`reference_agent/`) | A working `issue-triage` agent — open-source library maintainer assistant. Other agents are compared against it. |
| **Skills** (`.claude/skills/`) | `review-agent-pr`, `compare-agents`, `tool-description-audit`. Invoked from Claude Code. |
| **Broken candidate** (`examples/broken_candidate/`) | A second agent with deliberate flaws. Used in the example outputs to show what the skills find. |
| **Example outputs** (`examples/outputs/`) | What each skill produces when run against the broken candidate. |
| **Conventions** (`docs/claude/`) | Reference-agent spec and shared docs the skills read. |

## Why

Most agent work is repetitive: reviewing prompt changes, comparing new agents against working ones, scaffolding evals, sanity-checking routing. The skills here encode the parts I do most often. They read the actual codebase, not cached assumptions.

## Design principles

The skills follow four rules. New skills should too.

**Skills over commands.** Capabilities live as `.claude/skills/<name>/SKILL.md`. Skills are discoverable, composable, and auto-load. Slash commands are not.

**Thin orchestrators.** Each `SKILL.md` is 70–130 lines. Templates go in `helpers/`. Conventions go in `docs/claude/*.md`. The skill reads docs on demand instead of inlining content.

**Goal-oriented, not prescriptive.** Skills state the goal and the validation criteria. They let Claude Code read the actual codebase. Pinning to specific lines or function names makes skills brittle.

**Self-reference checks.** Each skill ends with a checklist Claude runs against its own output before signaling completion. Catches the "looked thorough but missed the obvious thing" failure.

## The skills

| Skill | Purpose |
|-------|---------|
| `review-agent-pr` | Walks a PR diff against repo conventions. Catches routing bugs, scope drift, missing eval coverage, implicit migrations. |
| `compare-agents` | Structural diff of a candidate against the reference agent. Surfaces gaps in handoff context, error handling, eval coverage, tool design. |
| `tool-description-audit` | Audits tool descriptions for clarity, when-not-to-use guidance, output shape, and parameter docs. Standalone — runs on any tool. |

See [`examples/outputs/`](examples/outputs/) for what each produces against a real candidate.

## How they compose

The skills aren't islands.

- **Reviewing a change.** PR touches an agent → `review-agent-pr` flags a routing concern → `compare-agents` shows what the change does to the gap-from-reference.
- **Onboarding a new agent.** New agent stood up → `compare-agents` surfaces missing patterns → `tool-description-audit` cleans up the tools.
- **Pre-merge gate.** Before merging, run `tool-description-audit` on any modified tools and `compare-agents` to confirm no regression against the reference.

The connective tissue is `docs/claude/*.md`. Skills read these on demand. When a convention changes, the docs change. The skills don't.

## The reference agent

`reference_agent/issue-triage` — open-source library maintainer assistant. In-scope: bug reports, feature requests, doc questions. Out-of-scope: security disclosures, paid-support, code-review. Demonstrates calibrated routing, graceful degradation, structured handoff, and eval coverage.

It's the gold standard `compare-agents` checks against. Spec lives in [`docs/claude/reference-agent.md`](docs/claude/reference-agent.md).

Run it:

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...

python -m reference_agent.runner --issue 101 --show-trace   # bug
python -m reference_agent.runner --issue 104 --show-trace   # security — must escalate
python -m reference_agent.runner --issue 107 --show-trace   # ambiguous — must escalate as unknown

python -m reference_agent.evals.routing.run_eval            # routing accuracy
```

## Roadmap

Skills I haven't built yet, in rough order of leverage:

1. `eval-failure-triage` — given a batch of eval failures, classify root cause: prompt issue, tool misuse, judge miscalibration, data issue, environmental flake.
2. `judge-calibration` — runs the LLM-as-judge calibration loop end-to-end.
3. `version-diff` — surfaces real semantic changes between agent versions, separated from cosmetic noise.
4. `rollout-readiness-check` — checks gates before production rollout (eval coverage, regression suite, monitoring hooks, etc.).
5. `scaffold-eval` — generates eval scaffolding from templates.

PRs welcome.

## Adoption

The repo-level skills are agent-agnostic by design. Anyone running Claude Code from inside this repo gets them automatically. Agent-specific context layers on top via nested `CLAUDE.md` files.

Pattern for adopting in your own repo:

1. Run the shared skills as-is from your repo root.
2. Add an agent-specific `CLAUDE.md` next to your agent's prompt directory for context (current phase, owner, test fixtures, known issues, active PRs).
3. If you find yourself repeating a check three times, promote it to a skill.

See [`EXTENDING.md`](EXTENDING.md) for adding a new agent to this kit.

## Related

Part of a set:

- [`agent-tool-kit`](https://github.com/ivaylogb/agent-tool-kit) — tool design patterns
- [`agent-context-kit`](https://github.com/ivaylogb/agent-context-kit) — context engineering and sub-agent isolation
- [`agent-eval-loop`](https://github.com/ivaylogb/agent-eval-loop) — simulate → evaluate → improve
- `agent-skill-kit` (this repo) — the methodology and audit skills

## License

MIT.
