#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-$(pwd)}"
LOG_DIR="$ROOT/.bqa-team/logs"
SAFETY_DIR="$ROOT/.bqa-team/safety"
CONTEXT_FILE="$SAFETY_DIR/context_snapshot.md"
REPORT_FILE="$SAFETY_DIR/drift_report.md"

mkdir -p "$LOG_DIR" "$SAFETY_DIR"

MODE="${BQA_AGENT_GUARD_MODE:-check}"
TARGET_GOAL="${BQA_TARGET_GOAL:-Unknown goal. Set BQA_TARGET_GOAL for stronger guard checks.}"

{
  echo "# BQA Agent Context Snapshot"
  echo
  echo "Time: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "Root: $ROOT"
  echo "Mode: $MODE"
  echo
  echo "## Target goal"
  echo
  echo "$TARGET_GOAL"
  echo
  echo "## Git branch"
  echo
  git -C "$ROOT" branch --show-current 2>/dev/null || true
  echo
  echo "## Git status"
  echo
  git -C "$ROOT" status --short 2>/dev/null || true
  echo
  echo "## Recent commits"
  echo
  git -C "$ROOT" log --oneline -5 2>/dev/null || true
  echo
  echo "## BQA output files"
  echo
  find "$ROOT/.bqa/output" -maxdepth 4 -type f -print 2>/dev/null || true
  echo
  echo "## Team logs"
  echo
  find "$LOG_DIR" -maxdepth 1 -type f -print 2>/dev/null | tail -20 || true
} > "$CONTEXT_FILE"

status="OK"
reasons=()

changed_count="$(git -C "$ROOT" status --short 2>/dev/null | wc -l | tr -d ' ')"
if [[ "$changed_count" -gt 30 ]]; then
  status="WARN"
  reasons+=("Large working tree change count: $changed_count")
fi

if git -C "$ROOT" status --short 2>/dev/null | grep -E '(^.. internal/|^.. cmd/|^.. go.mod|^.. go.sum)' >/dev/null; then
  if [[ "$TARGET_GOAL" == *"ETL QA Pack"* || "$TARGET_GOAL" == *"etl-agent-pack"* ]]; then
    status="STOP"
    reasons+=("ETL artifact task changed Go/source files unexpectedly")
  fi
fi

if [[ -d "$ROOT/.bqa/output/etl-agent-pack" ]]; then
  if [[ ! -f "$ROOT/.bqa/output/etl-agent-pack/statistics/session_stats.json" ]]; then
    status="WARN"
    reasons+=("ETL pack exists but statistics/session_stats.json is missing")
  elif ! python3 -m json.tool "$ROOT/.bqa/output/etl-agent-pack/statistics/session_stats.json" >/dev/null 2>&1; then
    status="STOP"
    reasons+=("ETL pack statistics/session_stats.json is invalid")
  fi
fi

if [[ ${#reasons[@]} -eq 0 ]]; then
  reasons+=("No drift signals detected by shell guard")
fi

{
  echo "# BQA Agent Drift Report"
  echo
  echo "DRIFT_STATUS: $status"
  echo
  echo "## Reason"
  printf -- '- %s\n' "${reasons[@]}"
  echo
  echo "## Saved context"
  echo
  echo "$CONTEXT_FILE"
  echo
  echo "## Recovery actions"
  echo
  if [[ "$status" == "STOP" ]]; then
    echo "- Stop current agent run."
    echo "- Inspect git status and diff."
    echo "- Compare current state with original acceptance criteria."
    echo "- Restore unrelated files or split into a separate issue."
    echo "- Run validator before continuing."
    echo "- If ambiguity remains, create a bqa:question issue."
  elif [[ "$status" == "WARN" ]]; then
    echo "- Pause before committing."
    echo "- Inspect changed files."
    echo "- Validate generated artifacts."
    echo "- Continue only with a small reversible next step."
  else
    echo "- Continue."
  fi
  echo
  echo "## Critical thinking checkpoint"
  echo
  echo "- What is the exact goal?"
  echo "- What evidence proves it is done?"
  echo "- What assumptions are unsupported?"
  echo "- What changed since the last safe state?"
  echo "- What is the smallest reversible next step?"
  echo
  echo "## TRIZ checkpoint"
  echo
  echo "- Useful function: keep useful agent progress."
  echo "- Harmful effect: drift, hallucination, or scope expansion."
  echo "- Contradiction: move fast while staying correct."
  echo "- Resource: git diff, logs, validation, issue acceptance criteria."
  echo "- Ideal result: agent stops itself before damaging the workflow."
} > "$REPORT_FILE"

cat "$REPORT_FILE"

if [[ "$status" == "STOP" ]]; then
  exit 2
fi

if [[ "$status" == "WARN" ]]; then
  exit 1
fi
