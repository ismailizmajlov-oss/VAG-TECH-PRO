import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "data" / "source-manifests" / "vag-factory-source-register.json"


class AutoToolsPublicApiRightsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        manifest = json.loads(REGISTER.read_text(encoding="utf-8"))
        matches = [
            source for source in manifest["sources"]
            if source["source_id"] == "autotools-brightcoding-public-api-candidate"
        ]
        if len(matches) != 1:
            raise AssertionError(f"expected one AutoTools candidate, got {len(matches)}")
        cls.source = matches[0]

    def test_conflicting_api_and_terms_claims_do_not_clear_bulk_reuse(self):
        rights = self.source["rights"]
        self.assertEqual(rights["api_docs_claimed_commercial_use"], "with_attribution")
        self.assertEqual(rights["api_docs_claimed_client_cache"], "allowed_by_documentation_statement")
        self.assertEqual(rights["published_terms_commercial_copying"], "prohibited_for_substantial_parts")
        self.assertEqual(rights["terms_and_api_docs_consistency"], "conflicting_or_ambiguous")
        for key in (
            "dataset_license",
            "commercial_use_for_offline_redistributed_pack",
            "display_in_third_party_offline_app",
            "bulk_reuse_allowed",
            "offline_cache_for_redistribution",
            "redistribution_allowed",
        ):
            self.assertEqual(rights[key], "not_established")
        self.assertEqual(rights["permission_status"], "clarification_required")

    def test_torque_values_are_not_critical_or_exact_vag_applicability(self):
        source = self.source
        evidence = source["source_data_evidence"]
        self.assertEqual(evidence["torque_page_claim"], "common_workshop_figures_from_technical_documentation")
        self.assertFalse(source["applicability"]["critical_torque_use_allowed"])
        self.assertFalse(source["applicability"]["vag_specific"])
        self.assertFalse(source["applicability"]["exact_vehicle_fitment"])
        self.assertEqual(source["counts"]["approved_critical_torque_values"], 0)
        self.assertEqual(source["counts"]["imported_rows"], 0)
        self.assertEqual(source["display_status"], "quarantined_not_displayed")

    def test_no_api_records_or_source_snapshot_are_claimed(self):
        evidence = self.source["source_data_evidence"]
        self.assertFalse(evidence["api_records_downloaded"])
        self.assertIsNone(evidence["source_snapshot_sha256"])
        self.assertEqual(self.source["verification_status"], "rights_and_row_provenance_not_cleared")
        self.assertIn("quarantine_no_import_no_offline_pack", self.source["project_decision"])


if __name__ == "__main__":
    unittest.main()
