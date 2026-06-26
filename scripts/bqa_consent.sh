#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-$(pwd)}"
CONSENT_DIR="$ROOT/.bqa-team/consent"
CONSENT_FILE="$CONSENT_DIR/team-consent.accepted"

mkdir -p "$CONSENT_DIR"

if [[ -f "$CONSENT_FILE" ]]; then
  exit 0
fi

cat <<'NOTICE'

BQA Team Notice

This workflow can read local runtime files to improve your local BQA Team setup:

- local run logs
- local safety reports
- local validation reports
- local git status and diffs

It can use that context to improve roles, scripts, templates, and runbooks.

Do not run it with sensitive customer data or unsanitized logs.
If you do not agree, stop now and do not run the workflow.

Type exactly: I AGREE

NOTICE

read -r answer
if [[ "$answer" != "I AGREE" ]]; then
  echo "Consent not granted. Stopping."
  exit 3
fi

date -u +%Y-%m-%dT%H:%M:%SZ > "$CONSENT_FILE"
echo "Consent saved to $CONSENT_FILE"
