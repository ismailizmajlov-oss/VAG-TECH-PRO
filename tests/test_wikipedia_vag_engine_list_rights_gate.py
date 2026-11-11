#!/usr/bin/env python3
"""Wikipedia VAG engine lists are CC BY-SA text, but remain quarantined by data quality."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "data/source-manifests/vag-factory-source-register.json"
REVIEW = ROOT / "docs/research/WIKIPEDIA_VAG_ENGINE_CODE_LISTS_RIGHTS_AND_QUALITY_REVIEW_2026-11-08.md"
SOURCE_ID = "wikipedia-vag-engine-code-lists-cc-by-sa-4-0"
PAGES = {
    "List of Volkswagen Group petrol engines": "1383476161",
    "List of Volkswagen Group diesel engines": "1383504097",
    "List of discontinued Volkswagen Group petrol engines": "1381198237",
    "List of discontinued Volkswagen Group diesel engines": "1375791889",
}


class WikipediaVagEngineListGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTER.read_text(encoding="utf-8"))
        cls.source = next(item for item in cls.registry["sources"] if item["source_id"] == SOURCE_ID)

    def test_text_license_is_cc_by_sa_and_reuse_obligations_are_explicit(self):
        rights = self.source["rights"]
        self.assertEqual(rights["data_license_status"], "CC-BY-SA-4.0")
        for field in ("commercial_use_allowed", "display_allowed", "offline_cache_allowed", "bulk_reuse_allowed", "redistribution_allowed"):
            with self.subTest(right=field):
                self.assertTrue(rights[field])
        self.assertTrue(rights["attribution_required"])
        self.assertTrue(rights["share_alike_required"])
        self.assertIn("article text only", rights["scope_note"].casefold())

    def test_quality_warnings_keep_source_out_of_product_database(self):
        source = self.source
        self.assertFalse(source["data_ingested"])
        self.assertFalse(source["product_import_allowed"])
        self.assertEqual(source["source_snapshot_sha256"], "77fd59c37f5d22d013efe8b34a872898c26cd75d1475a22a63d671aa376cdb23")
        self.assertEqual(source["source_manifest_sha256"], "50381fb8b93cf007456b1a56a84275d19b48512c7313ef7b0c4767f5d0362a9f")
        self.assertEqual(source["hash_status"], "verified_four_pinned_revisions_and_separate_candidate_pack")
        self.assertTrue(source["access"]["raw_revision_bytes_retrieved"])
        self.assertTrue(source["access"]["mediawiki_api_snapshot_retrieved"])
        self.assertTrue(source["research_pack_built"])
        self.assertFalse(source["research_pack_ingested"])
        self.assertFalse(source["research_database_included_in_desktop"])
        pack = source["research_pack"]
        self.assertEqual(pack["workflow_run_id"], 43003516695)
        self.assertEqual(pack["workflow_run_number"], 378)
        self.assertEqual(pack["artifact_id"], 13846613276)
        self.assertEqual(pack["artifact_sha256"], "4f675b559b54eab613806e6ce480c4a49ac74c8018b9c0655bcf4dcd442dc1f9")
        self.assertEqual(pack["inner_archive_sha256"], "b5e851e19784e90a1b238cd6427d094d83d2e03b40a8197058573ccb26f9b8e0")
        self.assertEqual(pack["pack_manifest_sha256"], "0eb4246a357f6d1cbca9a8277cd30f8fdebfb72d08e2b4c7cb5b8be524a1a08a")
        self.assertEqual(pack["database_sha256"], "12e2de36f8c356e0b348e56a6f49430941bda885511c5abeb86d43c0a1a96f50")
        self.assertEqual(pack["counts"]["candidate_rows"], 241)
        self.assertEqual(pack["counts"]["unique_candidate_codes"], 241)
        self.assertFalse(pack["product_import_allowed"])
        self.assertFalse(pack["repair_use_allowed"])
        self.assertFalse(pack["diagnostic_execution_allowed"])
        quality = source["quality_review"]
        self.assertEqual(quality["status"], "not_approved_for_technical_use")
        self.assertGreaterEqual(len(quality["blocking_warnings"]), 4)
        self.assertEqual(source["project_decision"], "licensed_discovery_only; no technical or vehicle-fitment import until pinned snapshots, extraction QA and independent primary-source verification are complete")

    def test_all_four_revisions_are_pinned_and_market_scope_is_unknown(self):
        source_pages = {page["title"]: str(page["revision_id"]) for page in self.source["pages"]}
        self.assertEqual(source_pages, PAGES)
        self.assertEqual(self.source["market_scope"], ["UNKNOWN"])
        self.assertEqual(self.source["applicability_precision"], "community_engine_code_candidate_only; no model_year_market_or_fitment_confirmation")

    def test_review_records_zero_imports_and_sharealike_requirements(self):
        review = REVIEW.read_text(encoding="utf-8").casefold()
        for phrase in (
            "raw article/api bytes retrieved: four pinned wikitext revisions",
            "engine-code candidate rows extracted: 241",
            "production engine-code rows imported: 0",
            "engine/gearbox pairings imported: 0",
            "production applicability claims created: 0",
            "sharealike obligations",
            "source-quality warnings block data promotion",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, review)


if __name__ == "__main__":
    unittest.main()
