# Business Task: Codex Team Pipeline MVP

Create a scripted workflow where business tasks are transformed into GitHub issues, routed through architecture review, implemented by role-specific Codex agents, checked by QA, and finally sent to business acceptance.

Expected workflow:

```text
business task
  -> architect
  -> GitHub issue
  -> developer
  -> PR
  -> QA
  -> bug if failed
  -> business acceptance
```

Constraints:
- dry-run by default;
- mutating actions require `--execute`;
- no unbounded autonomous loops;
- every task must remain reviewable by a human.
