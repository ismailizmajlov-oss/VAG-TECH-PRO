import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "data" / "source-manifests" / "vag-factory-source-register.json"


class VwFlashSimos18DtcRightsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        manifest = json.loads(REGISTER.read_text(encoding="utf-8"))
        matches = [
            source for source in manifest["sources"]
            if source["source_id"] == "bri3d-vw-flash-simos18-dtc-candidate"
        ]
        if len(matches) != 1:
            raise AssertionError(f"expected one VW_Flash DTC candidate, got {len(matches)}")
        cls.source = matches[0]

    def test_repository_code_license_is_not_misapplied_to_dtc_data(self):
        rights = self.source["rights"]
        self.assertEqual(rights["repository_code_license"], "BSD-2-Clause")
        self.assertEqual(rights["database_data_license"], "not_separately_established")
        self.assertEqual(rights["data_license_covers_dtcs_csv"], "not_verified")
        for key in (
            "commercial_use_allowed",
            "display_allowed",
            "offline_cache_allowed",
            "bulk_reuse_allowed",
            "redistribution_allowed",
        ):
            self.assertEqual(rights[key], "not_established_for_dataset")
        self.assertEqual(rights["permission_status"], "not_cleared")

    def test_csv_provenance_and_scope_remain_unverified(self):
        source = self.source
        evidence = source["source_data_evidence"]
        self.assertEqual(evidence["commit_sha"], "c8376416c4df7f12789679fb216c47b6e795ffc8")
        self.assertEqual(evidence["git_blob_sha1"], "e5c65fff0c6f0d98aafb082ff1acefa483be016e")
        self.assertEqual(evidence["line_count"], 658)
        self.assertEqual(evidence["data_rows"], 657)
        self.assertEqual(source["counts"]["verified_vag_specific_dtc_rows"], 0)
        self.assertEqual(source["counts"]["exact_ecu_fitment_rows"], 0)
        self.assertEqual(source["counts"]["exact_vehicle_fitment_rows"], 0)
        self.assertIs(source["technical_scope"]["exact_ecu_identity_per_row"], False)
        self.assertIs(source["technical_scope"]["exact_vehicle_fitment"], False)
        self.assertIs(source["technical_scope"]["diagnostic_execution_allowed"], False)
        self.assertEqual(source["verification_status"], "source_provenance_unverified")
        self.assertEqual(source["display_status"], "quarantined_not_displayed")

    def test_candidate_is_not_mixed_with_generic_dtc_or_product_data(self):
        source = self.source
        self.assertIn("quarantine_no_import_no_display_no_cache", source["project_decision"])
        self.assertTrue(any("do not merge this candidate into the generic DTC namespace" in item for item in source["quality_limits"]))
        self.assertTrue(any("may be derived from OEM ODX material" in item for item in source["quality_limits"]))


if __name__ == "__main__":
    unittest.main()
