#!/usr/bin/env python3
"""Keep the ELPTS e-SBKTS UI as metadata-only discovery, not OTTS fitment data."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CENTRAL = ROOT / "data/source-manifests/vag-factory-source-register.json"
REGIONAL_OTTS = ROOT / "data/source-manifests/russian-eaeu-otts-sources.json"
REVIEW = ROOT / "docs/research/ELPTS_ESBKTS_PUBLIC_UI_REVIEW_2026-11-10.md"


class ElptsEsbktsPublicUiRightsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.central = json.loads(CENTRAL.read_text(encoding="utf-8"))
        cls.sources = {item["source_id"]: item for item in cls.central["sources"]}

    def test_source_is_separate_sbkts_discovery_only_entry(self):
        source = self.sources["elpts-esbkts-public-query"]
        self.assertEqual(source["source_kind"], "official_public_query_for_electronic_sbkts_certificates")
        self.assertEqual(source["url"], "https://docs.elpts.ru/ncher/esbkts")
        self.assertEqual(source["document_types"], ["SBKTS"])
        self.assertEqual(source["market_scope"], ["RU"])
        self.assertEqual(source["applicability_precision"], "individual_certificate_metadata_only")
        self.assertFalse(source["data_ingested"])
        self.assertFalse(source["product_import_allowed"])
        self.assertIsNone(source["source_snapshot_sha256"])
        self.assertEqual(source["hash_status"], "not_downloaded_no_ingestion")

    def test_rights_remain_unestablished_and_no_record_bytes_are_retrieved(self):
        source = self.sources["elpts-esbkts-public-query"]
        rights = source["rights"]
        self.assertEqual(rights["data_license_status"], "not_established")
        self.assertEqual(rights["permission_status"], "not_obtained")
        self.assertTrue(rights["permission_required_before_product_import_or_distribution"])
        for field in (
            "commercial_use_allowed",
            "display_allowed",
            "offline_cache_allowed",
            "bulk_reuse_allowed",
            "redistribution_allowed",
        ):
            with self.subTest(field=field):
                self.assertEqual(rights[field], "not_established")
        access = source["access"]
        self.assertTrue(access["public_query_page_observed"])
        self.assertFalse(access["raw_record_bytes_retrieved"])
        self.assertFalse(access["pdf_downloaded"])
        self.assertEqual(access["bulk_export"], "not_established")
        self.assertEqual(access["offline_cache"], "not_established")
        self.assertEqual(access["redistribution"], "not_established")

    def test_personal_fields_and_pdfs_are_explicitly_excluded(self):
        source = self.sources["elpts-esbkts-public-query"]
        privacy = source["privacy"]
        self.assertTrue(privacy["individual_vehicle_certificate_records"])
        self.assertTrue(privacy["may_contain_personal_data"])
        self.assertTrue(privacy["applicant_field_present"])
        self.assertTrue(privacy["pdf_may_contain_personal_data"])
        self.assertFalse(privacy["personal_values_retrieved"])
        self.assertFalse(privacy["personal_data_retained"])
        excluded = set(privacy["excluded_fields"])
        self.assertTrue({"applicant_name", "VIN", "registration_plate", "owner_identity", "certificate_pdf_contents"}.issubset(excluded))

    def test_search_index_observation_is_not_a_registry_snapshot_or_fitment_claim(self):
        source = self.sources["elpts-esbkts-public-query"]
        observation = source["sample_index_observation"]
        self.assertEqual(observation["observed_at"], "2026-11-10")
        self.assertEqual(observation["observation_method"], "search_indexed_preview_of_official_dynamic_page; not a raw registry export")
        self.assertEqual(observation["filtered_result_count"], 155)
        self.assertEqual(observation["total_records_displayed"], 2799410)
        self.assertEqual(observation["non_personal_example"], {"make": "VOLKSWAGEN", "vehicle_type": "FV6462HADCG"})
        self.assertIn("exact engine-gearbox pair", " ".join(source["not_confirmed"]))
        self.assertIn("individual-vehicle", source["project_decision"])

    def test_sbkts_is_not_mixed_into_the_otts_import_manifest(self):
        regional = json.loads(REGIONAL_OTTS.read_text(encoding="utf-8"))
        regional_ids = {item["source_id"] for item in regional["sources"]}
        self.assertNotIn("elpts-esbkts-public-query", regional_ids)
        self.assertEqual(source_document_types(self.sources["elpts-esbkts-public-query"]), {"SBKTS"})

    def test_review_records_zero_acquisition_and_separate_document_scope(self):
        review = REVIEW.read_text(encoding="utf-8").casefold()
        self.assertIn("eec.eaeunion.org", review)
        for phrase in (
            "discovery-only",
            "individual-vehicle safety certificate",
            "not a pinned source snapshot",
            "raw registry records downloaded: 0",
            "certificate pdfs downloaded: 0",
            "personal values retrieved or retained: 0",
            "source snapshot sha-256: intentionally null",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase.casefold(), review)


def source_document_types(source):
    return set(source["document_types"])


if __name__ == "__main__":
    unittest.main()
