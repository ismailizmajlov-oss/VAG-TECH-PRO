#!/usr/bin/env python3
"""Guard the OTTS.BOT source from accidental ingestion or redistribution."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_json(relative_path: str):
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


class OttsBotRightsBoundaryTests(unittest.TestCase):
    def test_russian_eaeu_manifest_keeps_aggregator_quarantined(self):
        manifest = load_json("data/source-manifests/russian-eaeu-otts-sources.json")
        source = next(s for s in manifest["sources"] if s["source_id"] == "otts-bot")
        self.assertFalse(source["data_ingested"])
        self.assertIsNone(source["source_snapshot_sha256"])
        self.assertEqual(source["status"], "restricted_no_automated_collection_or_redistribution_without_written_permission")
        self.assertEqual(source["license"]["permission_status"], "not_cleared")
        self.assertIn("ordinary_user_scenario", source["license"]["automated_extraction"])
        self.assertEqual(source["license"]["redistribution"], "prohibited_under_published_user_agreement_clause_3")
        self.assertFalse(source["license"]["written_permission_obtained"])
        self.assertIn("operator only", source["license"]["partner_program_grant_scope"])
        self.assertIn("2026-11-11", source["terms_revision"])
        self.assertEqual(source["rights_recheck_2026_11_11"]["terms_last_updated"], "2026-08-26")
        self.assertTrue(source["rights_recheck_2026_11_11"]["clauses"]["3"]["automated_collection"].startswith("scraping"))
        self.assertFalse(source["rights_recheck_2026_11_11"]["clauses"]["4.3-4.4"]["sublicense_to_vag_tech_pro"])
        self.assertTrue(source["rights_recheck_2026_11_11"]["clauses"]["5"]["underlying_documents"].startswith("rights remain"))
        self.assertEqual(source["observed_counts"]["observed_at"], "2026-11-11")
        self.assertIn("not independently audited", source["observed_counts"]["limitation"])
        self.assertEqual(source["rights_recheck_2026_11_11"]["page_observation"]["result_counter"], 74115)
        self.assertTrue(source["rights_recheck_2026_11_11"]["page_observation"]["count_discrepancy_unresolved"])
        self.assertEqual(source["rights_recheck_2026_11_11"]["homepage_observation"]["sbkts_records"], 224744)
        self.assertEqual(source["rights_recheck_2026_11_11"]["homepage_observation"]["otsh_records"], 1655)
        self.assertIn("46,000+", source["observed_counts"]["marketing_headline"])
        self.assertFalse(source["technical_scope"]["exact_vehicle_fitment"])
        self.assertEqual(source["technical_scope"]["engine_gearbox_pairing"], "not_established")

    def test_central_source_registry_keeps_aggregator_out_of_product(self):
        registry = load_json("data/source-manifests/vag-factory-source-register.json")
        source = next(s for s in registry["sources"] if s["source_id"] == "otts-bot")
        self.assertFalse(source["data_ingested"])
        self.assertFalse(source["product_import_allowed"])
        self.assertIsNone(source["source_snapshot_sha256"])
        self.assertEqual(source["rights"]["permission_status"], "not_cleared")
        self.assertFalse(source["rights"]["third_party_display_allowed"])
        self.assertFalse(source["rights"]["offline_cache_allowed"])
        self.assertEqual(source["rights"]["redistribution"], "prohibited_under_published_user_agreement_clause_3")
        self.assertFalse(source["rights"]["written_permission_obtained"])
        self.assertIn("no_offline_cache", source["project_decision"])
        self.assertFalse(source["applicability"]["engine_gearbox_pairing"])
        self.assertFalse(source["applicability"]["exact_ecu_dtc_fitment"])
        self.assertEqual(source["evidence_status"], "OTTS_page_and_user_agreement_rechecked_2026-11-11; agreement_last_updated_2026-08-26")
        self.assertEqual(source["rights"]["review_date"], "2026-11-11")
        self.assertEqual(source["rights_recheck_2026_11_11"]["page_observation"]["result_counter"], 74115)
        self.assertTrue(source["rights_recheck_2026_11_11"]["page_observation"]["count_discrepancy_unresolved"])

    def test_published_terms_block_bulk_extraction_and_own_product_redistribution(self):
        source = load_json("data/source-manifests/russian-eaeu-otts-sources.json")
        item = next(s for s in source["sources"] if s["source_id"] == "otts-bot")
        self.assertIn("prohibits scraping/mass requests", " ".join(item["notes"]))
        self.assertIn("prohibits resale, publication or other distribution", " ".join(item["notes"]))
        self.assertIn("respective rightsholders", " ".join(item["notes"]))
        self.assertEqual({e["url"] for e in item["terms_evidence_reviewed"]}, {
            "https://www.otts.bot/terms",
            "https://www.otts.bot/otts",
            "https://www.otts.bot/",
        })

    def test_provider_counts_are_observations_not_a_dataset_snapshot(self):
        item = load_json("data/source-manifests/russian-eaeu-otts-sources.json")
        source = next(s for s in item["sources"] if s["source_id"] == "otts-bot")
        self.assertFalse(source["data_ingested"])
        self.assertIsNone(source["source_snapshot_sha256"])
        self.assertEqual(source["hash_status"], "terms_review_only_no_dataset_snapshot")
        self.assertTrue(source["observed_counts"]["provider_displayed"])
        self.assertIn("not independently audited", source["observed_counts"]["limitation"])


if __name__ == "__main__":
    unittest.main()
