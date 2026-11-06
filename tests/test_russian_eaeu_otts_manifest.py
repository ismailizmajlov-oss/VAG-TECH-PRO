import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "source-manifests" / "russian-eaeu-otts-sources.json"


class RussianEaeuOttsManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.sources = {item["source_id"]: item for item in cls.manifest["sources"]}

    def test_rosstandart_fgis_stays_blocked_without_reuse_rights(self):
        source = self.sources["rosstandart-fgis-reestr-kts"]
        self.assertEqual(source["status"], "permission_required")
        self.assertFalse(source["data_ingested"])
        self.assertIsNone(source["source_snapshot_sha256"])
        self.assertEqual(source["license"]["commercial_use"], "not_confirmed")
        self.assertEqual(source["license"]["display"], "not_confirmed")
        self.assertEqual(source["license"]["offline_cache"], "not_confirmed")
        self.assertEqual(source["license"]["bulk_export"], "not_confirmed")
        self.assertEqual(source["license"]["pdf_redistribution"], "not_confirmed")

    def test_fgis_software_access_is_not_a_data_reuse_license(self):
        source = self.sources["rosstandart-fgis-reestr-kts"]
        access = source["access_details"]
        self.assertTrue(access["software_request"]["formal_application_required"])
        self.assertIn("TR TS 018/2011", access["software_request"]["accreditation_scope_as_listed_in_main_faq"])
        self.assertIn("GOST 33670", access["software_request"]["accreditation_scope_in_consolidated_page_text"])
        self.assertIn("unresolved", access["software_request"]["eligibility_wording_discrepancy"])
        self.assertEqual(access["software_runtime"]["platform"], "IBM/HCL Domino")
        self.assertFalse(access["software_runtime"]["project_license_obtained"])
        self.assertIn("does not grant", access["rights_boundary"])
        self.assertFalse(source["data_ingested"])
        self.assertEqual(source["status"], "permission_required")

    def test_public_annex2_and_internal_annex1_field_numbers_are_separate(self):
        source = self.sources["rosstandart-fgis-reestr-kts"]
        contract = source["publication_contract"]
        self.assertTrue(contract["official_site_search_required"])
        self.assertEqual(contract["effective_from"], "2025-10-01")
        self.assertEqual(contract["official_site_search_scope"], "electronically_issued_records_only")
        self.assertTrue(contract["field_numbers_are_not_interchangeable"])
        self.assertEqual(contract["internal_fgis_attribute_namespace"], "annex_1_internal_database_fields")
        self.assertEqual(contract["public_site_search_namespace"], "annex_2_publication_fields")
        fields = contract["public_site_search_fields"]
        self.assertEqual([item["field"] for item in fields], list(range(1, 29)))
        by_number = {item["field"]: item["name"] for item in fields}
        self.assertEqual(by_number[12], "make")
        self.assertEqual(by_number[13], "commercial_name")
        self.assertEqual(by_number[19], "annex_1_pdf")
        self.assertEqual(by_number[25], "early_termination_date")
        self.assertEqual(by_number[27], "early_termination_date_based_on_cancellation_notice")
        self.assertEqual(by_number[28], "early_termination_reason_based_on_cancellation_notice")
        self.assertEqual(source["ot_ts_attribute_map_scope"], "annex_1_internal_database_fields")
        self.assertIn(
            "The existing ot_ts_attribute_map uses Annex 1 internal FGIS field numbers. Public-site search fields are a separate Annex 2 namespace; never join or interpret them by field number without the namespace.",
            source["important_limitations"],
        )

    def test_public_annex2_does_not_expose_powertrain_or_repair_fitment(self):
        source = self.sources["rosstandart-fgis-reestr-kts"]
        contract = source["publication_contract"]
        fields = contract["public_site_search_fields"]
        self.assertEqual(len(fields), 28)
        names = {item["name"] for item in fields}
        technical_terms = ("engine", "gearbox", "transmission", "ecu", "dtc", "wiring", "pinout", "torque")
        self.assertFalse(any(any(term in name.lower() for term in technical_terms) for name in names))
        scope = contract["public_annex2_technical_data_scope"]
        self.assertEqual(scope["scope"], "document_identity_and_registry_status_metadata_only")
        self.assertEqual(scope["public_search_scope"], "electronically_issued_records_only")
        self.assertEqual(scope["engine_type_or_code"], "not_present_in_public_annex2_fields")
        self.assertEqual(scope["gearbox_type_or_code"], "not_present_in_public_annex2_fields")
        self.assertEqual(scope["engine_gearbox_pair"], "cannot_be_established_from_public_annex2_fields")
        self.assertFalse(source.get("data_ingested"))
        self.assertIn("no engine or gearbox technical designation/code", " ".join(source["important_limitations"]))

    def test_legal_revision_and_source_quality_are_explicit(self):
        source = self.sources["rosstandart-fgis-reestr-kts"]
        legal = source["legal_basis"]
        self.assertEqual(legal["current_revision"], "2038_as_amended_by_2335")
        self.assertEqual(legal["latest_amendment_found"]["document"], "Приказ Росстандарта от 30.10.2025 № 2335")
        verification = source["publication_contract"]["source_verification"]
        self.assertTrue(verification["order_2038_secondary_copy_reviewed"])
        self.assertTrue(verification["order_2335_secondary_copy_reviewed"])
        self.assertFalse(verification["official_primary_order_copy_retrieved"])
        self.assertFalse(verification["official_public_search_endpoint_resolved"])
        self.assertIsNone(legal["primary_signed_pdf_sha256"])

    def test_kyrgyz_single_window_registry_is_captcha_gated_and_not_ingested(self):
        source = self.sources["kyrgyzstan-single-window-otts-registry"]
        self.assertEqual(source["status"], "permission_required")
        self.assertEqual(source["market_scope"], ["KG", "EAEU_TR_TS_018_2011"])
        self.assertFalse(source["data_ingested"])
        self.assertFalse(source["product_import_allowed"])
        self.assertIsNone(source["source_snapshot_sha256"])
        self.assertTrue(source["observed_public_query"]["captcha_required_before_record_view"])
        self.assertEqual(source["access_and_reuse"]["documented_api"], "not_identified")
        self.assertEqual(source["license"]["offline_cache"], "not_confirmed")
        self.assertIn("No CAPTCHA was bypassed", source["observed_public_query"]["note"])

    def test_elpts_otts_public_table_is_metadata_only_and_not_ingested(self):
        source = self.sources["elpts-national-otts-register"]
        self.assertEqual(source["status"], "permission_required")
        self.assertFalse(source["data_ingested"])
        self.assertIsNone(source["source_snapshot_sha256"])
        self.assertEqual(source["license"]["commercial_use"], "not_confirmed")
        self.assertEqual(source["license"]["offline_cache"], "not_confirmed")
        observation = source["public_page_observations"]["ot_ts_page"]
        self.assertEqual(observation["visible_total_label"], "Всего оформлено: 14822")
        self.assertEqual(observation["visible_date_filters"], ["05.11.2026", "06.11.2026"])
        self.assertEqual(observation["filtered_result_count"], 0)
        self.assertEqual(len(observation["visible_columns"]), 14)
        self.assertFalse(observation["public_table_exposes_engine_code"])
        self.assertFalse(observation["public_table_exposes_gearbox_code"])
        self.assertFalse(observation["public_table_exposes_engine_gearbox_pair"])
        self.assertFalse(observation["public_table_exposes_ecu"])
        self.assertIn("UI label", observation["count_interpretation"])
        self.assertEqual(source["access"]["bulk_export"], "not_established")
        self.assertEqual(source["access"]["offline_cache"], "not_established")

    def test_elpts_internal_gearbox_entry_notice_does_not_create_public_fields_or_reuse_rights(self):
        source = self.sources["elpts-national-otts-register"]
        notice = source["operator_notices"][0]
        self.assertEqual(notice["notice_id"], "elpts-as-eotts-gearbox-entry-fix-2026-08-21")
        self.assertEqual(notice["notice_date"], "2026-08-21")
        self.assertEqual(notice["evidence_class"], "operator_notice_about_internal_data_entry_workflow")
        self.assertIn("additional reduction gears and hydraulic transmissions", notice["statement"])
        self.assertIn("the exact internal field name or schema", notice["does_not_establish"])
        self.assertIn("that the value is a factory gearbox code", notice["does_not_establish"])
        self.assertIn("offline caching", " ".join(notice["does_not_establish"]))
        self.assertEqual(notice["product_decision"], "retain_as_access_and_schema_discovery_evidence_only; no import or fitment claim")
        self.assertEqual(source["status"], "permission_required")
        self.assertFalse(source["data_ingested"])
        self.assertIsNone(source["source_snapshot_sha256"])
        self.assertEqual(source["license"]["commercial_use"], "not_confirmed")
        self.assertEqual(source["license"]["offline_cache"], "not_confirmed")
        public = source["public_page_observations"]["ot_ts_page"]
        self.assertFalse(public["public_table_exposes_gearbox_code"])
        self.assertFalse(public["public_table_exposes_engine_gearbox_pair"])

    def test_rosstandart_internal_gearbox_notice_does_not_override_public_annex2_scope(self):
        source = self.sources["rosstandart-fgis-reestr-kts"]
        limitation = next(item for item in source["important_limitations"] if "internal AS EOTTS" in item)
        self.assertIn("exact internal schema", limitation)
        self.assertIn("does not change the separate public Annex 2", limitation)
        self.assertIn("no gearbox field", limitation)
        self.assertFalse(source["data_ingested"])
        self.assertEqual(source["status"], "permission_required")

    def test_rusavtolab_private_aggregator_is_not_a_bulk_source(self):
        source = self.sources["rusavtolab-otts-public-index"]
        self.assertEqual(source["status"], "permission_required")
        self.assertEqual(source["market_scope"], ["RU", "EAEU"])
        self.assertFalse(source["data_ingested"])
        self.assertFalse(source["product_import_allowed"])
        self.assertIsNone(source["source_snapshot_sha256"])
        self.assertTrue(source["observed_public_claims"]["access_claims_conflict"])
        self.assertEqual(source["access_and_reuse"]["bulk_export"], "not_established")
        self.assertEqual(source["license"]["offline_cache"], "not_confirmed")
        self.assertIn("private document-retrieval", source["limitations"][0])
    def test_other_otts_sources_keep_their_separate_rights_gates(self):
        eaeu = self.sources["eaeu-open-data-portal"]
        self.assertEqual(eaeu["status"], "discovery_only")
        self.assertFalse(eaeu["data_ingested"])
        hpt = self.sources["hpt-su-otts-api"]
        self.assertEqual(hpt["status"], "restricted_for_product_distribution")
        self.assertFalse(hpt["paid_terms_accepted"])
        self.assertFalse(hpt["data_ingested"])
        aggregators = self.sources["otts-bot-and-public-aggregators"]
        self.assertEqual(aggregators["status"], "permission_required")
        self.assertFalse(aggregators["data_ingested"])


if __name__ == "__main__":
    unittest.main()
