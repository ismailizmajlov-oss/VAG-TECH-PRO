import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "data" / "source-manifests" / "vag-factory-source-register.json"


class SaeJ2012SourceRightsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTER.read_text(encoding="utf-8"))

    def test_sae_j2012_metadata_source_is_registered_once(self):
        matches = [
            source for source in self.registry["sources"]
            if source.get("source_id") == "sae-j2012-dtc-standard"
        ]
        self.assertEqual(len(matches), 1)

    def test_copyrighted_standard_content_is_not_licensed_or_ingested(self):
        source = next(
            source for source in self.registry["sources"]
            if source.get("source_id") == "sae-j2012-dtc-standard"
        )
        rights = source["rights"]
        self.assertEqual(
            rights["data_license_status"],
            "copyrighted_standard_no_project_reuse_license_acquired",
        )
        self.assertFalse(rights["standard_text_storage_allowed"])
        self.assertFalse(rights["definition_table_storage_allowed"])
        self.assertFalse(rights["current_annex_allocation_table_storage_allowed"])
        self.assertFalse(rights["offline_cache_allowed"])
        self.assertFalse(rights["redistribution_allowed"])
        self.assertEqual(rights["permission_status"], "not_obtained")
        self.assertIsNone(source["source_snapshot_sha256"])
        self.assertEqual(
            source["hash_status"],
            "metadata_only_no_standard_content_downloaded",
        )

    def test_current_standard_and_annex_revisions_are_metadata_only(self):
        source = next(
            source for source in self.registry["sources"]
            if source.get("source_id") == "sae-j2012-dtc-standard"
        )
        self.assertIn("SAE J2012_202509", source["source_revision"])
        self.assertIn("J2012DA_202607", source["source_revision"])
        self.assertIn(
            "https://saemobilus.sae.org/standards/j2012da_202510-digital-annex-diagnostic-trouble-code-definitions-failure-type-byte-definitions",
            source["related_urls"],
        )
        self.assertFalse(source["rights"]["current_annex_allocation_table_storage_allowed"])
        self.assertIn("not licensed or acquired", source["evidence_status"])

    def test_standard_metadata_cannot_become_product_dtc_content(self):
        source = next(
            source for source in self.registry["sources"]
            if source.get("source_id") == "sae-j2012-dtc-standard"
        )
        self.assertFalse(source["data_ingested"])
        self.assertFalse(source["research_pack_ingested"])
        self.assertFalse(source["product_database_ingested"])
        self.assertFalse(source["product_import_allowed"])
        self.assertFalse(source["applicability"]["vag_specific"])
        self.assertEqual(
            source["applicability"]["applicability_precision"],
            "namespace_policy_only",
        )


if __name__ == "__main__":
    unittest.main()
