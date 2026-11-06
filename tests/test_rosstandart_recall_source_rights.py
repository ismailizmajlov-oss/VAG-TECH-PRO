import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "data" / "source-manifests" / "vag-factory-source-register.json"


class RosstandartRecallSourceRightsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        manifest = json.loads(REGISTER.read_text(encoding="utf-8"))
        matches = [s for s in manifest["sources"] if s["source_id"] == "rosstandart-recall-campaigns-open-data"]
        if len(matches) != 1:
            raise AssertionError(f"expected one Rosstandart recall source, got {len(matches)}")
        cls.source = matches[0]

    def test_russian_recall_source_is_separate_from_otts_and_vag_factory_data(self):
        self.assertEqual(self.source["source_kind"], "official_ru_vehicle_recall_campaign_open_data")
        self.assertEqual(self.source["market_scope"], ["RU"])
        self.assertFalse(self.source["applicability"]["exact_engine_code"])
        self.assertFalse(self.source["applicability"]["exact_transmission_code"])
        self.assertFalse(self.source["applicability"]["exact_engine_transmission_pair"])
        self.assertFalse(self.source["applicability"]["ecu_fitment"])
        self.assertFalse(self.source["applicability"]["dtc_fitment"])
        self.assertFalse(self.source["applicability"]["oem_repair_procedure"])
        self.assertTrue(self.source["applicability"]["recall_remedy_is_not_a_factory_workshop_procedure"])

    def test_no_import_or_fabricated_hash_until_official_snapshot_is_retrieved(self):
        self.assertFalse(self.source["data_ingested"])
        self.assertIsNone(self.source["source_snapshot_sha256"])
        self.assertIsNone(self.source["source_snapshot_bytes"])
        self.assertTrue(self.source["hash_status"].startswith("not_downloaded_"))
        self.assertEqual(self.source["access"]["current_snapshot_downloaded"], False)

    def test_vin_and_repair_completion_rows_are_excluded_from_future_product_pack(self):
        self.assertTrue(self.source["applicability"]["vin_level_rows_excluded"])
        self.assertTrue(self.source["applicability"]["repair_completion_and_dealer_location_fields_excluded"])
        self.assertIn("VIN", self.source["reported_fields"])
        self.assertIn("repair_completion_date", self.source["reported_fields"])

    def test_historical_noncommercial_statement_is_not_overstated_as_cache_or_redistribution_license(self):
        rights = self.source["rights"]
        self.assertIn("historical_rosstandart_statement_supports_noncommercial_service_use", rights["noncommercial_use_allowed"])
        self.assertEqual(rights["commercial_use_allowed"], "not_established_for_this_dataset")
        self.assertEqual(rights["display_allowed"], "not_established_for_offline_product_display")
        self.assertEqual(rights["offline_cache_allowed"], "not_established")
        self.assertEqual(rights["redistribution_allowed"], "not_established_for_packaged_offline_database")
        self.assertEqual(rights["permission_status"], "current_dataset_page_and_linked_terms_not_verified; no_written_permission_obtained")

    def test_source_decision_remains_candidate_only(self):
        self.assertIn("candidate_only", self.source["project_decision"])
        self.assertIn("do_not_download_or_import", self.source["project_decision"])


if __name__ == "__main__":
    unittest.main()
