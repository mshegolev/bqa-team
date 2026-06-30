import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "team" / "brain" / "registry.json"
EXPORTER = ROOT / "scripts" / "bqa_brain_export.sh"
INTEGRATION_DOC = ROOT / "docs" / "BQA_BRAIN_INTEGRATION.md"


class BQABrainRegistryTests(unittest.TestCase):
    def test_unified_registry_schema_and_sources(self):
        registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        artifacts = registry["artifacts"]

        self.assertEqual(registry["kind"], "BQATeamUnifiedRegistry")
        self.assertGreaterEqual(len(artifacts), 10)

        seen_ids = set()
        allowed_types = {"agent", "skill", "workflow", "guardrail", "project_profile", "memory_index"}
        allowed_roots = ("agents/", "skills/", "workflows/", "guardrails/", "project-profiles/", "memory/")
        for artifact in artifacts:
            with self.subTest(artifact=artifact.get("id")):
                self.assertIn(artifact["type"], allowed_types)
                self.assertNotIn(artifact["id"], seen_ids)
                seen_ids.add(artifact["id"])
                self.assertFalse(artifact["destination"].startswith("/"))
                self.assertTrue(artifact["destination"].startswith(allowed_roots))
                self.assertTrue((ROOT / artifact["source"]).is_file(), artifact["source"])
                self.assertIsInstance(artifact["tags"], list)
                self.assertGreater(len(artifact["summary"]), 20)

    def test_exporter_writes_unified_brain_artifacts_and_registry(self):
        with tempfile.TemporaryDirectory() as tmp:
            brain_dir = Path(tmp) / "brain"
            result = subprocess.run(
                ["bash", str(EXPORTER), "--brain-dir", str(brain_dir), "--registry", str(REGISTRY)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                timeout=20,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("BQA Brain export complete", result.stdout)

            registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
            for artifact in registry["artifacts"]:
                with self.subTest(destination=artifact["destination"]):
                    exported = brain_dir / artifact["destination"]
                    self.assertTrue(exported.is_file())
                    self.assertIn("BQA_UNIFIED_ARTIFACT", exported.read_text(encoding="utf-8"))

            brain_registry = (brain_dir / "registry" / "bqa_registry.yaml").read_text(encoding="utf-8")
            self.assertIn("kind: BQARegistry", brain_registry)
            self.assertIn("source_registry: team/brain/registry.json", brain_registry)
            self.assertIn("bqa-os-project-profile", brain_registry)

    def test_bqa_os_brain_integration_runbook_is_actionable(self):
        content = INTEGRATION_DOC.read_text(encoding="utf-8")

        for expected in [
            "https://github.com/mshegolev/bqa-brain.git",
            "bqa brain connect",
            "bqa brain pull",
            "scripts/bqa_brain_export.sh",
            "bqa brain sync --sanitize",
            "/opt/develop/bqa-os",
        ]:
            with self.subTest(expected=expected):
                self.assertIn(expected, content)


if __name__ == "__main__":
    unittest.main()
