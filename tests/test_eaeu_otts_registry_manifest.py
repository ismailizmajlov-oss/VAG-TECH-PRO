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
        self.assertFalse(source["data_ingested"])

    def test_source_revision_is_pinned_and_ingestion_is_disabled(self):
        source = self.factory_sources["eaeu-otts-unified-register-public-portal"]
        self.assertEqual(source["source_revision"], "Decision 88 / R.TR.TS.07.001 v1.0.0")
        self.assertFalse(source["data_ingested"])
        self.assertEqual(source["rights"]["permission_status"], "not_obtained")

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
