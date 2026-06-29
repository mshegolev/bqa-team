# BQA-OS Project Profile

## Purpose

`bqa-os` is the Go/Cobra CLI runtime for BQA workflows. It provides local
project discovery, session ingestion, knowledge extraction, demo archive
generation, runtime adapters, and BQA Brain connectivity.

## Current Brain Commands

```bash
bqa brain connect <repo-url>
bqa brain pull
bqa brain status
bqa brain sync --sanitize
```

## Memory Goals

Store sanitized memory about:

- implemented BQA-OS features;
- project profiles and runtime commands;
- reusable QA and ETL patterns;
- unified agents, skills, workflows, and guardrails;
- known integration gotchas and validation commands.

## Integration Rule

Use `bqa-team/scripts/bqa_brain_export.sh` to populate unified artifacts, then
use `bqa brain sync --sanitize` from `bqa-os` to commit and push the brain cache.
