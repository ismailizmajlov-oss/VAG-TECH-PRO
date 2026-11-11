from __future__ import annotations
import json
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REGISTER=ROOT/"data"/"source-manifests"/"vag-factory-source-register.json"
class CardirLiveSnapshotProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        register=json.loads(REGISTER.read_text(encoding="utf-8"))
        cls.entry=next(item for item in register["sources"] if item["source_id"]=="cardir-vag-owner-manual-facts-cc-by-4.0")
        cls.pack=cls.entry["research_pack"]; cls.probe=cls.pack["latest_live_probe"]
    def test_live_csv_change_is_page_url_only_and_vag_values_are_unchanged(self):
        p=self.probe
        self.assertEqual(p["status"],"reviewed_live_source_snapshot_page_url_only_research_pack_rebuild_verified")
        self.assertEqual(p["live_raw_snapshot_sha256"],"902adb1ea1c20eeb98f803a12ffb787a5d082fb184f914091ff8e79bc67ccbbb")
        self.assertEqual(p["source_file_bytes"],15179458)
        self.assertEqual(p["page_url_changed_groups"],126); self.assertEqual(p["page_url_changed_rows"],252)
        self.assertEqual(p["vag_page_url_changed_groups"],13); self.assertEqual(p["vag_page_url_changed_rows"],26)
        self.assertEqual(p["vag_page_url_changed_brands"],["Skoda"])
        self.assertEqual(p["vag_value_or_unit_changed_groups"],0)
        self.assertEqual(p["source_rows_added"],252); self.assertEqual(p["source_rows_removed"],252); self.assertEqual(p["source_rows_net_change"],0)
        self.assertEqual(p["vag_rows_added"],13); self.assertEqual(p["vag_rows_removed"],13); self.assertEqual(p["vag_rows_net_change"],0)
        self.assertEqual(p["source_row_count"],44272); self.assertEqual(p["model_count"],611)
        self.assertEqual(p["vag_row_count"],948); self.assertEqual(p["vag_model_count"],26)
        self.assertEqual(p["full_row_multiset_sha256"],"c84a7c2add81f5400234a608b4f0ea1669fead4434779f26cf29ef341cc43b5f")
        self.assertEqual(p["vag_row_multiset_sha256"],"af5102dba4f010cb0909f7a91a3f9cbc1efd692e1e298600946fdd94c9204dca")
        self.assertEqual(p["source_rows_multiset_excluding_page_url_sha256"],"9a4eb1b268758404bced45802070d77bdfff5d386aeec10d3c1cafaf4d9d0eec")
        self.assertEqual(p["vag_rows_multiset_excluding_page_url_sha256"],"8033e6628dca374804fb0282c47b12d315be136a155ee6c3e17e1244984a3a3")
        self.assertTrue(p["row_order_changed"]); self.assertTrue(p["semantic_rows_unchanged_excluding_page_url"])
        self.assertFalse(p["exact_row_multiset_unchanged"]); self.assertTrue(p["exact_vag_values_unchanged"])
        self.assertTrue(p["exact_vag_subset_unchanged_except_page_url"]); self.assertEqual(p["non_page_url_field_changes"],0)
    def test_latest_live_probe_did_not_downgrade_newer_pinned_pack(self):
        attempt=self.pack["latest_live_probe_attempt"]
        self.assertEqual(attempt["status"],"live_endpoint_returned_previously_verified_older_snapshot_pinned_newer_pack_retained")
        self.assertEqual(attempt["live_raw_snapshot_sha256"],"d4b3f7baf3b278d404bedc512e57bc0cf007b1b95114da0ad1d5a13d160800bf")
        self.assertEqual(attempt["source_file_bytes"],15178035)
        self.assertEqual(attempt["source_rows"],44272); self.assertEqual(attempt["source_models"],611)
        self.assertEqual(attempt["vag_rows"],948); self.assertEqual(attempt["vag_models"],26)
        self.assertEqual(attempt["full_row_multiset_sha256"],"af09d2f806e22e294193f7b50faefc9581743427946be5f770fc671d2209e54f")
        self.assertEqual(attempt["vag_row_multiset_sha256"],"6826b00fbab01c356ec52067e9829441e1c12a8b8c31cf981ab71cceb4f068d0")
        self.assertTrue(attempt["exact_snapshot_previously_verified"])
        self.assertEqual(attempt["previous_verified_pack_run_number"],126)
        self.assertEqual(attempt["current_pinned_snapshot_sha256"],"902adb1ea1c20eeb98f803a12ffb787a5d082fb184f914091ff8e79bc67ccbbb")
        self.assertEqual(attempt["current_pinned_pack_run_number"],145)

    def test_current_pack_is_integrated_read_only_in_desktop_without_production_promotion(self):
        self.assertEqual(self.pack["status"],"verified_research_only")
        self.assertEqual(self.pack["pack_build_status"],"verified_research_only")
        self.assertTrue(self.pack["research_pack_current"])
        self.assertTrue(self.pack["research_database_included_in_desktop"])
        self.assertEqual(self.pack["source_snapshot_sha256"],"902adb1ea1c20eeb98f803a12ffb787a5d082fb184f914091ff8e79bc67ccbbb")
        self.assertEqual(self.pack["artifact_id"],13740955733); self.assertEqual(self.pack["artifact_run_number"],145)
        self.assertEqual(self.pack["database_sha256"],"20b5f84ec5e265ea7455cdfa149bf357864d4c9d7571933d65d4f75d80025b4f")
        self.assertEqual(self.pack["source_row_hashes_verified"],948); self.assertTrue(self.pack["source_row_number_mapping_verified"])
        self.assertEqual(self.pack["sqlite_integrity_check"],"ok"); self.assertEqual(self.pack["foreign_key_violations"],0)
        self.assertEqual(self.pack["desktop_integration_status"],"verified_read_only_research_pack_integrated_in_offline_desktop")
        evidence=self.pack["desktop_integration_evidence"]
        self.assertEqual(evidence["workflow_run_id"],42964628461)
        self.assertEqual(evidence["successful_step"],"Integrate CarDir VAG reference facts into offline desktop")
        self.assertFalse(evidence["product_database_imported"])
        self.assertFalse(evidence["native_windows_10_11_verified"])
        self.assertEqual(self.pack["previous_verified_pack"]["artifact_run_number"],126)
        self.assertEqual(self.pack["previous_desktop_lifecycle_evidence"]["run_number"],1208)
        self.assertIsNone(self.pack["desktop_lifecycle_evidence"])
        self.assertFalse(self.entry["data_ingested"]); self.assertFalse(self.entry["product_import_allowed"])
        self.assertFalse(self.entry["applicability"]["exact_vehicle_fitment"])
        self.assertFalse(self.entry["applicability"]["exact_engine_gearbox_pair"])
        self.assertFalse(self.entry["applicability"]["ru_eaeu"])
        self.assertEqual(self.entry["market_scope"],["UNKNOWN"])
if __name__=="__main__": unittest.main()
