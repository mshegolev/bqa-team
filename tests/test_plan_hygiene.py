import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PlanHygieneTests(unittest.TestCase):
    def test_completed_superpower_plans_have_no_unchecked_steps(self):
        plan_files = sorted((ROOT / "docs" / "superpowers" / "plans").glob("*.md"))
        self.assertGreater(len(plan_files), 0)

        unchecked = []
        for path in plan_files:
            for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                if re.match(r"^- \[ \]", line):
                    unchecked.append(f"{path.relative_to(ROOT)}:{lineno}: {line}")

        self.assertEqual(unchecked, [])


if __name__ == "__main__":
    unittest.main()
