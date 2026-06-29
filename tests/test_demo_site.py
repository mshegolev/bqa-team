import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SITE_DIR = ROOT / "demo" / "site"


class DemoSiteTests(unittest.TestCase):
    def test_static_site_files_exist(self):
        for filename in ["index.html", "styles.css", "app.js"]:
            with self.subTest(filename=filename):
                self.assertTrue((SITE_DIR / filename).exists())

    def test_index_contains_required_app_regions_and_labels(self):
        index = SITE_DIR / "index.html"
        self.assertTrue(index.exists(), "index.html should exist")
        html = index.read_text(encoding="utf-8")

        for expected in [
            "BQA Demo Archive",
            "Local only",
            "Upload synthetic archive",
            "Archive validated",
            "Agents",
            "Workflows",
            "Specs",
            "Knowledge",
            "Recommendations",
            "Download result",
        ]:
            with self.subTest(expected=expected):
                self.assertIn(expected, html)

    def test_app_references_bundled_fixture(self):
        app_path = SITE_DIR / "app.js"
        self.assertTrue(app_path.exists(), "app.js should exist")
        app = app_path.read_text(encoding="utf-8")

        self.assertIn("../fixtures/bqa-demo-archive.json", app)

    def test_app_does_not_use_network_upload_primitives(self):
        app_path = SITE_DIR / "app.js"
        self.assertTrue(app_path.exists(), "app.js should exist")
        app = app_path.read_text(encoding="utf-8")

        for forbidden in ["fetch(", "XMLHttpRequest", "navigator.sendBeacon", "WebSocket"]:
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, app)


if __name__ == "__main__":
    unittest.main()
