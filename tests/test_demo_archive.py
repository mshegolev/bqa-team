import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_PATH = ROOT / "demo" / "fixtures" / "bqa-demo-archive.json"


class DemoArchiveTests(unittest.TestCase):
    def load_archive(self):
        self.assertTrue(ARCHIVE_PATH.exists(), "demo fixture should exist")
        return json.loads(ARCHIVE_PATH.read_text(encoding="utf-8"))

    def test_archive_contains_required_sections(self):
        archive = self.load_archive()

        required = [
            "manifest",
            "sessions",
            "agents",
            "workflows",
            "specs",
            "knowledge",
            "recommendations",
        ]
        for section in required:
            with self.subTest(section=section):
                self.assertIn(section, archive)

    def test_manifest_marks_archive_as_synthetic(self):
        archive = self.load_archive()
        manifest = archive["manifest"]

        self.assertEqual(manifest["archive_type"], "bqa-demo")
        self.assertTrue(manifest["synthetic"])
        self.assertEqual(manifest["privacy"], "synthetic-only")

    def test_artifact_sections_are_non_empty_lists(self):
        archive = self.load_archive()

        for section in ["sessions", "agents", "workflows", "specs", "knowledge", "recommendations"]:
            with self.subTest(section=section):
                self.assertIsInstance(archive[section], list)
                self.assertGreater(len(archive[section]), 0)

    def test_archive_does_not_contain_private_data_terms(self):
        self.assertTrue(ARCHIVE_PATH.exists(), "demo fixture should exist")
        text = ARCHIVE_PATH.read_text(encoding="utf-8").lower()

        forbidden_terms = [
            "password",
            "secret",
            "token",
            "customer",
            "jira_token",
            "confluence_token",
            "authorization",
            "bearer ",
        ]
        for term in forbidden_terms:
            with self.subTest(term=term):
                self.assertNotIn(term, text)


if __name__ == "__main__":
    unittest.main()
