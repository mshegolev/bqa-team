# BQA Team Autopilot Operations

## Runtime Target

`bqa-team` can operate the `bqa-os` GitHub issue pipeline through
`scripts/bqa_autopilot.sh` and `scripts/bqa_team_orchestrator.py`.

## Operational Rules

- After substantial runtime/autopilot changes, check whether the target-project
  autopilot process is still running old code.
- If the process is dead, stale, or idle beyond the stale threshold, clear stale
  PID state and restart through the wrapper.
- Continue independent issues when some tasks are blocked; do not stop the whole
  queue for unrelated blockers.
- Use labels to separate ready-dev, in-dev, ready-qa, ready-business, blocked,
  and done states.

## Commands

```bash
scripts/bqa_autopilot.sh status
scripts/bqa_autopilot.sh start
scripts/bqa_autopilot.sh stop
```

When run from `bqa-team`, the wrapper targets the sibling `bqa-os` checkout by
default.

## Verification

- `make verify` validates the local `bqa-team` automation tests.
- Check live process state with `ps -p <pid> -o pid,stat,etime,command`.
- Check recent activity with the target log under
  `.bqa-team/logs/autopilot.log`.

