#!/usr/bin/env python3
"""Keep ELPTS public OTTS/reference links quarantined until dataset reuse rights are explicit."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CENTRAL = "data/source-manifests/vag-factory-source-register.json"
REGIONAL = "data/source-manifests/russian-eaeu-otts-sources.json"
REVIEW = "docs/research/ELPTS_PUBLIC_REFERENCE_AND_TARIFF_RECHECK_2026-11-08.md"

RIGHTS = (
    "commercial_use_allowed",
    "display_allowed",
    "offline_cache_allowed",
    "bulk_reuse_allowed",
    "redistribution_allowed",
)


def load_json(relative_path: str):
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


class ElptsReferenceRightsGateTests(unittest.TestCase):
    def test_central_elpts_sources_remain_permission_required(self):
        registry = load_json(CENTRAL)
        by_id = {source["source_id"]: source for source in registry["sources"]}
        expected = {
            "elpts-national-otts-register-public-query",
            "elpts-sep-make-directory",
            "elpts-sep-technical-characteristics-reference",
        }
        self.assertTrue(expected.issubset(by_id))
        for source_id in sorted(expected):
            source = by_id[source_id]
            with self.subTest(source_id=source_id):
                rights = source["rights"]
                self.assertEqual(rights["data_license_status"], "not_established")
                self.assertEqual(rights["permission_status"], "not_obtained")
                self.assertTrue(rights["permission_required_before_product_import_or_distribution"])
                for field in RIGHTS:
                    self.assertEqual(rights[field], "not_established")
                self.assertFalse(source["data_ingested"])
                self.assertFalse(source.get("product_import_allowed", False))
                self.assertIsNone(source.get("source_snapshot_sha256"))
                recheck = source["rights_recheck_2026_11_08"]
                self.assertEqual(recheck["rights_effect"], "none; dataset-specific reuse rights remain not_established and permission_status remains not_obtained")
                self.assertFalse(recheck["acquisition_state"]["product_import_allowed"])
                self.assertFalse(recheck["acquisition_state"]["permission_request_sent"])

    def test_reference_workbooks_have_no_retrieved_bytes_or_fabricated_hash(self):
        registry = load_json(CENTRAL)
        by_id = {source["source_id"]: source for source in registry["sources"]}
        for source_id in (
            "elpts-sep-make-directory",
            "elpts-sep-technical-characteristics-reference",
        ):
            source = by_id[source_id]
            with self.subTest(source_id=source_id):
                self.assertFalse(source["file_metadata"]["file_bytes_retrieved"])
                self.assertIsNone(source["file_metadata"]["source_snapshot_sha256"])
                self.assertFalse(source["access"]["file_downloaded"])
                self.assertFalse(source["access"]["raw_file_bytes_retrieved"])
                self.assertIsNone(source["source_snapshot_sha256"])
                self.assertEqual(source["hash_status"], "not_downloaded_no_ingestion")

    def test_regional_otts_register_keeps_elpts_permission_gate(self):
        registry = load_json(REGIONAL)
        source = next(
            item for item in registry["sources"]
            if item["source_id"] == "elpts-national-otts-register"
        )
        self.assertEqual(source["status"], "permission_required")
        self.assertFalse(source["data_ingested"])
        self.assertFalse(source.get("product_import_allowed", False))
        self.assertIsNone(source["source_snapshot_sha256"])
        for field in ("commercial_use", "display", "offline_cache", "bulk_export", "redistribution"):
            with self.subTest(right=field):
                self.assertEqual(source["license"][field], "not_confirmed")

    def test_review_distinguishes_software_tariff_from_dataset_rights(self):
        review = (ROOT / REVIEW).read_text(encoding="utf-8").casefold()
        for phrase in (
            "do not download either xlsx",
            "they do not grant a dataset-specific reuse licence",
            "software-use tariff",
            "effective 2026-11-01",
            "permission request sent: no",
            "source-file sha-256 values: intentionally null",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase.casefold(), review)


if __name__ == "__main__":
    unittest.main()
