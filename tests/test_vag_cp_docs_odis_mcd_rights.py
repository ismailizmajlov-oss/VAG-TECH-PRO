import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "data" / "source-manifests" / "vag-factory-source-register.json"


class VagCpDocsOdisMcdRightsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        manifest = json.loads(REGISTER.read_text(encoding="utf-8"))
        matches = [
            source for source in manifest["sources"]
            if source["source_id"] == "dspl1236-vag-cp-docs-au57x-odis-mcd-extract"
        ]
        if len(matches) != 1:
            raise AssertionError(f"expected one AU57X ODIS MCD candidate, got {len(matches)}")
        cls.source = matches[0]

    def test_uploader_cc0_claim_does_not_clear_underlying_oem_rights(self):
        rights = self.source["rights"]
        self.assertEqual(rights["repository_content_license_claimed"], "CC0-1.0")
        self.assertEqual(rights["underlying_oem_data_rights"], "not_established")
        self.assertEqual(rights["permission_status"], "not_cleared")
        for key in (
            "commercial_use_allowed",
            "display_allowed",
            "offline_cache_allowed",
            "bulk_reuse_allowed",
            "redistribution_allowed",
        ):
            self.assertEqual(rights[key], "not_confirmed_for_underlying_oem_data")

    def test_internal_odis_mcd_origin_is_excluded(self):
        source = self.source
        evidence = source["source_data_evidence"]
        self.assertEqual(evidence["project_name"], "AU57X ODIS MCD Project")
        self.assertEqual(evidence["project_revision"], "DVR 72 / 072102")
        self.assertEqual(evidence["build_host_claimed"], "VWAGWOSOB127")
        self.assertEqual(evidence["document_commit_sha"], "1d6948369cdaf6acc013907b5f35591f236ca649")
        self.assertEqual(source["verification_status"], "underlying_oem_data_rights_unverified")
        self.assertEqual(source["display_status"], "restricted_not_imported")
        self.assertEqual(source["counts"]["verified_vag_specific_dtc_rows"], 0)
        self.assertEqual(source["counts"]["verified_did_records"], 0)
        self.assertIn("restricted_no_import_no_display_no_cache", source["project_decision"])
        self.assertTrue(any("VW internal server" in item for item in source["quality_limits"]))
        self.assertTrue(any("cannot be cleared by the uploader's CC0 declaration alone" in item for item in source["quality_limits"]))


if __name__ == "__main__":
    unittest.main()
