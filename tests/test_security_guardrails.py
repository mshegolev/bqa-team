import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONSENT = ROOT / "scripts" / "bqa_consent.sh"
GUARD = ROOT / "scripts" / "bqa_agent_guard.sh"


class SecurityGuardrailTests(unittest.TestCase):
    def test_consent_rejects_incorrect_answer_and_does_not_persist(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)

            result = subprocess.run(
                ["bash", str(CONSENT), str(target)],
                input="no\n",
                text=True,
                capture_output=True,
                timeout=10,
            )

            self.assertEqual(result.returncode, 3)
            self.assertIn("Consent not granted", result.stdout)
            self.assertFalse((target / ".bqa-team" / "consent" / "team-consent.accepted").exists())

    def test_consent_accepts_once_and_skips_prompt_next_time(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            consent_file = target / ".bqa-team" / "consent" / "team-consent.accepted"

            accepted = subprocess.run(
                ["bash", str(CONSENT), str(target)],
                input="I AGREE\n",
                text=True,
                capture_output=True,
                timeout=10,
            )
            second = subprocess.run(
                ["bash", str(CONSENT), str(target)],
                input="",
                text=True,
                capture_output=True,
                timeout=10,
            )

            self.assertEqual(accepted.returncode, 0, accepted.stderr)
            self.assertTrue(consent_file.exists())
            self.assertIn("Consent saved", accepted.stdout)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(second.stdout, "")

    def test_agent_guard_stops_etl_goal_when_source_files_changed(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            self._init_repo(target)
            source_file = target / "internal" / "unexpected.go"
            source_file.parent.mkdir()
            source_file.write_text("package internal\n", encoding="utf-8")

            result = self._run_guard(target, goal="ETL QA Pack under .bqa/output/etl-agent-pack")

            self.assertEqual(result.returncode, 2)
            report = (target / ".bqa-team" / "safety" / "drift_report.md").read_text(encoding="utf-8")
            self.assertIn("DRIFT_STATUS: STOP", report)
            self.assertIn("ETL artifact task changed Go/source files unexpectedly", report)

    def test_agent_guard_stops_on_invalid_etl_pack_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            self._init_repo(target)
            stats = target / ".bqa" / "output" / "etl-agent-pack" / "statistics" / "session_stats.json"
            stats.parent.mkdir(parents=True)
            stats.write_text("{invalid json\n", encoding="utf-8")

            result = self._run_guard(target, goal="Validate ETL QA Pack")

            self.assertEqual(result.returncode, 2)
            report = (target / ".bqa-team" / "safety" / "drift_report.md").read_text(encoding="utf-8")
            self.assertIn("DRIFT_STATUS: STOP", report)
            self.assertIn("statistics/session_stats.json is invalid", report)

    def _init_repo(self, target: Path) -> None:
        subprocess.run(["git", "init"], cwd=target, text=True, capture_output=True, timeout=10, check=True)

    def _run_guard(self, target: Path, *, goal: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["BQA_TARGET_GOAL"] = goal
        return subprocess.run(
            ["bash", str(GUARD), str(target)],
            text=True,
            capture_output=True,
            timeout=10,
            env=env,
        )


if __name__ == "__main__":
    unittest.main()
