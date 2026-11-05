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
        for source_id in ("rosstandart-fgis-reestr-kts", "eaeu-open-data-portal", "hpt-su-otts-api", "otts-bot", "otts-baza-ru", "elpts-national-otts-register"):
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


if __name__ == "__main__":
    unittest.main()
