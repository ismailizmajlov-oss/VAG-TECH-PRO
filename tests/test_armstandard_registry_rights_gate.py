#!/usr/bin/env python3
"""Keep Armenian OTTS discovery metadata quarantined until dataset reuse rights are explicit."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_json(relative_path: str):
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


class ArmeniaOttsRightsGateTests(unittest.TestCase):
    def test_central_source_register_keeps_armenia_listing_metadata_only(self):
        registry = load_json("data/source-manifests/vag-factory-source-register.json")
        source = next(
            s for s in registry["sources"]
            if s["source_id"] == "armstandard-am-otts-public-register"
        )
        self.assertEqual(source["market_scope"], ["AM", "EAEU_TR_TS_018_2011"])
        self.assertFalse(source["data_ingested"])
        self.assertFalse(source["product_import_allowed"])
        self.assertIsNone(source["source_snapshot_sha256"])
        self.assertEqual(source["hash_status"], "not_downloaded_no_ingestion")
        self.assertEqual(source["rights"]["permission_status"], "not_obtained")
        for key in (
            "commercial_use_allowed",
            "display_allowed",
            "offline_cache_allowed",
            "bulk_reuse_allowed",
            "redistribution_allowed",
        ):
            with self.subTest(right=key):
                self.assertEqual(source["rights"][key], "not_established")
        self.assertFalse(source["applicability"]["exact_vag_vehicle_fitment"])
        self.assertFalse(source["applicability"]["engine_gearbox_pairing"])
        self.assertFalse(source["applicability"]["russian_market_scope"])

    def test_regional_register_does_not_promote_public_listing_to_importable_data(self):
        registry = load_json("data/source-manifests/russian-eaeu-otts-sources.json")
        source = next(
            s for s in registry["sources"]
            if s["source_id"] == "armstandard-am-otts-public-register"
        )
        self.assertEqual(source["market_scope"], ["AM", "EAEU_TR_TS_018_2011"])
        self.assertEqual(source["status"], "permission_required")
        self.assertFalse(source["data_ingested"])
        self.assertFalse(source["product_import_allowed"])
        self.assertIsNone(source["source_snapshot_sha256"])
        self.assertEqual(source["hash_status"], "not_downloaded_no_ingestion")
        self.assertEqual(source["license"]["commercial_use"], "not_confirmed")
        self.assertEqual(source["license"]["offline_cache"], "not_confirmed")
        self.assertEqual(source["license"]["bulk_export"], "not_confirmed")
        self.assertEqual(source["license"]["redistribution"], "not_confirmed")
        self.assertEqual(source["observed_public_listing"]["visible_pdf_entries"], 40)
        self.assertFalse(source["observed_public_listing"]["files_downloaded"])
        self.assertFalse(source["observed_public_listing"]["vag_records_verified"])
        self.assertFalse(source["technical_scope"]["exact_vag_vehicle_fitment"])
        self.assertFalse(source["technical_scope"]["engine_gearbox_pairing"])
        self.assertFalse(source["technical_scope"]["russian_market_scope"])

    def test_review_document_preserves_no_download_and_no_hash_boundary(self):
        review = (
            ROOT / "docs/research/ARMENIA_NATIONAL_OTTS_PUBLIC_LISTING_RIGHTS_REVIEW_2026-11-08.md"
        ).read_text(encoding="utf-8")
        for phrase in (
            "No PDF was downloaded or inspected",
            "no dataset-specific licence",
            "metadata-only discovery",
            "info@armstandard.am",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, review)


if __name__ == "__main__":
    unittest.main()
