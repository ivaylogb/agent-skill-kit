# Example outputs

Pre-computed outputs of the skills, run against the broken candidate or the reference agent. Captured here so a reader can see what each skill produces without running it.

| File | What it shows |
|------|---------------|
| `compare-agents-output.md` | `compare-agents` run on the broken candidate against the reference. Surfaces 2 Critical, 5 Important, 1 Nit, 2 Shared. |
| `tool-description-audit-broken.md` | `tool-description-audit` on the broken candidate's tools. Both fail. |
| `tool-description-audit-reference.md` | `tool-description-audit` on the reference agent's tools. All pass. |

These outputs are illustrative. Actual runs against the same files will produce close-but-not-identical results — file:line references are accurate, severity grading is consistent, but exact wording will vary.
