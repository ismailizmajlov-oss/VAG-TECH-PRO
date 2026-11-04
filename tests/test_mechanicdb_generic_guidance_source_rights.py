import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class MechanicDbGenericGuidanceSourceRightsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = json.loads(
            (ROOT / "data/source-manifests/mechanicdb-generic-repair-guidance.json").read_text(encoding="utf-8")
        )
        cls.register = json.loads(
            (ROOT / "data/source-manifests/vag-factory-source-register.json").read_text(encoding="utf-8")
        )

    def test_pinned_source_and_license_scope(self):
        self.assertEqual(self.source["pinned_revision"], "c788dfe9ed1517d4cd0be27f5aacb4776abf4864")
        self.assertEqual(self.source["data_license"], "ODbL-1.0")
        rights = self.source["rights"]
        for key in (
            "commercial_use_allowed", "display_allowed", "offline_cache_allowed",
            "redistribution_allowed", "share_alike_required", "attribution_required",
        ):
            self.assertTrue(rights[key], key)

    def test_import_is_generic_only_and_not_vag_fitment(self):
        scope = self.source["data_scope"]
        self.assertEqual(scope["namespace"], "generic_sae_iso")
        self.assertEqual(scope["market_scope"], "UNKNOWN")
        self.assertFalse(scope["vag_specific"])
        self.assertFalse(scope["exact_vehicle_fitment"])
        self.assertFalse(scope["model_generation_year_fitment"])
        self.assertFalse(scope["engine_gearbox_fitment"])
        self.assertFalse(scope["ecu_fitment"])
        self.assertFalse(scope["diagnostic_execution_allowed"])
        self.assertFalse(scope["oem_repair_procedure"])

    def test_oem_rows_and_descriptions_are_excluded(self):
        counts = self.source["expected_counts"]
        self.assertEqual(counts["generic_sae_dtc_rows"], 75)
        self.assertEqual(counts["manufacturer_labelled_rows_excluded"], 15)
        self.assertEqual(counts["generic_guidance_rows"], 275)
        self.assertEqual(counts["manufacturer_labelled_guidance_rows_excluded"], 51)
        policy = self.source["import_policy"]
        self.assertTrue(policy["import_allowed"])
        self.assertEqual(policy["purpose"], "generic_educational_reference_only")
        self.assertIn("all generic DTC descriptions and detailed explanations", policy["excluded_content"])

    def test_source_register_contains_separate_generic_source(self):
        entries = [
            item for item in self.register["sources"]
            if item["source_id"] == self.source["source_id"]
        ]
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(entry["market_scope"], ["UNKNOWN"])
        self.assertTrue(entry["rights"]["redistribution_allowed_under_odbl"])
        self.assertTrue(entry["rights"]["share_alike_required"])
        self.assertFalse(entry["applicability"]["vag_specific"])
        self.assertFalse(entry["applicability"]["exact_vehicle_fitment"])

    def test_restricted_wal33d_source_remains_quarantined(self):
        wal33d = next(item for item in self.register["sources"] if item["source_id"] == "wal33d-dtc-database")
        self.assertFalse(wal33d["rights"]["product_import_allowed"])
        self.assertIn("quarantine", wal33d["project_decision"])


if __name__ == "__main__":
    unittest.main()
