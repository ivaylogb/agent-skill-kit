# compare-agents

Compare a candidate agent against the reference agent (`issue-triage`) and produce a structured audit report. The audit catalogues gaps the candidate has that the reference does not, and flags shared gaps where the reference is also incomplete.

## When to invoke

When a new agent is up and you want to know how far it is from the reference. Specifically:

- A new agent has been added under any directory mirroring the reference's shape (manifest, `prompts/`, `tools/`, `evals/`, `fixtures/`).
- A pull request adds a new agent and you want a structural review before code-review begins.
- An existing agent has accumulated changes and you want to check whether it has drifted away from the reference.

If the candidate doesn't have a manifest at all, this skill does not apply — that's a `routine-to-yaml` problem, not a comparison problem.

## Goal

Surface gaps in the candidate that, if not addressed, would prevent it from being production-ready. The audit is *not* a pass/fail verdict. It's a structured list of findings with severity, so a human can decide what to fix first.

The audit must be **honest about shared gaps**. If the reference is also `not_measured` for quality evals, do not flag the candidate's missing quality eval as a candidate-specific issue — flag it as a shared gap.

## How to do this

1. **Read `docs/claude/reference-agent.md`** to ground yourself in what "good" looks like.
2. **Read `reference_agent/agent.yaml`** for the reference's structural baseline.
3. **Read the candidate's `agent.yaml`** at the path the user provides.
4. **Walk the comparison dimensions below.** For each, classify findings as `Critical`, `Important`, `Nit`, or `Shared gap`.
5. **For each finding, name the specific file and line where the gap is visible.** "Tool descriptions are weak" is not a finding. "`tools/github_search.py` line 9: description is 8 words, no when-not-to-use guidance" is a finding.
6. **Write the audit using the format below.**

## Comparison dimensions

**Manifest structure.** Reference: in_scope ∋ {bug, feature, docs}, out_of_scope ⊇ {security, paid_support, code_review}, `routing.confidence_threshold` set. Check the candidate's manifest against each. *Security in `in_scope` is always Critical.*

**Prompt completeness.** Reference has: `system.j2`, `classification.j2`, three flow prompts, `handoff.j2`. Check which prompts the candidate has and which are missing.

**Prompt structure.** Each flow prompt should: (a) contain the issue content via Jinja substitution, (b) explicitly handle tool failure modes, (c) describe what the flow does NOT do. Check each candidate flow prompt for these.

**Tool design.** Each tool definition should: (a) describe what the tool does, (b) describe when *not* to use it, (c) describe output shape including error cases, (d) have parameter descriptions that include valid values and edge cases. Check each candidate tool against these.

**Eval coverage.** The reference has a working routing eval. Quality and regression are `not_measured` in both. If the candidate has *fewer* eval files than the reference (no working routing eval), that's a candidate gap. If both are `not_measured` for the same eval, that's a shared gap.

**Manifest-code consistency.** The manifest's prompt versions must match the actual `version: N` comment in each `.j2` file. The manifest's tool versions must match the tools' definition. Check for drift.

## Output format

```markdown
# Comparison: <candidate name> vs. issue-triage

## Summary

<2-3 sentences. Lead with the highest-severity finding. State the count of findings by severity.>

## Critical findings

### 1. <Short title>
**Where:** <file:line>
**What:** <2-3 sentences explaining the gap>
**Why it matters:** <1-2 sentences on the production consequence>
**Reference behavior:** <what issue-triage does in this dimension>

(repeat for each Critical)

## Important findings

(same structure)

## Nits

(same structure, can be terser)

## Shared gaps with the reference

<Findings where the candidate AND the reference are both incomplete. These are not the candidate's fault but worth surfacing.>

## What I read

<List of files read in the order read. For reviewer trust.>
```

## Self-check before completing

Before signaling done, verify:

- [ ] I read `docs/claude/reference-agent.md` and `reference_agent/agent.yaml` in this session.
- [ ] I read every `*.j2`, every `*.py` in `tools/`, and the `agent.yaml` in the candidate.
- [ ] Every finding (Critical, Important, Nit) has a specific file:line reference.
- [ ] Shared gaps are in their own section, not mixed with candidate-specific findings.
- [ ] If `agent.yaml` lists `intents.in_scope` containing `security`, I flagged it as Critical. (Single most important check.)
- [ ] If routing has no `confidence_threshold`, I flagged it as Critical.
- [ ] If any tool description is under 200 chars, I noted it.
- [ ] Summary at the top includes the count of findings by severity.

If any of these is no, complete them before producing the final audit.

## What this skill does not do

- It does not fix the gaps. It surfaces them.
- It does not run the candidate to test runtime behavior. (That's what evals do.)
- It does not re-derive what "good" means — it uses the reference as ground truth. If the reference is wrong, the audit will be wrong in the same direction. Update the reference first.

## Common failure modes for this skill

- **Treating shared gaps as candidate-specific.** If the reference has `quality.status: not_measured`, do not flag the candidate's `quality.status: not_measured` as a problem. The reference is the standard.
- **Vague findings.** "Tool descriptions could be better" is not actionable. Always cite the specific file and what specifically is missing.
- **Missing the security-in-scope flaw.** This is the single highest-impact misconfiguration in the candidate's class. Always check `intents.in_scope` first.
- **Running out of comparison dimensions.** If you've only flagged manifest issues, you haven't checked prompts and tools. The audit should typically have findings across at least 3 dimensions.
