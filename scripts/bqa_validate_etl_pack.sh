#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-$(pwd)}"
PACK_DIR="$ROOT/.bqa/output/etl-agent-pack"
REPORT_DIR="$ROOT/.bqa/output/validation"
REPORT_FILE="$REPORT_DIR/etl-pack-validation-report.md"
JSON_FILE="$PACK_DIR/statistics/session_stats.json"

mkdir -p "$REPORT_DIR"

required_files=(
  "README_NEXT_STEPS.md"
  "statistics/session_stats.json"
  "statistics/knowledge_summary.md"
  "agents/codex_etl_qa_agent.md"
  "agents/claude_code_etl_qa_agent.md"
  "workflows/etl_regression_workflow.md"
  "workflows/data_reconciliation_workflow.md"
  "workflows/dq_validation_workflow.md"
  "specs/etl_test_spec_template.md"
  "specs/data_quality_checklist.md"
  "specs/source_to_target_mapping_review.md"
  "prompts/generate_etl_test_cases.md"
  "prompts/review_sql_transformation.md"
  "prompts/find_data_quality_risks.md"
  "examples/synthetic_etl_session.md"
  "examples/synthetic_mapping.md"
)

missing=()
empty=()

for file in "${required_files[@]}"; do
  path="$PACK_DIR/$file"
  if [[ ! -f "$path" ]]; then
    missing+=("$file")
  elif [[ ! -s "$path" ]]; then
    empty+=("$file")
  fi
done

json_status="PASS"
if [[ ! -f "$JSON_FILE" ]]; then
  json_status="MISSING"
elif ! python3 -m json.tool "$JSON_FILE" >/dev/null 2>&1; then
  json_status="INVALID"
fi

coverage_terms=(
  "source-to-target"
  "SQL"
  "reconciliation"
  "incremental"
  "null"
  "duplicate"
  "schema drift"
  "partition"
  "row count"
)

coverage_missing=()
combined_text=""
if [[ -d "$PACK_DIR" ]]; then
  combined_text="$(find "$PACK_DIR" -type f \( -name '*.md' -o -name '*.json' \) -print0 | xargs -0 cat 2>/dev/null || true)"
fi

for term in "${coverage_terms[@]}"; do
  if ! grep -qi "$term" <<< "$combined_text"; then
    coverage_missing+=("$term")
  fi
done

status="PASS"
if (( ${#missing[@]} > 0 )) || (( ${#empty[@]} > 0 )) || [[ "$json_status" != "PASS" ]] || (( ${#coverage_missing[@]} > 0 )); then
  status="FAIL"
fi

{
  echo "# ETL Pack Validation Report"
  echo
  echo "Status: $status"
  echo
  echo "Pack dir: $PACK_DIR"
  echo
  echo "## Required files"
  echo
  if (( ${#missing[@]} == 0 )); then
    echo "Missing files: none"
  else
    echo "Missing files:"
    printf -- '- %s\n' "${missing[@]}"
  fi
  echo
  if (( ${#empty[@]} == 0 )); then
    echo "Empty files: none"
  else
    echo "Empty files:"
    printf -- '- %s\n' "${empty[@]}"
  fi
  echo
  echo "## JSON"
  echo
  echo "session_stats.json: $json_status"
  echo
  echo "## Coverage terms"
  echo
  if (( ${#coverage_missing[@]} == 0 )); then
    echo "Missing coverage terms: none"
  else
    echo "Missing coverage terms:"
    printf -- '- %s\n' "${coverage_missing[@]}"
  fi
} > "$REPORT_FILE"

cat "$REPORT_FILE"

if [[ "$status" != "PASS" ]]; then
  exit 1
fi
