#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-$(pwd)}"
REPORT_DIR="$ROOT/.bqa-team/security"
REPORT="$REPORT_DIR/devsecops-scan-$(date +%Y%m%d-%H%M%S).md"
mkdir -p "$REPORT_DIR"

if [[ ! -d "$ROOT/.git" ]]; then
  echo "ERROR: target is not a git repository: $ROOT" >&2
  exit 2
fi

status="PASS"
blockers=()
warnings=()

changed_files="$(git -C "$ROOT" status --short | awk '{print $2}' | sed 's#^"##; s#"$##' || true)"
staged_files="$(git -C "$ROOT" diff --cached --name-only || true)"
all_files="$(printf '%s\n%s\n' "$changed_files" "$staged_files" | awk 'NF' | sort -u)"

blocked_path_regex='^(\.bqa/|\.bqa-team/generated/|\.bqa-team/logs/|\.bqa-team/processes/|\.bqa-team/prompts/|\.bqa-team/safety/|\.bqa-team/evolution/|\.bqa-team/consent/|\.bqa-team/state\.json|\.serena/)|.*\.(log|env|pem|key|p12|pfx)$|^\.env'

while IFS= read -r file; do
  [[ -z "$file" ]] && continue
  if [[ "$file" =~ $blocked_path_regex ]]; then
    blockers+=("Blocked public-repo path: $file")
    status="FAIL"
  fi
done <<< "$all_files"

scan_content_files="$(printf '%s\n' "$all_files" | while IFS= read -r f; do [[ -f "$ROOT/$f" ]] && printf '%s\n' "$f"; done)"

if [[ -n "$scan_content_files" ]]; then
  while IFS= read -r file; do
    [[ -z "$file" ]] && continue
    case "$file" in
      *.png|*.jpg|*.jpeg|*.gif|*.zip|*.gz|*.tar|*.ico|*.pdf) continue ;;
    esac

    if grep -Eiq '(api[_-]?key|access[_-]?token|secret[_-]?key|private[_-]?key|password|passwd|bearer[[:space:]]+[A-Za-z0-9._-]+)' "$ROOT/$file" 2>/dev/null; then
      blockers+=("Suspicious secret-like content in: $file")
      status="FAIL"
    fi

    if grep -Eiq 'AKIA[0-9A-Z]{16}|-----BEGIN (RSA |EC |OPENSSH |)PRIVATE KEY-----' "$ROOT/$file" 2>/dev/null; then
      blockers+=("High-confidence credential pattern in: $file")
      status="FAIL"
    fi

    if grep -Eiq '/Users/[^ /]+|/opt/develop/[^ ]+' "$ROOT/$file" 2>/dev/null; then
      warnings+=("Local absolute path found in: $file")
      [[ "$status" == "PASS" ]] && status="WARN"
    fi

    if grep -Eiq 'bqa-brain|sanitized sessions|session logs|customer data|production dump' "$ROOT/$file" 2>/dev/null; then
      warnings+=("Private-data boundary term found in: $file")
      [[ "$status" == "PASS" ]] && status="WARN"
    fi
  done <<< "$scan_content_files"
fi

{
  echo "# BQA DevSecOps Scan Report"
  echo
  echo "DEVSECOPS_STATUS: $status"
  echo "SAFE_TO_COMMIT: $([[ "$status" == "PASS" ]] && echo yes || echo no)"
  echo
  echo "Root: $ROOT"
  echo
  echo "## Changed files"
  echo
  if [[ -z "$all_files" ]]; then
    echo "No changed files."
  else
    printf '%s\n' "$all_files" | sed 's/^/- /'
  fi
  echo
  echo "## Blockers"
  echo
  if (( ${#blockers[@]} == 0 )); then
    echo "None."
  else
    printf '%s\n' "${blockers[@]}" | sed 's/^/- /'
  fi
  echo
  echo "## Warnings"
  echo
  if (( ${#warnings[@]} == 0 )); then
    echo "None."
  else
    printf '%s\n' "${warnings[@]}" | sed 's/^/- /'
  fi
  echo
  echo "## Recommended fixes"
  echo
  if [[ "$status" == "PASS" ]]; then
    echo "- Continue."
  else
    echo "- Remove runtime artifacts from git."
    echo "- Keep private data outside bqa-os."
    echo "- Add local-only paths to .git/info/exclude or .gitignore as appropriate."
    echo "- Re-run this scanner before commit and PR."
  fi
} > "$REPORT"

cat "$REPORT"

if [[ "$status" == "FAIL" ]]; then
  exit 2
fi

if [[ "$status" == "WARN" ]]; then
  exit 1
fi
