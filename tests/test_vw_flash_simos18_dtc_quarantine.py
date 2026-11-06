import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "data" / "source-manifests" / "vag-factory-source-register.json"


class VwFlashSimos18DtcQuarantineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        manifest = json.loads(REGISTER.read_text(encoding="utf-8"))
        cls.source = next(item for item in manifest["sources"] if item["source_id"] == "bri3d-vw-flash-simos18-dtc-candidate")

    def test_candidate_remains_quarantined_and_not_ingested(self):
        source = self.source
        self.assertFalse(source["data_ingested"])
        self.assertEqual(source["display_status"], "quarantined_not_displayed")
        self.assertEqual(source["rights"]["permission_status"], "not_cleared")
        self.assertEqual(source["rights"]["review_status"], "quarantined")
        self.assertEqual(source["rights"]["database_data_license"], "not_separately_established")
        self.assertNotEqual(source["rights"]["offline_cache_allowed"], True)
        self.assertNotEqual(source["rights"]["display_allowed"], True)
        self.assertNotEqual(source["rights"]["bulk_reuse_allowed"], True)
        self.assertNotEqual(source["rights"]["redistribution_allowed"], True)
        self.assertIn("quarantine_no_import", source["project_decision"])

    def test_data_license_and_row_provenance_are_not_overstated(self):
        evidence = self.source["source_data_evidence"]
        self.assertEqual(evidence["data_rows"], 657)
        self.assertEqual(evidence["per_row_source_attribution"], "not_provided_in_the_addition_commit_or_reviewed_README")
        self.assertEqual(evidence["data_license_assessment"], "Repository BSD-2-Clause is declared, but the origin and rights of the CSV data are not independently established; no data import is permitted.")
        for key in ("retrieved_content_sha256", "license_file_sha256", "readme_sha256"):
            self.assertRegex(evidence[key], re.compile(r"^[a-f0-9]{64}$"))
        self.assertEqual(evidence["git_blob_sha1"], "e5c65fff0c6f0d98aafb082ff1acefa483be016e")
        self.assertEqual(evidence["license_file_blob_sha1"], "78fe76374aca450843661a30406a363e7a2ae93b")
        self.assertEqual(evidence["readme_blob_sha1"], "830a60eef56dd7d22b04250cdb5b87accc1205b4")


if __name__ == "__main__":
    unittest.main()
