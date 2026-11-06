#!/usr/bin/env python3
"""Guard the Open Vehicle Schema review against accidental empty-data imports."""
import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ID = "open-vehicle-schema-reference-dataset"
PINNED_REVISION = "d7223f3edfe4adcebf22d3ffa7a60599ae25016c"
EMPTY_FILE_SHA256 = "e4cf0694d2bd3ba2d319ba1552ee9f0d33eb1e8a6ddd0ce53b17921dd39da75c"
EMPTY_FILE_GIT_BLOB = "9f1c8a72514a9f9f252f3959a732d40a914b2cc8"
EXPECTED_PATHS = {
    "data/reference/vehicles.json",
    "data/reference/engines.json",
    "data/reference/transmissions.json",
    "data/reference/bodies.json",
}


class OpenVehicleSchemaSourceReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = ROOT / "data/source-manifests/vag-factory-source-register.json"
        manifest = json.loads(path.read_text(encoding="utf-8"))
        matches = [item for item in manifest["sources"] if item.get("source_id") == SOURCE_ID]
        if len(matches) != 1:
            raise AssertionError(f"Expected one {SOURCE_ID} source entry, got {len(matches)}")
        cls.source = matches[0]
        cls.review = (ROOT / "docs/research/OPEN_VEHICLE_SCHEMA_SOURCE_REVIEW_2026-11-06.md").read_text(encoding="utf-8")

    def test_source_is_pinned_but_not_ingested(self):
        self.assertEqual(self.source["source_revision"], PINNED_REVISION)
        self.assertIs(self.source["data_ingested"], False)
        self.assertEqual(self.source["market_scope"], ["UNKNOWN"])
        self.assertEqual(self.source["vehicle_scope"]["observed_vag_records"], 0)
        self.assertIn("exclude_empty_reference_dataset", self.source["project_decision"])

    def test_dataset_license_and_provenance_are_not_overstated(self):
        rights = self.source["rights"]
        self.assertEqual(rights["repository_license"], "MIT")
        self.assertIn("no_separate_data_license", rights["dataset_license_status"])
        self.assertEqual(rights["permission_status"], "not_cleared_for_dataset_import")
        self.assertIn("no_row_level_citations", rights["data_provenance_status"])
        self.assertEqual(rights["offline_cache_allowed"], "not_established_for_reference_data")
        self.assertEqual(rights["redistribution_allowed"], "not_established_for_reference_data")

    def test_all_observed_reference_arrays_are_empty_and_hashed(self):
        files = self.source["observed_data_files"]
        self.assertEqual({item["path"] for item in files}, EXPECTED_PATHS)
        raw = b"[]\n\n\n"
        self.assertEqual(len(raw), 5)
        self.assertEqual(hashlib.sha256(raw).hexdigest(), EMPTY_FILE_SHA256)
        for item in files:
            self.assertEqual(item["bytes"], 5)
            self.assertEqual(item["record_count"], 0)
            self.assertEqual(item["git_blob_sha"], EMPTY_FILE_GIT_BLOB)
            self.assertEqual(item["sha256"], EMPTY_FILE_SHA256)

    def test_review_records_exclusion_and_no_import(self):
        self.assertIn("Do not import the reference dataset", self.review)
        self.assertIn(PINNED_REVISION, self.review)
        self.assertIn("Data records imported: 0", self.review)
        self.assertIn("not treated as proof", self.review)


if __name__ == "__main__":
    unittest.main()
