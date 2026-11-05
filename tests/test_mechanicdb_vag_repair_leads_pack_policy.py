import json
import unittest
from pathlib import Path

class MechanicDBVagRepairLeadPolicyTests(unittest.TestCase):
    def test_pinned_odbl_sample_keeps_make_candidates_and_community_leads_separate(self):
        root = Path(__file__).resolve().parents[1]
        manifest = json.loads((root / "data/source-manifests/mechanicdb-vag-dtc-sample-repair-leads.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["source_revision"], "c788dfe9ed1517d4cd0be27f5aacb4776abf4864")
        self.assertEqual(manifest["data_license"], "ODbL-1.0")
        self.assertEqual(manifest["rights_status"], "approved_by_published_license")
        self.assertTrue(manifest["display_allowed"])
        self.assertTrue(manifest["cache_allowed"])
        self.assertTrue(manifest["redistribution_allowed"])
        self.assertTrue(manifest["share_alike_required"])
        self.assertEqual(manifest["source_row_counts"]["vag_make_codes"], 2)
        self.assertEqual(manifest["source_row_counts"]["vag_fix_candidates"], 6)
        self.assertEqual(manifest["source_row_counts"]["vag_part_candidates"], 6)
        policy = manifest["product_policy"]
        self.assertEqual(policy["display_status"], "candidate_reference_visible_separate_namespace")
        self.assertEqual(policy["repair_procedure_status"], "community_authored_not_factory_not_verified")
        for key in ("vehicle_fitment_claim", "ecu_fitment_claim", "pr_code_claim", "production_import",
                    "oem_part_numbers_included", "cost_or_labor_estimates_included",
                    "external_part_search_urls_included", "diagnostic_execution_allowed"):
            self.assertFalse(policy[key])
        self.assertEqual(policy["market_scope"], "UNKNOWN")
        self.assertEqual(policy["applicability_precision"], "manufacturer_make_only_candidate")
        self.assertEqual(len(manifest["selected_records"]["manufacturer_dtc_candidates"]), 2)
        self.assertEqual(len(manifest["selected_records"]["community_fix_candidates"]), 6)
        self.assertEqual(len(manifest["selected_records"]["community_part_candidates"]), 6)

if __name__ == "__main__":
    unittest.main()
