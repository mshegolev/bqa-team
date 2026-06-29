import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ProjectFoundationTests(unittest.TestCase):
    def test_makefile_exposes_standard_verification_targets(self):
        makefile = ROOT / "Makefile"

        self.assertTrue(makefile.exists(), "Makefile should define the local verification contract")

        content = makefile.read_text(encoding="utf-8")
        for target in ["test", "lint", "verify"]:
            with self.subTest(target=target):
                self.assertRegex(content, rf"(?m)^{re.escape(target)}:")

    def test_ci_delegates_to_make_verify(self):
        workflow = ROOT / ".github" / "workflows" / "ci.yml"

        self.assertTrue(workflow.exists(), "CI should run the same verification command used locally")

        content = workflow.read_text(encoding="utf-8")
        self.assertIn("make verify", content)
        self.assertIn("actions/checkout", content)
        self.assertIn("actions/setup-python", content)

    def test_roadmap_references_every_backlog_item(self):
        roadmap = ROOT / "docs" / "ROADMAP.md"

        self.assertTrue(roadmap.exists(), "docs/ROADMAP.md should map backlog to delivery phases")

        content = roadmap.read_text(encoding="utf-8")
        backlog_files = sorted((ROOT / "team" / "backlog").glob("*.md"))
        self.assertGreater(len(backlog_files), 0)
        for backlog_file in backlog_files:
            with self.subTest(backlog=backlog_file.name):
                self.assertIn(f"team/backlog/{backlog_file.name}", content)

    def test_gitignore_excludes_python_runtime_artifacts(self):
        gitignore = ROOT / ".gitignore"
        content = gitignore.read_text(encoding="utf-8")

        self.assertIn("__pycache__/", content)
        self.assertIn("*.pyc", content)


if __name__ == "__main__":
    unittest.main()
