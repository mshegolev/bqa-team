# Operational Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a repeatable repository verification loop and a concise roadmap for the next BQA Team work.

**Architecture:** Keep the foundation lightweight: `make verify` is the local contract, GitHub Actions delegates to that contract, and `docs/ROADMAP.md` maps the existing backlog into executable phases. Python unit tests assert the foundation files exist and stay aligned with the backlog.

**Tech Stack:** Python `unittest`, Bash syntax checks, GNU/Unix `make`, GitHub Actions.

---

### Task 1: Foundation Tests

**Files:**
- Create: `tests/test_project_foundation.py`

- [x] **Step 1: Write failing tests**

Create tests that assert:
- `Makefile` exposes `test`, `lint`, and `verify` targets.
- GitHub Actions runs `make verify`.
- `docs/ROADMAP.md` references every current `team/backlog/*.md` item.
- `.gitignore` excludes Python bytecode caches.

- [x] **Step 2: Run tests to verify failure**

Run:

```bash
python3 -m unittest tests.test_project_foundation -v
```

Expected before implementation: failures for missing `Makefile`, missing CI workflow, missing roadmap, and missing Python cache ignore entries.

### Task 2: Verification Contract

**Files:**
- Create: `Makefile`
- Modify: `.gitignore`
- Create: `.github/workflows/ci.yml`

- [x] **Step 1: Add `Makefile` targets**

Add:
- `test`: runs `python3 -m unittest discover -s tests -v`
- `lint`: runs Python compile checks and `bash -n` for shell scripts
- `verify`: runs `lint` then `test`

- [x] **Step 2: Add CI**

Add a GitHub Actions workflow for pushes and pull requests that checks out the repo, sets up Python 3, and runs `make verify`.

- [x] **Step 3: Ignore Python bytecode**

Add `__pycache__/` and `*.pyc` to `.gitignore`.

### Task 3: Roadmap

**Files:**
- Create: `docs/ROADMAP.md`

- [x] **Step 1: Map backlog into phases**

Create a short roadmap with:
- Foundation and safety.
- Demo archive and browser upload flow.
- Static demo/landing experience.
- Autopilot hardening.
- Sales pilot package.

- [x] **Step 2: Reference source backlog files**

Each roadmap phase must link or name the relevant `team/backlog/*.md` file, so backlog and roadmap do not diverge silently.

### Task 4: Verify

**Files:**
- No new files.

- [x] **Step 1: Run targeted foundation tests**

```bash
python3 -m unittest tests.test_project_foundation -v
```

- [x] **Step 2: Run full verification**

```bash
make verify
```

- [x] **Step 3: Check workspace**

```bash
git status --short
```
