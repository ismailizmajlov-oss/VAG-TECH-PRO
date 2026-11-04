import json
import unittest
from pathlib import Path


class OpenVAGSourceRightsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        manifest_path = (
            Path(__file__).resolve().parents[1]
            / "data"
            / "source-manifests"
            / "openvag-dtc-candidate.json"
        )
        cls.manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    def test_source_is_pinned_but_not_data_licensed(self):
        self.assertEqual(
            self.manifest["pinned_revision"],
            "407d5e042cf46d55087ed4ae4e056605f2b04f08",
        )
        self.assertEqual(
            self.manifest["repository_license"]["id"],
            "MIT",
        )
        self.assertEqual(
            self.manifest["repository_license"]["data_license"],
            "not_separately_declared",
        )

    def test_missing_database_artifact_fails_closed(self):
        evidence = self.manifest["repository_evidence"]
        self.assertFalse(evidence["tracked_data_artifact"])
        self.assertTrue(evidence["expected_database_is_gitignored"])
        self.assertFalse(evidence["database_generation_script_present"])
        self.assertFalse(evidence["release_artifact_present"])
        self.assertIsNone(self.manifest["provenance_review"]["data_snapshot_sha256"])

    def test_no_record_level_provenance_or_fitment_is_claimed(self):
        provenance = self.manifest["provenance_review"]
        self.assertFalse(provenance["per_record_source_url"])
        self.assertFalse(provenance["per_record_source_revision"])
        self.assertFalse(provenance["per_record_source_file_hash"])
        self.assertFalse(provenance["per_record_license"])
        self.assertFalse(
            self.manifest["data_model_review"]["generic_and_manufacturer_namespaces_separated"]
        )
        self.assertEqual(self.manifest["data_model_review"]["market_scope"], "UNKNOWN")
        self.assertFalse(self.manifest["data_model_review"]["ecu_applicability"])

    def test_candidate_cannot_enter_product_or_offline_packs(self):
        policy = self.manifest["product_policy"]
        self.assertFalse(policy["product_eligibility"])
        self.assertFalse(policy["import_allowed"])
        self.assertFalse(policy["display_allowed"])
        self.assertFalse(policy["offline_cache_allowed"])
        self.assertFalse(policy["redistribution_allowed"])


if __name__ == "__main__":
    unittest.main()
