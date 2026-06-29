import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSTALL = ROOT / "scripts" / "install.sh"


class AutopilotDryRunSmokeTests(unittest.TestCase):
    def test_installed_team_pack_runs_local_dry_run_autopilot_smoke(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "target"
            target.mkdir()
            self._run(["git", "init"], cwd=target)

            self._run(["bash", str(INSTALL), str(target)], cwd=ROOT)
            self.assertTrue((target / "scripts" / "bqa_team_orchestrator.py").exists())
            self.assertTrue((target / ".bqa-team" / "roles" / "BQA_OS_QA_Test_Engineer.md").exists())

            self._run(["python3", "scripts/bqa_team_orchestrator.py", "--repo", "example/repo", "init"], cwd=target)
            self._run(["python3", "scripts/bqa_team_orchestrator.py", "--repo", "example/repo", "architect"], cwd=target)
            self._run(["python3", "scripts/bqa_team_orchestrator.py", "--repo", "example/repo", "create-issues"], cwd=target)
            self._run(
                ["python3", "scripts/bqa_team_orchestrator.py", "--repo", "example/repo", "autopilot", "--once"],
                cwd=target,
            )

            issue_specs = sorted((target / ".bqa-team" / "generated" / "issues").glob("*.issues.md"))
            self.assertGreater(len(issue_specs), 0)
            self.assertIn("DRY-RUN", (target / ".bqa-team" / "state.json").read_text(encoding="utf-8"))

            status = json.loads((target / ".bqa-team" / "status" / "autopilot-status.json").read_text(encoding="utf-8"))
            self.assertEqual(status["repo"], "example/repo")
            self.assertEqual(status["last_cycle_status"], "idle")
            self.assertEqual(status["processed_this_run"], 0)

            history = (target / ".bqa-team" / "status" / "autopilot-history.jsonl").read_text(encoding="utf-8")
            last_record = json.loads(history.strip().splitlines()[-1])
            self.assertEqual(last_record["status"], "idle")
            self.assertEqual(last_record["stop_reason"], "no_candidates")

    def _run(self, cmd: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, timeout=30, check=True)


if __name__ == "__main__":
    unittest.main()
