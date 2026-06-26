# BQA Issue Spec Template

Use this template for developer-ready tasks.

## Title

Short task name.

## Context

Why this task exists and which workflow it supports.

## Goal

What should work after this task.

## Scope

### Create/change

- `internal/...`
- `site/...`
- `docs/...`

### Do not touch

- private repo data
- real session logs
- secrets
- unrelated code

## Architecture

Follow:

core use case
↓
port interface
↓
adapter implementation
↓
CLI wiring

Cobra must stay thin.

## Behavior

Expected behavior.

## Acceptance criteria

- [ ] Works on synthetic data.
- [ ] Does not require private data.
- [ ] Does not break existing commands.
- [ ] Has tests where reasonable.
- [ ] `go test ./...` passes when Go code changes.
- [ ] Errors are clear and actionable.

## Manual verification

```bash
go test ./...
go run ./cmd/bqa <command>
```

## Expected output

Describe stdout and generated files.

## Notes for developer

Additional constraints or hints.
