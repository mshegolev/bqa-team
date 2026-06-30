# BQA Brain Integration For BQA-OS

## What Exists Now

GitHub repository:

```text
git@github.com:mshegolev/bqa-brain.git
```

The repository is a private git-backed memory store. Its current contract keeps
generated agents, skills, workflows, guardrails, project profiles, sanitized
session summaries, and registry metadata.

`bqa-os` already has BQA Brain commands:

```bash
bqa brain connect <repo-url>
bqa brain pull
bqa brain status
bqa brain sync --sanitize
```

If `bqa brain sync --sanitize` reports `unknown flag: --sanitize`, the `bqa`
binary in `PATH` is older than the current `/opt/develop/bqa-os` checkout. Use
the checkout directly until the local binary is rebuilt:

```bash
cd /opt/develop/bqa-os
go run ./cmd/bqa brain sync --help
go run ./cmd/bqa brain sync --sanitize
```

## Unified Source Of Truth

`bqa-team` owns the unified team artifact registry:

```text
team/brain/registry.json
```

Every exported artifact has the same fields:

- `id`
- `type`
- `title`
- `source`
- `destination`
- `summary`
- `tags`

The supported artifact types are:

- `agent`
- `skill`
- `workflow`
- `guardrail`
- `project_profile`
- `memory_index`

## Install For `/opt/develop/bqa-os`

From the `bqa-os` checkout:

```bash
cd /opt/develop/bqa-os
bqa brain connect git@github.com:mshegolev/bqa-brain.git
bqa brain pull
bqa brain status
```

By default, current `bqa-os` stores the brain cache at:

```text
$HOME/.bqa/brain
```

## Export Unified Team Artifacts

From `bqa-team`:

```bash
cd /opt/develop/bqa-team
scripts/bqa_brain_export.sh --brain-dir "$HOME/.bqa/brain"
```

This writes:

- `agents/*.md`
- `skills/*.md`
- `workflows/*.md`
- `guardrails/*.md`
- `project-profiles/*.md`
- `memory/*.md`
- `registry/bqa_registry.yaml`

Each exported file includes a `BQA_UNIFIED_ARTIFACT` header so future tooling can
trace it back to `team/brain/registry.json`.

## Sync To Git-Backed Brain Memory

Inspect the brain diff first:

```bash
git -C "$HOME/.bqa/brain" status --short
git -C "$HOME/.bqa/brain" diff --stat
```

Then sync through `bqa-os` with sanitization:

```bash
cd /opt/develop/bqa-os
bqa brain sync --sanitize
```

## What To Store

Store only reusable, sanitized knowledge:

- implemented BQA-OS features and commands;
- project profiles and known validation commands;
- unified agents, skills, workflows, guardrails, and memory indexes;
- sanitized lessons from completed runs.

Do not store:

- secrets or tokens;
- raw customer data;
- production dumps;
- unsanitized logs;
- full private transcripts;
- unrelated product source dumps.

## Verification

For `bqa-team`:

```bash
python3 -m unittest tests.test_bqa_brain_registry -v
make verify
```

For `bqa-os`, after export and sync setup:

```bash
cd /opt/develop/bqa-os
bqa brain status
go test ./...
```
