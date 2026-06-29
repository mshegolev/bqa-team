#!/usr/bin/env bash
set -euo pipefail

ACTION="${1:-status}"
if [[ $# -gt 0 ]]; then
  shift
fi

TARGET_REPO="${BQA_TARGET_REPO:-$(pwd)}"
TEAM_REPO="${BQA_TEAM_REPO:-/opt/develop/bqa-team}"
REPO="${BQA_GITHUB_REPO:-mshegolev/bqa-os}"
CONFIG=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target-repo) TARGET_REPO="$2"; shift 2 ;;
    --team-repo) TEAM_REPO="$2"; shift 2 ;;
    --repo) REPO="$2"; shift 2 ;;
    --config) CONFIG="$2"; shift 2 ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

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
PID_FILE="$STATUS_DIR/autopilot.pid"
LOG_FILE="$LOG_DIR/autopilot.log"
STATUS_MD="$STATUS_DIR/autopilot-status.md"

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

case "$ACTION" in
  configure)
    cd "$TARGET_REPO"
    python3 "$ORCH" --repo "$REPO" configure-autopilot --config "$CONFIG"
    ;;

  start)
    if is_running; then
      echo "BQA autopilot is already running. PID: $(cat "$PID_FILE")"
      exit 0
    fi
    if [[ ! -f "$CONFIG" ]]; then
      echo "No autopilot config found: $CONFIG"
      echo "Starting quick config wizard."
      cd "$TARGET_REPO"
      python3 "$ORCH" --repo "$REPO" configure-autopilot --config "$CONFIG"
      REPO="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("repo", sys.argv[2]))' "$CONFIG" "$REPO")"
    fi
    (
      cd "$TARGET_REPO"
      nohup python3 "$ORCH" --repo "$REPO" --execute autopilot --config "$CONFIG" > "$LOG_FILE" 2>&1 &
      echo "$!" > "$PID_FILE"
    )
    echo "Started BQA autopilot. PID: $(cat "$PID_FILE")"
    echo "Log: $LOG_FILE"
    echo "Status: $STATUS_MD"
    ;;

  status)
    if is_running; then
      echo "BQA autopilot: RUNNING pid=$(cat "$PID_FILE")"
    else
      echo "BQA autopilot: STOPPED"
    fi
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
      kill -TERM "$(cat "$PID_FILE")"
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
