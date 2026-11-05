import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTER_PATH = ROOT / "data/source-manifests/vag-factory-source-register.json"
REVIEW_PATH = ROOT / "docs/research/AUTOMOTIVE_9_VW_DTC_SOURCE_REVIEW_2026-11-06.md"


class Automotive9VwDtcSourceRightsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        register = json.loads(REGISTER_PATH.read_text(encoding="utf-8"))
        cls.source = next(
            item for item in register["sources"]
            if item["source_id"] == "automotive-9-vw-dtc-candidate"
        )
        cls.review = REVIEW_PATH.read_text(encoding="utf-8")

    def test_no_data_license_or_reuse_rights_are_claimed(self):
        rights = self.source["rights"]
        self.assertEqual(rights["data_license_status"], "no_license_found")
        self.assertFalse(rights["root_license_file_present"])
        self.assertFalse(rights["readme_data_license_statement_present"])
        self.assertFalse(rights["row_level_source_provenance_present"])
        for key in ("commercial_use", "display", "offline_cache", "bulk_reuse", "redistribution"):
            self.assertEqual(rights[key], "not_confirmed")
        self.assertEqual(rights["permission_status"], "not_cleared")

    def test_source_is_excluded_from_all_product_data_paths(self):
        self.assertFalse(self.source["data_ingested"])
        self.assertIsNone(self.source["source_snapshot_sha256"])
        self.assertEqual(self.source["verification_status"], "quarantined_unverified_mixed_namespace")
        self.assertEqual(self.source["display_status"], "quarantined_no_display")
        self.assertEqual(self.source["cache_status"], "quarantined_no_offline_cache")
        applicability = self.source["applicability"]
        for key in (
            "vag_specific_verified", "exact_vehicle_fitment", "generation_verified",
            "model_year_verified", "engine_code_fitment", "transmission_code_fitment",
            "ecu_fitment", "diagnostic_execution_allowed", "repair_advice_approved"
        ):
            self.assertFalse(applicability[key], key)

    def test_pinned_revision_and_independent_triage_counts(self):
        provenance = self.source["provenance"]
        self.assertEqual(provenance["upstream_head_commit"], "e5cf6906badc81e2bdac3ec7b7c1bba5c01fa108")
        self.assertEqual(provenance["source_file_git_blob_sha1"], "9a2f7303a0d28a9e60259c3c91646484d04d4266")
        counts = self.source["counts"]
        self.assertEqual(counts["source_file_entries"], 9137)
        self.assertEqual(counts["numeric_legacy_or_component_keys"], 7131)
        self.assertEqual(counts["sae_shaped_keys"], 2006)
        self.assertEqual(counts["semicolon_joined_descriptions"], 5339)
        self.assertEqual(counts["numeric_key_rows_with_embedded_sae_code_text"], 2153)
        self.assertEqual(counts["numeric_key_rows_with_component_or_function_like_labels"], 3691)
        self.assertEqual(counts["empty_descriptions"], 2)

    def test_review_explains_namespace_and_rights_boundaries(self):
        self.assertIn("no root `LICENSE` file", self.review)
        self.assertIn("Do not import, display, cache, bundle or redistribute", self.review)
        self.assertIn("9,137", self.review)
        self.assertIn("generic SAE-shaped code", self.review)
        self.assertIn("Russian/EAEU", self.review)


if __name__ == "__main__":
    unittest.main()
