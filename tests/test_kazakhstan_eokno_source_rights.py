import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RU_PATH = ROOT / "data/source-manifests/russian-eaeu-otts-sources.json"
CENTRAL_PATH = ROOT / "data/source-manifests/vag-factory-source-register.json"
SOURCE_ID = "kazakhstan-eokno-trts018-conformity-register"
PAGE_URL = "https://eokno.gov.kz/public-register/register-ktrm2.xhtml"
KGD_URL = "https://kgd.gov.kz/ru/news/press-reliz-po-avtomatizacii-v-edinoe-okno-po-eksportno-importnym-operaciyam-polucheniya"


class KazakhstanEoknoSourceRightsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ru = json.loads(RU_PATH.read_text(encoding="utf-8"))
        cls.central = json.loads(CENTRAL_PATH.read_text(encoding="utf-8"))
        cls.ru_rows = [s for s in cls.ru["sources"] if s["source_id"] == SOURCE_ID]
        cls.central_rows = [s for s in cls.central["sources"] if s["source_id"] == SOURCE_ID]

    def test_source_is_registered_once_in_both_authoritative_manifests(self):
        self.assertEqual(len(self.ru_rows), 1)
        self.assertEqual(len(self.central_rows), 1)
        self.assertEqual(self.ru_rows[0]["source_url"], PAGE_URL)
        self.assertEqual(self.central_rows[0]["url"], PAGE_URL)

    def test_document_type_coverage_tracks_official_release_evidence(self):
        ru = self.ru_rows[0]
        central = self.central_rows[0]
        self.assertEqual(ru["observed_public_query"]["document_type_coverage"]["SBKTS"],
                         "confirmed_by_official_Kazakhstan_State_Revenue_Committee_2023_press_release")
        self.assertEqual(ru["observed_public_query"]["document_type_coverage"]["OTTS"], "confirmed_as_online_register_records_by_official_KTRM_2023_12_28_release")
        self.assertEqual(ru["observed_public_query"]["document_type_coverage"]["OTSH"], "confirmed_as_online_register_records_by_official_KTRM_2023_12_28_release")
        self.assertEqual(central["observed_claims"]["document_type_coverage"]["OTTS"], "confirmed_as_online_register_records_by_official_KTRM_2023_12_28_release")
        self.assertTrue(central["applicability"]["otts_record_flow_verified"])
        self.assertTrue(central["applicability"]["otsh_record_flow_verified"])
        self.assertEqual(ru["observed_public_query"]["current_service_notice"]["indexed_issuance_portal_url"], "https://techreg.gov.kz/index/")
        self.assertFalse(ru["observed_public_query"]["current_service_notice"]["live_status_verified"])
        self.assertEqual(ru["observed_public_query"]["current_service_notice"]["live_fetch_status"], "timeout")
        self.assertIn("techreg.gov.kz/index/", central["observed_claims"]["current_service_notice"]["indexed_issuance_portal_url"])
        self.assertFalse(central["observed_claims"]["current_service_notice"]["live_status_verified"])
        self.assertEqual(ru["access_and_reuse"]["offline_cache"], "not_confirmed")
        self.assertIn(KGD_URL, [item["url"] for item in ru["evidence_reviewed"]])
        self.assertIn("https://www.gov.kz/org/mti-ktrm/press/news/details/679816?lang=ru", [item["url"] for item in ru["evidence_reviewed"]])

    def test_rights_gate_blocks_automation_cache_display_and_product_import(self):
        ru = self.ru_rows[0]
        central = self.central_rows[0]
        self.assertEqual(ru["status"], "permission_required")
        self.assertFalse(ru["data_ingested"])
        self.assertFalse(ru["product_import_allowed"])
        self.assertIsNone(ru["source_snapshot_sha256"])
        self.assertEqual(ru["hash_status"], "not_downloaded_no_ingestion")
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
