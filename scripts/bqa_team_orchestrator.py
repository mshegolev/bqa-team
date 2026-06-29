#!/usr/bin/env python3
"""
BQA Team Orchestrator

Local orchestration layer for BQA role prompts + GitHub Issues + Codex CLI.

Safety:
- Dry-run by default.
- Mutating operations require --execute.
- Do not run unbounded loops.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import time
from copy import copy
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

ROOT = Path.cwd()
TEAM_DIR = ROOT / ".bqa-team"
ROLES_DIR = TEAM_DIR / "roles"
BACKLOG_DIR = TEAM_DIR / "backlog"
GENERATED_DIR = TEAM_DIR / "generated"
ISSUES_DIR = GENERATED_DIR / "issues"
PROMPTS_DIR = GENERATED_DIR / "prompts"
RUNS_DIR = GENERATED_DIR / "runs"
TMP_DIR = GENERATED_DIR / "tmp"
STATUS_DIR = TEAM_DIR / "status"
STATUS_JSON = STATUS_DIR / "autopilot-status.json"
STATUS_MD = STATUS_DIR / "autopilot-status.md"
PROJECT_VIEW_JSON = STATUS_DIR / "project-view.json"
PROJECT_VIEW_HTML = STATUS_DIR / "project-view.html"
AUTOPILOT_CONFIG = TEAM_DIR / "autopilot-config.json"
STATE_FILE = TEAM_DIR / "state.json"

LABELS = {
    "bqa:business": "Business-originated task",
    "bqa:needs-arch": "Needs technical architecture review",
    "bqa:arch-approved": "Approved by technical architect",
    "bqa:ready-dev": "Ready for implementation",
    "bqa:in-dev": "Currently being implemented",
    "bqa:ready-qa": "Ready for QA verification",
    "bqa:qa-failed": "QA found issues",
    "bqa:bug": "Bug found by QA or business review",
    "bqa:ready-business": "Ready for business acceptance",
    "bqa:business-approved": "Accepted by business owner",
    "bqa:done": "Done",
    "bqa:cancelled": "Cancelled by replanning because it is no longer relevant",
    "bqa:static-site": "Static web application work",
    "bqa:game-ui": "Game-style team visualization work",
    "bqa:codex-team": "Codex team automation work",
    "bqa:question": "Open question raised during development",
    "bqa:blocked": "Task is blocked by an unresolved question",
    "bqa:decision": "Resolved decision or clarification",
    "bqa:needs-product": "Needs product/business clarification",
    "bqa:needs-architect": "Needs technical architect decision",
    "bqa:needs-qa": "Needs QA/domain clarification",
}

ROLE_FILES = {
    "business": "Founder_Product_Sales_Implementation.md",
    "architect": "BQA_OS_Tech_Lead_Architect.md",
    "developer": "BQA_OS_Go_CLI_Implementer.md",
    "qa": "BQA_OS_QA_Test_Engineer.md",
    "designer": "Designer_Frontend.md",
    "devroom": "BQA_OS_Dev_Room.md",
}

SUBAGENT_FILES = {
    "go-cli-implementer": "BQA_OS_Go_CLI_Implementer.md",
    "senior-go-ai-engineer": "Senior_Go_AI_Engineer.md",
    "tech-lead-architect": "BQA_OS_Tech_Lead_Architect.md",
    "qa-test-engineer": "BQA_OS_QA_Test_Engineer.md",
    "designer-frontend": "Designer_Frontend.md",
    "devsecops-guard": "DevSecOps_Guard.md",
    "agent-safety-drift-guard": "Agent_Safety_Drift_Guard.md",
    "devrel-content-community": "DevRel_Content_Community.md",
    "founder-product-sales-implementation": "Founder_Product_Sales_Implementation.md",
    "solutions-engineer-implementation": "Solutions_Engineer_Implementation.md",
    "pilot-manager": "Pilot_Manager.md",
    "qa-domain-advisor": "QA_Domain_Advisor.md",
}

ISSUE_TEMPLATE = """## Context

{context}

## Goal

{goal}

## Scope

### Create/change

{create_change}

### Do not touch

{do_not_touch}

## Architecture

Follow:

core use case
↓
port interface
↓
adapter implementation
↓
CLI wiring

Business logic must not live directly in Cobra commands.

## Behavior

{behavior}

## Acceptance criteria

{acceptance}

## Manual verification

```bash
{verification}
```

## Role routing

- Business owner: validates value and scope.
- Technical architect: validates architecture before development.
- Developer: implements only after architecture approval.
- QA: verifies and creates bug issues if acceptance criteria fail.
- Business owner: performs final acceptance.
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def run(cmd: list[str], *, execute: bool, capture: bool = False, check: bool = True) -> subprocess.CompletedProcess[str]:
    printable = " ".join(shlex.quote(c) for c in cmd)
    if not execute:
        print(f"DRY-RUN: {printable}")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
    log(f"RUN: {printable}")
    return subprocess.run(cmd, cwd=str(ROOT), text=True, capture_output=capture, check=check)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def slugify(text: str, max_len: int = 56) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-") or "task"
    return text[:max_len].strip("-")


def require_tools(names: Iterable[str], execute: bool) -> None:
    for name in names:
        result = subprocess.run(["bash", "-lc", f"command -v {shlex.quote(name)}"], text=True, capture_output=True)
        if result.returncode != 0:
            msg = f"Required tool not found: {name}"
            if execute:
                raise SystemExit(msg)
            log(f"WARNING: {msg}")


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(read(STATE_FILE))
    return {"processed_backlog": {}, "created_issues": {}, "runs": []}


def save_state(state: dict) -> None:
    write(STATE_FILE, json.dumps(state, indent=2, ensure_ascii=False) + "\n")


def load_role(role: str) -> str:
    path = ROLES_DIR / ROLE_FILES[role]
    if not path.exists():
        raise SystemExit(f"Missing role prompt: {path}")
    return read(path)


def load_subagent(subagent: str) -> str:
    filename = SUBAGENT_FILES.get(subagent, SUBAGENT_FILES["go-cli-implementer"])
    path = ROLES_DIR / filename
    if not path.exists():
        return load_role("developer")
    return read(path)


def cmd_init(args: argparse.Namespace) -> None:
    for d in [ROLES_DIR, BACKLOG_DIR, ISSUES_DIR, PROMPTS_DIR, RUNS_DIR, TMP_DIR, STATUS_DIR]:
        d.mkdir(parents=True, exist_ok=True)
    if not STATE_FILE.exists():
        save_state(load_state())
    log(f"Initialized {TEAM_DIR}")
    log("Put business task markdown files into .bqa-team/backlog/")


def cmd_seed(args: argparse.Namespace) -> None:
    BACKLOG_DIR.mkdir(parents=True, exist_ok=True)
    seeds = {
        "001_static_site_app.md": """# Business Task: Static BQA Web App MVP

Create a static HTML/JS application for BQA-OS where a user can upload a specially marked session archive and receive a generated output archive containing agents, workflows, specs, instructions, and recommendations.

Constraints:
- static site only: HTML/CSS/JavaScript;
- local-first by default;
- no private data uploaded externally;
- output downloadable as zip;
- include synthetic sample input only.
""",
        "002_agent_game_visualization.md": """# Business Task: Agent Team Visualization / Warcraft-style Map MVP

Create a lightweight static dashboard that represents BQA agents as units on a board/map and shows task flow from business idea to architecture review, development, QA, bug fixing, business acceptance, and done.
""",
        "003_codex_team_pipeline.md": """# Business Task: Codex Team Pipeline MVP

Create a scripted workflow where business tasks are transformed into GitHub issues, routed through architecture review, implemented by role-specific Codex agents, checked by QA, and finally sent to business acceptance.
""",
    }
    for name, body in seeds.items():
        path = BACKLOG_DIR / name
        if not path.exists():
            write(path, body)
            log(f"Seeded {path}")


def cmd_ensure_labels(args: argparse.Namespace) -> None:
    require_tools(["gh"], args.execute)
    for name, desc in LABELS.items():
        run([
            "gh", "label", "create", name,
            "--repo", args.repo,
            "--description", desc,
            "--force",
        ], execute=args.execute, check=False)


def fallback_issue_spec(path: Path) -> str:
    body = read(path)
    first = body.splitlines()[0] if body.splitlines() else path.stem
    title = first.replace("# Business Task:", "").replace("#", "").strip() or path.stem
    labels = ["bqa:arch-approved", "bqa:ready-dev"]
    text = body.lower()
    if "static" in text or "landing" in text or "site" in text:
        labels.append("bqa:static-site")
    if "warcraft" in text or "visualization" in text or "game" in text:
        labels.append("bqa:game-ui")
    if "codex" in text or "pipeline" in text:
        labels.append("bqa:codex-team")
    spec = ISSUE_TEMPLATE.format(
        context=f"Business task from `{path.name}`. This issue was routed through the technical architect stage.",
        goal=title,
        create_change="- To be refined by Architect/Codex output before execution.",
        do_not_touch="- Private repo data\n- Real session logs\n- Secrets",
        behavior=body,
        acceptance="- [ ] Architecture boundaries are respected.\n- [ ] Synthetic data only.\n- [ ] Manual verification steps pass.",
        verification="go test ./...",
    )
    return f"---ISSUE---\nTITLE: {title}\nLABELS: {','.join(labels)}\nBODY:\n{spec}\n---END---\n"


def architect_prompt(path: Path, repo: str) -> str:
    architect = load_role("architect")
    devroom = ""
    try:
        devroom = load_role("devroom")[:8000]
    except SystemExit:
        pass
    return f"""
{architect}

---

Additional Dev Room context:

{devroom}

---

Transform this business task into one or more GitHub-ready issue specs for `{repo}`.

Business task file: {path.name}

Business task:

{read(path)}

Rules:
- Every business task must pass through technical architecture review before development.
- Keep issues small and implementation-ready.
- Follow the BQA-OS issue template.
- Preserve hexagonal architecture.
- No private data, real session logs, or secrets.
- For static site tasks, prefer plain HTML/CSS/JS MVP unless architecture says otherwise.

Return markdown with this exact structure for each issue:

---ISSUE---
TITLE: <short title>
LABELS: bqa:arch-approved,bqa:ready-dev,<domain labels>
BODY:
<full GitHub issue body using the project template>
---END---
""".strip()


def cmd_architect(args: argparse.Namespace) -> None:
    require_tools(["codex"], args.execute)
    state = load_state()
    tasks = sorted(BACKLOG_DIR.glob("*.md"))
    if not tasks:
        log("No backlog markdown files found in .bqa-team/backlog/")
        return
    for path in tasks:
        if state["processed_backlog"].get(path.name) and not args.force:
            log(f"Skip already architected: {path.name}")
            continue
        prompt = architect_prompt(path, args.repo)
        prompt_path = PROMPTS_DIR / f"architect_{path.stem}.md"
        output_path = ISSUES_DIR / f"{path.stem}.issues.md"
        write(prompt_path, prompt)
        if args.execute:
            result = run(["codex", "exec", prompt], execute=True, capture=True, check=False)
            if result.returncode != 0:
                write(output_path.with_suffix(".error.txt"), result.stderr)
                log(f"Architect failed for {path.name}; see {output_path.with_suffix('.error.txt')}")
                continue
            write(output_path, result.stdout)
        else:
            write(output_path, fallback_issue_spec(path))
        state["processed_backlog"][path.name] = {"architected_at": now(), "output": str(output_path)}
        save_state(state)
        log(f"Architected {path.name} -> {output_path}")


def parse_issue_blocks(text: str) -> list[dict]:
    blocks = re.findall(r"---ISSUE---(.*?)---END---", text, re.S)
    issues = []
    for block in blocks:
        title_match = re.search(r"^TITLE:\s*(.+)$", block, re.M)
        labels_match = re.search(r"^LABELS:\s*(.+)$", block, re.M)
        body_match = re.search(r"^BODY:\s*(.*)", block, re.M | re.S)
        if not title_match or not body_match:
            continue
        labels = []
        if labels_match:
            labels = [x.strip() for x in labels_match.group(1).split(",") if x.strip()]
        issues.append({"title": title_match.group(1).strip(), "labels": labels, "body": body_match.group(1).strip()})
    return issues


def cmd_create_issues(args: argparse.Namespace) -> None:
    require_tools(["gh"], args.execute)
    state = load_state()
    for spec_path in sorted(ISSUES_DIR.glob("*.issues.md")):
        for issue in parse_issue_blocks(read(spec_path)):
            key = f"{spec_path.name}:{issue['title']}"
            if state["created_issues"].get(key) and not args.force:
                log(f"Skip existing issue: {issue['title']}")
                continue
            body_file = TMP_DIR / f"{slugify(issue['title'])}.md"
            write(body_file, issue["body"])
            cmd = ["gh", "issue", "create", "--repo", args.repo, "--title", issue["title"], "--body-file", str(body_file)]
            for label in issue["labels"]:
                cmd += ["--label", label]
            result = run(cmd, execute=args.execute, capture=args.execute, check=False)
            url = result.stdout.strip() if args.execute else "DRY-RUN"
            state["created_issues"][key] = {"created_at": now(), "url": url, "labels": issue["labels"]}
            save_state(state)
            log(f"Issue ready: {issue['title']} -> {url}")


def issue_json(repo: str, number: int, execute: bool) -> str:
    result = run(["gh", "issue", "view", str(number), "--repo", repo, "--json", "title,body,labels", "--jq", "."], execute=execute, capture=True)
    return result.stdout if execute else json.dumps({"title": f"Issue {number}", "body": "DRY-RUN", "labels": []}, indent=2)


def subagent_catalog() -> str:
    return "\n".join(f"- {name}: {filename}" for name, filename in sorted(SUBAGENT_FILES.items()))


def parse_subagent_decision(text: str) -> dict:
    json_match = re.search(r"\{.*?\}", text, re.S)
    if json_match:
        try:
            data = json.loads(json_match.group(0))
            subagent = str(data.get("subagent", "")).strip()
            if subagent in SUBAGENT_FILES:
                return {"subagent": subagent, "reason": str(data.get("reason", "")).strip() or "Selected by router."}
        except json.JSONDecodeError:
            pass

    match = re.search(r"^SUBAGENT:\s*([a-z0-9-]+)\s*$", text, re.M)
    if match and match.group(1) in SUBAGENT_FILES:
        reason_match = re.search(r"^REASON:\s*(.+)$", text, re.M)
        return {
            "subagent": match.group(1),
            "reason": reason_match.group(1).strip() if reason_match else "Selected by router.",
        }

    return {"subagent": "go-cli-implementer", "reason": "Router output was missing or invalid; using default implementer."}


def route_issue_to_subagent(repo: str, issue: int, raw_issue_json: str, execute: bool) -> dict:
    prompt = f"""
You are the BQA Team Router.

Choose exactly one subagent to execute GitHub issue #{issue} in `{repo}`.

Available subagents:

{subagent_catalog()}

Issue JSON:

{raw_issue_json}

Rules:
- Return one and only one subagent key from the catalog.
- Prefer `go-cli-implementer` for normal Go CLI/runtime work.
- Prefer `senior-go-ai-engineer` for complex AI/runtime architecture implementation.
- Prefer `designer-frontend` for UI, static site, layout, and frontend implementation.
- Prefer `devsecops-guard` for security, scanning, guardrail, and compliance tasks.
- Prefer `qa-test-engineer` or `qa-domain-advisor` only when the issue is primarily test/QA design.
- Do not return a team, only a single subagent key.

Return strict JSON:
{{"subagent":"<key>","reason":"<short reason>"}}
""".strip()
    if not execute:
        return {"subagent": "go-cli-implementer", "reason": "Dry run default."}
    result = run(["codex", "exec", prompt], execute=True, capture=True, check=False)
    return parse_subagent_decision(result.stdout + "\n" + result.stderr)


def save_subagent_route(issue: int, route: dict) -> None:
    write(RUNS_DIR / f"route_issue_{issue}.json", json.dumps(route, indent=2, ensure_ascii=False) + "\n")


def dev_prompt(raw_issue_json: str, repo: str, subagent: str = "go-cli-implementer") -> str:
    developer = load_subagent(subagent)
    architect = load_role("architect")[:6000]
    return f"""
{developer}

---

Architectural constraints:

{architect}

---

Implement the following GitHub issue from `{repo}`.

Selected subagent: {subagent}

Issue JSON:

{raw_issue_json}

Workflow rules:
- Treat the issue as architecture-approved.
- Create a small, focused implementation.
- Follow AGENTS.md.
- Do not add private data, real session logs, or secrets.
- Add/update tests where reasonable.
- Run `go test ./...`.
- Do not merge anything.
- If blocked or requirements are ambiguous, output QUESTION_STATUS: OPEN with QUESTION_TYPE and BLOCKS_ISSUE instead of guessing silently.

At the end, summarize:
- files changed;
- tests run;
- any remaining risks.
""".strip()


def cmd_dev(args: argparse.Namespace) -> None:
    require_tools(["gh", "git", "codex"], args.execute)
    raw = issue_json(args.repo, args.issue, args.execute)
    title = json.loads(raw).get("title", f"issue-{args.issue}") if raw else f"issue-{args.issue}"
    branch = args.branch or f"codex/issue-{args.issue}-{slugify(title, 32)}"
    subagent = getattr(args, "subagent", None) or "go-cli-implementer"
    prompt = dev_prompt(raw, args.repo, subagent)
    write(PROMPTS_DIR / f"dev_issue_{args.issue}.md", prompt)

    checkout_issue_branch(branch, args.execute)
    run(["gh", "issue", "edit", str(args.issue), "--repo", args.repo, "--remove-label", "bqa:ready-dev", "--add-label", "bqa:in-dev"], execute=args.execute, check=False)
    result = run(["codex", "exec", prompt], execute=args.execute, capture=args.execute, check=False)
    if args.execute:
        out = result.stdout + "\n" + result.stderr
        write(RUNS_DIR / f"dev_issue_{args.issue}.out.txt", out)
        if re.search(r"^\s*QUESTION_STATUS\s*:\s*OPEN\b", out, re.MULTILINE):
            run(["gh", "issue", "edit", str(args.issue), "--repo", args.repo, "--add-label", "bqa:blocked"], execute=True, check=False)
            log("Developer raised an open question. See run output before continuing.")
            return
    run(["go", "test", "./..."], execute=args.execute, check=False)
    run(["git", "status", "--short"], execute=args.execute, check=False)
    if args.auto_commit:
        run(["git", "add", "."], execute=args.execute)
        run(["git", "commit", "-m", f"Implement issue #{args.issue}: {title}"], execute=args.execute, check=False)
        run(["git", "push", "-u", "origin", branch], execute=args.execute, check=False)
        body = f"Implements #{args.issue}.\n\nGenerated by BQA Team Orchestrator.\n\nChecklist:\n- [ ] go test ./... passes\n- [ ] QA review pending\n- [ ] Business acceptance pending\n"
        pr_cmd = ["gh", "pr", "create", "--repo", args.repo, "--title", f"Implement #{args.issue}: {title}", "--body", body]
        if getattr(args, "base_branch", None):
            pr_cmd += ["--base", args.base_branch]
        run(pr_cmd, execute=args.execute, check=False)
    run(["gh", "issue", "edit", str(args.issue), "--repo", args.repo, "--remove-label", "bqa:in-dev", "--add-label", "bqa:ready-qa"], execute=args.execute, check=False)


def qa_prompt(pr: int, repo: str) -> str:
    qa = load_role("qa")
    return f"""
{qa}

---

Review PR #{pr} in repository `{repo}` as BQA-OS QA / Test Engineer.

Tasks:
- inspect the PR diff;
- verify acceptance criteria from linked issue;
- run or recommend test commands;
- check architecture-sensitive QA risks;
- if implementation is incomplete, create a concise bug report body.

Return:
QA_STATUS: PASS or FAIL
BUG_TITLE: <only if FAIL>
BUG_BODY:
<only if FAIL>
""".strip()


def cmd_qa(args: argparse.Namespace) -> None:
    require_tools(["gh", "codex"], args.execute)
    prompt = qa_prompt(args.pr, args.repo)
    write(PROMPTS_DIR / f"qa_pr_{args.pr}.md", prompt)
    if args.execute:
        diff = run(["gh", "pr", "diff", str(args.pr), "--repo", args.repo], execute=True, capture=True, check=False).stdout
        result = run(["codex", "exec", prompt + "\n\nPR diff:\n\n" + diff[:30000]], execute=True, capture=True, check=False)
        out = result.stdout + "\n" + result.stderr
    else:
        out = "QA_STATUS: DRY-RUN\n"
        print("DRY-RUN: would run Codex QA review")
    write(RUNS_DIR / f"qa_pr_{args.pr}.out.txt", out)
    if args.execute and "QA_STATUS: FAIL" in out:
        bug_title = re.search(r"BUG_TITLE:\s*(.+)", out)
        bug_body = re.search(r"BUG_BODY:\s*(.*)", out, re.S)
        title = bug_title.group(1).strip() if bug_title else f"QA bug found in PR #{args.pr}"
        body = bug_body.group(1).strip() if bug_body else out
        body_file = TMP_DIR / f"bug_pr_{args.pr}.md"
        write(body_file, body)
        run(["gh", "issue", "create", "--repo", args.repo, "--title", title, "--body-file", str(body_file), "--label", "bqa:bug", "--label", "bqa:qa-failed", "--label", "bqa:ready-dev"], execute=True, check=False)


def business_prompt(pr: int, repo: str) -> str:
    business = load_role("business")
    return f"""
{business}

---

Perform final business acceptance for PR #{pr} in `{repo}`.

Evaluate:
- Does this deliver visible project value?
- Does it support the BQA-OS business direction?
- Is the UX/workflow understandable for first pilot users?
- Should this be accepted, revised, or split?

Return:
BUSINESS_STATUS: ACCEPT or REVISE
REASON:
<concise explanation>
""".strip()


def cmd_business_accept(args: argparse.Namespace) -> None:
    require_tools(["gh", "codex"], args.execute)
    prompt = business_prompt(args.pr, args.repo)
    write(PROMPTS_DIR / f"business_accept_pr_{args.pr}.md", prompt)
    if args.execute:
        diff = run(["gh", "pr", "diff", str(args.pr), "--repo", args.repo], execute=True, capture=True, check=False).stdout
        result = run(["codex", "exec", prompt + "\n\nPR diff:\n\n" + diff[:30000]], execute=True, capture=True, check=False)
        out = result.stdout + "\n" + result.stderr
    else:
        out = "BUSINESS_STATUS: DRY-RUN\n"
        print("DRY-RUN: would run Codex business acceptance")
    write(RUNS_DIR / f"business_accept_pr_{args.pr}.out.txt", out)


def issue_snapshot(repo: str, execute: bool, limit: int = 100) -> str:
    if not execute:
        return "[]"
    result = run([
        "gh", "issue", "list",
        "--repo", repo,
        "--state", "open",
        "--limit", str(limit),
        "--json", "number,title,body,labels,url",
        "--jq", ".",
    ], execute=True, capture=True, check=False)
    return result.stdout


def vision_text(path: str | None) -> str:
    if path:
        vision_path = Path(path)
    else:
        vision_path = TEAM_DIR / "PROJECT_VISION.md"
    if vision_path.exists():
        return read(vision_path)
    return "No explicit project vision file found. Use the repository goals and open issue context."


def replan_prompt(repo: str, issues_json: str, vision: str) -> str:
    business = load_role("business")
    architect = load_role("architect")[:6000]
    return f"""
{business}

---

Technical architecture context:

{architect}

---

Replan the open GitHub issue backlog for `{repo}`.

Project vision:

{vision}

Open issues JSON:

{issues_json}

Goals:
- Keep the backlog aligned with the project vision.
- Create missing implementation-ready tasks when the current backlog has gaps.
- Cancel only issues that are clearly obsolete, duplicated, or contradicted by the current vision.
- Do not cancel tasks just because they are hard.
- Do not include private data, secrets, or real session logs.
- New tasks must be small and ready for the developer role.

Return zero or more action blocks:

---CREATE_ISSUE---
TITLE: <short title>
LABELS: bqa:ready-dev,<optional labels>
BODY:
<full issue body>
---END_CREATE_ISSUE---

---CANCEL_ISSUE---
NUMBER: <issue number>
REASON: <short reason>
---END_CANCEL_ISSUE---
""".strip()


def parse_replan_actions(text: str) -> dict:
    create = []
    cancel = []

    for block in re.findall(r"---CREATE_ISSUE---(.*?)---END_CREATE_ISSUE---", text, re.S):
        title_match = re.search(r"^TITLE:\s*(.+)$", block, re.M)
        labels_match = re.search(r"^LABELS:\s*(.+)$", block, re.M)
        body_match = re.search(r"^BODY:\s*(.*)", block, re.M | re.S)
        if not title_match or not body_match:
            continue
        labels = []
        if labels_match:
            labels = [x.strip() for x in labels_match.group(1).split(",") if x.strip()]
        create.append({
            "title": title_match.group(1).strip(),
            "labels": labels,
            "body": body_match.group(1).strip(),
        })

    for block in re.findall(r"---CANCEL_ISSUE---(.*?)---END_CANCEL_ISSUE---", text, re.S):
        number_match = re.search(r"^NUMBER:\s*(\d+)$", block, re.M)
        reason_match = re.search(r"^REASON:\s*(.+)$", block, re.M)
        if not number_match:
            continue
        cancel.append({
            "number": int(number_match.group(1)),
            "reason": reason_match.group(1).strip() if reason_match else "Cancelled by BQA replanning.",
        })

    return {"create": create, "cancel": cancel}


def apply_replan_actions(repo: str, actions: dict, execute: bool) -> None:
    for issue in actions["create"]:
        body_file = TMP_DIR / f"replan_{slugify(issue['title'])}.md"
        write(body_file, issue["body"])
        cmd = ["gh", "issue", "create", "--repo", repo, "--title", issue["title"], "--body-file", str(body_file)]
        labels = issue["labels"] or ["bqa:ready-dev"]
        for label in labels:
            cmd += ["--label", label]
        run(cmd, execute=execute, check=False)

    for issue in actions["cancel"]:
        edit_issue_labels(repo, issue["number"], execute=execute, add=["bqa:cancelled"])
        run([
            "gh", "issue", "close", str(issue["number"]),
            "--repo", repo,
            "--comment", f"Cancelled by BQA replanning: {issue['reason']}",
        ], execute=execute, check=False)


def cmd_replan(args: argparse.Namespace) -> None:
    require_tools(["gh", "codex"], args.execute)
    issues = issue_snapshot(args.repo, args.execute, args.issue_limit)
    prompt = replan_prompt(args.repo, issues, vision_text(args.vision_file))
    prompt_path = PROMPTS_DIR / f"replan_{datetime.now().strftime('%Y%m%d-%H%M%S')}.md"
    write(prompt_path, prompt)

    if args.execute:
        result = run(["codex", "exec", prompt], execute=True, capture=True, check=False)
        out = result.stdout + "\n" + result.stderr
    else:
        out = ""
        print(f"DRY-RUN: replan prompt written to {prompt_path}")

    output_path = RUNS_DIR / f"replan_{datetime.now().strftime('%Y%m%d-%H%M%S')}.out.txt"
    write(output_path, out)
    actions = parse_replan_actions(out)
    apply_replan_actions(args.repo, actions, args.execute)
    log(f"Replan actions: create={len(actions['create'])}, cancel={len(actions['cancel'])}")


def branch_name_for_issue(issue: int, title: str, branch_override: str | None = None) -> str:
    if branch_override:
        return branch_override
    return f"codex/issue-{issue}-{slugify(title, 32)}"


def run_output_contains(path: Path, marker: str) -> bool:
    return path.exists() and marker in read(path)


def run_output_has_status(path: Path, key: str, value: str) -> bool:
    if not path.exists():
        return False
    pattern = re.compile(rf"^\s*{re.escape(key)}\s*:\s*{re.escape(value)}\b", re.MULTILINE)
    return bool(pattern.search(read(path)))


def find_pr_for_branch(repo: str, branch: str, execute: bool) -> int | None:
    result = run([
        "gh", "pr", "list",
        "--repo", repo,
        "--head", branch,
        "--state", "open",
        "--json", "number",
        "--jq", ".[0].number",
    ], execute=execute, capture=True, check=False)
    if not execute:
        return None
    try:
        return int(result.stdout.strip())
    except ValueError:
        return None


def edit_issue_labels(repo: str, issue: int, *, execute: bool, remove: list[str] | None = None, add: list[str] | None = None) -> None:
    cmd = ["gh", "issue", "edit", str(issue), "--repo", repo]
    for label in remove or []:
        cmd += ["--remove-label", label]
    for label in add or []:
        cmd += ["--add-label", label]
    run(cmd, execute=execute, check=False)


def merge_pr(repo: str, pr: int, execute: bool) -> None:
    run(["gh", "pr", "merge", str(pr), "--repo", repo, "--squash", "--delete-branch"], execute=execute, check=False)


def close_issue(repo: str, issue: int, execute: bool) -> None:
    run([
        "gh", "issue", "close", str(issue),
        "--repo", repo,
        "--comment", "Completed by BQA autopilot after QA and business acceptance.",
    ], execute=execute, check=False)


def issue_count(repo: str, execute: bool, *, state: str = "open", label: str | None = None) -> int:
    if not execute:
        return 0
    cmd = [
        "gh", "issue", "list",
        "--repo", repo,
        "--state", state,
        "--limit", "1000",
        "--json", "number",
        "--jq", "length",
    ]
    if label:
        cmd += ["--label", label]
    result = run(cmd, execute=True, capture=True, check=False)
    try:
        return int(result.stdout.strip())
    except ValueError:
        return 0


def monitor_snapshot(repo: str, execute: bool) -> dict:
    in_dev = issue_count(repo, execute, label="bqa:in-dev")
    ready_qa = issue_count(repo, execute, label="bqa:ready-qa")
    ready_business = issue_count(repo, execute, label="bqa:ready-business")
    return {
        "repo": repo,
        "updated_at": now(),
        "issues": {
            "open_total": issue_count(repo, execute),
            "ready_dev": issue_count(repo, execute, label="bqa:ready-dev"),
            "doing": in_dev + ready_qa + ready_business,
            "in_dev": in_dev,
            "ready_qa": ready_qa,
            "ready_business": ready_business,
            "blocked": issue_count(repo, execute, label="bqa:blocked"),
            "completed_done": issue_count(repo, execute, state="closed", label="bqa:done"),
        },
    }


def monitor_markdown(snapshot: dict) -> str:
    issues = snapshot["issues"]
    return f"""# BQA Autopilot Status

Updated: {snapshot['updated_at']}
Repo: {snapshot['repo']}
Last cycle status: {snapshot.get('last_cycle_status', 'unknown')}
Processed this run: {snapshot.get('processed_this_run', 0)}

## Issue counts

- Open total: {issues['open_total']}
- Ready dev: {issues['ready_dev']}
- Doing: {issues['doing']}
- In dev: {issues['in_dev']}
- Ready QA: {issues['ready_qa']}
- Ready business: {issues['ready_business']}
- Blocked: {issues['blocked']}
- Completed done: {issues['completed_done']}
"""


def issue_project_snapshot(repo: str, execute: bool, limit: int = 100) -> str:
    if not execute:
        return "[]"
    result = run([
        "gh", "issue", "list",
        "--repo", repo,
        "--state", "all",
        "--limit", str(limit),
        "--json", "number,title,body,labels,state,url,createdAt,updatedAt,closedAt",
        "--jq", ".",
    ], execute=True, capture=True, check=False)
    if result.returncode != 0:
        raise SystemExit(f"Failed to fetch GitHub issues for project view: {result.stderr.strip()}")
    return result.stdout


def label_names(issue: dict) -> list[str]:
    labels = issue.get("labels") or []
    names = []
    for label in labels:
        if isinstance(label, dict) and label.get("name"):
            names.append(label["name"])
        elif isinstance(label, str):
            names.append(label)
    return names


def issue_status(issue: dict) -> str:
    labels = set(label_names(issue))
    if "bqa:blocked" in labels:
        return "blocked"
    if issue.get("state", "").upper() == "CLOSED" or "bqa:done" in labels:
        return "done"
    if "bqa:ready-business" in labels:
        return "ready-business"
    if "bqa:ready-qa" in labels:
        return "ready-qa"
    if "bqa:in-dev" in labels:
        return "in-dev"
    if "bqa:ready-dev" in labels:
        return "ready-dev"
    return "open"


def parse_issue_dependencies(text: str) -> list[int]:
    deps = set()
    patterns = [
        r"(?:depends on|depend on|blocked by|requires|required by|after)\s+#(\d+)",
        r"BQA_DEPENDS_ON:\s*([#\d,\s]+)",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, text or "", re.I):
            if match.lastindex == 1:
                for number in re.findall(r"#?(\d+)", match.group(1)):
                    deps.add(int(number))
    return sorted(deps)


def project_view_model(repo: str, execute: bool, limit: int = 100) -> dict:
    raw = issue_project_snapshot(repo, execute, limit)
    try:
        source_issues = json.loads(raw)
    except json.JSONDecodeError:
        source_issues = []

    issues = []
    edges = []
    counts = {"open": 0, "ready-dev": 0, "in-dev": 0, "ready-qa": 0, "ready-business": 0, "blocked": 0, "done": 0}

    for item in source_issues:
        status = issue_status(item)
        deps = parse_issue_dependencies(item.get("body") or "")
        issue = {
            "number": item.get("number"),
            "title": item.get("title") or "",
            "url": item.get("url") or "",
            "status": status,
            "labels": label_names(item),
            "deps": deps,
            "created_at": item.get("createdAt"),
            "updated_at": item.get("updatedAt"),
            "closed_at": item.get("closedAt"),
        }
        issues.append(issue)
        counts[status] = counts.get(status, 0) + 1
        for dep in deps:
            edges.append({"from": dep, "to": issue["number"]})

    return {"repo": repo, "updated_at": now(), "counts": counts, "issues": issues, "edges": edges}


def html_escape(text: object) -> str:
    return (
        str(text if text is not None else "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def render_project_view_html(model: dict) -> str:
    statuses = ["open", "ready-dev", "in-dev", "ready-qa", "ready-business", "blocked", "done"]
    status_columns = "".join(f"<th>{html_escape(status)}</th>" for status in statuses)
    count_cards = "".join(
        f"<div class=\"metric\"><span>{html_escape(status)}</span><strong>{model['counts'].get(status, 0)}</strong></div>"
        for status in statuses
    )
    rows = []
    for issue in model["issues"]:
        cells = []
        for status in statuses:
            active = status == issue["status"]
            cell = ""
            if active:
                deps = ", ".join(f"#{dep}" for dep in issue["deps"]) or "none"
                labels = ", ".join(issue["labels"][:4])
                cell = (
                    f"<a class=\"bar {html_escape(status)}\" href=\"{html_escape(issue['url'])}\">"
                    f"<span>#{html_escape(issue['number'])}</span>"
                    f"<b>{html_escape(issue['title'])}</b>"
                    f"<em>deps: {html_escape(deps)}</em>"
                    f"<small>{html_escape(labels)}</small>"
                    "</a>"
                )
            cells.append(f"<td>{cell}</td>")
        rows.append(
            "<tr>"
            f"<th><a href=\"{html_escape(issue['url'])}\">#{html_escape(issue['number'])}</a></th>"
            + "".join(cells)
            + "</tr>"
        )

    edges = "".join(
        f"<li aria-label=\"#{edge['from']} -> #{edge['to']}\"><a href=\"#issue-{edge['from']}\">#{edge['from']}</a> -&gt; <a href=\"#issue-{edge['to']}\">#{edge['to']}</a></li>"
        for edge in model["edges"]
    ) or "<li>No explicit dependencies found. Use phrases like `Depends on #12` or `blocked by #12` in issue bodies.</li>"

    issue_cards = "".join(
        f"<article id=\"issue-{html_escape(issue['number'])}\" class=\"issue-card {html_escape(issue['status'])}\">"
        f"<div><a href=\"{html_escape(issue['url'])}\">#{html_escape(issue['number'])}</a> "
        f"<strong>{html_escape(issue['title'])}</strong></div>"
        f"<p>Status: {html_escape(issue['status'])}</p>"
        f"<p>Depends on: {html_escape(', '.join('#' + str(dep) for dep in issue['deps']) or 'none')}</p>"
        "</article>"
        for issue in model["issues"]
    )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>BQA Project View</title>
  <style>
    :root {{
      --bg: #f7f8fb;
      --panel: #ffffff;
      --ink: #18202f;
      --muted: #667085;
      --line: #d9deea;
      --accent: #276ef1;
      --ready: #dbeafe;
      --work: #e0f2fe;
      --qa: #fef3c7;
      --biz: #ede9fe;
      --blocked: #fee2e2;
      --done: #dcfce7;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: var(--bg); color: var(--ink); }}
    header {{ padding: 24px 28px 16px; border-bottom: 1px solid var(--line); background: var(--panel); }}
    h1 {{ margin: 0 0 8px; font-size: 28px; line-height: 1.15; }}
    header p {{ margin: 0; color: var(--muted); }}
    main {{ padding: 20px 28px 36px; display: grid; gap: 18px; }}
    .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 10px; }}
    .metric {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 12px; }}
    .metric span {{ display: block; color: var(--muted); font-size: 12px; text-transform: uppercase; }}
    .metric strong {{ font-size: 28px; }}
    .panel {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; overflow: hidden; }}
    .panel h2 {{ margin: 0; padding: 14px 16px; border-bottom: 1px solid var(--line); font-size: 16px; }}
    .timeline-wrap {{ overflow-x: auto; }}
    table {{ width: 100%; border-collapse: collapse; min-width: 980px; }}
    th, td {{ border-bottom: 1px solid var(--line); border-right: 1px solid var(--line); padding: 8px; vertical-align: top; }}
    th {{ background: #f2f4f8; font-size: 12px; text-align: left; color: var(--muted); }}
    td {{ height: 86px; min-width: 130px; }}
    a {{ color: var(--accent); text-decoration: none; }}
    .bar {{ display: grid; gap: 3px; min-height: 68px; padding: 8px; border-radius: 7px; color: var(--ink); border: 1px solid rgba(24,32,47,.1); }}
    .bar span, .bar em, .bar small {{ color: var(--muted); font-size: 11px; font-style: normal; }}
    .bar b {{ font-size: 13px; line-height: 1.25; }}
    .bar.open {{ background: #eef2ff; }}
    .bar.ready-dev {{ background: var(--ready); }}
    .bar.in-dev {{ background: var(--work); }}
    .bar.ready-qa {{ background: var(--qa); }}
    .bar.ready-business {{ background: var(--biz); }}
    .bar.blocked {{ background: var(--blocked); }}
    .bar.done {{ background: var(--done); }}
    .deps {{ padding: 12px 18px 18px; columns: 2; }}
    .deps li {{ break-inside: avoid; margin: 0 0 8px; }}
    .cards {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 10px; padding: 14px; }}
    .issue-card {{ border: 1px solid var(--line); border-left: 5px solid var(--accent); border-radius: 8px; padding: 10px; background: #fff; }}
    .issue-card p {{ margin: 6px 0 0; color: var(--muted); font-size: 13px; }}
    @media (max-width: 720px) {{
      header, main {{ padding-left: 14px; padding-right: 14px; }}
      .deps {{ columns: 1; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>BQA Project View</h1>
    <p>{html_escape(model['repo'])} · updated {html_escape(model['updated_at'])}</p>
  </header>
  <main>
    <section class="metrics">{count_cards}</section>
    <section class="panel">
      <h2>Gantt-like Status Timeline</h2>
      <div class="timeline-wrap">
        <table>
          <thead><tr><th>Issue</th>{status_columns}</tr></thead>
          <tbody>{''.join(rows)}</tbody>
        </table>
      </div>
    </section>
    <section class="panel">
      <h2>Dependencies</h2>
      <ul class="deps">{edges}</ul>
    </section>
    <section class="panel">
      <h2>Issue Details</h2>
      <div class="cards">{issue_cards}</div>
    </section>
  </main>
</body>
</html>
"""


def cmd_view(args: argparse.Namespace) -> None:
    model = project_view_model(args.repo, args.execute, args.issue_limit)
    write(PROJECT_VIEW_JSON, json.dumps(model, indent=2, ensure_ascii=False) + "\n")
    write(PROJECT_VIEW_HTML, render_project_view_html(model))
    print(f"Project view: {PROJECT_VIEW_HTML}")


def write_monitor_status(repo: str, execute: bool, last_cycle_status: str = "unknown", processed_this_run: int = 0) -> dict:
    snapshot = monitor_snapshot(repo, execute)
    snapshot["last_cycle_status"] = last_cycle_status
    snapshot["processed_this_run"] = processed_this_run
    write(STATUS_JSON, json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n")
    write(STATUS_MD, monitor_markdown(snapshot))
    return snapshot


def cmd_monitor(args: argparse.Namespace) -> None:
    snapshot = write_monitor_status(args.repo, args.execute)
    print(monitor_markdown(snapshot))


def default_autopilot_config(repo: str) -> dict:
    return {
        "repo": repo,
        "max_cycles": 200,
        "sleep_seconds": 60,
        "all_open": True,
        "issue_label": "bqa:ready-dev",
        "oldest_first": True,
        "auto_commit": True,
        "merge": True,
        "close_issue": True,
        "replan_every": 7,
        "vision_file": ".bqa-team/PROJECT_VISION.md",
        "issue_limit": 100,
        "base_branch": "main",
        "stop_on_fail": True,
    }


def write_default_autopilot_config(path: Path, repo: str) -> dict:
    config = default_autopilot_config(repo)
    write(path, json.dumps(config, indent=2, ensure_ascii=False) + "\n")
    return config


def prompt_config_value(name: str, default: object) -> object:
    answer = input(f"{name} [{default}]: ").strip()
    if answer == "":
        return default
    if isinstance(default, bool):
        return answer.lower() in {"1", "yes", "y", "true", "on"}
    if isinstance(default, int):
        return int(answer)
    return answer


def cmd_configure_autopilot(args: argparse.Namespace) -> None:
    config_path = Path(args.config)
    config = default_autopilot_config(args.repo)
    if not args.yes:
        for key in list(config):
            config[key] = prompt_config_value(key, config[key])
    write(config_path, json.dumps(config, indent=2, ensure_ascii=False) + "\n")
    print(f"Autopilot config written: {config_path}")


def load_autopilot_config(path: str | None) -> dict:
    config_path = Path(path) if path else AUTOPILOT_CONFIG
    if not config_path.exists():
        return {}
    return json.loads(read(config_path))


def apply_autopilot_config(args: argparse.Namespace) -> argparse.Namespace:
    config = load_autopilot_config(getattr(args, "config", None))
    if not config:
        return args
    for key, value in config.items():
        current = getattr(args, key, None)
        if key == "repo" or current is None:
            setattr(args, key, value)
    return args


def apply_autopilot_defaults(args: argparse.Namespace) -> argparse.Namespace:
    defaults = default_autopilot_config(args.repo)
    for key, value in defaults.items():
        if getattr(args, key, None) is None:
            setattr(args, key, value)
    if getattr(args, "once", None) is None:
        args.once = False
    if getattr(args, "branch", None) is None:
        args.branch = None
    if getattr(args, "subagent", None) is None:
        args.subagent = None
    return args


def sync_base_branch(args: argparse.Namespace) -> None:
    base_branch = getattr(args, "base_branch", None)
    if not base_branch:
        return
    run(["git", "checkout", base_branch], execute=args.execute, check=False)
    run(["git", "pull", "--ff-only"], execute=args.execute, check=False)


def checkout_issue_branch(branch: str, execute: bool) -> None:
    exists = run(["git", "rev-parse", "--verify", branch], execute=execute, capture=True, check=False)
    cmd = ["git", "checkout", branch] if exists.returncode == 0 else ["git", "checkout", "-b", branch]
    result = run(cmd, execute=execute, capture=True, check=False)
    if execute and result.returncode != 0:
        raise SystemExit(f"Failed to checkout issue branch {branch}: {result.stderr.strip()}")


def list_ready_issues(repo: str, execute: bool, label: str | None = "bqa:ready-dev") -> list[int]:
    if not execute:
        return []
    cmd = ["gh", "issue", "list", "--repo", repo, "--state", "open", "--json", "number", "--jq", ".[].number"]
    if label:
        cmd += ["--label", label]
    result = run(cmd, execute=True, capture=True, check=False)
    nums = []
    for line in result.stdout.splitlines():
        try:
            nums.append(int(line.strip()))
        except ValueError:
            pass
    return nums


def open_issue_snapshot(repo: str, execute: bool, label: str | None = None) -> str:
    if not execute:
        return "[]"
    cmd = [
        "gh", "issue", "list",
        "--repo", repo,
        "--state", "open",
        "--limit", "1000",
        "--json", "number,body,labels,state",
        "--jq", ".",
    ]
    if label:
        cmd += ["--label", label]
    result = run(cmd, execute=True, capture=True, check=False)
    return result.stdout


def list_candidate_issues(repo: str, execute: bool, label: str | None = "bqa:ready-dev") -> list[int]:
    if label:
        return list_ready_issues(repo, execute, label)
    raw = open_issue_snapshot(repo, execute, None)
    try:
        issues = json.loads(raw)
    except json.JSONDecodeError:
        return []

    issue_by_number = {issue.get("number"): issue for issue in issues}
    excluded_labels = {
        "bqa:blocked",
        "bqa:in-dev",
        "bqa:ready-qa",
        "bqa:ready-business",
        "bqa:done",
        "bqa:business-approved",
    }
    candidates = []
    for issue in issues:
        labels = set(label_names(issue))
        if labels & excluded_labels:
            continue
        blocked_dependency = False
        for dep in parse_issue_dependencies(issue.get("body") or ""):
            dep_issue = issue_by_number.get(dep)
            if dep_issue and issue_status(dep_issue) == "blocked":
                blocked_dependency = True
                break
        if not blocked_dependency and issue.get("number") is not None:
            candidates.append(int(issue["number"]))
    return candidates


def run_autopilot_cycle(args: argparse.Namespace) -> str:
    issue_label = None if getattr(args, "all_open", False) else args.issue_label
    ready = list_candidate_issues(args.repo, args.execute, issue_label)
    if not ready:
        if issue_label:
            log(f"No open issues with label {issue_label}.")
        else:
            log("No open issues found.")
        return "idle"

    issue = ready[-1] if args.oldest_first else ready[0]
    raw = issue_json(args.repo, issue, args.execute)
    title = json.loads(raw).get("title", f"issue-{issue}") if raw else f"issue-{issue}"
    branch = branch_name_for_issue(issue, title, args.branch)

    route = {"subagent": getattr(args, "subagent", None), "reason": "Selected by CLI override."}
    if not route["subagent"]:
        route = route_issue_to_subagent(args.repo, issue, raw, args.execute)
    if route["subagent"] not in SUBAGENT_FILES:
        route = {"subagent": "go-cli-implementer", "reason": "Invalid CLI subagent override; using default implementer."}
    save_subagent_route(issue, route)
    log(f"Routed issue {issue} to subagent {route['subagent']}: {route['reason']}")

    sync_base_branch(args)

    cycle_args = copy(args)
    cycle_args.issue = issue
    cycle_args.branch = branch
    cycle_args.auto_commit = args.auto_commit
    cycle_args.subagent = route["subagent"]

    log(f"Autopilot dev issue {issue} on branch {branch}")
    cmd_dev(cycle_args)

    if run_output_has_status(RUNS_DIR / f"dev_issue_{issue}.out.txt", "QUESTION_STATUS", "OPEN"):
        log(f"Issue {issue} blocked by developer question.")
        return "blocked"

    pr = find_pr_for_branch(args.repo, branch, args.execute)
    if pr is None:
        log(f"No open PR found for branch {branch}.")
        edit_issue_labels(args.repo, issue, execute=args.execute, add=["bqa:blocked"])
        return "blocked"

    cycle_args.pr = pr

    log(f"Autopilot QA PR {pr}")
    cmd_qa(cycle_args)
    if run_output_has_status(RUNS_DIR / f"qa_pr_{pr}.out.txt", "QA_STATUS", "FAIL"):
        log(f"QA failed for PR {pr}.")
        return "blocked"

    edit_issue_labels(args.repo, issue, execute=args.execute, remove=["bqa:ready-qa"], add=["bqa:ready-business"])

    log(f"Autopilot business acceptance PR {pr}")
    cmd_business_accept(cycle_args)
    if run_output_has_status(RUNS_DIR / f"business_accept_pr_{pr}.out.txt", "BUSINESS_STATUS", "REVISE"):
        log(f"Business requested revision for PR {pr}.")
        edit_issue_labels(args.repo, issue, execute=args.execute, add=["bqa:blocked"])
        return "blocked"

    edit_issue_labels(args.repo, issue, execute=args.execute, remove=["bqa:ready-business"], add=["bqa:business-approved", "bqa:done"])

    if args.merge:
        merge_pr(args.repo, pr, args.execute)
    if args.close_issue:
        close_issue(args.repo, issue, args.execute)

    sync_base_branch(args)
    return "processed"


def cmd_loop(args: argparse.Namespace) -> None:
    if not args.once and args.max_cycles <= 0:
        raise SystemExit("Refusing unbounded loop. Use --once or --max-cycles N.")
    cycles = 1 if args.once else args.max_cycles
    for i in range(cycles):
        log(f"Cycle {i + 1}/{cycles}")
        cmd_architect(args)
        cmd_create_issues(args)
        ready = list_ready_issues(args.repo, args.execute)
        if ready:
            log(f"Ready issues: {ready}")
        else:
            log("No ready-dev issues found or dry-run mode.")
        if args.run_dev and ready:
            issue = ready[-1] if args.oldest_first else ready[0]
            log(f"Running dev for issue {issue}")
            args.issue = issue
            cmd_dev(args)
        if args.sleep_seconds and i < cycles - 1:
            time.sleep(args.sleep_seconds)


def cmd_autopilot(args: argparse.Namespace) -> None:
    apply_autopilot_config(args)
    apply_autopilot_defaults(args)
    require_tools(["gh", "git", "codex"], args.execute)
    if not args.once and args.max_cycles <= 0:
        raise SystemExit("Refusing unbounded autopilot. Use --once or --max-cycles N.")
    cycles = 1 if args.once else args.max_cycles
    processed = 0
    write_monitor_status(args.repo, args.execute, "starting", processed)
    for i in range(cycles):
        log(f"Autopilot cycle {i + 1}/{cycles}")
        status = run_autopilot_cycle(args)
        if status == "idle":
            write_monitor_status(args.repo, args.execute, status, processed)
            break
        if status == "processed":
            processed += 1
            if args.replan_every > 0 and processed % args.replan_every == 0:
                cmd_replan(args)
        write_monitor_status(args.repo, args.execute, status, processed)
        if status == "blocked" and args.stop_on_fail:
            break
        if args.sleep_seconds and i < cycles - 1:
            time.sleep(args.sleep_seconds)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="BQA team role orchestrator")
    p.add_argument("--repo", default=os.environ.get("BQA_REPO", "mshegolev/bqa-os"), help="GitHub repo, e.g. mshegolev/bqa-os")
    p.add_argument("--execute", action="store_true", help="Actually run mutating commands and Codex. Default is dry-run.")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init")
    sub.add_parser("seed")
    sub.add_parser("ensure-labels")
    sub.add_parser("monitor")
    view = sub.add_parser("view")
    view.add_argument("--issue-limit", type=int, default=100)

    configure = sub.add_parser("configure-autopilot")
    configure.add_argument("--config", default=str(AUTOPILOT_CONFIG))
    configure.add_argument("--yes", action="store_true", help="Write recommended defaults without interactive questions")

    arch = sub.add_parser("architect")
    arch.add_argument("--force", action="store_true")

    ci = sub.add_parser("create-issues")
    ci.add_argument("--force", action="store_true")

    dev = sub.add_parser("dev")
    dev.add_argument("--issue", type=int, required=True)
    dev.add_argument("--branch")
    dev.add_argument("--base-branch")
    dev.add_argument("--subagent", choices=sorted(SUBAGENT_FILES))
    dev.add_argument("--auto-commit", action="store_true", help="Commit, push and open PR after Codex run")

    qa = sub.add_parser("qa")
    qa.add_argument("--pr", type=int, required=True)

    ba = sub.add_parser("business-accept")
    ba.add_argument("--pr", type=int, required=True)

    replan = sub.add_parser("replan")
    replan.add_argument("--vision-file")
    replan.add_argument("--issue-limit", type=int, default=100)

    loop = sub.add_parser("loop")
    loop.add_argument("--once", action="store_true")
    loop.add_argument("--max-cycles", type=int, default=0)
    loop.add_argument("--sleep-seconds", type=int, default=0)
    loop.add_argument("--force", action="store_true")
    loop.add_argument("--run-dev", action="store_true", help="Also run dev for one ready issue per cycle")
    loop.add_argument("--oldest-first", action="store_true", help="Pick oldest ready issue instead of newest")
    loop.add_argument("--auto-commit", action="store_true", help="Passed to dev when --run-dev is enabled")
    loop.add_argument("--branch")

    autopilot = sub.add_parser("autopilot")
    autopilot.add_argument("--config", default=str(AUTOPILOT_CONFIG))
    autopilot.add_argument("--once", action="store_true", default=None)
    autopilot.add_argument("--max-cycles", type=int)
    autopilot.add_argument("--sleep-seconds", type=int)
    autopilot.add_argument("--issue-label", default="bqa:ready-dev")
    autopilot.add_argument("--all-open", action=argparse.BooleanOptionalAction, default=None, help="Process all open issues instead of filtering by --issue-label")
    autopilot.add_argument("--oldest-first", action=argparse.BooleanOptionalAction, default=None)
    autopilot.add_argument("--no-auto-commit", dest="auto_commit", action="store_false")
    autopilot.set_defaults(auto_commit=None)
    autopilot.add_argument("--replan-every", type=int)
    autopilot.add_argument("--vision-file")
    autopilot.add_argument("--issue-limit", type=int)
    autopilot.add_argument("--merge", action=argparse.BooleanOptionalAction, default=None, help="Merge accepted PRs with squash after QA and business acceptance")
    autopilot.add_argument("--close-issue", action=argparse.BooleanOptionalAction, default=None, help="Close accepted issues after QA and business acceptance")
    autopilot.add_argument("--continue-on-fail", dest="stop_on_fail", action="store_false")
    autopilot.set_defaults(stop_on_fail=None)
    autopilot.add_argument("--branch")
    autopilot.add_argument("--base-branch")
    autopilot.add_argument("--subagent", choices=sorted(SUBAGENT_FILES), help="Override router and force one subagent for every issue")

    return p


def main() -> None:
    args = build_parser().parse_args()
    handlers = {
        "init": cmd_init,
        "seed": cmd_seed,
        "ensure-labels": cmd_ensure_labels,
        "monitor": cmd_monitor,
        "view": cmd_view,
        "configure-autopilot": cmd_configure_autopilot,
        "architect": cmd_architect,
        "create-issues": cmd_create_issues,
        "dev": cmd_dev,
        "qa": cmd_qa,
        "business-accept": cmd_business_accept,
        "replan": cmd_replan,
        "loop": cmd_loop,
        "autopilot": cmd_autopilot,
    }
    handlers[args.cmd](args)


if __name__ == "__main__":
    main()
