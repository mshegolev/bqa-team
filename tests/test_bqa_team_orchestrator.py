import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


def load_orchestrator():
    script = Path(__file__).resolve().parents[1] / "scripts" / "bqa_team_orchestrator.py"
    spec = importlib.util.spec_from_file_location("bqa_team_orchestrator", script)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class AutopilotTests(unittest.TestCase):
    def test_cmd_qa_truncates_long_bug_body_before_issue_create(self):
        orchestrator = load_orchestrator()
        created_issue_body_files = []

        with tempfile.TemporaryDirectory() as tmp:
            orchestrator.PROMPTS_DIR = Path(tmp) / "prompts"
            orchestrator.RUNS_DIR = Path(tmp) / "runs"
            orchestrator.TMP_DIR = Path(tmp) / "tmp"
            orchestrator.load_role = lambda role: "QA role"
            orchestrator.require_tools = lambda names, execute: None

            long_bug_body = "What failed:\n" + ("x" * 70000) + "\n\ntokens used\n123"

            def fake_run(cmd, *, execute, capture=False, check=True):
                if cmd[:3] == ["gh", "pr", "diff"]:
                    return subprocess.CompletedProcess(cmd, 0, stdout="diff", stderr="")
                if cmd[:2] == ["codex", "exec"]:
                    out = "QA_STATUS: FAIL\nBUG_TITLE: oversized bug\nBUG_BODY:\n" + long_bug_body
                    return subprocess.CompletedProcess(cmd, 0, stdout=out, stderr="")
                if cmd[:3] == ["gh", "issue", "create"]:
                    body_file = Path(cmd[cmd.index("--body-file") + 1])
                    created_issue_body_files.append(body_file)
                    return subprocess.CompletedProcess(cmd, 0, stdout="https://example.test/bug\n", stderr="")
                raise AssertionError(f"unexpected command: {cmd}")

            orchestrator.run = fake_run
            args = SimpleNamespace(repo="mshegolev/bqa-os", pr=73, execute=True)

            orchestrator.cmd_qa(args)

            self.assertEqual(len(created_issue_body_files), 1)
            body = created_issue_body_files[0].read_text(encoding="utf-8")
            self.assertLessEqual(len(body), 60000)
            self.assertIn("What failed:", body)
            self.assertIn("truncated", body.lower())

    def test_cmd_qa_strips_prompt_echo_from_bug_body(self):
        orchestrator = load_orchestrator()
        created_issue_body_files = []

        with tempfile.TemporaryDirectory() as tmp:
            orchestrator.PROMPTS_DIR = Path(tmp) / "prompts"
            orchestrator.RUNS_DIR = Path(tmp) / "runs"
            orchestrator.TMP_DIR = Path(tmp) / "tmp"
            orchestrator.load_role = lambda role: "QA role"
            orchestrator.require_tools = lambda names, execute: None

            def fake_run(cmd, *, execute, capture=False, check=True):
                if cmd[:3] == ["gh", "pr", "diff"]:
                    return subprocess.CompletedProcess(cmd, 0, stdout="diff", stderr="")
                if cmd[:2] == ["codex", "exec"]:
                    out = (
                        "QA_STATUS: FAIL\n"
                        "BUG_TITLE: documented workflow skips sessions\n"
                        "BUG_BODY:\n"
                        "What failed: build processed zero sessions.\n"
                        "Expected behavior: build reads ingest2 output.\n"
                        "\n"
                        "Reading additional input from stdin...\n"
                        "user\n"
                        "QA_STATUS: PASS or FAIL\n"
                        "PR diff:\n"
                        "diff --git a/README.md b/README.md\n"
                    )
                    return subprocess.CompletedProcess(cmd, 0, stdout=out, stderr="")
                if cmd[:3] == ["gh", "issue", "create"]:
                    body_file = Path(cmd[cmd.index("--body-file") + 1])
                    created_issue_body_files.append(body_file)
                    return subprocess.CompletedProcess(cmd, 0, stdout="https://example.test/bug\n", stderr="")
                raise AssertionError(f"unexpected command: {cmd}")

            orchestrator.run = fake_run
            args = SimpleNamespace(repo="mshegolev/bqa-os", pr=69, execute=True)

            orchestrator.cmd_qa(args)

            self.assertEqual(len(created_issue_body_files), 1)
            body = created_issue_body_files[0].read_text(encoding="utf-8")
            self.assertIn("What failed: build processed zero sessions.", body)
            self.assertNotIn("Reading additional input from stdin", body)
            self.assertNotIn("QA_STATUS: PASS or FAIL", body)
            self.assertNotIn("diff --git", body)

    def test_cmd_dev_ignores_prompt_echo_question_status_before_blocking(self):
        orchestrator = load_orchestrator()
        calls = []

        with tempfile.TemporaryDirectory() as tmp:
            orchestrator.PROMPTS_DIR = Path(tmp) / "prompts"
            orchestrator.RUNS_DIR = Path(tmp) / "runs"
            orchestrator.require_tools = lambda names, execute: None
            orchestrator.load_subagent = lambda subagent: "Developer role"
            orchestrator.load_role = lambda role: "Architect role"
            orchestrator.checkout_issue_branch = lambda branch, execute: calls.append(("checkout", branch))
            orchestrator.issue_json = lambda repo, issue, execute: json.dumps(
                {"title": "ETL QA Agent Pack MVP", "body": "Build it", "labels": []}
            )

            def fake_run(cmd, *, execute, capture=False, check=True):
                calls.append(tuple(cmd))
                if cmd[:2] == ["codex", "exec"]:
                    out = (
                        "Implemented feature successfully.\n"
                        "\n"
                        "Reading additional input from stdin...\n"
                        "user\n"
                        "If blocked, output:\n"
                        "QUESTION_STATUS: OPEN\n"
                    )
                    return subprocess.CompletedProcess(cmd, 0, stdout=out, stderr="")
                return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

            orchestrator.run = fake_run
            args = SimpleNamespace(
                repo="mshegolev/bqa-os",
                issue=64,
                execute=True,
                branch=None,
                subagent="go-cli-implementer",
                auto_commit=True,
                base_branch="main",
            )

            orchestrator.cmd_dev(args)

        self.assertNotIn(
            ("gh", "issue", "edit", "64", "--repo", "mshegolev/bqa-os", "--add-label", "bqa:blocked"),
            calls,
        )
        self.assertIn(("git", "commit", "-m", "Implement issue #64: ETL QA Agent Pack MVP"), calls)
        self.assertIn(
            (
                "gh",
                "issue",
                "edit",
                "64",
                "--repo",
                "mshegolev/bqa-os",
                "--remove-label",
                "bqa:in-dev",
                "--add-label",
                "bqa:ready-qa",
            ),
            calls,
        )

    def test_run_updates_autopilot_heartbeat_while_command_runs(self):
        orchestrator = load_orchestrator()

        with tempfile.TemporaryDirectory() as tmp:
            orchestrator.STATUS_DIR = Path(tmp) / "status"
            orchestrator.HEARTBEAT_INTERVAL_SECONDS = 0.05

            result = orchestrator.run(
                [
                    "python3",
                    "-c",
                    "import time; time.sleep(0.15); print('ok')",
                ],
                execute=True,
                capture=True,
            )

            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout.strip(), "ok")
            self.assertTrue((orchestrator.STATUS_DIR / "autopilot-heartbeat").exists())

    def test_autopilot_cycle_runs_dev_qa_business_acceptance_and_marks_done(self):
        orchestrator = load_orchestrator()
        events = []

        with tempfile.TemporaryDirectory() as tmp:
            orchestrator.RUNS_DIR = Path(tmp) / "runs"

            orchestrator.list_candidate_issues = lambda repo, execute, label="bqa:ready-dev": [42]
            orchestrator.issue_json = lambda repo, number, execute: json.dumps(
                {"title": "Add Widget", "body": "Build it", "labels": []}
            )

            def fake_dev(args):
                events.append(("dev", args.issue, args.branch, args.auto_commit))

            def fake_qa(args):
                events.append(("qa", args.pr))
                orchestrator.write(orchestrator.RUNS_DIR / "qa_pr_77.out.txt", "QA_STATUS: PASS\n")

            def fake_business(args):
                events.append(("business", args.pr))
                orchestrator.write(
                    orchestrator.RUNS_DIR / "business_accept_pr_77.out.txt",
                    "BUSINESS_STATUS: ACCEPT\n",
                )

            def fake_run(cmd, *, execute, capture=False, check=True):
                events.append(tuple(cmd))
                return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

            orchestrator.cmd_dev = fake_dev
            orchestrator.cmd_qa = fake_qa
            orchestrator.cmd_business_accept = fake_business
            orchestrator.find_pr_for_branch = lambda repo, branch, execute: 77
            orchestrator.run = fake_run

            args = SimpleNamespace(
                repo="mshegolev/bqa-os",
                execute=True,
                issue_label="bqa:ready-dev",
                oldest_first=True,
                auto_commit=True,
                merge=True,
                close_issue=True,
                stop_on_fail=True,
                branch=None,
            )

            status = orchestrator.run_autopilot_cycle(args)

        self.assertEqual(status, "processed")
        self.assertIn(("dev", 42, "codex/issue-42-add-widget", True), events)
        self.assertIn(("qa", 77), events)
        self.assertIn(("business", 77), events)
        self.assertIn(
            (
                "gh",
                "issue",
                "edit",
                "42",
                "--repo",
                "mshegolev/bqa-os",
                "--remove-label",
                "bqa:ready-qa",
                "--remove-label",
                "bqa:qa-failed",
                "--remove-label",
                "bqa:blocked",
                "--add-label",
                "bqa:ready-business",
            ),
            events,
        )
        self.assertIn(
            (
                "gh",
                "issue",
                "close",
                "42",
                "--repo",
                "mshegolev/bqa-os",
                "--comment",
                "Completed by BQA autopilot after QA and business acceptance.",
            ),
            events,
        )
        self.assertIn(("gh", "pr", "merge", "77", "--repo", "mshegolev/bqa-os", "--squash", "--delete-branch"), events)

    def test_autopilot_cycle_resumes_ready_qa_issue_without_dev(self):
        orchestrator = load_orchestrator()
        events = []

        with tempfile.TemporaryDirectory() as tmp:
            orchestrator.RUNS_DIR = Path(tmp) / "runs"

            def fake_list_candidate_issues(repo, execute, label="bqa:ready-dev"):
                if label == "bqa:ready-dev":
                    return []
                if label == "bqa:ready-qa":
                    return [31]
                return []

            orchestrator.list_candidate_issues = fake_list_candidate_issues
            orchestrator.issue_json = lambda repo, number, execute: json.dumps(
                {"title": "Static site upload flow", "body": "Verify it", "labels": [{"name": "bqa:ready-qa"}]}
            )
            orchestrator.cmd_dev = lambda args: events.append(("dev", args.issue))

            def fake_qa(args):
                events.append(("qa", args.pr))
                orchestrator.write(orchestrator.RUNS_DIR / "qa_pr_88.out.txt", "QA_STATUS: PASS\n")

            def fake_business(args):
                events.append(("business", args.pr))
                orchestrator.write(
                    orchestrator.RUNS_DIR / "business_accept_pr_88.out.txt",
                    "BUSINESS_STATUS: ACCEPT\n",
                )

            def fake_find_pr(repo, branch, execute):
                events.append(("find-pr", branch))
                return 88

            orchestrator.cmd_qa = fake_qa
            orchestrator.cmd_business_accept = fake_business
            orchestrator.find_pr_for_branch = fake_find_pr
            orchestrator.run = lambda cmd, *, execute, capture=False, check=True: subprocess.CompletedProcess(
                cmd, 0, stdout="", stderr=""
            )

            args = SimpleNamespace(
                repo="mshegolev/bqa-os",
                execute=True,
                issue_label="bqa:ready-dev",
                oldest_first=True,
                auto_commit=True,
                merge=True,
                close_issue=True,
                stop_on_fail=True,
                branch=None,
            )

            status = orchestrator.run_autopilot_cycle(args)

        self.assertEqual(status, "processed")
        self.assertIn(("find-pr", "codex/issue-31-static-site-upload-flow"), events)
        self.assertNotIn(("dev", 31), events)
        self.assertIn(("qa", 88), events)
        self.assertIn(("business", 88), events)

    def test_autopilot_cycle_resumes_ready_business_issue_without_dev_or_qa(self):
        orchestrator = load_orchestrator()
        events = []

        with tempfile.TemporaryDirectory() as tmp:
            orchestrator.RUNS_DIR = Path(tmp) / "runs"

            def fake_list_candidate_issues(repo, execute, label="bqa:ready-dev"):
                if label == "bqa:ready-business":
                    return [62]
                return []

            orchestrator.list_candidate_issues = fake_list_candidate_issues
            orchestrator.issue_json = lambda repo, number, execute: json.dumps(
                {"title": "Monday sales package", "body": "Accept it", "labels": [{"name": "bqa:ready-business"}]}
            )
            orchestrator.cmd_dev = lambda args: events.append(("dev", args.issue))
            orchestrator.cmd_qa = lambda args: events.append(("qa", args.pr))

            def fake_business(args):
                events.append(("business", args.pr))
                orchestrator.write(
                    orchestrator.RUNS_DIR / "business_accept_pr_91.out.txt",
                    "BUSINESS_STATUS: ACCEPT\n",
                )

            orchestrator.cmd_business_accept = fake_business
            orchestrator.find_pr_for_branch = lambda repo, branch, execute: 91
            orchestrator.run = lambda cmd, *, execute, capture=False, check=True: subprocess.CompletedProcess(
                cmd, 0, stdout="", stderr=""
            )

            args = SimpleNamespace(
                repo="mshegolev/bqa-os",
                execute=True,
                issue_label="bqa:ready-dev",
                oldest_first=True,
                auto_commit=True,
                merge=True,
                close_issue=True,
                stop_on_fail=True,
                branch=None,
            )

            status = orchestrator.run_autopilot_cycle(args)

        self.assertEqual(status, "processed")
        self.assertNotIn(("dev", 62), events)
        self.assertNotIn(("qa", 91), events)
        self.assertIn(("business", 91), events)

    def test_autopilot_cycle_stops_before_business_acceptance_when_qa_fails(self):
        orchestrator = load_orchestrator()
        events = []
        label_events = []

        with tempfile.TemporaryDirectory() as tmp:
            orchestrator.RUNS_DIR = Path(tmp) / "runs"

            orchestrator.list_candidate_issues = lambda repo, execute, label="bqa:ready-dev": [7]
            orchestrator.issue_json = lambda repo, number, execute: json.dumps(
                {"title": "Broken Feature", "body": "Build it", "labels": []}
            )
            orchestrator.cmd_dev = lambda args: events.append(("dev", args.issue))
            orchestrator.find_pr_for_branch = lambda repo, branch, execute: 12

            def fake_qa(args):
                events.append(("qa", args.pr))
                orchestrator.write(orchestrator.RUNS_DIR / "qa_pr_12.out.txt", "QA_STATUS: FAIL\n")

            orchestrator.cmd_qa = fake_qa
            orchestrator.cmd_business_accept = lambda args: events.append(("business", args.pr))
            orchestrator.edit_issue_labels = lambda repo, issue, *, execute, remove=None, add=None: label_events.append(
                (repo, issue, tuple(remove or []), tuple(add or []))
            )
            orchestrator.run = lambda cmd, *, execute, capture=False, check=True: subprocess.CompletedProcess(
                cmd, 0, stdout="", stderr=""
            )

            args = SimpleNamespace(
                repo="mshegolev/bqa-os",
                execute=True,
                issue_label="bqa:ready-dev",
                oldest_first=True,
                auto_commit=True,
                merge=True,
                close_issue=True,
                stop_on_fail=True,
                branch=None,
            )

            status = orchestrator.run_autopilot_cycle(args)

        self.assertEqual(status, "blocked")
        self.assertIn(("dev", 7), events)
        self.assertIn(("qa", 12), events)
        self.assertNotIn(("business", 12), events)
        self.assertIn(
            ("mshegolev/bqa-os", 7, ("bqa:ready-qa",), ("bqa:qa-failed", "bqa:blocked")),
            label_events,
        )

    def test_autopilot_routes_issue_to_subagent_before_development(self):
        orchestrator = load_orchestrator()
        events = []

        with tempfile.TemporaryDirectory() as tmp:
            orchestrator.RUNS_DIR = Path(tmp) / "runs"

            orchestrator.list_candidate_issues = lambda repo, execute, label="bqa:ready-dev": [21]
            orchestrator.issue_json = lambda repo, number, execute: json.dumps(
                {"title": "Improve landing page", "body": "Update UI copy and layout.", "labels": []}
            )
            orchestrator.route_issue_to_subagent = lambda repo, issue, raw, execute: {
                "subagent": "designer-frontend",
                "reason": "UI implementation task",
            }
            orchestrator.cmd_dev = lambda args: events.append(("dev", args.issue, getattr(args, "subagent", None)))
            orchestrator.cmd_qa = lambda args: orchestrator.write(
                orchestrator.RUNS_DIR / "qa_pr_31.out.txt", "QA_STATUS: PASS\n"
            )
            orchestrator.cmd_business_accept = lambda args: orchestrator.write(
                orchestrator.RUNS_DIR / "business_accept_pr_31.out.txt", "BUSINESS_STATUS: ACCEPT\n"
            )
            orchestrator.find_pr_for_branch = lambda repo, branch, execute: 31
            orchestrator.run = lambda cmd, *, execute, capture=False, check=True: subprocess.CompletedProcess(
                cmd, 0, stdout="", stderr=""
            )

            args = SimpleNamespace(
                repo="mshegolev/bqa-os",
                execute=True,
                issue_label="bqa:ready-dev",
                oldest_first=True,
                auto_commit=True,
                merge=False,
                close_issue=False,
                stop_on_fail=True,
                branch=None,
            )

            status = orchestrator.run_autopilot_cycle(args)

        self.assertEqual(status, "processed")
        self.assertIn(("dev", 21, "designer-frontend"), events)

    def test_parse_replan_actions_extracts_create_and_cancel_blocks(self):
        orchestrator = load_orchestrator()

        actions = orchestrator.parse_replan_actions(
            """
---CREATE_ISSUE---
TITLE: Add install smoke test
LABELS: bqa:ready-dev,bqa:qa
BODY:
Create a smoke test for install.sh.
---END_CREATE_ISSUE---

---CANCEL_ISSUE---
NUMBER: 15
REASON: Replaced by the install smoke test issue.
---END_CANCEL_ISSUE---
"""
        )

        self.assertEqual(
            actions["create"],
            [
                {
                    "title": "Add install smoke test",
                    "labels": ["bqa:ready-dev", "bqa:qa"],
                    "body": "Create a smoke test for install.sh.",
                }
            ],
        )
        self.assertEqual(actions["cancel"], [{"number": 15, "reason": "Replaced by the install smoke test issue."}])

    def test_autopilot_runs_replan_after_configured_processed_count(self):
        orchestrator = load_orchestrator()
        events = []
        statuses = iter(["processed", "processed", "idle"])

        orchestrator.require_tools = lambda names, execute: None
        orchestrator.run_autopilot_cycle = lambda args: next(statuses)
        orchestrator.cmd_replan = lambda args: events.append(("replan", args.repo))
        orchestrator.write_monitor_status = lambda repo, execute, status="unknown", processed=0: events.append(
            ("monitor", status, processed)
        )
        orchestrator.time.sleep = lambda seconds: None

        args = SimpleNamespace(
            repo="mshegolev/bqa-os",
            execute=True,
            once=False,
            max_cycles=3,
            sleep_seconds=0,
            stop_on_fail=True,
            replan_every=2,
        )

        orchestrator.cmd_autopilot(args)

        self.assertIn(("replan", "mshegolev/bqa-os"), events)
        self.assertIn(("monitor", "processed", 2), events)

    def test_autopilot_parser_supports_stop_on_fail_override(self):
        orchestrator = load_orchestrator()

        args = orchestrator.build_parser().parse_args(["--repo", "mshegolev/bqa-os", "autopilot", "--stop-on-fail"])

        self.assertTrue(args.stop_on_fail)

    def test_list_ready_issues_can_list_all_open_issues_without_label_filter(self):
        orchestrator = load_orchestrator()
        calls = []

        def fake_run(cmd, *, execute, capture=False, check=True):
            calls.append(cmd)
            return subprocess.CompletedProcess(cmd, 0, stdout="3\n4\n", stderr="")

        orchestrator.run = fake_run

        issues = orchestrator.list_ready_issues("mshegolev/bqa-os", True, None)

        self.assertEqual(issues, [3, 4])
        self.assertNotIn("--label", calls[0])

    def test_candidate_issues_skip_blocked_non_dev_and_blocked_dependencies(self):
        orchestrator = load_orchestrator()
        payload = [
            {"number": 1, "body": "", "state": "OPEN", "labels": [{"name": "bqa:ready-dev"}]},
            {"number": 2, "body": "", "state": "OPEN", "labels": [{"name": "bqa:blocked"}]},
            {"number": 3, "body": "", "state": "OPEN", "labels": [{"name": "bqa:ready-qa"}]},
            {"number": 4, "body": "Depends on #2", "state": "OPEN", "labels": [{"name": "bqa:ready-dev"}]},
            {"number": 5, "body": "", "state": "OPEN", "labels": [{"name": "bqa:in-dev"}]},
            {"number": 6, "body": "", "state": "OPEN", "labels": []},
        ]

        orchestrator.open_issue_snapshot = lambda repo, execute, label=None: json.dumps(payload)

        issues = orchestrator.list_candidate_issues("mshegolev/bqa-os", True, None)

        self.assertEqual(issues, [1, 6])

    def test_candidate_issues_skip_blocked_dependencies_with_label_filter(self):
        orchestrator = load_orchestrator()
        payload = [
            {"number": 1, "body": "", "state": "OPEN", "labels": [{"name": "bqa:ready-dev"}]},
            {"number": 2, "body": "", "state": "OPEN", "labels": [{"name": "bqa:blocked"}]},
            {"number": 3, "body": "Depends on #2", "state": "OPEN", "labels": [{"name": "bqa:ready-dev"}]},
            {"number": 4, "body": "Depends on #1", "state": "OPEN", "labels": [{"name": "bqa:ready-dev"}]},
            {"number": 5, "body": "", "state": "OPEN", "labels": [{"name": "bqa:ready-qa"}]},
        ]

        orchestrator.open_issue_snapshot = lambda repo, execute, label=None: json.dumps(payload)

        issues = orchestrator.list_candidate_issues("mshegolev/bqa-os", True, "bqa:ready-dev")

        self.assertEqual(issues, [1, 4])

    def test_checkout_issue_branch_uses_existing_local_branch(self):
        orchestrator = load_orchestrator()
        calls = []

        def fake_run(cmd, *, execute, capture=False, check=True):
            calls.append(cmd)
            if cmd[:3] == ["git", "rev-parse", "--verify"]:
                return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        orchestrator.run = fake_run

        orchestrator.checkout_issue_branch("codex/issue-28-sales-pilot-landing-page", True)

        self.assertIn(["git", "checkout", "codex/issue-28-sales-pilot-landing-page"], calls)
        self.assertNotIn(["git", "checkout", "-b", "codex/issue-28-sales-pilot-landing-page"], calls)

    def test_monitor_snapshot_counts_done_and_doing_buckets(self):
        orchestrator = load_orchestrator()

        def fake_run(cmd, *, execute, capture=False, check=True):
            if "--state" in cmd and cmd[cmd.index("--state") + 1] == "closed":
                return subprocess.CompletedProcess(cmd, 0, stdout="8\n", stderr="")
            if "--label" not in cmd:
                return subprocess.CompletedProcess(cmd, 0, stdout="20\n", stderr="")
            label = cmd[cmd.index("--label") + 1]
            counts = {
                "bqa:ready-dev": "4\n",
                "bqa:in-dev": "1\n",
                "bqa:ready-qa": "2\n",
                "bqa:ready-business": "3\n",
                "bqa:blocked": "5\n",
            }
            return subprocess.CompletedProcess(cmd, 0, stdout=counts[label], stderr="")

        orchestrator.run = fake_run

        snapshot = orchestrator.monitor_snapshot("mshegolev/bqa-os", True)

        self.assertEqual(snapshot["issues"]["open_total"], 20)
        self.assertEqual(snapshot["issues"]["completed_done"], 8)
        self.assertEqual(snapshot["issues"]["doing"], 6)
        self.assertEqual(snapshot["issues"]["blocked"], 5)

    def test_write_monitor_status_writes_json_and_markdown(self):
        orchestrator = load_orchestrator()

        with tempfile.TemporaryDirectory() as tmp:
            orchestrator.STATUS_DIR = Path(tmp) / "status"
            orchestrator.STATUS_JSON = orchestrator.STATUS_DIR / "autopilot-status.json"
            orchestrator.STATUS_MD = orchestrator.STATUS_DIR / "autopilot-status.md"
            orchestrator.monitor_snapshot = lambda repo, execute: {
                "repo": repo,
                "updated_at": "2026-06-29T00:00:00+00:00",
                "issues": {
                    "open_total": 9,
                    "ready_dev": 4,
                    "doing": 2,
                    "in_dev": 1,
                    "ready_qa": 1,
                    "ready_business": 0,
                    "blocked": 1,
                    "completed_done": 3,
                },
            }

            snapshot = orchestrator.write_monitor_status("mshegolev/bqa-os", True, "processed", 7)

            self.assertEqual(snapshot["last_cycle_status"], "processed")
            self.assertEqual(snapshot["processed_this_run"], 7)
            self.assertTrue(orchestrator.STATUS_JSON.exists())
            self.assertTrue(orchestrator.STATUS_MD.exists())
            self.assertIn("Completed done: 3", orchestrator.STATUS_MD.read_text())

    def test_autopilot_history_records_processed_cycle_details(self):
        orchestrator = load_orchestrator()

        with tempfile.TemporaryDirectory() as tmp:
            orchestrator.STATUS_DIR = Path(tmp) / "status"
            orchestrator.STATUS_JSON = orchestrator.STATUS_DIR / "autopilot-status.json"
            orchestrator.STATUS_MD = orchestrator.STATUS_DIR / "autopilot-status.md"
            orchestrator.AUTOPILOT_HISTORY = orchestrator.STATUS_DIR / "autopilot-history.jsonl"
            orchestrator.require_tools = lambda names, execute: None
            orchestrator.write_monitor_status = lambda repo, execute, status="unknown", processed=0: {
                "last_cycle_status": status,
                "processed_this_run": processed,
            }
            orchestrator.time.sleep = lambda seconds: None

            def fake_cycle(args):
                orchestrator.set_last_autopilot_cycle(
                    {
                        "status": "processed",
                        "issue": 42,
                        "title": "Add Widget",
                        "branch": "codex/issue-42-add-widget",
                        "pr": 77,
                        "subagent": "go-cli-implementer",
                        "route_reason": "CLI override.",
                        "stop_reason": "completed",
                    }
                )
                return "processed"

            orchestrator.run_autopilot_cycle = fake_cycle
            args = SimpleNamespace(
                repo="mshegolev/bqa-os",
                execute=True,
                once=True,
                max_cycles=1,
                sleep_seconds=0,
                stop_on_fail=False,
                replan_every=0,
            )

            orchestrator.cmd_autopilot(args)

            entries = [json.loads(line) for line in orchestrator.AUTOPILOT_HISTORY.read_text().splitlines()]
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["repo"], "mshegolev/bqa-os")
            self.assertEqual(entries[0]["cycle"], 1)
            self.assertEqual(entries[0]["total_cycles"], 1)
            self.assertEqual(entries[0]["status"], "processed")
            self.assertEqual(entries[0]["processed_this_run"], 1)
            self.assertEqual(entries[0]["issue"], 42)
            self.assertEqual(entries[0]["branch"], "codex/issue-42-add-widget")
            self.assertEqual(entries[0]["pr"], 77)
            self.assertEqual(entries[0]["subagent"], "go-cli-implementer")
            self.assertEqual(entries[0]["stop_reason"], "completed")

    def test_autopilot_cycle_records_missing_pr_stop_reason(self):
        orchestrator = load_orchestrator()

        with tempfile.TemporaryDirectory() as tmp:
            orchestrator.RUNS_DIR = Path(tmp) / "runs"
            orchestrator.list_candidate_issues = lambda repo, execute, label="bqa:ready-dev": [42]
            orchestrator.issue_json = lambda repo, number, execute: json.dumps(
                {"title": "Add Widget", "body": "Build it", "labels": []}
            )
            orchestrator.route_issue_to_subagent = lambda repo, issue, raw, execute: {
                "subagent": "go-cli-implementer",
                "reason": "Default route.",
            }
            orchestrator.sync_base_branch = lambda args: None
            orchestrator.cmd_dev = lambda args: orchestrator.write(
                orchestrator.RUNS_DIR / "dev_issue_42.out.txt",
                "QUESTION_STATUS: CLOSED\n",
            )
            orchestrator.find_pr_for_branch = lambda repo, branch, execute: None
            orchestrator.edit_issue_labels = lambda *args, **kwargs: None

            args = SimpleNamespace(
                repo="mshegolev/bqa-os",
                execute=True,
                issue_label="bqa:ready-dev",
                oldest_first=True,
                auto_commit=True,
                merge=True,
                close_issue=True,
                stop_on_fail=False,
                branch=None,
                subagent=None,
            )

            status = orchestrator.run_autopilot_cycle(args)

            self.assertEqual(status, "blocked")
            self.assertEqual(orchestrator.LAST_AUTOPILOT_CYCLE["status"], "blocked")
            self.assertEqual(orchestrator.LAST_AUTOPILOT_CYCLE["issue"], 42)
            self.assertEqual(orchestrator.LAST_AUTOPILOT_CYCLE["stop_reason"], "missing_pr")

    def test_run_output_has_status_ignores_prompt_instructions(self):
        orchestrator = load_orchestrator()

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "dev_issue.out.txt"
            output.write_text(
                "- If blocked or requirements are ambiguous, output QUESTION_STATUS: OPEN with details.\n"
                "Implementation completed without questions.\n"
            )

            self.assertFalse(orchestrator.run_output_has_status(output, "QUESTION_STATUS", "OPEN"))

    def test_run_output_has_status_ignores_fenced_prompt_contract(self):
        orchestrator = load_orchestrator()

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "dev_issue.out.txt"
            output.write_text(
                "Prompt instructions:\n"
                "```text\n"
                "QUESTION_STATUS: OPEN\n"
                "QUESTION_TYPE: architecture | product | qa | implementation\n"
                "BLOCKS_ISSUE: <issue number>\n"
                "```\n"
                "Implementation completed without questions.\n"
            )

            self.assertFalse(orchestrator.run_output_has_status(output, "QUESTION_STATUS", "OPEN"))

    def test_run_output_has_status_ignores_prompt_echo_after_stdin_marker(self):
        orchestrator = load_orchestrator()

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "dev_issue.out.txt"
            output.write_text(
                "Implemented feature successfully.\n"
                "\n"
                "Reading additional input from stdin...\n"
                "OpenAI Codex v0.142.0\n"
                "--------\n"
                "user\n"
                "If blocked or requirements are ambiguous, output:\n"
                "QUESTION_STATUS: OPEN\n"
                "QUESTION_TYPE: architecture | product | qa | implementation\n"
            )

            self.assertFalse(orchestrator.run_output_has_status(output, "QUESTION_STATUS", "OPEN"))

    def test_run_output_has_status_detects_explicit_status_line(self):
        orchestrator = load_orchestrator()

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "dev_issue.out.txt"
            output.write_text(
                "Developer cannot continue.\n"
                "QUESTION_STATUS: OPEN\n"
                "QUESTION_TYPE: REQUIREMENTS\n"
                "BLOCKS_ISSUE: true\n"
            )

            self.assertTrue(orchestrator.run_output_has_status(output, "QUESTION_STATUS", "OPEN"))

    def test_parse_issue_dependencies_from_explicit_references(self):
        orchestrator = load_orchestrator()

        deps = orchestrator.parse_issue_dependencies(
            "Depends on #12 and blocked by #17. Related to #99 but not a dependency."
        )

        self.assertEqual(deps, [12, 17])

    def test_project_view_model_extracts_statuses_and_dependencies(self):
        orchestrator = load_orchestrator()

        payload = [
            {
                "number": 2,
                "title": "Build CLI",
                "body": "Depends on #1",
                "state": "OPEN",
                "url": "https://example.test/2",
                "labels": [{"name": "bqa:in-dev"}],
                "createdAt": "2026-06-01T00:00:00Z",
                "updatedAt": "2026-06-02T00:00:00Z",
                "closedAt": None,
            },
            {
                "number": 1,
                "title": "Define core",
                "body": "",
                "state": "CLOSED",
                "url": "https://example.test/1",
                "labels": [{"name": "bqa:done"}],
                "createdAt": "2026-05-30T00:00:00Z",
                "updatedAt": "2026-06-01T00:00:00Z",
                "closedAt": "2026-06-01T00:00:00Z",
            },
        ]

        orchestrator.issue_project_snapshot = lambda repo, execute, limit=100: json.dumps(payload)

        view = orchestrator.project_view_model("mshegolev/bqa-os", True, 100)

        self.assertEqual(view["counts"]["in-dev"], 1)
        self.assertEqual(view["counts"]["done"], 1)
        self.assertEqual(view["edges"], [{"from": 1, "to": 2}])

    def test_issue_project_snapshot_fails_loudly_when_gh_fails(self):
        orchestrator = load_orchestrator()
        orchestrator.run = lambda cmd, *, execute, capture=False, check=True: subprocess.CompletedProcess(
            cmd, 1, stdout="", stderr="network unavailable"
        )

        with self.assertRaises(SystemExit) as err:
            orchestrator.issue_project_snapshot("mshegolev/bqa-os", True, 100)

        self.assertIn("network unavailable", str(err.exception))

    def test_render_project_view_html_contains_gantt_and_dependency_data(self):
        orchestrator = load_orchestrator()

        html = orchestrator.render_project_view_html(
            {
                "repo": "mshegolev/bqa-os",
                "updated_at": "2026-06-29T00:00:00+00:00",
                "counts": {"ready-dev": 1, "in-dev": 1, "ready-qa": 0, "ready-business": 0, "blocked": 0, "done": 0},
                "issues": [
                    {
                        "number": 2,
                        "title": "Build CLI",
                        "url": "https://example.test/2",
                        "status": "in-dev",
                        "labels": ["bqa:in-dev"],
                        "deps": [1],
                        "created_at": "2026-06-01T00:00:00Z",
                        "updated_at": "2026-06-02T00:00:00Z",
                    }
                ],
                "edges": [{"from": 1, "to": 2}],
            }
        )

        self.assertIn("BQA Project View", html)
        self.assertIn("Build CLI", html)
        self.assertIn("#1 -> #2", html)

    def test_write_default_autopilot_config_creates_reusable_config(self):
        orchestrator = load_orchestrator()

        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "autopilot-config.json"

            config = orchestrator.write_default_autopilot_config(config_path, "mshegolev/bqa-os")

            saved = json.loads(config_path.read_text())
            self.assertEqual(config["repo"], "mshegolev/bqa-os")
            self.assertEqual(saved["max_cycles"], 200)
            self.assertTrue(saved["all_open"])
            self.assertEqual(saved["replan_every"], 7)
            self.assertFalse(saved["stop_on_fail"])

    def test_apply_autopilot_config_fills_missing_args(self):
        orchestrator = load_orchestrator()

        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "autopilot-config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "repo": "mshegolev/bqa-os",
                        "max_cycles": 50,
                        "sleep_seconds": 10,
                        "all_open": True,
                        "oldest_first": True,
                        "merge": True,
                        "close_issue": True,
                        "replan_every": 5,
                        "vision_file": ".bqa-team/PROJECT_VISION.md",
                        "issue_limit": 100,
                        "base_branch": "main",
                        "auto_commit": True,
                        "stop_on_fail": True,
                    }
                )
            )
            args = SimpleNamespace(repo="default/repo", config=str(config_path), max_cycles=None, all_open=None)

            orchestrator.apply_autopilot_config(args)

            self.assertEqual(args.repo, "mshegolev/bqa-os")
            self.assertEqual(args.max_cycles, 50)
            self.assertEqual(args.sleep_seconds, 10)
            self.assertTrue(args.all_open)
            self.assertTrue(args.merge)


if __name__ == "__main__":
    unittest.main()
