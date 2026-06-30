# BQA-OS Workspace Jira Task Flow

## Product Direction

The desired workflow is a single command that accepts a Jira key and prepares
the rest of the QA/development workspace automatically.

Target shape:

```bash
bqa task start DATA-16154
```

## Expected Behavior

- Fetch Jira metadata for the task.
- Create or reuse a workspace and git worktree.
- Register task state under the shared `.bqa` workspace.
- Resolve context in this order: global, repo, ETL, task.
- Pick the right skills, agents, and workflows for the task.
- Open an interactive console with prepared context.

## Design Preference

Favor shared workspace orchestration over one full repo copy per ETL. Feature
issues should be command-shaped and practical, with concrete task lifecycle
commands such as start, status, and finish.

## GitHub Reference

The workspace/Jira-key feature request was captured as `mshegolev/bqa-os#67`.

