import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "data" / "source-manifests" / "vag-factory-source-register.json"


class Wal33DDtcSourceRightsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        manifest = json.loads(REGISTER.read_text(encoding="utf-8"))
        matches = [s for s in manifest["sources"] if s["source_id"] == "wal33d-dtc-database"]
        if len(matches) != 1:
            raise AssertionError(f"expected one Wal33D source record, got {len(matches)}")
        cls.source = matches[0]

    def test_repo_license_is_not_misrepresented_as_verified_data_provenance(self):
        rights = self.source["rights"]
        self.assertEqual(rights["repository_level_license_declared"], "MIT")
        self.assertEqual(rights["per_source_file_attribution"], "not documented in reviewed README/INTEGRATION pages")
        self.assertEqual(rights["underlying_data_provenance"], "not established")
        self.assertFalse(rights["product_import_allowed"])
        self.assertEqual(rights["project_permission_status"], "not_verified")

    def test_generic_and_manufacturer_specific_counts_remain_distinct(self):
        counts = self.source["data_counts_as_published"]
        self.assertEqual(counts["generic_sae_j2012_definitions"], 9415)
        self.assertEqual(counts["manufacturer_specific_definitions"], 9390)
        self.assertEqual(counts["snapshot_total_definitions"], 18805)
        self.assertEqual(counts["unique_dtc_codes"], 12128)
        self.assertEqual(counts["manufacturers_excluding_generic"], 33)
        self.assertNotEqual(counts["headline_total_codes"], counts["snapshot_total_definitions"])

    def test_no_vag_applicability_is_inferred(self):
        applicability = self.source["applicability"]
        self.assertFalse(applicability["manufacturer_list_published"])
        self.assertFalse(applicability["audi_or_volkswagen_presence_independently_verified"])
        self.assertEqual(applicability["model_generation_year_mapping"], "not documented")
        self.assertEqual(applicability["ecu_mapping"], "not documented")
        self.assertEqual(applicability["engine_or_gearbox_mapping"], "not documented")
        self.assertIn("quarantine_no_import", self.source["project_decision"])
        self.assertIn("do not label any row VAG-specific", self.source["project_decision"])


if __name__ == "__main__":
    unittest.main()
