import json
import unittest
from pathlib import Path


class WikidataGenerationSourceRightsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        register_path = (
            Path(__file__).resolve().parents[1]
            / "data" / "source-manifests" / "vag-factory-source-register.json"
        )
        register = json.loads(register_path.read_text(encoding="utf-8"))
        cls.source = next(
            item for item in register["sources"]
            if item["source_id"] == "wikidata-vag-generation-candidates"
        )

    def test_cc0_rights_cover_display_offline_cache_and_redistribution(self):
        rights = self.source["rights"]
        self.assertEqual(rights["data_license_status"], "CC0-1.0")
        self.assertEqual(rights["license_url"], "https://creativecommons.org/publicdomain/zero/1.0/")
        for field in (
            "commercial_use_allowed", "display_allowed", "offline_cache_allowed",
            "bulk_reuse_allowed", "redistribution_allowed"
        ):
            self.assertTrue(rights[field], field)
        self.assertFalse(rights["attribution_required"])
        self.assertTrue(rights["attribution_recommended"])
        self.assertFalse(rights["share_alike_required"])

    def test_generation_relationships_remain_candidates_only(self):
        self.assertEqual(
            self.source["project_decision"],
            "allow_candidate_series_member_taxonomy_only"
        )
        scope = self.source["vehicle_scope"]
        self.assertTrue(scope["series_member_candidates_only"])
        self.assertFalse(scope["generation_mapping_verified"])
        self.assertFalse(scope["exact_vehicle_fitment"])
        self.assertFalse(scope["engine_codes"])
        self.assertFalse(scope["gearbox_codes"])
        self.assertFalse(scope["ecu_data"])
        self.assertFalse(scope["dtc_data"])
        self.assertFalse(scope["repair_procedures"])
        self.assertEqual(self.source["applicability"]["precision"], "series_member_candidate")
        self.assertEqual(self.source["applicability"]["review_status"], "candidate")
        self.assertEqual(self.source["applicability"]["market_scope"], "UNKNOWN")
        self.assertFalse(self.source["applicability"]["generation_verified"])
        self.assertFalse(self.source["applicability"]["production_years_inferred"])

    def test_source_is_public_but_completeness_and_market_are_unknown(self):
        access = self.source["access"]
        self.assertEqual(access["status"], "public_sparql")
        self.assertFalse(access["authentication_required"])
        self.assertTrue(access["offline_snapshot_retained"])
        self.assertEqual(access["completeness_status"], "unknown")
        self.assertEqual(access["query_batch_size"], 50)
        self.assertEqual(access["query_limit"], 5000)
        self.assertEqual(access["query_limit_scope"], "per_batch")
        self.assertEqual(self.source["market_scope"], ["UNKNOWN"])
        self.assertTrue(self.source["provenance"]["parent_model_snapshot_sha256_required"])
        self.assertTrue(self.source["provenance"]["parent_model_database_sha256_required"])
        self.assertTrue(self.source["provenance"]["per_binding_sha256_required"])


if __name__ == "__main__":
    unittest.main()
