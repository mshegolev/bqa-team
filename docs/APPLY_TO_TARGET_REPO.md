# Applying BQA Team to a target repo

BQA Team can be applied to a target repository in two modes. Pick the one that
matches what you need.

| Mode | What runs | Use for |
|------|-----------|---------|
| **Full team** | architect -> GitHub issue -> Codex dev -> PR -> QA -> business accept | A repo where you want the whole role pipeline driving GitHub issues (e.g. the Go `bqa-os` repo). |
| **Testing-only** | just the QA / Test Engineer persona via Codex | You only want Codex to write/extend **tests** in a working copy - no architect, no dev role, no GitHub issue dance. |

---

## Mode 1 - Full team (GitHub pipeline)

This is the default documented in [`README.md`](../README.md). It needs a GitHub
repo (issues + PRs), `gh` authenticated, and `codex` installed.

```bash
cd /path/to/target-repo
bash /opt/develop/bqa-team/scripts/install.sh
python3 scripts/bqa_team_orchestrator.py --repo <owner>/<repo> init
python3 scripts/bqa_team_orchestrator.py --repo <owner>/<repo> --execute ensure-labels
# then: architect -> create-issues -> dev -> qa -> business-accept (or autopilot)
```

Note: the orchestrator's `dev`/`qa` steps assume a Go repo (`go test ./...`)
and GitHub for issues/PRs. For a non-Go, non-GitHub repo (e.g. an ETL pytest
repo hosted on GitLab), use **testing-only** mode instead.

---

## Mode 2 - Testing-only (just the QA role)

Use this when you want Codex to act purely as a QA / Test Engineer and generate
or extend tests directly in a target repo, without standing up the full team.

It uses a single persona file plus a free-text testing task, and runs
`codex exec` inside the target repo. Nothing is committed, pushed, or merged for
you - you review the diff yourself.

### Prerequisites

```bash
git --version
codex --version
```

### Persona resolution

`scripts/bqa_test_only.sh` picks the QA persona automatically:

1. `<target>/.bqa/agents/etl-qa-agent.md` if present (ETL/data repos), else
2. the bundled `team/roles/BQA_OS_QA_Test_Engineer.md`.

Override with `--role <file>`.

### Run it

```bash
# Dry-run: print the exact prompt that would be sent to Codex
bash /opt/develop/bqa-team/scripts/bqa_test_only.sh \
  --target /path/to/target-repo \
  --task "Describe what to test"

# Execute: actually launch Codex inside the target repo
bash /opt/develop/bqa-team/scripts/bqa_test_only.sh \
  --target /path/to/target-repo \
  --task "Describe what to test" \
  --execute
```

The persona is pinned to testing-only behavior: Codex only adds/extends tests,
fixtures, and test config; it must not change product code, add secrets, or use
real session/customer data, and it must report the exact test command(s).

---

## Worked example - VSR 1.4.0 ETL tests

Target repo `bigdata_testing` (checkout at `bigdata_testing_vsr`) is a Python /
pytest ETL test suite. The VSR pipeline lives in `bigdata_tests/VSR/`:

```text
bigdata_tests/VSR/
  etl_variables.py
  tables_config/   # hive_tables.yml, postgre_tables.yml, kafka_messages*.json, oozie.yml, airflow.yml
  tests/           # smoke_tests.py, functional_tests.py
```

Tests run via pytest with ETL/env selection:

```bash
pytest bigdata_tests/VSR/tests/ --etl VSR --env stage
```

Ask Codex to extend the VSR 1.4.0 tests:

```bash
bash /opt/develop/bqa-team/scripts/bqa_test_only.sh \
  --target /Users/m.v.shchegolev/bigdata_testing_vsr \
  --task "Write and extend tests for VSR 1.4.0 in bigdata_tests/VSR/tests/ \
(smoke_tests.py and functional_tests.py). Cover the Kafka -> Hive/Postgres flow \
described in tables_config/. Follow the existing pytest patterns and conftest \
options (--etl VSR --env <env>). Run: pytest bigdata_tests/VSR/tests/ --etl VSR --env stage" \
  --execute
```

Review the resulting diff in the target repo before committing.
