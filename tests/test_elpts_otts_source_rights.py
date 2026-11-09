import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "data" / "source-manifests" / "vag-factory-source-register.json"


class ElptsOttsSourceRightsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        manifest = json.loads(REGISTER.read_text(encoding="utf-8"))
        matches = [
            source for source in manifest["sources"]
            if source["source_id"] == "elpts-national-otts-register-public-query"
        ]
        if len(matches) != 1:
            raise AssertionError(f"expected one ELPTS public-register source, got {len(matches)}")
        cls.source = matches[0]

    def test_public_visibility_does_not_grant_bulk_or_offline_reuse(self):
        source = self.source
        self.assertEqual(source["market_scope"], ["RU", "EAEU"])
        self.assertEqual(source["rights"]["data_license_status"], "not_established")
        for key in (
            "commercial_use_allowed",
            "display_allowed",
            "offline_cache_allowed",
            "bulk_reuse_allowed",
            "redistribution_allowed",
        ):
            self.assertEqual(source["rights"][key], "not_established")
        self.assertEqual(source["rights"]["permission_status"], "not_obtained")
        self.assertIs(source["rights"]["permission_required_before_product_import_or_distribution"], True)
        self.assertIn("no scraping", source["project_decision"])
        self.assertIn("offline caching", source["project_decision"])
        self.assertIn("written permission", source["project_decision"])


    def test_new_public_search_routes_remain_discovery_only(self):
        source = self.source
        observations = source["public_page_observations"]
        self.assertEqual(observations["observed_at"], "2026-11-08")
        self.assertEqual(observations["ot_ts"]["url"], "https://docs.elpts.ru/ncher/otts")
        self.assertEqual(observations["ot_ts"]["manufacturer_filter_options_observed"], ["AUDI AG", "Volkswagen AG"])
        self.assertTrue(observations["ot_ts"]["manufacturer_filter_values_are_options_only"])
        self.assertFalse(observations["ot_ts"]["vag_records_observed"])
        self.assertFalse(observations["ot_ts"]["vag_record_count_verified"])
        self.assertFalse(observations["ot_ts"]["bulk_api_discovered"])
        self.assertEqual(observations["ot_ts"]["visible_date_filters"], ["07.11.2026", "08.11.2026"])
        self.assertEqual(observations["history"][0]["ot_ts"]["visible_export_controls"], ["CSV", "PDF", "XML"])
        self.assertEqual(source["access"]["export_controls_last_observed_at"], "2026-11-07")
        self.assertFalse(observations["history"][0]["ot_ts"]["export_file_downloaded"])
        self.assertFalse(observations["history"][0]["ot_ts"]["export_endpoint_verified"])
        self.assertEqual(observations["history"][0]["ot_ts"]["export_scope"], "not_established")
        self.assertEqual(source["access"]["export_controls_observed"], ["CSV", "PDF", "XML"])
        self.assertIn("reuse rights not verified", source["access"]["bulk_export"])
        self.assertFalse(observations["ot_ts"]["pdf_downloaded"])
        self.assertTrue(observations["sbkts"]["vag_metadata_row_observed"])
        self.assertIn("not OTTS", observations["sbkts"]["search_snapshot"])
        self.assertEqual(observations["sbkts"]["rights_effect"], "none; this observation is not OTTS fitment evidence and grants no reuse rights")
        self.assertEqual(observations["ot_sh"]["url"], "https://docs.elpts.ru/ncher/otsh")
        self.assertIn("not a verified complete-corpus count", observations["ot_ts"]["count_interpretation"])
        self.assertEqual(observations["history"][0]["ot_ts"]["observed_at"], "2026-11-07")
        self.assertEqual(observations["history"][0]["ot_ts"]["visible_date_filters"], ["06.11.2026", "07.11.2026"])
        self.assertFalse(observations["ot_ts"]["raw_page_bytes_captured"])
        self.assertIsNone(observations["ot_ts"]["raw_page_sha256"])
        self.assertEqual(source["rights"]["permission_status"], "not_obtained")
        self.assertEqual(source["rights"]["offline_cache_allowed"], "not_established")
        self.assertEqual(source["rights"]["bulk_reuse_allowed"], "not_established")
        self.assertTrue(source["rights"]["permission_required_before_product_import_or_distribution"])

    def test_otts_sbKts_and_zoets_are_not_collapsed(self):
        source = self.source
        self.assertEqual(set(source["document_types"]), {"OTTS", "OTSH", "SBKTS", "ZOETS", "cancellation_notices"})
        self.assertIn("Do not treat an SBKTS record as an OTTS record", source["limitations"][2])
        self.assertIn("exact OTTS query coverage and completeness not established", source["access"]["individual_query_access"])


    def test_elpts_sep_reference_files_are_quarantined_until_data_rights_are_confirmed(self):
        manifest = json.loads(REGISTER.read_text(encoding="utf-8"))
        sources = {item["source_id"]: item for item in manifest["sources"]}
        expected = {
            "elpts-sep-make-directory": {
                "url": "https://elpts.ru/wp-content/uploads/2023/06/spravochnik-marok.xlsx",
                "file_name": "spravochnik-marok.xlsx",
                "market_scope": ["RU"],
            },
            "elpts-sep-technical-characteristics-reference": {
                "url": "https://disk.yandex.ru/d/VeYxsi3IcnmK2w",
                "file_name": "Справочник технических характеристик_202601106_1645.xlsx",
                "market_scope": ["RU"],
            },
        }
        for source_id, contract in expected.items():
            source = sources[source_id]
            self.assertEqual(source["url"], contract["url"])
            self.assertEqual(source["market_scope"], contract["market_scope"])
            self.assertFalse(source["data_ingested"])
            self.assertIsNone(source["source_snapshot_sha256"])
            self.assertEqual(source["hash_status"], "not_downloaded_no_ingestion")
            self.assertFalse(source["file_metadata"]["file_bytes_retrieved"])
            self.assertIsNone(source["file_metadata"]["source_snapshot_sha256"])
            self.assertFalse(source["access"]["file_downloaded"])
            self.assertFalse(source["access"]["raw_file_bytes_retrieved"])
            self.assertEqual(source["rights"]["permission_status"], "not_obtained")
            self.assertTrue(source["rights"]["permission_required_before_product_import_or_distribution"])
            for key in ("commercial_use_allowed", "display_allowed", "offline_cache_allowed", "bulk_reuse_allowed", "redistribution_allowed"):
                self.assertEqual(source["rights"][key], "not_established")
            self.assertIn("written permission", source["project_decision"])
            self.assertIn("not a data-reuse licence", source["rights"]["rights_evidence"])
            self.assertIn(contract["file_name"], json.dumps(source["file_metadata"], ensure_ascii=False))

        technical = sources["elpts-sep-technical-characteristics-reference"]
        self.assertEqual(technical["file_metadata"]["size_display"], "16.9 МБ")
        self.assertEqual(technical["file_metadata"]["modified_at_display"], "06.11.2026 16:52")
        self.assertEqual(technical["applicability_precision"], "unknown_until_rights_cleared_and_workbook_reviewed")
        make = sources["elpts-sep-make-directory"]
        self.assertEqual(make["applicability_precision"], "make_name_taxonomy_candidate_only; no model_or_powertrain_fitment_verified")


    def test_eec_official_temporary_register_link_is_recorded_without_rights_upgrade(self):
        registry = json.loads(REGISTER.read_text(encoding="utf-8"))
        eaeu = next(
            source for source in registry["sources"]
            if source["source_id"] == "eaeu-otts-unified-register-public-portal"
        )
        observation = eaeu["access"]["official_temporary_register_page_observation_2026_11_09"]
        self.assertEqual(observation["official_page_url"], "https://eec.eaeunion.org/comission/department/deptexreg/tr/temprorary_otts.php")
        self.assertEqual(observation["linked_otts_url"], "https://portal.elpts.ru/ncher/otts")
        self.assertEqual(observation["observed_at"], "2026-11-09")
        self.assertEqual(observation["destination_fetch_status"], "502_bad_gateway_on_2026_11_09")
        self.assertFalse(observation["destination_content_verified"])
        self.assertFalse(observation["record_rows_observed"])
        self.assertFalse(observation["export_or_api_verified"])
        self.assertFalse(observation["data_downloaded"])
        self.assertFalse(observation["data_ingested"])
        self.assertFalse(observation["product_import_allowed"])
        self.assertIsNone(observation["source_snapshot_sha256"])
        self.assertEqual(eaeu["rights"]["permission_status"], "not_obtained")
        self.assertEqual(eaeu["rights"]["bulk_reuse_allowed"], "not_established")
        self.assertEqual(eaeu["rights"]["offline_cache_allowed"], "not_established")
        self.assertEqual(eaeu["rights"]["display_and_redistribution_allowed"], "not_established")
    def test_alternative_elpts_page_shell_does_not_claim_records_or_rights(self):
        registry = json.loads(REGISTER.read_text(encoding="utf-8"))
        source = next(item for item in registry["sources"] if item["source_id"] == "elpts-national-otts-register-public-query")
        observation = source["access"]["alternative_public_page_shell_observation_2026_11_09"]
        self.assertEqual(observation["url"], "https://docs.elpts.ru/ncher/otts")
        self.assertTrue(observation["page_shell_accessible"])
        self.assertTrue(observation["dynamic_result_placeholders_unresolved"])
        self.assertFalse(observation["record_rows_observed"])
        self.assertFalse(observation["api_or_export_endpoint_verified"])
        self.assertIsNone(observation["source_snapshot_sha256"])
        self.assertEqual(source["rights"]["permission_status"], "not_obtained")
        self.assertEqual(source["rights"]["offline_cache_allowed"], "not_established")


    def test_2026_11_09_otts_and_sbkts_evidence_remains_separate(self):
        source = self.source
        reconciliation = source["access"]["cross_register_reconciliation_2026_11_09"]
        self.assertEqual(reconciliation["ot_ts_search_index_date_filters"], ["08.11.2026", "09.11.2026"])
        self.assertEqual(reconciliation["ot_ts_filter_options_observed"], ["Volkswagen AG"])
        self.assertFalse(reconciliation["audi_ag_found_in_otts_indexed_page"])
        self.assertEqual(reconciliation["esbkts_search_result_count"], 155)
        self.assertEqual(reconciliation["esbkts_filter_options_observed"], ["AUDI AG", "Volkswagen AG"])
        rows = reconciliation["sample_sbkt_records"]
        self.assertEqual(len(rows), 2)
        self.assertEqual({row["document_type"] for row in rows}, {"SBKTS"})
        self.assertEqual({row["brand"] for row in rows}, {"VOLKSWAGEN"})
        self.assertEqual({row["vehicle_type"] for row in rows}, {"FV6462HADCG", "SVW71421GT"})
        self.assertTrue(all(row["type_value_role"] == "vehicle_type_identifier_not_engine_or_gearbox_code" for row in rows))
        self.assertTrue(all(row["issue_date"] == "2026-11-04" for row in rows))
        self.assertFalse(reconciliation["raw_page_bytes_captured"])
        self.assertIsNone(reconciliation["source_snapshot_sha256"])
        self.assertFalse(reconciliation["pdf_downloaded"])
        self.assertFalse(reconciliation["data_ingested"])
        self.assertFalse(reconciliation["product_import_allowed"])
        self.assertEqual(source["rights"]["permission_status"], "not_obtained")
        self.assertEqual(source["rights"]["offline_cache_allowed"], "not_established")
        self.assertEqual(source["rights"]["bulk_reuse_allowed"], "not_established")


    def test_2026_11_09_paid_report_forms_are_participant_scoped_and_not_reuse_rights(self):
        source = self.source
        observation = source["access"]["official_paid_report_forms_observation_2026_11_09"]
        self.assertEqual(observation["forms_page_url"], "https://elpts.ru/formy-platnyh-otchetov-2/")
        self.assertEqual(observation["appendix_title"], "Приложение к приказу АО «Электронный паспорт» от 02.10.2026 № 10/81-26")
        self.assertEqual(observation["appendix_pages"], 20)
        self.assertTrue(observation["homepage_access_terms"]["sep_paid_reports_require_separate_additional_agreement"])
        self.assertIn("help.elpts.ru", observation["homepage_access_terms"]["sep_request_channel"])
        forms = {item["form"]: item for item in observation["report_forms"]}
        self.assertEqual(forms["R3"]["delivery_frequency"], "weekly")
        self.assertEqual(forms["R3"]["price_rub_per_row_including_vat"], 180)
        self.assertTrue(forms["R3"]["vin_field"])
        self.assertTrue(forms["R3"]["otts_number_field"])
        self.assertFalse(forms["R3"]["engine_code_field"])
        self.assertFalse(forms["R3"]["gearbox_code_field"])
        self.assertFalse(forms["R3"]["general_registry_corpus"])
        self.assertEqual(forms["R4"]["price_rub_per_row_including_vat"], 120)
        self.assertFalse(forms["R4"]["vin_field"])
        self.assertTrue(forms["R4"]["otts_number_field"])
        self.assertFalse(forms["R4"]["engine_code_field"])
        self.assertFalse(forms["R4"]["gearbox_code_field"])
        self.assertEqual(forms["R"]["price_rub_per_row_including_vat"], 15)
        self.assertIn("gearbox make/type", forms["R"]["selected_fields"])
        self.assertFalse(forms["R"]["exact_vag_gearbox_code_field"])
        self.assertFalse(observation["raw_pdf_bytes_downloaded"])
        self.assertFalse(observation["report_data_downloaded"])
        self.assertFalse(observation["data_ingested"])
        self.assertFalse(observation["product_import_allowed"])
        self.assertIsNone(observation["source_snapshot_sha256"])
        self.assertEqual(observation["rights_effect"], "none; contract and report fees are access conditions only; separate written reuse/redistribution permission remains required")
        self.assertEqual(source["rights"]["permission_status"], "not_obtained")
        self.assertEqual(source["rights"]["offline_cache_allowed"], "not_established")
        self.assertEqual(source["rights"]["bulk_reuse_allowed"], "not_established")
        self.assertEqual(source["rights"]["redistribution_allowed"], "not_established")



if __name__ == "__main__":
    unittest.main()
