#!/usr/bin/env python3
"""Keep Cars Base out of the offline product until embedding and upstream rights are explicit."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CarsBaseSourceRightsTests(unittest.TestCase):
    def test_central_register_keeps_cars_base_discovery_only(self):
        registry = json.loads((ROOT / "data/source-manifests/vag-factory-source-register.json").read_text(encoding="utf-8"))
        matches = [s for s in registry["sources"] if s["source_id"] == "cars-base-ru-vehicle-catalog"]
        self.assertEqual(len(matches), 1)
        source = matches[0]
        self.assertEqual(source["market_scope"], ["UNKNOWN"])
        self.assertFalse(source["data_ingested"])
        self.assertFalse(source["product_import_allowed"])
        self.assertIsNone(source["source_snapshot_sha256"])
        self.assertEqual(source["hash_status"], "not_downloaded_no_snapshot_hash_claimed")
        self.assertFalse(source["access"]["project_account_created"])
        self.assertFalse(source["access"]["api_key_obtained"])
        self.assertFalse(source["access"]["paid_terms_accepted"])
        self.assertFalse(source["access"]["data_file_downloaded"])
        self.assertEqual(source["rights"]["dataset_open_license"], "not stated in reviewed repository or API documentation")
        self.assertEqual(source["rights"]["permission_status"], "written_offline_embedding_and_end_user_distribution_permission_not_obtained")
        self.assertFalse(source["rights"]["offline_cache_allowed"])
        self.assertFalse(source["rights"]["redistribution_allowed"])
        self.assertEqual(source["applicability"]["per_record_market"], "unknown")
        self.assertFalse(source["applicability"]["factory_engine_codes"])
        self.assertFalse(source["applicability"]["factory_gearbox_codes"])
        self.assertFalse(source["applicability"]["exact_engine_gearbox_pairs"])
        self.assertIn("discovery_only_no_import", source["project_decision"])

    def test_offer_and_api_review_document_records_the_distribution_boundary(self):
        review = (ROOT / "docs/research/CARS_BASE_RUSSIAN_CATALOG_RIGHTS_REVIEW_2026-11-08.md").read_text(encoding="utf-8")
        for phrase in (
            "may not resell keys",
            "publish the full database archive",
            "distribute source exports",
            "offline caching",
            "Auto.ru-derived",
            "No data was imported into SQLite",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, review)


if __name__ == "__main__":
    unittest.main()
