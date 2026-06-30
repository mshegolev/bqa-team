# Autopilot Operations Skill

## Purpose

Operate BQA Autopilot safely for a target repository while preserving progress,
status visibility, and recovery options.

## Standard Commands

```bash
scripts/bqa_autopilot.sh status
scripts/bqa_autopilot.sh start
scripts/bqa_autopilot.sh logs
scripts/bqa_autopilot.sh stop
```

## Operating Rules

- Check status before making runtime assumptions.
- Treat `.bqa-team/status/autopilot.pid`, `autopilot-heartbeat`, and
  `autopilot-history.jsonl` as the compact health view.
- If runtime code changed, verify whether the live process is stale before
  restarting.
- Do not restart a target repo while a dirty worktree or active child process
  indicates in-progress work.

## Recovery

- Dead PID: clear stale PID and start through the wrapper.
- Stale heartbeat without child work: restart through the wrapper.
- Runtime failure: inspect generated run output before changing labels or code.
