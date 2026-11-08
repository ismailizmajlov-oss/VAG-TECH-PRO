import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "data" / "source-manifests" / "vag-factory-source-register.json"


class TestElptsPublicIndexObservation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTER.read_text(encoding="utf-8"))
        cls.elpts = next(
            source for source in cls.registry["sources"]
            if source["source_id"] == "elpts-national-otts-register-public-query"
        )

    def test_search_index_metadata_is_not_promoted_to_vag_approval_data(self):
        observation = self.elpts["access"]["search_index_recheck_2026_11_09"]
        self.assertEqual(observation["url"], "https://docs.elpts.ru/ncher/otts")
        self.assertEqual(observation["visible_total_label"], "Всего оформлено: 14822")
        self.assertEqual(observation["visible_date_filters"], ["07.11.2026", "08.11.2026"])
        self.assertEqual(observation["search_result_label"], "Найдено: []")
        self.assertEqual(
            observation["manufacturer_filter_options_observed"],
            ["AUDI AG", "Volkswagen AG"],
        )
        self.assertTrue(observation["manufacturer_filter_values_are_options_only"])
        self.assertFalse(observation["vag_records_observed"])
        self.assertFalse(observation["vag_record_count_verified"])
        self.assertFalse(observation["engine_code_exposed"])
        self.assertFalse(observation["gearbox_code_exposed"])
        self.assertFalse(observation["exact_engine_gearbox_pair_exposed"])
        self.assertFalse(observation["ecu_exposed"])
        self.assertFalse(observation["api_or_export_endpoint_verified"])
        self.assertFalse(observation["pdf_downloaded"])
        self.assertFalse(observation["raw_page_bytes_captured"])
        self.assertIsNone(observation["source_snapshot_sha256"])
        self.assertIn("not a verified complete-corpus count", observation["interpretation"])

    def test_elpts_rights_and_ingestion_gates_remain_closed(self):
        observation = self.elpts["access"]["search_index_recheck_2026_11_09"]
        self.assertEqual(observation["rights_effect"].split(";")[0], "none")
        self.assertFalse(self.elpts["data_ingested"])
        rights = self.elpts["rights"]
        self.assertEqual(rights["permission_status"], "not_obtained")
        self.assertEqual(rights["bulk_reuse_allowed"], "not_established")
        self.assertEqual(rights["offline_cache_allowed"], "not_established")
        self.assertEqual(rights["display_allowed"], "not_established")
        self.assertEqual(rights["redistribution_allowed"], "not_established")

    def test_official_elpts_link_to_russian_national_register_is_metadata_only(self):
        route = self.elpts["official_site_register_route_observation_2026_11_09"]
        self.assertEqual(route["official_operator_homepage"], "https://elpts.ru/")
        self.assertEqual(
            route["link_label"],
            "Национальная часть единого реестра выданных ОТТС, ОТШ, СБКТС",
        )
        self.assertEqual(
            route["linked_url"],
            "https://www.rst.gov.ru/portal/gost/home/activity/compliance/evaluationcompliance/AcknowledgementCorrespondence",
        )
        self.assertEqual(route["linked_page_fetch_status"], "timeout")
        self.assertFalse(route["linked_page_content_verified"])
        self.assertFalse(route["api_or_export_verified"])
        self.assertIn("does not grant bulk retrieval", route["rights_effect"])

        eaeu = next(
            source for source in self.registry["sources"]
            if source["source_id"] == "eaeu-otts-unified-register-public-portal"
        )
        russian_part = next(
            part for part in eaeu["access"]["national_parts"]
            if part["country_code"] == "RU"
        )
        self.assertEqual(
            russian_part["official_operator_linked_register_url"],
            route["linked_url"],
        )
        self.assertEqual(russian_part["official_operator_link_fetch_status"], "timeout")


if __name__ == "__main__":
    unittest.main()
