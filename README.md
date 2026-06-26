# BQA Team

BQA Team is a reusable role-orchestrator pack for running BQA-OS development with GitHub Issues, Codex CLI, QA review, and business acceptance.

It is intentionally separated from `bqa-os`:

- `bqa-os` = public Go CLI / runtime engine.
- `bqa-team` = reusable team prompts, orchestrator scripts, issue templates, and workflow automation.
- `.bqa-team/generated/`, `.bqa-team/logs/`, and `.bqa-team/state.json` are local runtime artifacts and should not be committed into product repositories.

## What it automates

```text
business backlog
  -> architect review
  -> GitHub issue
  -> developer role via Codex CLI
  -> PR
  -> QA role
  -> bug issue if QA fails
  -> fix
  -> business acceptance
```

## Requirements

Install these locally:

```bash
python3 --version
git --version
gh --version
codex --version
```

Authenticate GitHub CLI:

```bash
gh auth login
gh auth status
```

Optional GitHub Projects permission:

```bash
gh auth refresh -s project
```

## Install into a target project

From any project repo, for example `/opt/develop/bqa-os`:

```bash
cd /opt/develop/bqa-os

# clone this team pack outside the product repo if needed
git clone https://github.com/mshegolev/bqa-team ../bqa-team

# install/update local team files
bash ../bqa-team/scripts/install.sh

# initialize local runtime state
python3 scripts/bqa_team_orchestrator.py --repo mshegolev/bqa-os init
```

This installs:

```text
scripts/bqa_team_orchestrator.py
.bqa-team/backlog/
.bqa-team/roles/
.bqa-team/templates/
```

## Recommended `.gitignore` in target repos

Keep role definitions and backlog if you want to version them, but ignore runtime output:

```gitignore
# BQA local runtime artifacts
.bqa/
.bqa-team/generated/
.bqa-team/logs/
.bqa-team/state.json
bqa_team_orchestrator_pack/
error.log
```

## First setup in target repo

```bash
cd /opt/develop/bqa-os

python3 scripts/bqa_team_orchestrator.py --repo mshegolev/bqa-os --execute ensure-labels
python3 scripts/bqa_team_orchestrator.py --repo mshegolev/bqa-os architect
python3 scripts/bqa_team_orchestrator.py --repo mshegolev/bqa-os --execute create-issues
```

Note: global flags go before the command:

```bash
# correct
python3 scripts/bqa_team_orchestrator.py --repo mshegolev/bqa-os --execute create-issues

# wrong
python3 scripts/bqa_team_orchestrator.py --repo mshegolev/bqa-os create-issues --execute
```

## Run development for one issue

```bash
python3 scripts/bqa_team_orchestrator.py --repo mshegolev/bqa-os --execute dev --issue 28
```

After Codex finishes, inspect the diff before committing:

```bash
git status
git diff --stat
go test ./...
```

Commit only files related to that issue. Avoid `git add .` unless the diff is clean.

## Run QA for a PR

```bash
python3 scripts/bqa_team_orchestrator.py --repo mshegolev/bqa-os --execute qa --pr <PR_NUMBER>
```

If QA fails, the orchestrator creates a bug issue with:

```text
bqa:bug
bqa:qa-failed
bqa:ready-dev
```

## Run business acceptance

```bash
python3 scripts/bqa_team_orchestrator.py --repo mshegolev/bqa-os --execute business-accept --pr <PR_NUMBER>
```

## Safe weekend run

Do not start with an unlimited loop. Run bounded batches:

```bash
mkdir -p .bqa-team/logs

python3 scripts/bqa_team_orchestrator.py \
  --repo mshegolev/bqa-os \
  --execute \
  loop \
  --once \
  2>&1 | tee .bqa-team/logs/first-loop-$(date +%Y%m%d-%H%M%S).log
```

Then run selected issues manually:

```bash
python3 scripts/bqa_team_orchestrator.py --repo mshegolev/bqa-os --execute dev --issue 28
python3 scripts/bqa_team_orchestrator.py --repo mshegolev/bqa-os --execute dev --issue 29
python3 scripts/bqa_team_orchestrator.py --repo mshegolev/bqa-os --execute dev --issue 30
```

## Update in target repo

```bash
cd ../bqa-team
git pull

cd ../bqa-os
bash ../bqa-team/scripts/install.sh
```

Then review local changes:

```bash
git status
git diff --stat
```

## Question / blocker workflow

When a developer, QA role, or business role hits ambiguity, create a question issue:

```bash
scripts/bqa_question.sh \
  mshegolev/bqa-os \
  <BLOCKED_ISSUE_NUMBER> \
  architecture \
  "Should this be implemented in core or adapter?"
```

Supported question types:

- `architecture`
- `product`
- `qa`
- `implementation`

Question issues get labels such as `bqa:question`, `bqa:needs-architect`, and the blocked issue gets `bqa:blocked`.

## Repository contents

```text
scripts/
  bqa_team_orchestrator.py
  bqa_question.sh
  install.sh

team/
  backlog/
  roles/
  templates/
```

## Safety rules

- Do not commit real session logs.
- Do not commit secrets.
- Do not commit customer data.
- Do not put private brain knowledge into public repos.
- Keep tasks small: one issue -> one branch -> one PR -> QA -> business acceptance.
