#!/usr/bin/env bash
set -euo pipefail

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_DIR="${1:-$(pwd)}"

if [[ ! -d "$TARGET_DIR/.git" ]]; then
  echo "ERROR: target is not a git repository: $TARGET_DIR" >&2
  echo "Usage: bash /path/to/bqa-team/scripts/install.sh [target-repo-dir]" >&2
  exit 1
fi

mkdir -p "$TARGET_DIR/scripts"
mkdir -p "$TARGET_DIR/.bqa-team"

cp "$SOURCE_DIR/scripts/bqa_team_orchestrator.py" "$TARGET_DIR/scripts/bqa_team_orchestrator.py"
cp "$SOURCE_DIR/scripts/bqa_question.sh" "$TARGET_DIR/scripts/bqa_question.sh"
chmod +x "$TARGET_DIR/scripts/bqa_team_orchestrator.py" "$TARGET_DIR/scripts/bqa_question.sh"

mkdir -p "$TARGET_DIR/.bqa-team/roles" "$TARGET_DIR/.bqa-team/templates" "$TARGET_DIR/.bqa-team/backlog"
rsync -a --delete "$SOURCE_DIR/team/roles/" "$TARGET_DIR/.bqa-team/roles/"
rsync -a --delete "$SOURCE_DIR/team/templates/" "$TARGET_DIR/.bqa-team/templates/"

# Seed backlog only when target backlog is empty. This avoids overwriting project-specific business tasks.
if ! find "$TARGET_DIR/.bqa-team/backlog" -type f -name '*.md' | grep -q .; then
  rsync -a "$SOURCE_DIR/team/backlog/" "$TARGET_DIR/.bqa-team/backlog/"
fi

cat <<EOF
BQA Team installed into: $TARGET_DIR

Next commands:
  python3 scripts/bqa_team_orchestrator.py --repo <owner/repo> init
  python3 scripts/bqa_team_orchestrator.py --repo <owner/repo> --execute ensure-labels
  python3 scripts/bqa_team_orchestrator.py --repo <owner/repo> architect
  python3 scripts/bqa_team_orchestrator.py --repo <owner/repo> --execute create-issues

Recommended .gitignore entries in target repo:
  .bqa/
  .bqa-team/generated/
  .bqa-team/logs/
  .bqa-team/state.json
  error.log
EOF
