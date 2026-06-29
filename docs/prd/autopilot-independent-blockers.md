# Autopilot Independent Blockers PRD

## Problem

When BQA Autopilot hits a blocked issue, it should keep making progress on unrelated work. A blocked issue should only stop issues that explicitly depend on that blocker.

Current behavior is too conservative:
- Default config stops the run after a blocked cycle.
- Normal `bqa:ready-dev` candidate selection does not apply blocked-dependency filtering.

## Goal

BQA Autopilot continues processing independent issues by default while skipping:
- issues labeled `bqa:blocked`
- issues already in dev, QA, business review, or done states
- issues whose body explicitly depends on a blocked issue

## Non-Goals

- No new dependency graph engine.
- No change to GitHub issue labels or status taxonomy.
- No automatic unblock/retry of blocked issues.

## Requirements

1. Default generated autopilot config sets `stop_on_fail` to `false`.
2. Candidate issue filtering uses one consistent path for both `--all-open` and `--issue-label bqa:ready-dev`.
3. A ready-dev issue depending on a blocked issue is skipped.
4. A ready-dev issue independent of blockers remains eligible.
5. Operators can still force stop-on-fail behavior from config or CLI.
6. README documents the default behavior and override.

## Verification

- Unit test proves the default config continues on blocked cycles.
- Unit test proves label-filtered candidate selection skips blocked dependencies.
- Full `make verify` passes.
