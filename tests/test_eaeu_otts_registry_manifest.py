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
        revision = source["source_revision"]
        self.assertIn("EEC Decision No. 225 public-access basis", revision)
        self.assertIn("EEC Decision No. 232 current consolidated OTTS/OTSH form", revision)
        self.assertIn("Decision No. 88 / R.TR.TS.07.001 v1.0.0", revision)
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

    def test_elpts_public_otts_filter_options_do_not_establish_records_or_reuse_rights(self):
        source = self.factory_sources["elpts-national-otts-register-public-query"]
        observation = source["public_page_observations"]["ot_ts"]
        self.assertEqual(observation["observed_at"], "2026-11-08")
        self.assertEqual(observation["visible_date_filters"], ["07.11.2026", "08.11.2026"])
        history = source["public_page_observations"]["history"]
        self.assertEqual(history[0]["ot_ts"]["observed_at"], "2026-11-07")
        self.assertEqual(history[0]["ot_ts"]["visible_date_filters"], ["06.11.2026", "07.11.2026"])
        self.assertEqual(observation["manufacturer_filter_options_observed"], ["AUDI AG", "Volkswagen AG"])
        self.assertTrue(observation["manufacturer_filter_values_are_options_only"])
        self.assertFalse(observation["vag_records_observed"])
        self.assertFalse(observation["vag_record_count_verified"])
        self.assertFalse(observation["bulk_api_discovered"])
        self.assertFalse(observation["pdf_downloaded"])
        self.assertEqual(source["rights"]["permission_status"], "not_obtained")
        self.assertNotEqual(source["rights"].get("offline_cache_allowed"), True)
        self.assertNotEqual(source["rights"].get("redistribution_allowed"), True)
        self.assertFalse(source["data_ingested"])
        sbkts = source["public_page_observations"]["sbkts"]
        self.assertTrue(sbkts["vag_metadata_row_observed"])
        self.assertIn("not OTTS", sbkts["search_snapshot"])
        self.assertEqual(sbkts["rights_effect"], "none; this observation is not OTTS fitment evidence and grants no reuse rights")

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

    def test_gor3a_odbl_aggregator_does_not_clear_upstream_rights(self):
        source = self.factory_sources["gor3a-vehicle-makes-models-odbl"]
        self.assertEqual(source["rights"]["data_license_status"], "ODbL-1.0")
        self.assertEqual(source["rights"]["upstream_rights_status"], "not_established")
        self.assertEqual(source["rights"]["upstream_permission_status"], "not_obtained")
        self.assertEqual(source["upstream_license_evidence"]["upstream_source_license"], "not_identified_in_this_review")
        self.assertFalse(source["data_ingested"])
        self.assertIn("no_download_no_import", source["project_decision"])

    def test_vag_wiki_terms_remain_a_no_scrape_no_redistribution_gate(self):
        source = self.factory_sources["vag-wiki-community-technical-hub"]
        rights = source["rights"]
        self.assertTrue(rights["terms_explicitly_prohibit_unauthorized_mass_scraping"])
        self.assertTrue(rights["terms_explicitly_prohibit_automated_data_extraction_without_prior_authorization"])
        self.assertTrue(rights["terms_explicitly_prohibit_redistribution_without_prior_authorization"])
        self.assertFalse(source["product_import_allowed"])
        self.assertFalse(source["data_ingested"])

    def test_kazakhstan_techreg_registry_is_public_query_only_and_not_ingested(self):
        central = self.factory_sources["kazakhstan-techreg-otts-public-registry"]
        regional = self.russian_sources["kazakhstan-techreg-otts-public-registry"]
        self.assertEqual(central["market_scope"], ["KZ", "EAEU_TR_TS_018_2011"])
        self.assertEqual(central["rights"]["permission_status"], "not_obtained")
        self.assertFalse(central["product_import_allowed"])
        self.assertFalse(central["data_ingested"])
        self.assertFalse(central["applicability"]["exact_engine_code_fitment"])
        self.assertFalse(central["applicability"]["exact_gearbox_code_fitment"])
        self.assertFalse(central["applicability"]["engine_gearbox_pairing"])
        self.assertEqual(regional["status"], "permission_required")
        self.assertFalse(regional["data_ingested"])
        self.assertEqual(regional["license"]["offline_cache"], "not_confirmed")
        self.assertEqual(regional["observed_public_query"]["legacy_registry_visible_record_count"], 273)

    def test_kyrgyz_single_window_is_captcha_gated_and_rights_blocked(self):
        central = self.factory_sources["kyrgyzstan-single-window-otts-registry"]
        regional = self.russian_sources["kyrgyzstan-single-window-otts-registry"]
        self.assertEqual(central["market_scope"], ["KG", "EAEU_TR_TS_018_2011"])
        self.assertEqual(central["rights"]["permission_status"], "not_obtained")
        self.assertEqual(central["rights"]["public_query_visibility"], "captcha_gated")
        self.assertFalse(central["product_import_allowed"])
        self.assertFalse(central["data_ingested"])
        self.assertFalse(central["applicability"]["exact_engine_code_fitment"])
        self.assertFalse(central["applicability"]["exact_gearbox_code_fitment"])
        self.assertTrue(any("requires robot verification" in item for item in central["limitations"]))
        self.assertEqual(regional["status"], "permission_required")
        self.assertFalse(regional["data_ingested"])
        self.assertTrue(regional["observed_public_query"]["captcha_required_before_record_view"])
        self.assertIsNone(regional["source_snapshot_sha256"])

    def test_rusavtolab_aggregator_rights_are_not_inferred_from_public_download_claim(self):
        central = self.factory_sources["rusavtolab-otts-public-index"]
        regional = self.russian_sources["rusavtolab-otts-public-index"]
        self.assertEqual(central["rights"]["permission_status"], "not_obtained")
        self.assertEqual(central["rights"]["bulk_export_allowed"], "not_established")
        self.assertFalse(central["product_import_allowed"])
        self.assertFalse(central["data_ingested"])
        self.assertTrue(central["observed_claims"]["access_claims_conflict"])
        self.assertEqual(regional["status"], "permission_required")
        self.assertFalse(regional["data_ingested"])
        self.assertTrue(regional["observed_public_claims"]["access_claims_conflict"])
        self.assertIsNone(regional["source_snapshot_sha256"])
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

    def test_eaeu_open_data_manifest_uses_decision_225_for_access_and_88_for_schema(self):
        source = self.russian_sources["eaeu-open-data-portal"]
        legal = source["legal_basis"]
        self.assertIn("№ 225", legal["document"])
        self.assertEqual(legal["document_url"], "https://www.alta.ru/tamdoc/14kr0225/")
        self.assertIn("paragraph 13", legal["access_rule"])
        self.assertIn("№ 88", legal["schema_document"])
        self.assertEqual(legal["schema_document_url"], "https://www.alta.ru/tamdoc/16kr0088/")
        self.assertIn("not the public-access legal basis", legal["schema_rule"])
        self.assertEqual(source["status"], "discovery_only")
        self.assertFalse(source["data_ingested"])


if __name__ == "__main__":
    unittest.main()
