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
        source = self.sources["rosstandart-fgis-registers-kts"]
        self.assertEqual(source["status"], "permission_required")
        self.assertFalse(source["data_ingested"])
        self.assertIsNone(source["source_snapshot_sha256"])
        self.assertEqual(source["license"]["commercial_use"], "not_confirmed")
        self.assertEqual(source["license"]["display"], "not_confirmed")
        self.assertEqual(source["license"]["offline_cache"], "not_confirmed")
        self.assertEqual(source["license"]["bulk_export"], "not_confirmed")
        self.assertEqual(source["license"]["pdf_redistribution"], "not_confirmed")

    def test_public_annex2_and_internal_annex1_field_numbers_are_separate(self):
        source = self.sources["rosstandart-fgis-registers-kts"]
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
        source = self.sources["rosstandart-fgis-registers-kts"]
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
        source = self.sources["rosstandart-fgis-registers-kts"]
        legal = source["legal_basis"]
        self.assertEqual(legal["current_revision"], "2038_as_amended_by_2335")
        self.assertEqual(legal["latest_amendment_found"]["document"], "Приказ Росстандарта от 30.10.2025 № 2335")
        verification = source["publication_contract"]["source_verification"]
        self.assertTrue(verification["order_2038_secondary_copy_reviewed"])
        self.assertTrue(verification["order_2335_secondary_copy_reviewed"])
        self.assertFalse(verification["official_primary_order_copy_retrieved"])
        self.assertFalse(verification["official_public_search_endpoint_resolved"])
        self.assertIsNone(legal["primary_signed_pdf_sha256"])

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
