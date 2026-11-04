import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "data" / "source-manifests" / "vag-factory-source-register.json"


class ElptsOttsSourceRightsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        manifest = json.loads(REGISTER.read_text(encoding="utf-8"))
        matches = [
            source for source in manifest["sources"]
            if source["source_id"] == "elpts-national-otts-register-public-query"
        ]
        if len(matches) != 1:
            raise AssertionError(f"expected one ELPTS public-register source, got {len(matches)}")
        cls.source = matches[0]

    def test_public_visibility_does_not_grant_bulk_or_offline_reuse(self):
        source = self.source
        self.assertEqual(source["market_scope"], ["RU", "EAEU"])
        self.assertEqual(source["rights"]["data_license_status"], "not_established")
        for key in (
            "commercial_use_allowed",
            "display_allowed",
            "offline_cache_allowed",
            "bulk_reuse_allowed",
            "redistribution_allowed",
        ):
            self.assertEqual(source["rights"][key], "not_established")
        self.assertEqual(source["rights"]["permission_status"], "not_obtained")
        self.assertIs(source["rights"]["permission_required_before_product_import_or_distribution"], True)
        self.assertIn("no scraping", source["project_decision"])
        self.assertIn("offline caching", source["project_decision"])
        self.assertIn("written permission", source["project_decision"])

    def test_otts_sbKts_and_zoets_are_not_collapsed(self):
        source = self.source
        self.assertEqual(set(source["document_types"]), {"OTTS", "OTSH", "SBKTS", "ZOETS", "cancellation_notices"})
        self.assertIn("Do not treat an SBKTS record as an OTTS record", source["limitations"][2])
        self.assertEqual(source["access"]["exact_OTTS_coverage"], "not_established")


if __name__ == "__main__":
    unittest.main()
