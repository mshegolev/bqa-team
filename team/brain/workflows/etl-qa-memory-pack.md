# ETL QA Memory Pack Workflow

## Purpose

Generate and validate a reusable ETL QA memory pack for data-heavy projects.

## Flow

1. Gather sanitized or synthetic ETL evidence.
2. Build `.bqa/output/etl-agent-pack`.
3. Validate required files and coverage terms.
4. Run self-heal if validation fails and consent is granted.
5. Review guard reports before syncing knowledge.

## Required Checks

```bash
scripts/bqa_validate_etl_pack.sh
scripts/bqa_agent_guard.sh
```

## Coverage Topics

Mapping review, SQL transformation review, reconciliation, incremental loads,
full loads, nulls, duplicates, schema drift, partitions, row counts, checksums,
late arriving data, and slowly changing dimensions.
