import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RU_PATH = ROOT / "data/source-manifests/russian-eaeu-otts-sources.json"
CENTRAL_PATH = ROOT / "data/source-manifests/vag-factory-source-register.json"
SOURCE_ID = "kazakhstan-techreg-otts-public-registry"


class KazakhstanTechRegSourceRightsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ru = json.loads(RU_PATH.read_text(encoding="utf-8"))
        cls.central = json.loads(CENTRAL_PATH.read_text(encoding="utf-8"))
        cls.ru_rows = [s for s in cls.ru["sources"] if s["source_id"] == SOURCE_ID]
        cls.central_rows = [s for s in cls.central["sources"] if s["source_id"] == SOURCE_ID]

    def test_source_is_registered_once_in_both_authoritative_manifests(self):
        self.assertEqual(len(self.ru_rows), 1)
        self.assertEqual(len(self.central_rows), 1)
        self.assertEqual(self.ru_rows[0]["current_registry_url"], "https://techreg.kezekte.kz/ru/cert/ot-registry/list")
        self.assertEqual(self.central_rows[0]["current_registry_url"], "https://techreg.kezekte.kz/ru/cert/ot-registry/list")

    def test_latest_index_observation_is_not_a_verified_snapshot(self):
        ru = self.ru_rows[0]
        central = self.central_rows[0]
        indexed = ru["observed_public_query"]["latest_search_index_observation"]
        self.assertEqual(indexed["observed_at"], "2026-11-09")
        self.assertEqual(indexed["legacy_list"]["indexed_result_range"], "1-30 of 273")
        self.assertEqual(indexed["new_list"]["indexed_result_range"], "1-1 of 0")
        self.assertIn("applicant_name_and_address", indexed["legacy_list"]["visible_columns"])
        self.assertFalse(indexed["legacy_list"]["record_content_downloaded"])
        self.assertFalse(indexed["new_list"]["record_rows_observed"])
        self.assertFalse(indexed["api_or_export_endpoint_verified"])
        self.assertFalse(indexed["documented_bulk_export"])
        self.assertIsNone(indexed["source_snapshot_sha256"])
        self.assertEqual(indexed["rights_status"], "permission_required")
        self.assertEqual(central["observed_claims"]["latest_search_index_observation"], indexed)

    def test_rights_and_ingestion_remain_blocked(self):
        ru = self.ru_rows[0]
        central = self.central_rows[0]
        self.assertEqual(ru["status"], "permission_required")
        self.assertFalse(ru["data_ingested"])
        self.assertIsNone(ru["source_snapshot_sha256"])
        self.assertEqual(ru["license"]["offline_cache"], "not_confirmed")
        self.assertEqual(ru["license"]["bulk_export"], "not_confirmed")
        self.assertEqual(central["rights"]["permission_status"], "not_obtained")
        self.assertEqual(central["rights"]["offline_cache_allowed"], "not_established")
        self.assertEqual(central["rights"]["redistribution_allowed"], "not_established")
        self.assertFalse(central["product_import_allowed"])
        self.assertFalse(central["data_ingested"])
        self.assertIsNone(central["source_snapshot_sha256"])

    def test_no_vag_powertrain_or_repair_fitment_is_claimed(self):
        ru = self.ru_rows[0]
        central = self.central_rows[0]
        self.assertEqual(ru["technical_scope"]["exact_vag_engine_code"], "not_established")
        self.assertEqual(ru["technical_scope"]["exact_vag_gearbox_code"], "not_established")
        self.assertEqual(ru["technical_scope"]["engine_gearbox_pairing"], "not_established")
        self.assertFalse(central["applicability"]["exact_vag_vehicle_fitment"])
        self.assertFalse(central["applicability"]["engine_gearbox_pairing"])
        self.assertFalse(central["applicability"]["ecu_dtc_repair_applicability"])


if __name__ == "__main__":
    unittest.main()
