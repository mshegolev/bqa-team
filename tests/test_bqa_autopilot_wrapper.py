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
            self.addCleanup(self._stop_pid, stale_process.pid)
            (status_dir / "autopilot.pid").write_text(f"{stale_process.pid}\n", encoding="utf-8")

            result = self._run_wrapper("status", target_repo, team_repo, {"BQA_AUTOPILOT_STALE_SECONDS": "1"})

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Auto-heal: stale autopilot PID", result.stdout)
            self.assertIsNotNone(stale_process.poll())
            new_pid = int((status_dir / "autopilot.pid").read_text(encoding="utf-8").strip())
            self.assertNotEqual(new_pid, stale_process.pid)
            self._stop_pid(new_pid)

    def _make_fake_runtime(self, tmp_path: Path) -> tuple[Path, Path]:
        target_repo = tmp_path / "target"
        team_repo = tmp_path / "team"
        (target_repo / ".git").mkdir(parents=True)
        (target_repo / ".bqa-team").mkdir()
        (target_repo / ".bqa-team" / "autopilot-config.json").write_text(
            '{"repo":"example/repo","max_cycles":1,"sleep_seconds":0}\n',
            encoding="utf-8",
        )
        scripts_dir = team_repo / "scripts"
        scripts_dir.mkdir(parents=True)
        orchestrator = scripts_dir / "bqa_team_orchestrator.py"
        orchestrator.write_text(
            """#!/usr/bin/env python3
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
""",
            encoding="utf-8",
        )
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
            timeout=10,
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


if __name__ == "__main__":
    unittest.main()
