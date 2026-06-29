#!/usr/bin/env bash
set -euo pipefail

ACTION="${1:-status}"
if [[ $# -gt 0 ]]; then
  shift
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
DEFAULT_TEAM_REPO="$(cd "$SCRIPT_DIR/.." && pwd -P)"
TARGET_REPO_EXPLICIT=0
if [[ -n "${BQA_TARGET_REPO:-}" ]]; then
  TARGET_REPO_EXPLICIT=1
fi
TARGET_REPO="${BQA_TARGET_REPO:-$(pwd)}"
TEAM_REPO="${BQA_TEAM_REPO:-$DEFAULT_TEAM_REPO}"
REPO="${BQA_GITHUB_REPO:-mshegolev/bqa-os}"
CONFIG=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target-repo) TARGET_REPO="$2"; TARGET_REPO_EXPLICIT=1; shift 2 ;;
    --team-repo) TEAM_REPO="$2"; shift 2 ;;
    --repo) REPO="$2"; shift 2 ;;
    --config) CONFIG="$2"; shift 2 ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

canonical_dir() {
  cd "$1" 2>/dev/null && pwd -P
}

resolve_default_target_repo() {
  if [[ "$TARGET_REPO_EXPLICIT" -eq 1 ]]; then
    return
  fi

  local target_abs
  target_abs="$(canonical_dir "$TARGET_REPO" || true)"
  local team_abs
  team_abs="$(canonical_dir "$TEAM_REPO" || true)"
  if [[ -z "$target_abs" || -z "$team_abs" || "$target_abs" != "$team_abs" ]]; then
    return
  fi

  local repo_name="${REPO##*/}"
  local sibling
  sibling="$(canonical_dir "$team_abs/../$repo_name" || true)"
  if [[ -n "$sibling" && -d "$sibling/.git" ]]; then
    TARGET_REPO="$sibling"
  fi
}

resolve_default_target_repo

if [[ ! -d "$TARGET_REPO/.git" ]]; then
  echo "ERROR: target repo not found: $TARGET_REPO" >&2
  exit 2
fi

ORCH="$TEAM_REPO/scripts/bqa_team_orchestrator.py"
if [[ ! -f "$ORCH" ]]; then
  ORCH="$TARGET_REPO/scripts/bqa_team_orchestrator.py"
fi
if [[ ! -f "$ORCH" ]]; then
  echo "ERROR: bqa_team_orchestrator.py not found" >&2
  exit 2
fi

STATUS_DIR="$TARGET_REPO/.bqa-team/status"
LOG_DIR="$TARGET_REPO/.bqa-team/logs"
RUNS_DIR="$TARGET_REPO/.bqa-team/generated/runs"
PID_FILE="$STATUS_DIR/autopilot.pid"
LOG_FILE="$LOG_DIR/autopilot.log"
STATUS_MD="$STATUS_DIR/autopilot-status.md"
HISTORY_FILE="$STATUS_DIR/autopilot-history.jsonl"
HEARTBEAT_FILE="$STATUS_DIR/autopilot-heartbeat"
STALE_SECONDS="${BQA_AUTOPILOT_STALE_SECONDS:-900}"
AUTOHEAL="${BQA_AUTOPILOT_AUTOHEAL:-1}"
START_RETRIES="${BQA_AUTOPILOT_START_RETRIES:-1}"
STARTUP_GRACE_SECONDS="${BQA_AUTOPILOT_STARTUP_GRACE_SECONDS:-1}"

mkdir -p "$STATUS_DIR" "$LOG_DIR"

if [[ -z "$CONFIG" ]]; then
  CONFIG="$TARGET_REPO/.bqa-team/autopilot-config.json"
fi

if [[ -f "$CONFIG" ]]; then
  REPO="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("repo", sys.argv[2]))' "$CONFIG" "$REPO")"
fi

is_running() {
  [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null
}

child_pids() {
  local parent="$1"
  ps -axo pid=,ppid= 2>/dev/null | awk -v parent="$parent" '$2 == parent { print $1 }' || true
}

has_child_process() {
  [[ -n "$(child_pids "$1")" ]]
}

kill_process_group() {
  local signal="$1"
  local pid="$2"
  python3 -c 'import os, signal, sys
sig = int(sys.argv[1])
pgid = int(sys.argv[2])
try:
    os.killpg(pgid, sig)
except (ProcessLookupError, PermissionError):
    pass
' "$signal" "$pid"
}

file_epoch() {
  local path="$1"
  python3 - "$path" <<'PY'
import os
import sys

try:
    print(int(os.path.getmtime(sys.argv[1])))
except OSError:
    print(0)
PY
}

latest_activity_epoch() {
  local latest=0
  local epoch=0
  local path

  for path in "$LOG_FILE" "$HISTORY_FILE" "$HEARTBEAT_FILE"; do
    epoch="$(file_epoch "$path")"
    if [[ "$epoch" -gt "$latest" ]]; then
      latest="$epoch"
    fi
  done

  if [[ -d "$RUNS_DIR" ]]; then
    for path in "$RUNS_DIR"/*; do
      [[ -e "$path" ]] || continue
      epoch="$(file_epoch "$path")"
      if [[ "$epoch" -gt "$latest" ]]; then
        latest="$epoch"
      fi
    done
  fi

  if [[ "$latest" -eq 0 ]]; then
    latest="$(file_epoch "$PID_FILE")"
  fi
  echo "$latest"
}

stop_pid() {
  local pid="$1"
  local child
  for child in $(child_pids "$pid"); do
    stop_pid "$child"
  done
  kill_process_group 15 "$pid"
  kill -TERM "$pid" 2>/dev/null || true
  sleep 2
  for child in $(child_pids "$pid"); do
    stop_pid "$child"
  done
  kill_process_group 9 "$pid"
  if kill -0 "$pid" 2>/dev/null; then
    kill -KILL "$pid" 2>/dev/null || true
  fi
}

heal_runtime_state() {
  if [[ ! -f "$PID_FILE" ]]; then
    return 1
  fi

  local pid
  pid="$(cat "$PID_FILE")"
  if ! kill -0 "$pid" 2>/dev/null; then
    echo "Auto-heal: removed stale autopilot PID $pid"
    rm -f "$PID_FILE"
    return 0
  fi

  local latest
  latest="$(latest_activity_epoch)"
  local now
  now="$(date +%s)"
  local age=$((now - latest))
  if [[ "$latest" -gt 0 && "$age" -ge "$STALE_SECONDS" ]]; then
    if has_child_process "$pid"; then
      return 1
    fi
    echo "Auto-heal: stale autopilot PID $pid has no activity for ${age}s; restarting"
    stop_pid "$pid"
    rm -f "$PID_FILE"
    return 0
  fi

  return 1
}

ensure_config() {
  if [[ ! -f "$CONFIG" ]]; then
    echo "No autopilot config found: $CONFIG"
    echo "Starting quick config wizard."
    cd "$TARGET_REPO"
    python3 "$ORCH" --repo "$REPO" configure-autopilot --config "$CONFIG"
    REPO="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("repo", sys.argv[2]))' "$CONFIG" "$REPO")"
  fi
}

launch_autopilot_once() {
  local old_pwd="$PWD"
  cd "$TARGET_REPO"
  # -u keeps stdout/stderr unbuffered so autopilot.log reflects live
  # activity; without it Python block-buffers and the log looks empty,
  # which also misleads the auto-heal staleness detector.
  nohup python3 -c 'import os, sys; os.setsid(); os.execvp(sys.argv[1], sys.argv[1:])' python3 -u "$ORCH" --repo "$REPO" --execute autopilot --config "$CONFIG" > "$LOG_FILE" 2>&1 &
  LAST_LAUNCHED_PID="$!"
  echo "$LAST_LAUNCHED_PID" > "$PID_FILE"
  cd "$old_pwd"
}

launched_job_is_running() {
  local pid="$1"
  jobs -pr | awk -v pid="$pid" '$1 == pid { found = 1 } END { exit found ? 0 : 1 }'
}

start_autopilot() {
  ensure_config

  local attempt=1
  local max_attempts=$((START_RETRIES + 1))
  while [[ "$attempt" -le "$max_attempts" ]]; do
    launch_autopilot_once
    sleep "$STARTUP_GRACE_SECONDS"

    if launched_job_is_running "$LAST_LAUNCHED_PID"; then
      echo "Started BQA autopilot. PID: $(cat "$PID_FILE")"
      echo "Log: $LOG_FILE"
      echo "Status: $STATUS_MD"
      return 0
    fi

    rm -f "$PID_FILE"
    if [[ "$attempt" -lt "$max_attempts" ]]; then
      echo "Autopilot start attempt $attempt exited immediately; retrying"
    else
      echo "ERROR: autopilot failed to stay running after $attempt attempt(s). See log: $LOG_FILE" >&2
      return 1
    fi
    attempt=$((attempt + 1))
  done
}

case "$ACTION" in
  configure)
    cd "$TARGET_REPO"
    python3 "$ORCH" --repo "$REPO" configure-autopilot --config "$CONFIG"
    ;;

  start)
    if [[ "$AUTOHEAL" != "0" ]]; then
      heal_runtime_state >/dev/null || true
    fi
    if is_running; then
      echo "BQA autopilot is already running. PID: $(cat "$PID_FILE")"
      exit 0
    fi
    start_autopilot
    ;;

  status)
    healed=0
    if [[ "$AUTOHEAL" != "0" ]]; then
      if heal_runtime_state; then
        healed=1
      fi
    fi
    if is_running; then
      echo "BQA autopilot: RUNNING pid=$(cat "$PID_FILE")"
    else
      echo "BQA autopilot: STOPPED"
      if [[ "$healed" -eq 1 ]]; then
        start_autopilot
      fi
    fi
    echo "BQA target repo: $TARGET_REPO"
    cd "$TARGET_REPO"
    python3 "$ORCH" --repo "$REPO" --execute monitor >/dev/null
    cat "$STATUS_MD"
    ;;

  logs)
    touch "$LOG_FILE"
    tail -f "$LOG_FILE"
    ;;

  view)
    cd "$TARGET_REPO"
    python3 "$ORCH" --repo "$REPO" --execute view
    echo "Open: $TARGET_REPO/.bqa-team/status/project-view.html"
    ;;

  stop)
    if is_running; then
      stop_pid "$(cat "$PID_FILE")"
      echo "Stopped BQA autopilot. PID: $(cat "$PID_FILE")"
      rm -f "$PID_FILE"
    else
      echo "BQA autopilot is not running."
    fi
    ;;

  *)
    echo "Usage: $0 {configure|start|status|logs|view|stop} [--target-repo PATH] [--team-repo PATH] [--repo OWNER/REPO] [--config PATH]" >&2
    exit 2
    ;;
esac
