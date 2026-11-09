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
        self.assertEqual(source["license"]["automated_extraction"], "prohibited_for_scraping_or_mass_requests_beyond_ordinary_user_scenario_without_separate_written_permission")
        self.assertFalse(source["license"]["written_permission_obtained"])
        self.assertIn("46,000+", source["observed_counts"]["marketing_headline"])
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
        self.assertEqual(observation["observation_type"], "rendered_page_shell_only")
        self.assertEqual(observation["url"], "https://docs.elpts.ru/ncher/otts")
        self.assertEqual(observation["observed_at"], "2026-11-09")
        self.assertTrue(observation["dynamic_result_placeholders_unresolved"])
        self.assertEqual(observation["dynamic_result_placeholders"], ["{{ totalFiltered }}", "{{ totalNotFiltered }}"])
        self.assertFalse(observation["record_rows_observed"])
        self.assertFalse(observation["api_or_export_endpoint_verified"])
        self.assertFalse(observation["raw_page_bytes_retrieved"])
        self.assertIsNone(observation["source_snapshot_sha256"])
        self.assertEqual(source["status"], "permission_required")
        self.assertFalse(source["data_ingested"])
        self.assertFalse(source["product_import_allowed"])
        self.assertIsNone(source["source_snapshot_sha256"])

    def test_kazakhstan_eokno_preview_is_sbkts_pii_and_not_importable(self):
        source = self.sources["kazakhstan-eokno-trts018-conformity-register"]
        observation = source["observed_public_query"]["latest_search_index_recheck"]
        self.assertEqual(source["status"], "permission_required")
        self.assertFalse(source["data_ingested"])
        self.assertFalse(source["product_import_allowed"])
        self.assertIsNone(source["source_snapshot_sha256"])
        self.assertEqual(observation["preview_rows_document_type"], "SBKTS")
        self.assertIn("VIN", observation["pii_fields_observed"])
        self.assertIn("applicant name", observation["pii_fields_observed"])
        self.assertFalse(observation["record_rows_downloaded"])
        self.assertFalse(observation["source_bytes_downloaded"])
        self.assertIsNone(observation["source_snapshot_sha256"])
        self.assertFalse(observation["exact_vag_otts_record_identified"])
        self.assertTrue(source["technical_scope"]["pii_present_in_indexed_preview"])
        self.assertEqual(source["technical_scope"]["exact_vag_engine_code"], "not_established")
        self.assertEqual(source["technical_scope"]["exact_vag_gearbox_code"], "not_established")
        legal = source["legal_schema_review"]
        self.assertIn("gearbox make/type", legal["sbkts_section_9_explicit_powertrain_fields"])
        self.assertNotIn("gearbox make/type", legal["otts_otsh_section_8_explicit_fields"])
        self.assertIn("Do not treat SBKTS", legal["interpretation"])

if __name__ == "__main__":
    unittest.main()
