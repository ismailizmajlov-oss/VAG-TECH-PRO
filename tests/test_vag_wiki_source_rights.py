import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "data" / "source-manifests" / "vag-factory-source-register.json"


class VagWikiSourceRightsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        manifest = json.loads(REGISTER.read_text(encoding="utf-8"))
        matches = [
            source for source in manifest["sources"]
            if source["source_id"] == "vag-wiki-community-technical-hub"
        ]
        if len(matches) != 1:
            raise AssertionError(f"expected one VAG-Wiki source record, got {len(matches)}")
        cls.source = matches[0]

    def test_source_is_not_misrepresented_as_oem_or_russian_market_evidence(self):
        self.assertIn("independent", self.source["publisher"].lower())
        self.assertEqual(self.source["market_scope"], ["UNKNOWN"])
        self.assertFalse(self.source["applicability"]["exact_vehicle_fitment"])
        self.assertFalse(self.source["applicability"]["engine_gearbox_pairing"])
        self.assertFalse(self.source["applicability"]["ecu_dtc_fitment"])

    def test_terms_block_unauthorized_bulk_extraction_and_redistribution(self):
        rights = self.source["rights"]
        self.assertEqual(rights["dataset_license"], "not_found_in_reviewed_pages")
        self.assertFalse(rights["bulk_automated_extraction_allowed"])
        self.assertFalse(rights["redistribution_allowed"])
        self.assertTrue(rights["terms_explicitly_prohibit_unauthorized_mass_scraping"])
        self.assertTrue(rights["terms_explicitly_prohibit_automated_data_extraction_without_prior_authorization"])
        self.assertTrue(rights["terms_explicitly_prohibit_redistribution_without_prior_authorization"])
        self.assertEqual(rights["permission_status"], "not_obtained")
        self.assertFalse(self.source["product_import_allowed"])

    def test_provenance_and_technical_review_gaps_are_explicit(self):
        observed = self.source["observed_claims"]
        self.assertIn("various independent sources", observed["data_provenance_statement"])
        self.assertEqual(self.source["applicability"]["technical_review_status"], "not_independently_reviewed")
        self.assertIn("No per-record primary-source citations", " ".join(self.source["limitations"]))
        self.assertIn("no_bulk_extraction", self.source["project_decision"])

    def test_evidence_revision_and_urls_are_pinned(self):
        self.assertEqual(self.source["source_revision"], "terms_legal_revision_2026.01; pages reviewed 2026-11-05")
        urls = {item["url"] for item in self.source["evidence_reviewed"]}
        self.assertEqual(urls, {"https://vag-wiki.com/", "https://vag-wiki.com/terms-of-service"})


if __name__ == "__main__":
    unittest.main()
