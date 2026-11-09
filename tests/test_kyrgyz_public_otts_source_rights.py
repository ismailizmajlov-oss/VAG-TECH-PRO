#!/usr/bin/env python3
"""Keep the Kyrgyz public OTTS pilot discovery-only until record schema and reuse rights are cleared."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def load(relative_path):
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))

class KyrgyzPublicOttsRightsGateTests(unittest.TestCase):
    def test_regional_manifest_preserves_no_login_privacy_and_no_reuse_boundary(self):
        registry = load("data/source-manifests/russian-eaeu-otts-sources.json")
        source = next(s for s in registry["sources"] if s["source_id"] == "kyrgyz-single-window-public-registry")
        latest = source["observed_public_query"]["latest_official_recheck"]
        privacy = latest["privacy_policy_review"]

        self.assertEqual(source["market_scope"], ["KG", "EAEU_TR_TS_018_2011"])
        self.assertEqual(source["status"], "permission_required")
        self.assertFalse(source["data_ingested"])
        self.assertFalse(source["product_import_allowed"])
        self.assertIsNone(source["source_snapshot_sha256"])
        self.assertEqual(source["hash_status"], "not_downloaded_no_ingestion")
        self.assertFalse(latest["record_rows_observed"])
        self.assertFalse(latest["record_schema_retrieved"])
        self.assertFalse(latest["documented_api_identified"])
        self.assertFalse(latest["bulk_export_documented"])
        self.assertFalse(latest["source_bytes_downloaded"])
        self.assertFalse(latest["vin_or_document_query_submitted"])
        self.assertFalse(latest["personal_values_collected"])
        self.assertTrue(privacy["search_request_sent_to_server"])
        self.assertTrue(privacy["analytics_excludes_search_text_document_number_and_vin"])
        self.assertTrue(privacy["query_document_number_and_vin_not_linked_to_visitor"])
        self.assertFalse(privacy["reuse_license_granted"])
        for right in ("commercial_use", "display", "offline_cache", "bulk_export", "redistribution"):
            with self.subTest(right=right):
                self.assertEqual(source["license"][right], "not_confirmed")
        self.assertEqual(source["applicability_precision"], "type_approval_document_metadata_only")

    def test_central_register_keeps_application_engine_fields_separate_from_public_schema(self):
        registry = load("data/source-manifests/vag-factory-source-register.json")
        source = next(s for s in registry["sources"] if s["source_id"] == "kyrgyz-single-window-public-registry")
        latest = source["observed_claims"]["public_registry"]["latest_official_recheck"]
        self.assertEqual(source["market_scope"], ["KG", "EAEU_TR_TS_018_2011"])
        self.assertFalse(source["data_ingested"])
        self.assertFalse(source["product_import_allowed"])
        self.assertIsNone(source["source_snapshot_sha256"])
        self.assertFalse(latest["record_rows_observed"])
        self.assertFalse(latest["record_schema_retrieved"])
        self.assertFalse(latest["documented_api_identified"])
        self.assertFalse(latest["bulk_export_documented"])
        self.assertFalse(latest["source_bytes_downloaded"])
        self.assertFalse(latest["privacy_policy_review"]["reuse_license_granted"])
        self.assertEqual(source["rights"]["permission_status"], "not_obtained")
        self.assertEqual(source["rights"]["offline_cache_allowed"], "not_established")
        self.assertEqual(source["rights"]["redistribution_allowed"], "not_established")
        self.assertFalse(source["applicability"]["exact_vag_vehicle_fitment"])
        self.assertFalse(source["applicability"]["engine_gearbox_pairing"])
        self.assertFalse(source["applicability"]["russian_market_scope"])

    def test_review_document_records_no_query_no_download_and_no_hash(self):
        review = (ROOT / "docs/research/KYRGYZ_PUBLIC_OTTS_REGISTRY_RECHECK_2026-11-10.md").read_text(encoding="utf-8").casefold()
        for phrase in (
            "no vin or document query was submitted",
            "no registry row or source bytes were downloaded",
            "not a data-reuse licence",
            "no dataset-specific reuse rights",
            "application input fields are not the public record schema",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, review)

if __name__ == "__main__":
    unittest.main()
