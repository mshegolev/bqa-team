import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "scripts" / "bqa_autopilot.sh"


class BQAAutopilotWrapperTests(unittest.TestCase):
    def test_status_autoheals_dead_pid_and_restarts(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            target_repo, team_repo = self._make_fake_runtime(tmp_path)
            pid_file = target_repo / ".bqa-team" / "status" / "autopilot.pid"
            pid_file.parent.mkdir(parents=True, exist_ok=True)
            pid_file.write_text("999999\n", encoding="utf-8")

            result = self._run_wrapper("status", target_repo, team_repo)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Auto-heal: removed stale autopilot PID 999999", result.stdout)
            self.assertIn("Started BQA autopilot.", result.stdout)
            new_pid = int(pid_file.read_text(encoding="utf-8").strip())
            self.assertNotEqual(new_pid, 999999)
            self._stop_pid(new_pid)

    def test_status_autoheals_stale_running_pid_and_restarts(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            target_repo, team_repo = self._make_fake_runtime(tmp_path)
            status_dir = target_repo / ".bqa-team" / "status"
            log_dir = target_repo / ".bqa-team" / "logs"
            status_dir.mkdir(parents=True, exist_ok=True)
            log_dir.mkdir(parents=True, exist_ok=True)
            old_log = log_dir / "autopilot.log"
            old_log.write_text("old activity\n", encoding="utf-8")
            old_epoch = time.time() - 3600
            os.utime(old_log, (old_epoch, old_epoch))

            stale_process = subprocess.Popen(["sleep", "60"])
            self.addCleanup(self._stop_process, stale_process)
            (status_dir / "autopilot.pid").write_text(f"{stale_process.pid}\n", encoding="utf-8")

            result = self._run_wrapper(
                "status",
                target_repo,
                team_repo,
                {"BQA_AUTOPILOT_STALE_SECONDS": "1", "BQA_AUTOPILOT_STARTUP_GRACE_SECONDS": "0.1"},
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Auto-heal: stale autopilot PID", result.stdout)
            self.assertIsNotNone(stale_process.poll())
            new_pid = int((status_dir / "autopilot.pid").read_text(encoding="utf-8").strip())
            self.assertNotEqual(new_pid, stale_process.pid)
            self._stop_pid(new_pid)

    def test_status_keeps_stale_parent_with_fresh_heartbeat_running(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            target_repo, team_repo = self._make_fake_runtime(tmp_path)
            status_dir = target_repo / ".bqa-team" / "status"
            log_dir = target_repo / ".bqa-team" / "logs"
            status_dir.mkdir(parents=True, exist_ok=True)
            log_dir.mkdir(parents=True, exist_ok=True)
            old_log = log_dir / "autopilot.log"
            old_log.write_text("old activity\n", encoding="utf-8")
            old_epoch = time.time() - 3600
            os.utime(old_log, (old_epoch, old_epoch))
            (status_dir / "autopilot-heartbeat").write_text("active\n", encoding="utf-8")

            active_parent = subprocess.Popen(["sleep", "60"])
            self.addCleanup(self._stop_process, active_parent)
            (status_dir / "autopilot.pid").write_text(f"{active_parent.pid}\n", encoding="utf-8")

            result = self._run_wrapper("status", target_repo, team_repo, {"BQA_AUTOPILOT_STALE_SECONDS": "60"})

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(f"BQA autopilot: RUNNING pid={active_parent.pid}", result.stdout)
            self.assertNotIn("Auto-heal: stale autopilot PID", result.stdout)
            self.assertIsNone(active_parent.poll())
            self.assertEqual(
                str(active_parent.pid),
                (status_dir / "autopilot.pid").read_text(encoding="utf-8").strip(),
            )

    def test_stop_terminates_child_process_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            target_repo, team_repo = self._make_fake_runtime(tmp_path)
            status_dir = target_repo / ".bqa-team" / "status"
            status_dir.mkdir(parents=True, exist_ok=True)

            child_pid_file = tmp_path / "child.pid"
            child_term_file = tmp_path / "child.term"
            active_parent = subprocess.Popen(
                [
                    "bash",
                    "-c",
                    (
                        "bash -c '"
                        f"trap \"echo term > {child_term_file}; exit 0\" TERM; "
                        "while true; do sleep 1; done"
                        f"' & echo $! > {child_pid_file}; wait"
                    ),
                ],
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self.addCleanup(self._stop_process, active_parent)
            self._wait_for_file(child_pid_file)
            child_pid = int(child_pid_file.read_text(encoding="utf-8").strip())
            self.addCleanup(self._stop_pid, child_pid)
            (status_dir / "autopilot.pid").write_text(f"{active_parent.pid}\n", encoding="utf-8")

            result = self._run_wrapper("stop", target_repo, team_repo)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(f"Stopped BQA autopilot. PID: {active_parent.pid}", result.stdout)
            active_parent.wait(timeout=5)
            self._wait_for_file(child_term_file)
            self.assertFalse((status_dir / "autopilot.pid").exists())

    def test_status_from_team_repo_uses_sibling_target_repo_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            target_repo, team_repo = self._make_fake_runtime(tmp_path)
            status_dir = target_repo / ".bqa-team" / "status"
            status_dir.mkdir(parents=True, exist_ok=True)
            (status_dir / "autopilot.pid").write_text(f"{os.getpid()}\n", encoding="utf-8")

            result = self._run_wrapper_from_cwd("status", cwd=team_repo, team_repo=team_repo)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(f"BQA target repo: {target_repo.resolve()}", result.stdout)
            self.assertIn(f"BQA autopilot: RUNNING pid={os.getpid()}", result.stdout)

    def test_start_retries_when_first_autopilot_process_exits_immediately(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            target_repo, team_repo = self._make_fake_runtime(tmp_path, fail_first_autopilot_start=True)
            pid_file = target_repo / ".bqa-team" / "status" / "autopilot.pid"

            result = self._run_wrapper(
                "start",
                target_repo,
                team_repo,
                {"BQA_AUTOPILOT_START_RETRIES": "1", "BQA_AUTOPILOT_STARTUP_GRACE_SECONDS": "6"},
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Autopilot start attempt 1 exited immediately; retrying", result.stdout)
            pid = int(pid_file.read_text(encoding="utf-8").strip())
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                self.fail(f"start returned stale PID {pid}")
            attempt_file = target_repo / ".bqa-team" / "status" / "start-attempts"
            self.assertEqual("2", attempt_file.read_text(encoding="utf-8").strip())
            self._stop_pid(pid)

    def _make_fake_runtime(self, tmp_path: Path, *, fail_first_autopilot_start: bool = False) -> tuple[Path, Path]:
        target_repo = tmp_path / "bqa-os"
        team_repo = tmp_path / "bqa-team"
        (target_repo / ".git").mkdir(parents=True)
        (target_repo / ".bqa-team").mkdir()
        (target_repo / ".bqa-team" / "autopilot-config.json").write_text(
            '{"repo":"example/repo","max_cycles":1,"sleep_seconds":0}\n',
            encoding="utf-8",
        )
        scripts_dir = team_repo / "scripts"
        scripts_dir.mkdir(parents=True)
        orchestrator = scripts_dir / "bqa_team_orchestrator.py"
        if fail_first_autopilot_start:
            orchestrator_body = """#!/usr/bin/env python3
import pathlib
import sys
import time

root = pathlib.Path.cwd()
status_dir = root / ".bqa-team" / "status"
status_dir.mkdir(parents=True, exist_ok=True)
attempt_file = status_dir / "start-attempts"

if "monitor" in sys.argv:
    (status_dir / "autopilot-status.md").write_text("# Fake status\\n", encoding="utf-8")
elif "autopilot" in sys.argv:
    attempts = int(attempt_file.read_text(encoding="utf-8")) if attempt_file.exists() else 0
    attempts += 1
    attempt_file.write_text(str(attempts), encoding="utf-8")
    if attempts == 1:
        raise SystemExit(17)
    (status_dir / "autopilot-history.jsonl").write_text('{"status":"started"}\\n', encoding="utf-8")
    time.sleep(60)
elif "configure-autopilot" in sys.argv:
    pass
else:
    raise SystemExit(f"unexpected args: {sys.argv}")
"""
        else:
            orchestrator_body = """#!/usr/bin/env python3
import pathlib
import sys
import time

root = pathlib.Path.cwd()
status_dir = root / ".bqa-team" / "status"
status_dir.mkdir(parents=True, exist_ok=True)

if "monitor" in sys.argv:
    (status_dir / "autopilot-status.md").write_text("# Fake status\\n", encoding="utf-8")
elif "autopilot" in sys.argv:
    (status_dir / "autopilot-history.jsonl").write_text('{"status":"started"}\\n', encoding="utf-8")
    time.sleep(60)
elif "configure-autopilot" in sys.argv:
    pass
else:
    raise SystemExit(f"unexpected args: {sys.argv}")
"""
        orchestrator.write_text(orchestrator_body, encoding="utf-8")
        orchestrator.chmod(0o755)
        return target_repo, team_repo

    def _run_wrapper(self, action: str, target_repo: Path, team_repo: Path, env: dict[str, str] | None = None):
        full_env = os.environ.copy()
        full_env.update(env or {})
        return subprocess.run(
            [
                "bash",
                str(WRAPPER),
                action,
                "--target-repo",
                str(target_repo),
                "--team-repo",
                str(team_repo),
                "--repo",
                "example/repo",
            ],
            text=True,
            capture_output=True,
            env=full_env,
            timeout=40,
        )

    def _run_wrapper_from_cwd(self, action: str, cwd: Path, team_repo: Path):
        return subprocess.run(
            [
                "bash",
                str(WRAPPER),
                action,
                "--team-repo",
                str(team_repo),
                "--repo",
                "example/bqa-os",
            ],
            text=True,
            capture_output=True,
            cwd=cwd,
            timeout=40,
        )

    def _stop_pid(self, pid: int) -> None:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        for _ in range(20):
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                return
            time.sleep(0.05)
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass

    def _stop_process(self, process: subprocess.Popen) -> None:
        if process.poll() is not None:
            return
        self._stop_pid(process.pid)
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            self._stop_pid(process.pid)

    def _wait_for_file(self, path: Path) -> None:
        for _ in range(40):
            if path.exists():
                return
            time.sleep(0.05)
        raise AssertionError(f"file was not created: {path}")


if __name__ == "__main__":
    unittest.main()
