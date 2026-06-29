import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "bqa_test_only.sh"


class TestingOnlyRunnerTests(unittest.TestCase):
    def test_dry_run_prints_testing_only_prompt_without_launching_codex(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "target"
            (target / ".git").mkdir(parents=True)

            result = subprocess.run(
                [
                    "bash",
                    str(RUNNER),
                    "--target",
                    str(target),
                    "--task",
                    "Add pytest coverage for the synthetic ETL fixture.",
                ],
                text=True,
                capture_output=True,
                timeout=10,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("TESTING-ONLY mode", result.stdout)
        self.assertIn("Do NOT change product/source code", result.stdout)
        self.assertIn("Add pytest coverage for the synthetic ETL fixture.", result.stdout)
        self.assertIn("rerun with --execute", result.stdout)

    def test_rejects_missing_task_before_prompt_generation(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "target"
            (target / ".git").mkdir(parents=True)

            result = subprocess.run(
                ["bash", str(RUNNER), "--target", str(target)],
                text=True,
                capture_output=True,
                timeout=10,
            )

        self.assertEqual(result.returncode, 2)
        self.assertIn("ERROR: --task is required", result.stderr)

    def test_prefers_target_etl_agent_when_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "target"
            role = target / ".bqa" / "agents" / "etl-qa-agent.md"
            (target / ".git").mkdir(parents=True)
            role.parent.mkdir(parents=True)
            role.write_text("# Target ETL QA Agent\n\nUse pytest.\n", encoding="utf-8")

            result = subprocess.run(
                [
                    "bash",
                    str(RUNNER),
                    "--target",
                    str(target),
                    "--task",
                    "Add stage ETL tests.",
                ],
                text=True,
                capture_output=True,
                timeout=10,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("role: " + str(role), result.stdout)
        self.assertIn("# Target ETL QA Agent", result.stdout)


if __name__ == "__main__":
    unittest.main()
