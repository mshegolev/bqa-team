# BQA-OS Real Project Pilot Flow

## Safe Pilot Position

Use `bqa-os` on real internal projects in local-first, read-only-by-default
mode. The current safe value is artifact generation and human review, not
unattended production execution.

## First Run Pattern

```bash
cd /path/to/real-test-project
bqa init
bqa ingest --local --global=false
bqa build
```

Then inspect:

- `.bqa/knowledge/`
- `.bqa/skills/`
- `.bqa/agents/`
- `.bqa/workflows/`
- `.bqa/registry/`

## Required Review

- Check generated files for secrets and private data before any sync.
- Keep generated `.bqa` state local unless the project explicitly wants to
  commit it.
- Prefer `.git/info/exclude` for checkout-local BQA state.

## Missing Wider-Rollout Gates

- A real `bqa doctor` health gate.
- A clearer pilot checklist in docs.
- More explicit dry-run behavior for real projects.
- Stronger validation around generated agents, skills, and workflows.

