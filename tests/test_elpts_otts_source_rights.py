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
        self.assertEqual(observations["observed_at"], "2026-11-07")
        self.assertEqual(observations["ot_ts"]["url"], "https://docs.elpts.ru/ncher/otts")
        self.assertEqual(observations["ot_ts"]["manufacturer_filter_options_observed"], ["AUDI AG", "Volkswagen AG"])
        self.assertTrue(observations["ot_ts"]["manufacturer_filter_values_are_options_only"])
        self.assertFalse(observations["ot_ts"]["vag_records_observed"])
        self.assertFalse(observations["ot_ts"]["vag_record_count_verified"])
        self.assertFalse(observations["ot_ts"]["bulk_api_discovered"])
        self.assertEqual(observations["ot_ts"]["visible_date_filters"], ["06.11.2026", "07.11.2026"])
        self.assertEqual(observations["ot_ts"]["visible_export_controls"], ["CSV", "PDF", "XML"])
        self.assertTrue(observations["ot_ts"]["export_controls_observed"])
        self.assertFalse(observations["ot_ts"]["export_file_downloaded"])
        self.assertFalse(observations["ot_ts"]["export_endpoint_verified"])
        self.assertEqual(observations["ot_ts"]["export_scope"], "not_established")
        self.assertEqual(source["access"]["export_controls_observed"], ["CSV", "PDF", "XML"])
        self.assertIn("reuse rights not verified", source["access"]["bulk_export"])
        self.assertFalse(observations["ot_ts"]["pdf_downloaded"])
        self.assertTrue(observations["sbkts"]["vag_metadata_row_observed"])
        self.assertIn("not OTTS", observations["sbkts"]["search_snapshot"])
        self.assertEqual(observations["sbkts"]["rights_effect"], "none; this observation is not OTTS fitment evidence and grants no reuse rights")
        self.assertEqual(observations["ot_sh"]["url"], "https://docs.elpts.ru/ncher/otsh")
        self.assertIn("not a verified complete-corpus count", observations["ot_ts"]["count_interpretation"])
        self.assertEqual(source["rights"]["permission_status"], "not_obtained")
        self.assertEqual(source["rights"]["offline_cache_allowed"], "not_established")
        self.assertEqual(source["rights"]["bulk_reuse_allowed"], "not_established")
        self.assertTrue(source["rights"]["permission_required_before_product_import_or_distribution"])

    def test_otts_sbKts_and_zoets_are_not_collapsed(self):
        source = self.source
        self.assertEqual(set(source["document_types"]), {"OTTS", "OTSH", "SBKTS", "ZOETS", "cancellation_notices"})
        self.assertIn("Do not treat an SBKTS record as an OTTS record", source["limitations"][2])
        self.assertIn("exact OTTS query coverage and completeness not established", source["access"]["individual_query_access"])


if __name__ == "__main__":
    unittest.main()
