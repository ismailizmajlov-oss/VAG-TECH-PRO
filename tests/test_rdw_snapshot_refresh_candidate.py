import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / "research-refresh" / "rdw-eu-vag-type-approval-open-data-candidate.json"
SOURCE_ID = "rdw-eu-vag-type-approval-open-data-nl"
PREVIOUS_SNAPSHOT = "896a34b9b8377f2ed20c34d7e0e33b4cf2ce1958e2cdd2b7326ee8c3157b0706"


class RdwSnapshotRefreshCandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(CANDIDATE.read_text(encoding="utf-8"))

    def test_candidate_preserves_previous_snapshot_without_calling_it_current(self):
        manifest = self.manifest
        self.assertEqual(manifest["source_id"], SOURCE_ID)
        self.assertEqual(manifest["market_scope"], ["NL"])
        self.assertEqual(manifest["snapshot"]["status"], "not_downloaded_probe_only")
        self.assertIsNone(manifest["snapshot"]["source_snapshot_sha256"])
        self.assertIsNone(manifest["source_snapshot_sha256"])
        self.assertEqual(manifest["snapshot"]["source_files"], [])
        history = manifest["snapshot_history"]
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["source_snapshot_sha256"], PREVIOUS_SNAPSHOT)
        self.assertEqual(history[0]["status"], "filtered_research_snapshot_acquired")
        self.assertEqual(len(history[0]["source_files"]), 6)
        self.assertEqual(manifest["snapshot_refresh"]["previous_snapshot_sha256"], PREVIOUS_SNAPSHOT)
        self.assertEqual(manifest["snapshot_refresh"]["status"], "pending_candidate_reacquisition_and_review")

    def test_latest_probe_is_exact_scope_only_and_never_promotes_engine_gearbox_pair(self):
        probe = self.manifest["latest_probe"]
        self.assertEqual(probe["workflow_run_number"], 44)
        self.assertEqual(probe["probe_status"], "schema_and_exact_scope_verified")
        self.assertEqual(probe["market_scope"], ["NL"])
        self.assertEqual(probe["approval_scope_key"]["typegoedkeuringsnummer"], "e1*2018/858*00403*07")
        self.assertEqual(probe["approval_scope_key"]["variant"], "ACDUCAX0")
        self.assertEqual(probe["approval_scope_key"]["uitvoering"], "FD6FD6DD002PR4VNB50OO")
        self.assertEqual(probe["matched_rows"]["tgk_drive"]["motorcode"], "DUC")
        self.assertEqual(probe["matched_rows"]["tgk_gearbox"]["codetypeversnellingsbak"], "A")
        self.assertFalse(probe["field_semantics"]["motorcode_is_confirmed_vag_factory_engine_code"])
        self.assertFalse(probe["field_semantics"]["codetypeversnellingsbak_is_confirmed_vag_gearbox_code"])
        self.assertFalse(probe["field_semantics"]["engine_gearbox_pair_claim"])
        self.assertFalse(probe["field_semantics"]["generation_inferred"])
        self.assertFalse(probe["field_semantics"]["model_year_inferred"])
        self.assertIsNone(probe["source_snapshot_sha256"])
        self.assertEqual(probe["source_snapshot_status"], "probe_only_no_full_snapshot")
        self.assertFalse(probe["product_import_allowed"])
        self.assertFalse(probe["data_ingested"])
        self.assertFalse(probe["ru_eaeu_applicability"])

    def test_refresh_candidate_retains_cc0_rights_but_is_not_product_import_permission(self):
        rights = self.manifest["rights"]
        self.assertEqual(rights["rights_status"], "approved_by_published_CC0_license")
        for key in ("commercial_use_allowed", "display_allowed", "offline_cache_allowed", "bulk_reuse_allowed", "redistribution_allowed"):
            self.assertIs(rights[key], True)
        self.assertFalse(self.manifest["data_ingested"])
        self.assertFalse(self.manifest["import_policy"]["production_import"])
        self.assertFalse(self.manifest["import_policy"]["ru_eaeu_applicability"])
        self.assertFalse(self.manifest["applicability_policy"]["production_fitment"])
        self.assertFalse(self.manifest["applicability_policy"]["exact_engine_gearbox_pair"])
        self.assertFalse(self.manifest["applicability_policy"]["ru_eaeu_applicability"])


if __name__ == "__main__":
    unittest.main()
