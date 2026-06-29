# Autopilot History Ledger PRD

## Research Inputs

Similar agentic coding systems expose durable run artifacts:
- OpenHands positions Agent Canvas as an always-on engineering control center for agents and automations, including integrations with GitHub/Jira/Slack and multi-backend execution.
- SWE-agent writes trajectory JSON files with action, observation, state, and query data so a run can be inspected after the fact.
- AutoGen team runs expose stop reasons and streamable team messages, which makes multi-agent behavior debuggable.
- GitHub Copilot cloud agent emphasizes issue-to-PR agent sessions and reviewable agent output inside the GitHub workflow.

Source links:
- https://docs.openhands.dev/overview/introduction
- https://swe-agent.com/latest/usage/trajectories/
- https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/teams.html
- https://docs.github.com/en/copilot/concepts/agents/cloud-agent/about-cloud-agent

## Problem

BQA Autopilot currently writes a status snapshot and per-role output files, but it does not keep a compact append-only history of each autopilot cycle. Operators can see the current state, but reconstructing what happened across a long run requires reading logs and many generated output files.

## Goal

Add a structured JSONL history ledger for autopilot cycles:
- one line per cycle
- append-only
- safe for long-running `nohup` runs
- easy to parse by scripts or future dashboards

## Requirements

1. Write `.bqa-team/status/autopilot-history.jsonl`.
2. Each cycle entry includes `timestamp`, `repo`, `cycle`, `total_cycles`, `status`, and `processed_this_run`.
3. When an issue is selected, include `issue`, `title`, `branch`, `subagent`, and `route_reason`.
4. When a PR is found, include `pr`.
5. When a cycle blocks, include a stable `stop_reason`.
6. README documents where the ledger is written and what it is for.

## Non-Goals

- No full prompt/response capture.
- No replacement for detailed role output files under `.bqa-team/generated/runs`.
- No new dependency or database.

## Verification

- Unit test proves a processed cycle appends issue/branch/PR/route metadata.
- Unit test proves a blocked cycle appends `stop_reason`.
- Full `make verify` passes.
