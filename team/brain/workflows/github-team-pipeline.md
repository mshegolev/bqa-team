# GitHub Team Pipeline Workflow

## Purpose

Turn a business task into a reviewable GitHub issue, implementation PR, QA
result, and business acceptance decision.

## Flow

1. `init` - create `.bqa-team` local runtime directories.
2. `architect` - transform backlog markdown into issue specs.
3. `create-issues` - create GitHub issues when `--execute` is explicit.
4. `dev` - route an issue to a role-specific agent and open a PR.
5. `qa` - inspect PR diff and create or reuse QA-failure bugs.
6. `business-accept` - approve or request revision.
7. `autopilot` - repeat the loop with status, history, and blockers.

## Safety

- Dry-run is default.
- Mutating GitHub and git commands require `--execute`.
- `--stop-on-fail` is available for strict runs, but the default continues
  independent work while blocked issues remain blocked.
