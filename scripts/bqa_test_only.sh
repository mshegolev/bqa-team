#!/usr/bin/env bash
# BQA Team - testing-only runner.
#
# Applies ONLY the QA / Test Engineer role of the BQA team to a target repo,
# without the full architect -> dev -> qa -> business GitHub pipeline.
#
# It builds a Codex prompt from a QA role file + a free-text testing task and
# runs `codex exec` inside the target repo. Use it to ask Codex to write or
# extend tests (e.g. ETL pipeline tests) directly in a working copy.
#
# Usage:
#   bash bqa_test_only.sh --target <repo-dir> --task "<what to test>" [options]
#
# Options:
#   --target DIR     Target git repo to run Codex in (required).
#   --task TEXT      Testing task description (required).
#   --role FILE      Role/persona file. Default: auto-detect
#                    <target>/.bqa/agents/etl-qa-agent.md, else the bundled
#                    team/roles/BQA_OS_QA_Test_Engineer.md.
#   --execute        Actually run Codex. Without it, prints the prompt (dry-run).
#
# Example (VSR ETL pipeline):
#   bash scripts/bqa_test_only.sh \
#     --target /Users/m.v.shchegolev/bigdata_testing_vsr \
#     --task "Write/extend tests for VSR 1.4.0 in bigdata_tests/VSR/tests/ \
#             (smoke + functional). Run: pytest bigdata_tests/VSR/tests/ --etl VSR --env stage" \
#     --execute
set -euo pipefail

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="" TASK="" ROLE="" EXECUTE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target)  TARGET="$2"; shift 2;;
    --task)    TASK="$2";   shift 2;;
    --role)    ROLE="$2";   shift 2;;
    --execute) EXECUTE=1;   shift;;
    *) echo "Unknown option: $1" >&2; exit 2;;
  esac
done

[[ -n "$TARGET" ]] || { echo "ERROR: --target is required" >&2; exit 2; }
[[ -n "$TASK"   ]] || { echo "ERROR: --task is required"   >&2; exit 2; }
[[ -d "$TARGET/.git" ]] || { echo "ERROR: not a git repo: $TARGET" >&2; exit 2; }

# Resolve the QA persona: prefer the target repo's ETL QA agent, else bundled role.
if [[ -z "$ROLE" ]]; then
  if [[ -f "$TARGET/.bqa/agents/etl-qa-agent.md" ]]; then
    ROLE="$TARGET/.bqa/agents/etl-qa-agent.md"
  else
    ROLE="$SOURCE_DIR/team/roles/BQA_OS_QA_Test_Engineer.md"
  fi
fi
[[ -f "$ROLE" ]] || { echo "ERROR: role file not found: $ROLE" >&2; exit 2; }

PROMPT="$(cat "$ROLE")

---

You are acting in TESTING-ONLY mode. Do NOT change product/source code.
Only add or extend tests, fixtures, and test config in this repository.

Testing task:
$TASK

Rules:
- Follow existing test patterns and frameworks already in the repo.
- Keep changes focused; do not touch unrelated code.
- Do not add secrets, credentials, or real session/customer data.
- Show the exact test command(s) you ran or recommend.
- Summarize: files changed, tests added, how to run them, remaining risks."

if [[ "$EXECUTE" -eq 0 ]]; then
  echo "=== DRY-RUN (role: $ROLE, target: $TARGET) ==="
  echo "$PROMPT"
  echo "=== rerun with --execute to launch Codex ==="
  exit 0
fi

command -v codex >/dev/null || { echo "ERROR: codex CLI not found" >&2; exit 3; }
echo "Running Codex (testing-only) in $TARGET ..." >&2
( cd "$TARGET" && codex exec "$PROMPT" )
