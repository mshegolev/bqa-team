#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-$(pwd)}"
MAX_ATTEMPTS="${BQA_SELFHEAL_MAX_ATTEMPTS:-3}"
LOG_DIR="$ROOT/.bqa-team/logs"
PROMPT_DIR="$ROOT/.bqa-team/prompts"
PACK_DIR="$ROOT/.bqa/output/etl-agent-pack"
VALIDATOR="$ROOT/scripts/bqa_validate_etl_pack.sh"
GUARD="$ROOT/scripts/bqa_agent_guard.sh"
CONSENT="$ROOT/scripts/bqa_consent.sh"

mkdir -p "$LOG_DIR" "$PROMPT_DIR" "$ROOT/.bqa/output"

if [[ -x "$CONSENT" ]]; then
  bash "$CONSENT" "$ROOT"
fi

if [[ ! -x "$VALIDATOR" ]]; then
  echo "ERROR: validator not found or not executable: $VALIDATOR" >&2
  exit 2
fi

run_guard() {
  if [[ -x "$GUARD" ]]; then
    set +e
    BQA_TARGET_GOAL="ETL QA Pack under .bqa/output/etl-agent-pack" bash "$GUARD" "$ROOT"
    code=$?
    set -e
    if [[ "$code" -eq 2 ]]; then
      echo "Agent guard requested STOP. Context saved under .bqa-team/safety/." >&2
      exit 2
    fi
  fi
}

build_prompt="$PROMPT_DIR/build_etl_qa_agent_pack.md"
heal_prompt="$PROMPT_DIR/selfheal_etl_qa_agent_pack.md"

if [[ ! -f "$build_prompt" ]]; then
  cat > "$build_prompt" <<'PROMPT'
You are the BQA-OS ETL QA Pack builder.

Create a local ETL QA Pack for coding-agent tools.

Output folder:
.bqa/output/etl-agent-pack/

Required files:
- README_NEXT_STEPS.md
- statistics/session_stats.json
- statistics/knowledge_summary.md
- agents/codex_etl_qa_agent.md
- agents/claude_code_etl_qa_agent.md
- workflows/etl_regression_workflow.md
- workflows/data_reconciliation_workflow.md
- workflows/dq_validation_workflow.md
- specs/etl_test_spec_template.md
- specs/data_quality_checklist.md
- specs/source_to_target_mapping_review.md
- prompts/generate_etl_test_cases.md
- prompts/review_sql_transformation.md
- prompts/find_data_quality_risks.md
- examples/synthetic_etl_session.md
- examples/synthetic_mapping.md

The pack must cover ETL QA: mapping review, transformation review, reconciliation, full load, incremental load, null checks, duplicate checks, schema drift, partition/date-window checks, row count checks, checksum checks, late arriving data, and slowly changing dimensions.

Use markdown and JSON artifacts. Use clearly marked synthetic examples when real curated input is not available. Print created files.
PROMPT
fi

run_guard || true

attempt=1
while (( attempt <= MAX_ATTEMPTS )); do
  echo "=== BQA ETL selfheal attempt $attempt/$MAX_ATTEMPTS ==="

  run_guard || true

  if [[ $attempt -eq 1 && ! -d "$PACK_DIR" ]]; then
    codex exec "$(cat "$build_prompt")" 2>&1 | tee "$LOG_DIR/etl-pack-build-attempt-$attempt.log" || true
  fi

  run_guard || true

  if bash "$VALIDATOR" "$ROOT"; then
    echo "ETL pack validation passed."
    zip -r "$ROOT/.bqa/output/etl-agent-pack.zip" "$PACK_DIR" >/dev/null 2>&1 || true
    run_guard || true
    exit 0
  fi

  report="$ROOT/.bqa/output/validation/etl-pack-validation-report.md"
  cat > "$heal_prompt" <<PROMPT
You are the BQA-OS ETL QA Pack self-healing agent.

The current ETL QA Pack failed validation.

Validation report:

$(cat "$report" 2>/dev/null || echo "No validation report found.")

Fix the local files under:
.bqa/output/etl-agent-pack/

Do not delete good existing files. Add or improve only what is missing, empty, invalid, or incomplete.

Required behavior:
- create missing files;
- repair invalid JSON;
- make prompts copy-paste ready;
- make examples clearly synthetic;
- cover ETL mapping review, SQL review, reconciliation, incremental and full loads, null checks, duplicate checks, schema drift, partition/date-window checks, row count checks, checksum checks, late arriving data, and slowly changing dimensions;
- print a concise summary of fixes.
PROMPT

  codex exec "$(cat "$heal_prompt")" 2>&1 | tee "$LOG_DIR/etl-pack-selfheal-attempt-$attempt.log" || true
  attempt=$((attempt + 1))
done

echo "ETL pack selfheal failed after $MAX_ATTEMPTS attempts." >&2
bash "$VALIDATOR" "$ROOT" || true
run_guard || true
exit 1
