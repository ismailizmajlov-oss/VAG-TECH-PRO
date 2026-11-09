#!/usr/bin/env python3
"""Prevent unlicensed VAG-Hub workshop material from entering product or offline packs."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "data" / "source-manifests" / "vag-factory-source-register.json"


class VagHubSourceRightsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        manifest = json.loads(REGISTER.read_text(encoding="utf-8"))
        matches = [
            item for item in manifest["sources"]
            if item["source_id"] == "vag-hub-workshop-document-aggregator"
        ]
        if len(matches) != 1:
            raise AssertionError(f"expected exactly one VAG-Hub source record, got {len(matches)}")
        cls.source = matches[0]

    def test_source_is_quarantined_without_dataset_or_underlying_oem_rights(self):
        rights = self.source["rights"]
        self.assertEqual(rights["data_license_status"], "not_found_in_reviewed_pages")
        self.assertEqual(rights["permission_status"], "not_cleared")
        self.assertEqual(rights["underlying_oem_material_rights"], "not_established")
        self.assertEqual(rights["record_level_provenance"], "not_documented_in_reviewed_pages")
        self.assertFalse(rights["redistribution_allowed"])
        self.assertFalse(self.source["product_import_allowed"])
        self.assertFalse(self.source["data_ingested"])
        self.assertIsNone(self.source["source_snapshot_sha256"])
        self.assertIn("quarantined_no_import_no_display_no_cache_no_redistribution", self.source["project_decision"])

    def test_no_technical_applicability_is_promoted_from_web_table(self):
        applicability = self.source["applicability"]
        for field in (
            "exact_vehicle_fitment",
            "model_generation_year_fitment",
            "engine_code_fitment",
            "gearbox_code_fitment",
            "engine_gearbox_pairing",
            "ecu_fitment",
            "dtc_fitment",
            "repair_procedure_fitment",
            "diagnostic_execution_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(applicability[field])
        self.assertEqual(applicability["market_scope"], "UNKNOWN")
        self.assertEqual(applicability["technical_review_status"], "not_independently_reviewed")

    def test_oem_download_categories_are_not_reclassified_as_open_data(self):
        claims = self.source["observed_claims"]
        for category in ("ELSAWin service-information software", "ETKA/ETOS parts-catalogue material", "TPI reports", "Dataflash/firmware downloads"):
            with self.subTest(category=category):
                self.assertIn(category, claims["content_categories"])
        self.assertIn("delete downloaded files after reading", claims["dataflash_page"].lower())
        self.assertIn("purchase original", claims["elsawin_page"].lower())
        self.assertTrue(claims["about_page"].startswith("The publisher says materials are compiled from publicly available sources"))

    def test_evidence_urls_and_review_revision_are_pinned(self):
        self.assertEqual(self.source["source_revision"], "public_pages_reviewed_2026-11-09; no dataset-specific licence found")
        urls = {item["url"] for item in self.source["evidence_reviewed"]}
        self.assertEqual(urls, {
            "https://www.vag-hub.com/about/",
            "https://www.vag-hub.com/vag-programs/elsawin/",
            "https://www.vag-hub.com/vag-programs/dataflash-vag/",
            "https://www.vag-hub.com/vw-audi-seat-skoda-dtc/",
        })


if __name__ == "__main__":
    unittest.main()
