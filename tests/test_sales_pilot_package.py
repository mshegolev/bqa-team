import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SALES_DIR = ROOT / "docs" / "sales-pilot"


class SalesPilotPackageTests(unittest.TestCase):
    def test_sales_pilot_package_contains_required_artifacts(self):
        required = [
            "README.md",
            "one-pager.md",
            "demo-script.md",
            "discovery-call-script.md",
            "onboarding-checklist.md",
            "outreach-snippets.md",
            "pricing-hypothesis.md",
            "stakeholder-faq.md",
        ]

        for filename in required:
            with self.subTest(filename=filename):
                path = SALES_DIR / filename
                self.assertTrue(path.exists(), f"missing {filename}")
                self.assertGreater(len(path.read_text(encoding="utf-8").strip()), 200)

    def test_sales_pilot_package_matches_buyer_and_safety_profile(self):
        combined = "\n".join(path.read_text(encoding="utf-8") for path in SALES_DIR.glob("*.md"))

        for phrase in [
            "QA Lead",
            "QA Automation Lead",
            "local-first",
            "synthetic",
            "sanitized",
            "validation",
            "2-week QA Memory Pilot",
        ]:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, combined)

        forbidden = [
            "real customer data",
            "production dumps required",
            "credentials required",
            "upload private logs",
        ]
        lower = combined.lower()
        for phrase in forbidden:
            with self.subTest(forbidden=phrase):
                self.assertNotIn(phrase, lower)


if __name__ == "__main__":
    unittest.main()
