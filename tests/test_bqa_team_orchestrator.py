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
    def test_autopilot_cycle_runs_dev_qa_business_acceptance_and_marks_done(self):
        orchestrator = load_orchestrator()
        events = []

        with tempfile.TemporaryDirectory() as tmp:
            orchestrator.RUNS_DIR = Path(tmp) / "runs"

            orchestrator.list_ready_issues = lambda repo, execute, label="bqa:ready-dev": [42]
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

    def test_autopilot_cycle_stops_before_business_acceptance_when_qa_fails(self):
        orchestrator = load_orchestrator()
        events = []

        with tempfile.TemporaryDirectory() as tmp:
            orchestrator.RUNS_DIR = Path(tmp) / "runs"

            orchestrator.list_ready_issues = lambda repo, execute, label="bqa:ready-dev": [7]
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

    def test_autopilot_routes_issue_to_subagent_before_development(self):
        orchestrator = load_orchestrator()
        events = []

        with tempfile.TemporaryDirectory() as tmp:
            orchestrator.RUNS_DIR = Path(tmp) / "runs"

            orchestrator.list_ready_issues = lambda repo, execute, label="bqa:ready-dev": [21]
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
