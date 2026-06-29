# BQA Team Roadmap

This roadmap maps the current business backlog into delivery phases. The local verification contract is `make verify`; every phase should keep that command green before work is considered ready.

## Phase 1: Operational Foundation

Goal: make the repository easy to verify locally and in CI before larger product work starts.

Inputs:
- `team/backlog/003_codex_team_pipeline.md`

Deliverables:
- `Makefile` with `test`, `lint`, and `verify`.
- GitHub Actions workflow that runs `make verify`.
- Roadmap and hygiene checks that keep backlog references visible.

Verification:
- `make verify`

## Phase 2: Demo Archive and Browser Upload Flow

Goal: produce a synthetic archive and a browser-only flow that reads it locally and displays generated BQA artifacts.

Inputs:
- `team/backlog/001_static_site_app.md`
- `team/backlog/005_demo_archive_generator.md`
- `team/backlog/007_upload_flow.md`

Deliverables:
- Synthetic marked archive fixture with no private data.
- Static browser upload flow.
- Downloadable generated result archive.

Verification:
- Unit or browser smoke tests against synthetic fixtures.
- Manual check that no network upload is required.

## Phase 3: Static Demo and Visual Workflow

Goal: make the BQA Team workflow visible enough for demos and early buyer conversations.

Inputs:
- `team/backlog/002_agent_game_visualization.md`
- `team/backlog/004_sales_pilot_landing.md`

Deliverables:
- Static landing/demo page for the two-week QA Memory Pilot.
- Lightweight workflow visualization for issue states, role handoffs, and blocked work.

Verification:
- Browser rendering check on desktop and mobile widths.
- Synthetic demo data only.

## Phase 4: Autopilot Hardening

Goal: make longer autonomous runs safer and easier to inspect.

Inputs:
- `team/backlog/003_codex_team_pipeline.md`

Deliverables:
- More smoke coverage for install, dry-run, and failure paths.
- Stronger status artifacts for routes, blockers, PRs, QA, and business acceptance.
- Explicit stop-condition checks aligned with `docs/SECURITY_REQUIREMENTS.md`.

Verification:
- `make verify`
- Dry-run autopilot smoke test in a temporary git repository.

## Phase 5: Sales Pilot Package

Goal: package the product story for internal validation before external pilots.

Inputs:
- `team/backlog/006_monday_sales_package.md`

Deliverables:
- Pilot one-pager.
- Internal demo script.
- Discovery call script.
- Onboarding checklist.
- Outreach snippets, pricing hypothesis, and stakeholder FAQ.

Verification:
- Review against the buyer profile in `team/backlog/004_sales_pilot_landing.md`.
- Confirm all examples use synthetic or public-safe content.
