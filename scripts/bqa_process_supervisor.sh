#!/usr/bin/env bash
set -euo pipefail

EXECUTE=0
RESTART=0
TARGET_REPO="${BQA_TARGET_REPO:-$(pwd)}"
TEAM_REPO="${BQA_TEAM_REPO:-/opt/develop/bqa-team}"
LOG_DIR=""
REPORT=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --execute) EXECUTE=1; shift ;;
    --restart) RESTART=1; shift ;;
    --target-repo) TARGET_REPO="$2"; shift 2 ;;
    --team-repo) TEAM_REPO="$2"; shift 2 ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

if [[ ! -d "$TARGET_REPO/.git" ]]; then
  echo "ERROR: target repo not found: $TARGET_REPO" >&2
  exit 2
fi

LOG_DIR="$TARGET_REPO/.bqa-team/logs"
REPORT_DIR="$TARGET_REPO/.bqa-team/processes"
REPORT="$REPORT_DIR/process-supervisor-$(date +%Y%m%d-%H%M%S).md"
mkdir -p "$LOG_DIR" "$REPORT_DIR"

CONSENT="$TARGET_REPO/scripts/bqa_consent.sh"
if [[ -x "$CONSENT" ]]; then
  bash "$CONSENT" "$TARGET_REPO"
fi

SELF_PID="$$"
current_install_hash="missing"
team_hash="missing"
if [[ -f "$TARGET_REPO/scripts/bqa_selfheal_etl_pack.sh" ]]; then
  current_install_hash="$(shasum -a 256 "$TARGET_REPO/scripts/bqa_selfheal_etl_pack.sh" | awk '{print $1}')"
fi
if [[ -f "$TEAM_REPO/scripts/bqa_selfheal_etl_pack.sh" ]]; then
  team_hash="$(shasum -a 256 "$TEAM_REPO/scripts/bqa_selfheal_etl_pack.sh" | awk '{print $1}')"
fi

mapfile -t candidates < <(ps -axo pid=,ppid=,command= | grep -E 'bqa_selfheal_etl_pack|bqa_team_evolve|bqa_agent_guard|bqa_team_orchestrator|codex exec' | grep -v grep || true)

old_pids=()
{
  echo "# BQA Process Supervisor Report"
  echo
  echo "Time: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "Target repo: $TARGET_REPO"
  echo "Team repo: $TEAM_REPO"
  echo "Execute: $EXECUTE"
  echo "Restart: $RESTART"
  echo
  echo "## Version hashes"
  echo
  echo "Installed selfheal: $current_install_hash"
  echo "Team selfheal: $team_hash"
  echo
  echo "## Candidate processes"
  echo

  if (( ${#candidates[@]} == 0 )); then
    echo "No candidate BQA/Codex processes found."
  fi

  for line in "${candidates[@]}"; do
    pid="$(awk '{print $1}' <<< "$line")"
    ppid="$(awk '{print $2}' <<< "$line")"
    cmd="$(cut -d' ' -f3- <<< "$line")"

    # Never kill this supervisor or its direct parent shell.
    if [[ "$pid" == "$SELF_PID" || "$pid" == "$PPID" ]]; then
      echo "- KEEP pid=$pid reason=self-or-parent cmd=$cmd"
      continue
    fi

    # Only manage processes related to target repo or BQA scripts.
    if [[ "$cmd" != *"$TARGET_REPO"* && "$cmd" != *"bqa_"* && "$cmd" != *"bqa-team"* ]]; then
      echo "- KEEP pid=$pid reason=not-target-repo cmd=$cmd"
      continue
    fi

    reason="old-or-conflicting-bqa-run"
    if [[ "$current_install_hash" != "$team_hash" ]]; then
      reason="installed-version-differs-from-bqa-team"
    fi

    echo "- OLD pid=$pid ppid=$ppid reason=$reason cmd=$cmd"
    old_pids+=("$pid")
  done
} > "$REPORT"

cat "$REPORT"

if (( ${#old_pids[@]} > 0 )); then
  if [[ "$EXECUTE" -eq 1 ]]; then
    echo "Stopping old BQA processes: ${old_pids[*]}"
    for pid in "${old_pids[@]}"; do
      kill -TERM "$pid" 2>/dev/null || true
    done
    sleep 3
    for pid in "${old_pids[@]}"; do
      if kill -0 "$pid" 2>/dev/null; then
        echo "Force stopping pid=$pid"
        kill -KILL "$pid" 2>/dev/null || true
      fi
    done
  else
    echo "Dry run: would stop old BQA processes: ${old_pids[*]}"
  fi
else
  echo "No old BQA processes to stop."
fi

if [[ "$EXECUTE" -eq 1 && -d "$TEAM_REPO/.git" ]]; then
  git -C "$TEAM_REPO" pull --ff-only || true
  bash "$TEAM_REPO/scripts/install.sh" "$TARGET_REPO"
fi

if [[ "$RESTART" -eq 1 ]]; then
  if [[ "$EXECUTE" -eq 1 ]]; then
    echo "Starting fresh BQA selfheal/evolve run."
    nohup bash -lc "cd '$TARGET_REPO' && scripts/bqa_selfheal_etl_pack.sh && scripts/bqa_agent_guard.sh && scripts/bqa_team_evolve.sh --target-repo '$TARGET_REPO' --team-repo '$TEAM_REPO' --execute" > "$LOG_DIR/night-safe-selfheal-evolve.log" 2>&1 &
    echo "Started PID: $!"
    echo "Log: $LOG_DIR/night-safe-selfheal-evolve.log"
  else
    echo "Dry run: would start fresh BQA selfheal/evolve run."
  fi
fi
