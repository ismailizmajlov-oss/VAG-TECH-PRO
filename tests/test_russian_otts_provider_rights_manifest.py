import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "source-manifests" / "russian-eaeu-otts-sources.json"


class RussianOttsProviderRightsManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.sources = {item["source_id"]: item for item in manifest["sources"]}

    def test_otts_bot_is_not_cleared_for_automated_extraction_or_redistribution(self):
        source = self.sources["otts-bot"]
        self.assertEqual(source["status"], "restricted_no_automated_collection_or_redistribution_without_written_permission")
        self.assertFalse(source["data_ingested"])
        self.assertIsNone(source["source_snapshot_sha256"])
        self.assertEqual(source["license"]["automated_extraction"], "prohibited_beyond_ordinary_user_scenario_without_separate_written_permission")
        self.assertEqual(source["license"]["redistribution"], "prohibited_under_published_user_agreement_clause_3")

    def test_otts_baza_is_not_cleared_for_bulk_offline_product_reuse(self):
        source = self.sources["otts-baza-ru"]
        self.assertEqual(source["status"], "restricted_no_bulk_reuse_or_redistribution_without_written_permission")
        self.assertFalse(source["data_ingested"])
        self.assertIsNone(source["source_snapshot_sha256"])
        self.assertEqual(source["license"]["bulk_export"], "prohibited_without_separate_agreement")
        self.assertEqual(source["license"]["offline_cache"], "not_confirmed")
        self.assertEqual(source["license"]["redistribution"], "prohibited_without_separate_agreement")

    def test_elpts_public_register_is_not_cleared_for_offline_product_reuse(self):
        source = self.sources["elpts-national-otts-register"]
        self.assertEqual(source["status"], "permission_required")
        self.assertFalse(source["data_ingested"])
        self.assertIsNone(source["source_snapshot_sha256"])
        self.assertEqual(source["license"]["commercial_use"], "not_confirmed")
        self.assertEqual(source["license"]["display"], "not_confirmed")
        self.assertEqual(source["license"]["offline_cache"], "not_confirmed")
        self.assertEqual(source["license"]["bulk_export"], "not_confirmed")
        self.assertEqual(source["license"]["redistribution"], "not_confirmed")
        self.assertIn("OTTS", source["document_types"])
        self.assertIn("SBKTS", source["document_types"])
        self.assertIn("exact_OTTS_coverage", source["access"])
        self.assertEqual(source["access"]["exact_OTTS_coverage"], "not_established")
        self.assertIn("Require written permission", source["notes"][3])

    def test_all_ru_eaeu_otts_candidates_remain_non_imported_without_clear_rights(self):
        for source_id in ("rosstandart-fgis-reestr-kts", "eaeu-open-data-portal", "eaeu-temporary-otts-electronic-register", "hpt-su-otts-api", "otts-bot", "otts-baza-ru", "elpts-national-otts-register"):
            source = self.sources[source_id]
            self.assertFalse(source["data_ingested"], source_id)
            self.assertIsNone(source["source_snapshot_sha256"], source_id)
            self.assertIn(source["status"], (
                "permission_required",
                "discovery_only",
                "restricted_for_product_distribution",
                "restricted_no_automated_collection_or_redistribution_without_written_permission",
                "restricted_no_bulk_reuse_or_redistribution_without_written_permission",
            ), source_id)

    def test_eec_temporary_otts_register_route_is_not_a_data_reuse_grant(self):
        source = self.sources["eaeu-temporary-otts-electronic-register"]
        self.assertEqual(source["source_url"], "https://eec.eaeunion.org/comission/department/deptexreg/tr/temprorary_otts.php")
        self.assertEqual(source["linked_otts_register_url"], "https://portal.elpts.ru/ncher/otts")
        self.assertEqual(source["market_scope"], ["EAEU"])
        self.assertEqual(source["document_types"], ["OTTS"])
        self.assertEqual(source["status"], "permission_required")
        self.assertEqual(source["access"]["linked_destination_fetch_status"], "502_bad_gateway_on_2026_11_09")
        self.assertFalse(source["access"]["linked_destination_content_verified"])
        self.assertFalse(source["access"]["public_query_rows_observed"])
        self.assertFalse(source["data_ingested"])
        self.assertFalse(source["product_import_allowed"])
        self.assertIsNone(source["source_snapshot_sha256"])
        self.assertEqual(source["license"]["permission_status"], "not_obtained")
        for field in ("commercial_use", "display", "offline_cache", "bulk_export", "redistribution"):
            self.assertEqual(source["license"][field], "not_confirmed")
        self.assertFalse(source["technical_scope"]["exact_engine_gearbox_pair"])
        self.assertFalse(source["technical_scope"]["vag_record_observed"])
    def test_elpts_dynamic_otts_shell_is_not_a_record_dataset(self):
        source = self.sources["elpts-national-otts-register"]
        observation = source["access"]["alternative_public_page_shell"]
        self.assertEqual(observation["url"], "https://docs.elpts.ru/ncher/otts")
        self.assertTrue(observation["page_shell_accessible"])
        self.assertTrue(observation["dynamic_result_placeholders_unresolved"])
        self.assertFalse(observation["record_rows_observed"])
        self.assertFalse(observation["api_or_export_endpoint_verified"])
        self.assertIsNone(observation["source_snapshot_sha256"])
        self.assertEqual(source["status"], "permission_required")
        self.assertFalse(source["data_ingested"])
        self.assertFalse(source["product_import_allowed"])
        self.assertIsNone(source["source_snapshot_sha256"])

if __name__ == "__main__":
    unittest.main()
