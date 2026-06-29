# Autopilot History Ledger Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an append-only JSONL ledger that records every BQA Autopilot cycle.

**Architecture:** Keep the existing orchestrator script. `run_autopilot_cycle()` will publish compact metadata for the cycle, and `cmd_autopilot()` will append that metadata to `.bqa-team/status/autopilot-history.jsonl` after each cycle.

**Tech Stack:** Python standard library, JSONL files, `unittest`, Makefile verification.

---

### Task 1: Record Processed Cycle Metadata

**Files:**
- Modify: `tests/test_bqa_team_orchestrator.py`
- Modify: `scripts/bqa_team_orchestrator.py`

- [x] **Step 1: Write the failing test**

Add `test_autopilot_history_records_processed_cycle_details`. It should:
- redirect `STATUS_DIR`, `STATUS_JSON`, `STATUS_MD`, and `AUTOPILOT_HISTORY` into a temp directory
- stub `run_autopilot_cycle()` to set cycle details for issue `42`, branch `codex/issue-42-add-widget`, PR `77`, subagent `go-cli-implementer`
- call `cmd_autopilot()` once
- assert one JSONL entry exists with `status == "processed"`, `issue == 42`, `pr == 77`, and `processed_this_run == 1`

- [x] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_bqa_team_orchestrator.AutopilotTests.test_autopilot_history_records_processed_cycle_details -v`

Expected: FAIL because `AUTOPILOT_HISTORY` and append logic do not exist.

- [x] **Step 3: Implement minimal ledger support**

Add:
- `AUTOPILOT_HISTORY = STATUS_DIR / "autopilot-history.jsonl"`
- `LAST_AUTOPILOT_CYCLE = {}`
- `set_last_autopilot_cycle(details: dict)`
- `append_autopilot_history(args, cycle, total_cycles, status, processed)`

Call `append_autopilot_history()` from `cmd_autopilot()` after each cycle.

- [x] **Step 4: Run test to verify it passes**

Run the same unittest command.

Expected: PASS.

### Task 2: Capture Stop Reasons From Real Cycle Paths

**Files:**
- Modify: `tests/test_bqa_team_orchestrator.py`
- Modify: `scripts/bqa_team_orchestrator.py`

- [x] **Step 1: Write the failing test**

Add `test_autopilot_cycle_records_missing_pr_stop_reason`. It should run the real `run_autopilot_cycle()` path with a selected issue but no PR found, then assert the last cycle details include `status == "blocked"` and `stop_reason == "missing_pr"`.

- [x] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_bqa_team_orchestrator.AutopilotTests.test_autopilot_cycle_records_missing_pr_stop_reason -v`

Expected: FAIL because `run_autopilot_cycle()` does not yet set details.

- [x] **Step 3: Add details at each return path**

Set cycle details for:
- idle: `status="idle"`, `stop_reason="no_candidates"`
- developer question: `status="blocked"`, `stop_reason="developer_question_open"`
- missing PR: `status="blocked"`, `stop_reason="missing_pr"`
- QA failure: `status="blocked"`, `stop_reason="qa_failed"`
- business revision: `status="blocked"`, `stop_reason="business_revision"`
- processed: `status="processed"`, `stop_reason="completed"`

- [x] **Step 4: Run focused suite**

Run: `python3 -m unittest tests.test_bqa_team_orchestrator -v`

Expected: PASS.

### Task 3: Document The Ledger

**Files:**
- Modify: `README.md`

- [x] **Step 1: Update README**

Add `.bqa-team/status/autopilot-history.jsonl` to the monitor artifact list and document that it contains append-only cycle records.

- [x] **Step 2: Run full verification**

Run: `make verify`

Expected: PASS.
