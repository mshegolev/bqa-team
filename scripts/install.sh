#!/usr/bin/env bash
set -euo pipefail

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_DIR="${1:-$(pwd)}"

if [[ ! -d "$TARGET_DIR/.git" ]]; then
  echo "ERROR: target is not a git repository: $TARGET_DIR" >&2
  echo "Usage: bash /path/to/bqa-team/scripts/install.sh [target-repo-dir]" >&2
  exit 1
fi

mkdir -p "$TARGET_DIR/scripts" "$TARGET_DIR/.bqa-team"

for script in \
  bqa_team_orchestrator.py \
  bqa_question.sh \
  bqa_validate_etl_pack.sh \
  bqa_selfheal_etl_pack.sh \
  bqa_agent_guard.sh \
  bqa_team_evolve.sh
  do
    cp "$SOURCE_DIR/scripts/$script" "$TARGET_DIR/scripts/$script"
    chmod +x "$TARGET_DIR/scripts/$script"
  done

mkdir -p "$TARGET_DIR/.bqa-team/roles" "$TARGET_DIR/.bqa-team/templates" "$TARGET_DIR/.bqa-team/backlog"
rsync -a --delete "$SOURCE_DIR/team/roles/" "$TARGET_DIR/.bqa-team/roles/"
rsync -a --delete "$SOURCE_DIR/team/templates/" "$TARGET_DIR/.bqa-team/templates/"

if ! find "$TARGET_DIR/.bqa-team/backlog" -type f -name '*.md' | grep -q .; then
  rsync -a "$SOURCE_DIR/team/backlog/" "$TARGET_DIR/.bqa-team/backlog/"
fi

echo "BQA Team installed into: $TARGET_DIR"
echo "Self-heal: scripts/bqa_selfheal_etl_pack.sh"
echo "Validate: scripts/bqa_validate_etl_pack.sh"
echo "Guard: scripts/bqa_agent_guard.sh"
echo "Evolve: scripts/bqa_team_evolve.sh --execute"
