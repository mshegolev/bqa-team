#!/usr/bin/env bash
set -euo pipefail

EXECUTE=0
TARGET_REPO="${BQA_TARGET_REPO:-$(pwd)}"
TEAM_REPO="${BQA_TEAM_REPO:-/opt/develop/bqa-team}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --execute) EXECUTE=1; shift ;;
    --target-repo) TARGET_REPO="$2"; shift 2 ;;
    --team-repo) TEAM_REPO="$2"; shift 2 ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

if [[ ! -d "$TARGET_REPO/.git" ]]; then
  echo "ERROR: target repo not found: $TARGET_REPO" >&2
  exit 2
fi

if [[ ! -d "$TEAM_REPO/.git" ]]; then
  echo "ERROR: bqa-team repo not found: $TEAM_REPO" >&2
  exit 2
fi

CONSENT="$TARGET_REPO/scripts/bqa_consent.sh"
if [[ -x "$CONSENT" ]]; then
  bash "$CONSENT" "$TARGET_REPO"
fi

mkdir -p "$TARGET_REPO/.bqa-team/evolution" "$TARGET_REPO/.bqa-team/logs"
CONTEXT="$TARGET_REPO/.bqa-team/evolution/evolution_context.md"
PROMPT="$TARGET_REPO/.bqa-team/evolution/evolve_bqa_team_prompt.md"
LOG="$TARGET_REPO/.bqa-team/logs/team-evolution-$(date +%Y%m%d-%H%M%S).log"

{
  echo "# BQA Team Evolution Context"
  echo
  echo "Time: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "Target repo: $TARGET_REPO"
  echo "Team repo: $TEAM_REPO"
  echo
  echo "## Target git status"
  git -C "$TARGET_REPO" status --short || true
  echo
  echo "## Team git status"
  git -C "$TEAM_REPO" status --short || true
  echo
  echo "## Latest validation reports"
  find "$TARGET_REPO/.bqa/output/validation" -maxdepth 1 -type f -print -exec sh -c 'echo "--- $1"; tail -120 "$1"' sh {} \; 2>/dev/null || true
  echo
  echo "## Latest safety reports"
  find "$TARGET_REPO/.bqa-team/safety" -maxdepth 1 -type f -print -exec sh -c 'echo "--- $1"; tail -120 "$1"' sh {} \; 2>/dev/null || true
  echo
  echo "## Latest logs"
  find "$TARGET_REPO/.bqa-team/logs" -maxdepth 1 -type f -print 2>/dev/null | tail -8 | while read -r f; do echo "--- $f"; tail -120 "$f"; done
} > "$CONTEXT"

cat > "$PROMPT" <<PROMPT
You are the BQA Team Evolution Manager.

Goal:
Improve the bqa-team repository based on real run evidence, but only with small safe changes.

Target repo context:

$(cat "$CONTEXT")

Rules:
- Work inside this team repo only: $TEAM_REPO
- Do not edit product code in target repo.
- Do not include private data from logs in committed files.
- Prefer improving scripts, roles, templates, validators, security requirements, or runbooks.
- Preserve dry-run defaults and explicit --execute behavior.
- Keep changes small and reversible.
- If no useful safe improvement is obvious, create only a short evolution note under docs/ or do nothing.

Tasks:
1. Inspect current bqa-team files.
2. Propose the smallest improvement that prevents a repeated failure or improves safety.
3. Apply the improvement locally in $TEAM_REPO only.
4. Run basic shell syntax checks for changed shell scripts.
5. Print summary.

Return:
EVOLUTION_STATUS: APPLIED or STOP
OBSERVATIONS:
FILES_CHANGED:
VALIDATION:
NEXT_COMMANDS:
PROMPT

if [[ "$EXECUTE" -eq 1 ]]; then
  codex exec "$(cat "$PROMPT")" 2>&1 | tee "$LOG"
  echo "--- bqa-team diff ---"
  git -C "$TEAM_REPO" diff --stat || true

  if [[ -n "$(git -C "$TEAM_REPO" status --short)" ]]; then
    git -C "$TEAM_REPO" add scripts team docs README.md .gitignore 2>/dev/null || git -C "$TEAM_REPO" add .
    git -C "$TEAM_REPO" commit -m "Evolve BQA team from run feedback" || true
    git -C "$TEAM_REPO" push || true
    echo "Updated bqa-team pushed. Reinstall into target repo:"
    echo "  cd $TARGET_REPO && bash $TEAM_REPO/scripts/install.sh"
  else
    echo "No bqa-team changes to commit."
  fi
else
  echo "Dry run. Evolution context written to: $CONTEXT"
  echo "Prompt written to: $PROMPT"
  echo
  echo "To apply evolution:"
  echo "  $TEAM_REPO/scripts/bqa_team_evolve.sh --target-repo $TARGET_REPO --team-repo $TEAM_REPO --execute"
fi
