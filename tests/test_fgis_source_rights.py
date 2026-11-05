import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "data" / "source-manifests" / "vag-factory-source-register.json"


class FgisSourceRightsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        manifest = json.loads(REGISTER.read_text(encoding="utf-8"))
        matches = [s for s in manifest["sources"] if s["source_id"] == "rosstandart-fgis-registers-kts"]
        if len(matches) != 1:
            raise AssertionError(f"expected one FGIS source record, got {len(matches)}")
        cls.source = matches[0]

    def test_fgis_is_homologation_not_repair_or_vin_build_sheet(self):
        source = self.source
        self.assertIn("RU", source["market_scope"])
        self.assertIn("EAEU", source["market_scope"])
        self.assertIn("OTTS", source["document_types"])
        self.assertIn("not_individual_vin_factory_build_sheet", source["limitations"])
        self.assertIn("not_ecu_dtc_or_repair_procedure_source", source["limitations"])

    def test_access_is_limited_to_accredited_bodies(self):
        evidence = self.source["access"]["official_access_evidence"]
        self.assertTrue(evidence["software_request_process"]["formal_application_required"])
        self.assertIn("accredited certification body", evidence["eligible_organization"]["type"])
        self.assertIn("accredited testing laboratory", evidence["eligible_organization"]["type"])
        self.assertIn("TR TS 018/2011", evidence["eligible_organization"]["accreditation_scope_required"])
        self.assertIn("GOST 33670", evidence["eligible_organization"]["accreditation_scope_required"])
        self.assertTrue(evidence["software_runtime"]["licensed_runtime_required"])
        self.assertEqual(evidence["software_runtime"]["platform"], "IBM/HCL Domino")
        self.assertFalse(evidence["software_runtime"]["project_license_obtained"])

    def test_order_2038_public_search_is_distinct_from_bulk_reuse(self):
        publication = self.source["access"]["public_site_publication_contract"]
        self.assertTrue(publication["official_site_search_required"])
        self.assertEqual(publication["effective_from"], "2025-10-01")
        self.assertIn("Annex 2", publication["public_fields_namespace"])
        self.assertEqual(publication["endpoint_status"], "not_resolved")
        self.assertFalse(publication["primary_official_copy_retrieved"])
        self.assertEqual(self.source["rights"]["bulk_export_rights"], "not_established")
        self.assertEqual(self.source["rights"]["offline_cache_rights"], "not_established")
        self.assertEqual(self.source["rights"]["display_and_redistribution_rights"], "not_established")
        self.assertIn("public search", self.source["project_decision"])
        self.assertIn("do not bulk export", self.source["project_decision"])

    def test_no_bulk_or_offline_reuse_permission_is_claimed(self):
        rights = self.source["rights"]
        self.assertEqual(rights["bulk_export_rights"], "not_established")
        self.assertEqual(rights["offline_cache_rights"], "not_established")
        self.assertEqual(rights["display_and_redistribution_rights"], "not_established")
        self.assertEqual(rights["bulk_export_allowed"], "not_established")
        self.assertEqual(rights["offline_cache_allowed"], "not_established")
        self.assertEqual(rights["display_and_redistribution_allowed"], "not_established")
        self.assertEqual(rights["permission_status"], "not_obtained")
        self.assertIn("do not bulk export", self.source["project_decision"])


if __name__ == "__main__":
    unittest.main()
