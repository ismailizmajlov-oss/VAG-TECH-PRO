#!/usr/bin/env python3
"""Prevent HPT.SU aggregator data from entering an offline third-party product without written permission."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_json(relative_path: str):
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


class HptSuSourceRightsTests(unittest.TestCase):
    def test_central_registry_blocks_aggregator_distribution(self):
        registry = load_json("data/source-manifests/vag-factory-source-register.json")
        source = next(s for s in registry["sources"] if s["source_id"] == "hpt-su-otts-aggregator")
        rights = source["rights"]
        self.assertEqual(source["market_scope"], ["RU", "EAEU"])
        self.assertFalse(source["data_ingested"])
        self.assertIsNone(source.get("source_snapshot_sha256"))
        self.assertEqual(rights["dataset_open_license"], "not granted")
        for key in (
            "bulk_automated_download_allowed",
            "substantial_or_systematic_database_extraction_allowed",
            "full_database_copy_allowed",
            "third_party_equivalent_access_allowed",
            "derivative_database_reproducing_provider_database_allowed",
            "third_party_api_or_file_export_allowed",
            "redistribution_allowed",
            "offline_cache_for_product_distribution_allowed",
            "third_party_desktop_display_allowed",
            "written_permission_for_product_distribution_obtained",
        ):
            with self.subTest(right=key):
                self.assertIs(rights[key], False)
        self.assertTrue(rights["api_internal_use_does_not_authorize_third_party_distribution"])
        self.assertEqual(rights["permission_status"], "no_project_permission_or_subscription_obtained")
        self.assertIn("restricted_no_bulk_import_no_product_pack", source["project_decision"])

    def test_russian_eaeu_manifest_keeps_api_out_of_product_pack(self):
        manifest = load_json("data/source-manifests/russian-eaeu-otts-sources.json")
        source = next(s for s in manifest["sources"] if s["source_id"] == "hpt-su-otts-api")
        self.assertEqual(source["status"], "restricted_for_product_distribution")
        self.assertFalse(source["paid_terms_accepted"])
        self.assertFalse(source["data_ingested"])
        self.assertIsNone(source["source_snapshot_sha256"])
        license_info = source["license"]
        self.assertEqual(license_info["commercial_use"], "internal_user_use_only_with_active_api_subscription")
        self.assertEqual(license_info["display_to_third_parties"],
                         "not_authorized_as_equivalent_database_access_without_separate_written_consent")
        self.assertEqual(license_info["bulk_copy"], "prohibited")
        self.assertEqual(license_info["full_database_mirror"], "prohibited")

    def test_review_document_records_no_account_key_or_source_snapshot(self):
        path = ROOT / "docs/research/HPT_SU_OTTS_AGGREGATOR_RIGHTS_REVIEW_2026-11-07.md"
        text = path.read_text(encoding="utf-8")
        for phrase in (
            "No account, MCP key, API key, subscription, payment, API request, document download, or data snapshot",
            "offline caching",
            "redistribution",
            "MIT",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
