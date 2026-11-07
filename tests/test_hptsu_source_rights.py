import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "data" / "source-manifests" / "vag-factory-source-register.json"


class HptSuRightsRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(REGISTER.read_text(encoding="utf-8"))
        matches = [s for s in cls.manifest["sources"] if s["source_id"] == "hpt-su-otts-aggregator"]
        if len(matches) != 1:
            raise AssertionError(f"expected one HPT.SU source record, got {len(matches)}")
        cls.source = matches[0]

    def test_source_is_ru_eaeu_aggregator_not_primary_oem_evidence(self):
        self.assertEqual(self.source["source_kind"], "commercial_aggregated_ru_eaeu_vehicle_compliance_registry")
        self.assertEqual(set(self.source["market_scope"]), {"RU", "EAEU"})
        self.assertIn("type_approval", self.source["evidence_scope"])
        self.assertNotIn("repair_procedure", self.source["evidence_scope"])

    def test_individual_document_own_use_is_narrow_and_explicit(self):
        rights = self.source["rights"]
        own_use = rights["individual_document_own_use"]
        self.assertTrue(own_use["view_allowed"])
        self.assertTrue(own_use["local_save_allowed"])
        self.assertTrue(own_use["automated_extraction_for_own_needs_allowed"])
        self.assertIn("individual materials", own_use["scope"])
        self.assertFalse(rights["bulk_automated_download_allowed"])
        self.assertFalse(rights["substantial_or_systematic_database_extraction_allowed"])

    def test_third_party_database_distribution_is_blocked(self):
        rights = self.source["rights"]
        self.assertFalse(rights["full_database_copy_allowed"])
        self.assertFalse(rights["third_party_equivalent_access_allowed"])
        self.assertFalse(rights["derivative_database_reproducing_provider_database_allowed"])
        self.assertFalse(rights["third_party_api_or_file_export_allowed"])
        self.assertFalse(rights["redistribution_allowed"])
        self.assertFalse(rights["api_key_sharing_allowed"])
        self.assertEqual(rights["dataset_open_license"], "not granted")

    def test_mcp_code_license_is_not_misapplied_to_dataset(self):
        license_text = self.source["rights"]["server_code_license"].lower()
        self.assertIn("mit applies only", license_text)
        self.assertIn("not a license", license_text)
        self.assertEqual(self.source["access"]["public_mcp_free_tier"]["registration_required"], True)
        self.assertEqual(self.source["access"]["public_mcp_free_tier"]["used_by_project"], False)
        self.assertEqual(self.source["access"]["rest_api"]["used_by_project"], False)

    def test_project_is_fail_closed(self):
        self.assertEqual(self.source["access"]["status"], "restricted_registration_or_subscription_required")
        self.assertIn("restricted_no_bulk_import_no_product_pack", self.source["project_decision"])
        self.assertIn("without explicit owner authorization", self.source["project_decision"])
        self.assertFalse(self.source["data_ingested"])
        self.assertEqual(self.source["rights"]["permission_status"], "no_project_permission_or_subscription_obtained")


if __name__ == "__main__":
    unittest.main()
