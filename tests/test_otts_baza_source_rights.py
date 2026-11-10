import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "data" / "source-manifests" / "vag-factory-source-register.json"
SOURCE_ID = "otts-baza-commercial-otts-catalog"


class OtssBazaSourceRightsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.register = json.loads(REGISTER.read_text(encoding="utf-8"))
        matches = [item for item in cls.register["sources"] if item.get("source_id") == SOURCE_ID]
        if len(matches) != 1:
            raise AssertionError(f"expected exactly one {SOURCE_ID} entry, found {len(matches)}")
        cls.entry = matches[0]

    def test_published_terms_do_not_authorize_product_database_reuse(self):
        entry = self.entry
        rights = entry["rights"]
        self.assertFalse(entry["data_ingested"])
        self.assertFalse(entry["product_import_allowed"])
        self.assertEqual(rights["dataset_license"], "not_granted")
        self.assertFalse(rights["bulk_automated_extraction_allowed"])
        self.assertFalse(rights["systematic_extraction_of_substantial_part_allowed"])
        self.assertFalse(rights["competing_catalog_creation_allowed"])
        self.assertFalse(rights["offline_cache_for_product_distribution_allowed"])
        self.assertFalse(rights["third_party_display_allowed"])
        self.assertFalse(rights["redistribution_allowed"])
        self.assertFalse(rights["derivative_database_reproduction_allowed"])
        self.assertFalse(rights["written_permission_obtained"])
        self.assertIsNone(entry["source_snapshot_sha256"])
        self.assertEqual(entry["hash_status"], "not_computed_no_source_file_acquired")

    def test_review_note_records_owner_permission_gate(self):
        note = ROOT / self.entry["review_document"]
        self.assertTrue(note.is_file())
        content = note.read_text(encoding="utf-8")
        self.assertIn("Do not ingest", content)
        self.assertIn("separate written agreement", content)
        self.assertIn("No account was created", content)


if __name__ == "__main__":
    unittest.main()
