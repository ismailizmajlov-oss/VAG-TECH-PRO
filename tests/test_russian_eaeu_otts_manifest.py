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


    def test_kyrgyz_no_login_public_registry_remains_discovery_only(self):
        source = self.sources["kyrgyz-single-window-public-registry"]
        self.assertEqual(source["status"], "permission_required")
        self.assertEqual(source["market_scope"], ["KG", "EAEU_TR_TS_018_2011"])
        self.assertFalse(source["data_ingested"])
        self.assertFalse(source["product_import_allowed"])
        self.assertIsNone(source["source_snapshot_sha256"])
        observed = source["observed_public_query"]
        self.assertEqual(observed["registry_status"], "pilot")
        self.assertFalse(observed["login_required"])
        self.assertEqual(observed["search_fields"], ["approval_number", "make", "model"])
        self.assertEqual(observed["otts_summary_count"], 1)
        self.assertEqual(observed["otsh_summary_count"], 0)
        self.assertEqual(observed["summary_source_url"], "https://cert.trade.kg/")
        self.assertEqual(observed["count_treatment"], "separate_cert_trade_landing_page_ui_counters_only_not_a_complete_or_verified_public_register_corpus_count")
        self.assertFalse(observed["record_schema_retrieved"])
        self.assertFalse(observed["result_retrieval_independently_tested"])
        self.assertTrue(observed["engine_fields_in_application_form"])
        self.assertEqual(observed["engine_fields_in_public_record_schema"], "not_established")
        access = source["access_and_reuse"]
        self.assertEqual(access["public_query"], "observed_without_login")
        self.assertEqual(access["documented_api"], "not_identified")
        self.assertEqual(access["bulk_export"], "not_established")
        self.assertEqual(access["automated_extraction"], "not_established")
        self.assertEqual(access["offline_cache"], "not_confirmed")
        self.assertEqual(source["license"]["offline_cache"], "not_confirmed")
        self.assertEqual(source["project_decision"], "discovery_only_no_automation_no_import_until_documented_record_schema_and_written_reuse_rights_are_confirmed")
        self.assertIn("record_schema_and_reuse_rights_unresolved", source["verification_status"])
        self.assertTrue(any("must not be assumed to appear in public records" in item for item in source["limitations"]))

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
        self.assertEqual(observation["observed_at"], "2026-11-07")
        self.assertEqual(observation["manufacturer_filter_options_observed"], ["AUDI AG", "Volkswagen AG"])
        self.assertTrue(observation["manufacturer_filter_values_are_options_only"])
        self.assertFalse(observation["vag_records_observed"])
        self.assertFalse(observation["vag_record_count_verified"])
        self.assertFalse(observation["bulk_api_discovered"])
        self.assertTrue(observation["pdf_column_visible"])
        self.assertFalse(observation["pdf_downloaded"])
        self.assertFalse(observation["public_table_exposes_engine_code"])
        self.assertFalse(observation["public_table_exposes_gearbox_code"])
        self.assertFalse(observation["public_table_exposes_engine_gearbox_pair"])
        self.assertFalse(observation["public_table_exposes_ecu"])
        self.assertIn("UI label", observation["count_interpretation"])
        self.assertEqual(source["access"]["bulk_export"], "not_established")
        self.assertEqual(source["access"]["offline_cache"], "not_established")
        sbkts = source["public_page_observations"]["sbkts_page"]
        self.assertTrue(sbkts["vag_metadata_row_observed"])
        self.assertEqual(sbkts["sample_document_type"], "SBKTS")
        self.assertFalse(sbkts["pdf_downloaded"])
        self.assertIn("not an OTTS", sbkts["note"])
        self.assertEqual(sbkts["rights_effect"], "none; this observation is not OTTS fitment evidence and grants no reuse rights")

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
        self.assertFalse(hpt["product_import_allowed"])
        self.assertFalse(hpt["offline_cache_for_product_distribution_allowed"])
        self.assertFalse(hpt["third_party_desktop_display_allowed"])
        self.assertFalse(hpt["written_permission_for_product_distribution_obtained"])
        self.assertEqual(hpt["rights_review_date"], "2026-11-07")
        self.assertTrue(hpt["mcp_access"]["registration_required"])
        self.assertEqual(hpt["mcp_access"]["free_requests_per_day"], 50)
        self.assertEqual(hpt["api_pricing"]["entry_tier_rub_per_month"], 1000)
        self.assertTrue(hpt["pdf_download_requires_registry_subscription"])
        central = json.loads((ROOT / "data" / "source-manifests" / "vag-factory-source-register.json").read_text(encoding="utf-8"))
        central_hpt = next(item for item in central["sources"] if item["source_id"] == "hpt-su-otts-aggregator")
        self.assertEqual(central_hpt["evidence_status"], "official HPT.SU offer, API terms, pricing and MCP pages reviewed 2026-11-07; no account, key, subscription or data access used")
        self.assertFalse(central_hpt["rights"]["offline_cache_for_product_distribution_allowed"])
        self.assertFalse(central_hpt["rights"]["third_party_desktop_display_allowed"])
        self.assertFalse(central_hpt["rights"]["written_permission_for_product_distribution_obtained"])
        review = (ROOT / "docs" / "research" / "HPT_SU_OTTS_AGGREGATOR_RIGHTS_REVIEW_2026-11-07.md").read_text(encoding="utf-8")
        self.assertIn("Do not ingest, cache, bundle, mirror, or expose HPT.SU database records", review)
        self.assertIn("connector code, not HPT.SU's database", review)
        aggregators = self.sources["otts-bot-and-public-aggregators"]
        self.assertEqual(aggregators["status"], "permission_required")
        self.assertFalse(aggregators["data_ingested"])


if __name__ == "__main__":
    unittest.main()
