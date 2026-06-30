# BQA-OS Brain Sync Contract

## Brain Repository

`mshegolev/bqa-brain` is the private git-backed memory store for sanitized BQA
knowledge.

## BQA-OS Responsibilities

- Connect to the brain repository.
- Pull/update the local brain cache.
- Sanitize cache contents before sync.
- Commit and push sanitized knowledge.
- Read registry metadata for future agent, skill, workflow, and project profile
  loading.

## BQA Brain Responsibilities

- Store generated agents, skills, workflows, guardrails, reusable memory,
  project profiles, sanitized session summaries, and registry metadata.
- Never store secrets, raw transcripts, raw logs, customer data, or production
  dumps.

## Current Commands

```bash
bqa brain connect https://github.com/mshegolev/bqa-brain.git
bqa brain pull
bqa brain status
bqa brain sync --sanitize
```

If the installed `bqa` binary does not support `--sanitize`, run from the
current `bqa-os` checkout:

```bash
cd /opt/develop/bqa-os
go run ./cmd/bqa brain sync --sanitize
```
