# review-agent-pr

Review a PR that touches an agent (prompts, tools, configs, runners, evals) against the conventions in this repo.

## When to invoke

Whenever a PR modifies any file under an agent's directory. Specifically:

- `prompts/*.j2` changes
- `tools/*.py` changes
- `agent.yaml` changes
- `evals/**` changes
- New routing logic in classification prompts

If the PR only touches docs or non-agent code, this skill does not apply.

## Goal

Catch the class of bug that escapes human review and ships to production. The canonical example is a routing change that introduces an ambiguous classification path — humans see the diff, see the new path, and don't notice that an existing in-scope intent now matches two routes.

You are not approving or rejecting the PR. You are producing a structured review that a human reviewer uses to make the final call.

## How to do this

1. **Read `docs/claude/reference-agent.md`** to ground yourself in what "good" looks like.
2. **Read `docs/claude/pr-review-patterns.md`** for the specific heuristics this repo uses.
3. **Read the actual diff.** Do not rely on the PR description. Descriptions lie. Diffs don't.
4. **Walk the diff against the conventions in the reference agent doc.** For each changed file, ask:
   - Does the change preserve the production-ready properties? (calibrated routing, graceful degradation, visible reasoning, structured handoff, eval coverage, clean tool design)
   - Does it follow repo conventions for prompt structure, tool config, eval config, versioning?
   - Does it bump the relevant version in `agent.yaml`?
5. **For routing changes specifically, invoke `check-routing`** as a sub-task. Do not try to verify routing correctness inline — `check-routing` is more thorough.
6. **For tool changes specifically, invoke `tool-description-audit`** as a sub-task on the modified tools.
7. **Look for implicit migrations.** If the change requires existing data, configs, or downstream consumers to be updated, surface it explicitly. Implicit migrations are the second-most-common cause of production breakage after routing bugs.
8. **Write the review.** Use the format below.

## Output format

```markdown
# Review: <PR title>

## Summary

<2-3 sentence summary of what changes and the highest-priority concern, if any.>

## Conventions check

- [ ] Prompt component versions bumped where modified
- [ ] `agent.yaml` updated to reflect changes
- [ ] Eval coverage exists for new behavior
- [ ] Tool descriptions still pass audit (if tools touched)
- [ ] Routing still calibrated (if routing touched)
- [ ] No implicit migrations required

## Findings

### Critical
<Issues that should block merge. Include file:line references.>

### Important
<Issues that should be addressed but don't block. Include file:line references.>

### Nits
<Style / minor concerns. Optional to address.>

## Sub-task results

<If check-routing or tool-description-audit was invoked, summarize and link.>

## What I read
<List files read, in the order read. This is for reviewer trust, not for the author.>
```

## Self-check before completing

Before signaling done, verify:

- [ ] You read the actual diff, not just the PR description
- [ ] You read `reference-agent.md` and `pr-review-patterns.md` in this session
- [ ] If routing changed, you invoked `check-routing`
- [ ] If tools changed, you invoked `tool-description-audit`
- [ ] Every "Critical" or "Important" finding has a file:line reference
- [ ] You can name the specific convention each finding violates
- [ ] You looked for implicit migrations explicitly

If any of these is no, complete them before producing the final review.

## What this skill does not do

- It does not approve or merge PRs. Humans decide.
- It does not rewrite the code. It surfaces issues.
- It does not enforce style preferences that aren't conventions in this repo.
- It does not block on missing tests for unchanged behavior. New behavior needs evals; refactors don't.

## Common failure modes for this skill

- **Reading the description instead of the diff.** PRs are often described aspirationally. Always read the diff.
- **Missing routing changes hidden in classification prompts.** Routing logic lives in `classification.j2` more than in code. A wording change in the classification prompt is a routing change.
- **Approving an "obvious" fix without checking eval coverage.** The fix might be correct; the lack of regression test means it'll come back.
- **Letting tone of the PR description anchor the review.** "Trivial cleanup" PRs are how production-breaking changes ship.
