#!/usr/bin/env bash
set -euo pipefail

REPO="${1:?repo required, e.g. mshegolev/bqa-os}"
BLOCKS_ISSUE="${2:?blocked issue number required}"
TYPE="${3:?type required: architecture|product|qa|implementation}"
TITLE="${4:?title required}"

BODY_FILE="$(mktemp)"
cat > "$BODY_FILE" <<BODY
## Question

$TITLE

## Type

$TYPE

## Blocks issue

#$BLOCKS_ISSUE

## Context

Describe what the agent/developer was doing and why this question appeared.

## Options

### Option A

...

### Option B

...

## Recommendation

...

## Needed from

Tech Lead / Business Owner / QA Domain Advisor

## Resolution

_To be filled after decision._
BODY

case "$TYPE" in
  architecture) NEEDS_LABEL="bqa:needs-architect" ;;
  product) NEEDS_LABEL="bqa:needs-product" ;;
  qa) NEEDS_LABEL="bqa:needs-qa" ;;
  implementation) NEEDS_LABEL="bqa:needs-architect" ;;
  *) NEEDS_LABEL="bqa:needs-architect" ;;
esac

QUESTION_URL="$(gh issue create \
  --repo "$REPO" \
  --title "Question: $TITLE" \
  --body-file "$BODY_FILE" \
  --label "bqa:question" \
  --label "$NEEDS_LABEL")"

gh issue edit "$BLOCKS_ISSUE" \
  --repo "$REPO" \
  --add-label "bqa:blocked"

gh issue comment "$BLOCKS_ISSUE" \
  --repo "$REPO" \
  --body "Blocked by question: $QUESTION_URL"

echo "$QUESTION_URL"
