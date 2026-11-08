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



if __name__ == "__main__":
    unittest.main()
