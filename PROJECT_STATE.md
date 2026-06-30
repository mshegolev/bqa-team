# BQA Team Project State

Updated: 2026-06-30T19:02:12+04:00
Commit: `3bce397`
Branch: `main`
Remote: `origin/main`

## Current Status

`bqa-team` is finalized as a reusable team orchestration pack for `bqa-os` and
similar target repositories.

- Local checkout is clean.
- GitHub open PRs for `mshegolev/bqa-team`: 0.
- GitHub open issues for `mshegolev/bqa-team`: 0.
- Latest local verification: `make verify` passed with 73 tests.
- Latest known CI state on `main`: passing.

## Delivered Capabilities

- Operational foundation with `make test`, `make lint`, `make verify`, and CI.
- Team orchestrator for backlog, architecture review, GitHub issue creation,
  Codex development, PR creation, QA review, business acceptance, merge, and
  issue close.
- Autopilot with bounded runs, issue routing, status snapshots, append-only
  history ledger, project HTML view, and blocked-dependency filtering.
- Autopilot wrapper with start, status, logs, stop, stale PID cleanup,
  heartbeat checks, process-tree stop, and immediate-exit retry handling.
- QA failure handling that isolates source issues, de-duplicates PR-specific
  bugs, caps bug bodies, strips prompt echo, and clears active labels when
  blocking work.
- Runtime safety: fail-fast behavior for Codex/runtime command errors,
  timeout handling, Definition of Done, security requirements, consent checks,
  drift guardrails, and DevSecOps scan helper.
- Testing-only target runner for safe validation tasks.
- Synthetic demo archive fixture and browser-only static demo upload flow.
- Sales pilot package: one-pager, demo script, discovery call script,
  onboarding checklist, outreach snippets, pricing hypothesis, and FAQ.
- Unified BQA Brain registry/export with agents, skills, workflows, guardrails,
  project profiles, and memory source artifacts.
- BQA Brain integration docs for exporting `bqa-team` artifacts and syncing
  through `bqa-os`.

## Important Files

- `README.md` - operator guide and command reference.
- `docs/ROADMAP.md` - phase map for delivered work.
- `docs/APPLY_TO_TARGET_REPO.md` - how to apply the team pack to another repo.
- `docs/BQA_BRAIN_INTEGRATION.md` - BQA Brain export/sync runbook.
- `docs/SECURITY_REQUIREMENTS.md` - runtime and data-safety rules.
- `team/DEFINITION_OF_DONE.md` - quality gate for autopilot work.
- `team/brain/registry.json` - unified Brain registry.
- `scripts/bqa_team_orchestrator.py` - main orchestration engine.
- `scripts/bqa_autopilot.sh` - target-repo autopilot wrapper.
- `scripts/bqa_brain_export.sh` - unified Brain artifact exporter.

## Target Project Snapshot: bqa-os

`bqa-team` currently targets `/opt/develop/bqa-os` by default when the wrapper
is run from this checkout.

Current `mshegolev/bqa-os` backlog snapshot:

- Open issues: 32.
- Ready dev: 28.
- Needs architecture: 4.
- Blocked: 0.
- QA failed: 0.
- Open PRs: 0.

High-priority remaining target work:

- Architecture: `#16`, `#40`, `#59`, `#67`.
- Core reliability: `#23`, `#22`, `#14`, `#13`, `#20`.
- Brain/Codex integration: `#41`, `#49`.
- Pilot/demo/growth work: `#28`, `#48-#57`.
- Game polish: `#95`.

## Operating Notes

- Treat `.bqa-team/generated/`, `.bqa-team/logs/`, `.bqa-team/status/`, and
  `.bqa-team/state.json` as local runtime state unless a target repo explicitly
  chooses to version some of it.
- After changing runtime or autopilot code, run `make verify`, reinstall into
  the target repo with `scripts/install.sh`, then check the target autopilot
  process with `scripts/bqa_autopilot.sh status`.
- If a target autopilot PID is dead or stale, clear stale PID state and restart
  through `scripts/bqa_autopilot.sh start` from a normal user shell.
- Keep public examples synthetic. Do not commit private session logs, client
  data, credentials, or private Brain content.

## Latest Merged Work

- `#26` fix: avoid restarting completed autopilot runs.
- `#25` feat: add BQA Brain memory source artifacts.
- `#24` feat: add unified BQA Brain registry export.
- `#23` docs: add sales pilot package.
- `#22` test: cover security guardrails.
- `#21` test: add autopilot dry-run smoke.
- `#20` feat: add testing-only target runner.
- `#19` fix: retry autopilot startup after immediate exit.
- `#18` fix: clear active labels when blocking work.
- `#17` fix: dedupe QA failure bugs by PR.

