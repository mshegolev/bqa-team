# BQA-OS Capability Map

## Purpose

`bqa-os` is the local CLI/runtime that connects QA knowledge extraction,
project profiles, generated agents, skills, workflows, guardrails, and AI coding
runtimes such as Codex, Claude Code, and OpenCode.

## Current Command Surface

- `bqa init` creates a local `.bqa` workspace.
- `bqa discover` finds local AI coding session artifacts.
- `bqa ingest` and `bqa ingest2` normalize discovered session data.
- `bqa build` creates reusable QA knowledge artifacts from normalized sessions.
- `bqa sanitize` scans and redacts sensitive values in text files.
- `bqa brain connect`, `pull`, `status`, and `sync --sanitize` manage the
  git-backed BQA Brain repository.
- `bqa codex`, `bqa claude`, and `bqa opencode` prepare runtime-specific master
  agent context.
- `bqa runtime detect` reports installed runtime binaries.
- `bqa doctor`, `bqa run`, `bqa team`, `bqa etl-agent-pack`, and `bqa demo`
  cover health checks, local execution, team planning, ETL pack generation, and
  synthetic demo assets.

## Architecture Rules

- Keep Cobra command bodies thin.
- Put orchestration in `internal/app`.
- Put business logic in `internal/core`.
- Define interfaces in `internal/ports`.
- Implement filesystem and runtime details in adapters.
- Validate Go changes with `go test ./...`.

## Readiness Level

`bqa-os` is suitable for an internal, local-first pilot that generates and
reviews `.bqa` artifacts. It is not yet a fully mature autonomous QA runner.

