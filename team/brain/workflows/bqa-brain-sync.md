# BQA Brain Sync Workflow

## Purpose

Export unified BQA Team artifacts into a local BQA Brain cache and push sanitized
knowledge to the private `bqa-brain` repository.

## Flow

1. Connect `bqa-os` to the private brain repository.
2. Pull the local brain cache.
3. Export unified BQA Team artifacts with `scripts/bqa_brain_export.sh`.
4. Inspect the brain diff.
5. Sync with sanitizer enabled.

## Commands

```bash
bqa brain connect https://github.com/mshegolev/bqa-brain.git
bqa brain pull
/opt/develop/bqa-team/scripts/bqa_brain_export.sh --brain-dir "$HOME/.bqa/brain"
bqa brain sync --sanitize
```

## Rule

Only sanitized reusable knowledge belongs in the brain repository.
