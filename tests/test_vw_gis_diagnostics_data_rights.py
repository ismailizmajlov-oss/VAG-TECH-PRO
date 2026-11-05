import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "data" / "source-manifests" / "vag-factory-source-register.json"


class VwGisDiagnosticsDataRightsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        manifest = json.loads(REGISTER.read_text(encoding="utf-8"))
        matches = [s for s in manifest["sources"] if s["source_id"] == "vw-gis-diagnostics-data-oem-odx"]
        if len(matches) != 1:
            raise AssertionError(f"expected one GIS Diagnostics Data record, got {len(matches)}")
        cls.source = matches[0]

    def test_official_oem_source_is_not_mistaken_for_open_data(self):
        self.assertTrue(self.source["applicability"]["official_vag_oem_source"])
        rights = self.source["rights"]
        self.assertEqual(rights["data_license_status"], "contractual_restricted_no_public_license")
        self.assertEqual(rights["permission_status"], "not_obtained")
        self.assertFalse(rights["redistribution_allowed"] == True)
        self.assertFalse(rights["data_distribution_agreement_signed"])
        self.assertFalse(rights["one_business_id_created"])
        self.assertFalse(rights["api_key_obtained"])
        self.assertFalse(rights["sfd_agreement_signed"])
        self.assertFalse(rights["vw_ag_encryption_key_agreement_signed"])

    def test_no_data_is_imported_displayed_or_cached(self):
        self.assertFalse(self.source["data_ingested"])
        self.assertEqual(self.source["verification_status"], "official_source_identified_contractual_access_not_obtained")
        self.assertEqual(self.source["display_status"], "not_available_no_display")
        self.assertEqual(self.source["cache_status"], "not_available_no_offline_cache")
        self.assertFalse(self.source["applicability"]["diagnostic_execution_allowed"])

    def test_eligibility_and_written_permission_gates_are_explicit(self):
        access = self.source["access"]
        self.assertTrue(access["data_distribution_agreement_required"])
        self.assertTrue(access["api_key_required_for_zip_download"])
        self.assertEqual(access["customer_headquarters_eligibility"], ["EEA", "CH", "UK"])
        rights = self.source["rights"]
        self.assertEqual(rights["offline_cache_allowed"], "not_established_without_DDA_and_written_permission")
        self.assertEqual(rights["redistribution_allowed"], "not_established; specific express written permission required by Data Hub terms")


if __name__ == "__main__":
    unittest.main()
