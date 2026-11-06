import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUSSIAN = ROOT / "data" / "source-manifests" / "russian-eaeu-otts-sources.json"
FACTORY = ROOT / "data" / "source-manifests" / "vag-factory-source-register.json"


class EaeuOttsRegistryManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.russian = json.loads(RUSSIAN.read_text(encoding="utf-8"))
        cls.factory = json.loads(FACTORY.read_text(encoding="utf-8"))
        cls.russian_sources = {item["source_id"]: item for item in cls.russian["sources"]}
        cls.factory_sources = {item["source_id"]: item for item in cls.factory["sources"]}

    def test_decision_88_schema_is_recorded_without_claiming_public_field_exposure(self):
        source = self.factory_sources["eaeu-otts-unified-register-public-portal"]
        schema = source["registry_schema"]
        self.assertEqual(schema["schema_id"], "R.TR.TS.07.001")
        self.assertEqual(schema["schema_version"], "1.0.0")
        self.assertEqual(schema["root_element"], "ConformityVehicleDocsRegistryDetails")
        self.assertEqual(schema["gearbox_unit_kind_code"], "05")
        self.assertIn("EngineDetails.VehicleComponentModelCode", schema["engine_fields"])
        self.assertIn("TransmissionUnitDetails.VehicleComponentModelCode", schema["transmission_fields"])
        self.assertIn("ECUModelCode", schema["ecu_fields"])
        self.assertFalse(schema["public_field_exposure_verified"])
        self.assertFalse(schema["official_xsd_retrieved"])
        self.assertIn("VehicleManufacturerDetails.BusinessEntityName", schema["excluded_fields"])
        self.assertEqual(schema["market_scope_semantics"], "EAEU_is_market_scope; UnifiedCountryCode_is_issuing_country")
        self.assertFalse(source["data_ingested"])

    def test_source_revision_is_pinned_and_ingestion_is_disabled(self):
        source = self.factory_sources["eaeu-otts-unified-register-public-portal"]
        self.assertEqual(source["source_revision"], "Decision 88 / R.TR.TS.07.001 v1.0.0")
        self.assertFalse(source["data_ingested"])
        self.assertEqual(source["rights"]["permission_status"], "not_obtained")

    def test_public_access_basis_is_decision_225_not_decision_88(self):
        source = self.factory_sources["eaeu-otts-unified-register-public-portal"]
        self.assertIn("Decision No. 225", source["access"]["legal_access_basis"])
        self.assertEqual(source["legal_basis_url"], "https://www.alta.ru/tamdoc/14kr0225/")
        self.assertEqual(source["schema_basis_url"], "https://www.alta.ru/tamdoc/16kr0088/")
        self.assertEqual(source["access"]["public_access_basis"]["reference_url"], source["legal_basis_url"])
        self.assertIn("Decision No. 225", source["access"]["public_access_basis"]["legal_act"])
        self.assertIn("Decision No. 88", source["registry_schema"]["normative_basis"])
        self.assertEqual(source["access"]["public_access_basis"]["publication_deadline_working_days"], 5)
        self.assertEqual(source["access"]["bulk_export"], "not_established")
        russian = self.russian_sources["eaeu-open-data-portal"]
        self.assertIn("Decision No. 225", russian["access_and_reuse"]["individual_public_query"])

    def test_eaeu_vehicle_data_rights_remain_blocked(self):
        source = self.factory_sources["eaeu-otts-unified-register-public-portal"]
        rights = source["rights"]
        self.assertEqual(rights["permission_status"], "not_obtained")
        self.assertNotEqual(rights.get("commercial_use_allowed"), True)
        self.assertNotEqual(rights.get("bulk_reuse_allowed"), True)
        self.assertNotEqual(rights.get("offline_cache_allowed"), True)
        self.assertNotEqual(rights.get("display_and_redistribution_allowed"), True)
        self.assertIsNone(rights.get("permission_evidence"))
        self.assertFalse(source["data_ingested"])

    def test_schema_registry_is_not_misrepresented_as_vehicle_data(self):
        source = self.factory_sources["eaeu-rseds-xml-schema-registry"]
        self.assertEqual(source["source_kind"], "official_eaeu_electronic_document_structure_registry")
        self.assertTrue(source["access"]["batch_export_menu_observed"])
        self.assertTrue(source["access"]["xml_validation_menu_observed"])
        self.assertFalse(source["access"]["target_xsd_retrieved"])
        self.assertFalse(source["data_ingested"])
        self.assertEqual(source["rights"]["permission_status"], "not_required_schema_metadata_only")

    def test_samworld_gearbox_directory_is_quarantined_without_prior_consent(self):
        source = self.factory_sources["samworld-vag-gearbox-code-database"]
        self.assertEqual(source["observed_claims"]["unique_gearbox_code_count"], 3489)
        self.assertEqual(source["rights"]["permission_status"], "not_obtained")
        self.assertFalse(source["rights"]["bulk_automated_extraction_allowed"])
        self.assertFalse(source["rights"]["offline_cache_allowed"])
        self.assertFalse(source["rights"]["display_and_redistribution_allowed"])
        self.assertFalse(source["product_import_allowed"])
        self.assertFalse(source["data_ingested"])
        self.assertFalse(source["applicability"]["exact_vehicle_fitment"])

    def test_enginecode_vag_directory_is_not_reusable_without_a_license_or_permission(self):
        source = self.factory_sources["enginecode-uk-vag-engine-code-directory"]
        self.assertEqual(source["rights"]["permission_status"], "not_obtained")
        self.assertEqual(source["rights"]["dataset_license"], "not_stated_for_database_content")
        self.assertEqual(source["rights"]["commercial_reuse_allowed"], "not_established")
        self.assertEqual(source["rights"]["offline_cache_allowed"], "not_established")
        self.assertFalse(source["product_import_allowed"])
        self.assertFalse(source["data_ingested"])
        self.assertFalse(source["applicability"]["exact_vehicle_fitment"])
        self.assertFalse(source["applicability"]["ru_eaeu_scope"])

    def test_vag_wiki_terms_remain_a_no_scrape_no_redistribution_gate(self):
        source = self.factory_sources["vag-wiki-community-technical-hub"]
        rights = source["rights"]
        self.assertTrue(rights["terms_explicitly_prohibit_unauthorized_mass_scraping"])
        self.assertTrue(rights["terms_explicitly_prohibit_automated_data_extraction_without_prior_authorization"])
        self.assertTrue(rights["terms_explicitly_prohibit_redistribution_without_prior_authorization"])
        self.assertFalse(source["product_import_allowed"])
        self.assertFalse(source["data_ingested"])

    def test_russian_eaeu_manifest_keeps_open_data_catalog_and_otts_schema_separate(self):
        source = self.russian_sources["eaeu-open-data-portal"]
        schema = source["related_vehicle_approval_registry_schema"]
        self.assertEqual(schema["schema_id"], "R.TR.TS.07.001")
        self.assertFalse(schema["public_field_exposure_verified"])
        self.assertEqual(source["status"], "discovery_only")
        self.assertFalse(source["data_ingested"])
        schema_registry = self.russian_sources["eaeu-rseds-schema-registry"]
        self.assertEqual(schema_registry["status"], "schema_reference_only")
        self.assertFalse(schema_registry["data_ingested"])


if __name__ == "__main__":
    unittest.main()
