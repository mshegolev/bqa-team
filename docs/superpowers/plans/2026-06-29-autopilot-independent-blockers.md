# Autopilot Independent Blockers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make BQA Autopilot continue independent work when another issue is blocked.

**Architecture:** Keep the existing orchestrator module and issue status model. Replace the early label-only candidate path with one snapshot-based filter that applies label, lifecycle-label, and blocked-dependency checks consistently.

**Tech Stack:** Python standard library, Bash wrappers, `unittest`, Makefile verification.

---

### Task 1: Lock Default Continue Behavior

**Files:**
- Modify: `tests/test_bqa_team_orchestrator.py`
- Modify: `scripts/bqa_team_orchestrator.py`

- [x] **Step 1: Write the failing test**

Add an assertion to `test_write_default_autopilot_config_creates_reusable_config`:

```python
self.assertFalse(saved["stop_on_fail"])
```

- [x] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_bqa_team_orchestrator.AutopilotTests.test_write_default_autopilot_config_creates_reusable_config -v`

Expected: FAIL because `stop_on_fail` is currently `true`.

- [x] **Step 3: Write minimal implementation**

Change `default_autopilot_config()`:

```python
"stop_on_fail": False,
```

- [x] **Step 4: Run test to verify it passes**

Run the same unittest command.

Expected: PASS.

### Task 2: Apply Blocked Dependency Filtering With Labels

**Files:**
- Modify: `tests/test_bqa_team_orchestrator.py`
- Modify: `scripts/bqa_team_orchestrator.py`

- [x] **Step 1: Write the failing test**

Add a test that stubs `open_issue_snapshot()` with ready-dev issues, one blocked issue, and one ready-dev issue depending on the blocker. Call `list_candidate_issues(..., "bqa:ready-dev")` and expect only independent ready-dev issues.

- [x] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_bqa_team_orchestrator.AutopilotTests.test_candidate_issues_skip_blocked_dependencies_with_label_filter -v`

Expected: FAIL because the current implementation returns from `list_ready_issues()` before dependency filtering.

- [x] **Step 3: Write minimal implementation**

Make `list_candidate_issues()` load the full open issue snapshot, apply the requested label in Python, skip lifecycle labels, and skip issues whose dependencies point to blocked issues.

- [x] **Step 4: Run focused tests**

Run: `python3 -m unittest tests.test_bqa_team_orchestrator -v`

Expected: PASS.

### Task 3: Document Operator Behavior

**Files:**
- Modify: `README.md`

- [x] **Step 1: Update README**

Document that autopilot continues by default, skips blocked/dependent issues, and supports `--stop-on-fail` or config `stop_on_fail: true` for strict mode.

- [x] **Step 2: Run full verification**

Run: `make verify`

Expected: PASS with all tests.
