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

## Export unified BQA Brain artifacts

`bqa-team` keeps a unified registry of reusable agents, skills, workflows,
guardrails, project profiles, and memory indexes in:

```text
team/brain/registry.json
```

Export those artifacts into a local `bqa-brain` cache:

```bash
scripts/bqa_brain_export.sh --brain-dir "$HOME/.bqa/brain"
```

For `bqa-os` setup and sync commands, see
[`docs/BQA_BRAIN_INTEGRATION.md`](docs/BQA_BRAIN_INTEGRATION.md).

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

## Run the static demo archive app

Open the browser-only demo directly:

```text
demo/site/index.html
```

The bundled synthetic archive lives at:

```text
demo/fixtures/bqa-demo-archive.json
```

The demo parses JSON locally in the browser, renders generated BQA artifacts, and downloads a generated result JSON. It does not require a backend service.

## Run autopilot across GitHub issues

Autopilot processes open GitHub issues with `bqa:ready-dev` one at a time:

```text
bqa:ready-dev issue
  -> subagent routing
  -> developer role
  -> commit, push, PR
  -> QA role
  -> business acceptance role
  -> optional PR merge and issue close
```

Prepare the target repo:

```bash
cd /opt/develop/bqa-os

gh auth status
codex --version
git status --short

python3 ../bqa-team/scripts/bqa_team_orchestrator.py \
  --repo mshegolev/bqa-os \
  --execute ensure-labels
```

Run a bounded long cycle:

```bash
mkdir -p .bqa-team/logs

nohup python3 ../bqa-team/scripts/bqa_team_orchestrator.py \
  --repo mshegolev/bqa-os \
  --execute \
  autopilot \
  --max-cycles 200 \
  --sleep-seconds 60 \
  --all-open \
  --oldest-first \
  --base-branch main \
  --merge \
  --close-issue \
  --replan-every 7 \
  --vision-file .bqa-team/PROJECT_VISION.md \
  > .bqa-team/logs/autopilot.log 2>&1 &
```

Or create a reusable config once and run it through the wrapper:

```bash
cd /opt/develop/bqa-os

../bqa-team/scripts/bqa_autopilot.sh configure
../bqa-team/scripts/bqa_autopilot.sh start
```

Watch it:

```bash
../bqa-team/scripts/bqa_autopilot.sh status
../bqa-team/scripts/bqa_autopilot.sh logs
```

Stop it:

```bash
../bqa-team/scripts/bqa_autopilot.sh stop
```

Autopilot intentionally refuses unbounded runs. Use `--once` for one issue or `--max-cycles N` for a long run.

By default, a blocked issue does not stop the whole run. Autopilot skips issues labeled `bqa:blocked` and issues whose body explicitly depends on a blocked issue, then keeps processing independent work. To restore strict stop-on-blocked behavior for a run, pass `--stop-on-fail`; for a reusable config, set `stop_on_fail` to `true`.

The wrapper uses `nohup`, writes `.bqa-team/status/autopilot.pid`, and keeps running after the terminal is closed. The monitor writes:

```text
.bqa-team/status/autopilot-status.json
.bqa-team/status/autopilot-status.md
.bqa-team/status/autopilot-history.jsonl
```

The status view shows open, ready, doing, blocked, and completed counts. The history ledger is append-only JSONL: one record per autopilot cycle with status, stop reason, selected issue, branch, PR, and subagent routing metadata when available.

Generate a visual issue view:

```bash
../bqa-team/scripts/bqa_autopilot.sh view
```

This writes:

```text
.bqa-team/status/project-view.html
.bqa-team/status/project-view.json
```

The HTML view shows summary counts, a Gantt-like status timeline, issue detail cards, and dependency links parsed from explicit phrases such as `Depends on #12`, `blocked by #12`, `requires #12`, or `BQA_DEPENDS_ON: #12,#14` in issue bodies.

Before each issue is executed, autopilot asks the router to choose exactly one subagent from the role catalog, for example `go-cli-implementer`, `senior-go-ai-engineer`, `designer-frontend`, `devsecops-guard`, or `qa-test-engineer`. The routing decision is saved in:

```text
.bqa-team/generated/runs/route_issue_<ISSUE_NUMBER>.json
```

To force one subagent for a controlled run:

```bash
python3 ../bqa-team/scripts/bqa_team_orchestrator.py \
  --repo mshegolev/bqa-os \
  --execute \
  autopilot \
  --once \
  --all-open \
  --subagent senior-go-ai-engineer
```

## Replan GitHub issues

Replanning reviews the current open issue backlog against the project vision. It can create missing `bqa:ready-dev` issues and close obsolete issues with the `bqa:cancelled` label.

Store the project vision in the target repo:

```bash
cat > .bqa-team/PROJECT_VISION.md
```

Run replanning directly:

```bash
python3 ../bqa-team/scripts/bqa_team_orchestrator.py \
  --repo mshegolev/bqa-os \
  --execute \
  replan \
  --vision-file .bqa-team/PROJECT_VISION.md
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
