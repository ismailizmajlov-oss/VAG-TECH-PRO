import json
import unittest
from pathlib import Path


class MechanicDBVagDtcPackPolicyTests(unittest.TestCase):
    def test_pinned_odbl_sample_is_candidate_only_and_not_a_repair_database(self):
        root = Path(__file__).resolve().parents[1]
        manifest = json.loads((root / "data/source-manifests/mechanicdb-vag-dtc-sample.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["source_revision"], "c788dfe9ed1517d4cd0be27f5aacb4776abf4864")
        self.assertEqual(manifest["data_license"], "ODbL-1.0")
        self.assertEqual(manifest["rights_status"], "approved_by_published_license")
        self.assertTrue(manifest["display_allowed"])
        self.assertTrue(manifest["cache_allowed"])
        self.assertTrue(manifest["redistribution_allowed"])
        self.assertTrue(manifest["share_alike_required"])
        self.assertEqual(manifest["source_row_counts"]["vag_make_codes"], 2)
        self.assertEqual(len(manifest["selected_records"]["manufacturer_dtc_candidates"]), 2)
        self.assertEqual(manifest["product_policy"]["generic_dtc_rows"], 0)
        self.assertFalse(manifest["product_policy"]["vehicle_fitment_claim"])
        self.assertFalse(manifest["product_policy"]["ecu_fitment_claim"])
        self.assertFalse(manifest["product_policy"]["pr_code_claim"])
        self.assertFalse(manifest["product_policy"]["production_import"])
        self.assertEqual(manifest["product_policy"]["review_status"], "community_reference_unverified")
        self.assertEqual(manifest["product_policy"]["display_status"], "hidden_pending_technical_review")
        self.assertEqual(manifest["product_policy"]["repair_procedure_status"], "community_authored_not_factory_not_verified")
        self.assertFalse(manifest["product_policy"]["oem_part_numbers_included"])
        self.assertEqual(manifest["product_policy"]["market_scope"], "UNKNOWN")
        self.assertEqual(manifest["product_policy"]["applicability_precision"], "manufacturer_make_only_candidate")


if __name__ == "__main__":
    unittest.main()
