"""Fail-closed checks for the quarantined Autoevolution-derived VAG dataset."""

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "data/source-manifests/vag-factory-source-register.json"
WORKFLOW = ROOT / ".github/workflows/acquire-vag-engine-candidates.yml"
REVIEW = ROOT / "docs/research/AUTOEVOLUTION_UPSTREAM_RIGHTS_REVIEW_2026-11-04.md"


class Gor3aUpstreamRightsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        payload = json.loads(REGISTER.read_text(encoding="utf-8"))
        cls.source = next(
            item for item in payload["sources"]
            if item["source_id"] == "gor3a-vehicle-makes-models-odbl"
        )

    def test_downstream_odbl_does_not_clear_upstream_rights(self):
        rights = self.source["rights"]
        self.assertEqual(rights["data_license_status"], "ODbL-1.0")
        self.assertEqual(rights["upstream_rights_status"], "not_established")
        self.assertEqual(rights["upstream_permission_status"], "not_obtained")
        self.assertEqual(
            rights["downstream_license_scope"],
            "repository_declared_odbl_only_not_proof_of_upstream_autoevolution_rights",
        )
        self.assertIn("quarantine_no_download", self.source["project_decision"])
        self.assertIn("no_import", self.source["project_decision"])
        self.assertIn("no_cache", self.source["project_decision"])

    def test_acquisition_workflow_requires_owner_approval_gate(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn(
            "if: ${{ vars.VAG_GOR3A_AUTODEVOLUTION_REUSE_APPROVED == 'true' }}",
            workflow,
        )
        self.assertIn("VAG_GOR3A_AUTODEVOLUTION_REUSE_APPROVED", workflow)
        self.assertIn("AUTOEVOLUTION_UPSTREAM_RIGHTS_REVIEW_2026-11-04.md", workflow)

    def test_primary_rights_review_blocks_copying_until_written_permission(self):
        review = REVIEW.read_text(encoding="utf-8")
        for phrase in (
            "Do not import, cache, bundle, display, redistribute",
            "written permission",
            "SoftNews",
        ):
            self.assertIn(phrase, review)


if __name__ == "__main__":
    unittest.main()
