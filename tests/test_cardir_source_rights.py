from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "data" / "source-manifests" / "vag-factory-source-register.json"


class CardirLiveSnapshotProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        register = json.loads(REGISTER.read_text(encoding="utf-8"))
        cls.entry = next(
            item for item in register["sources"]
            if item["source_id"] == "cardir-vag-owner-manual-facts-cc-by-4.0"
        )
        cls.pack = cls.entry["research_pack"]
        cls.probe = cls.pack["latest_live_probe"]

    def test_live_csv_change_is_page_url_only_and_vag_values_are_unchanged(self) -> None:
        probe = self.probe
        self.assertEqual(probe["status"], "reviewed_and_pinned_page_url_only_snapshot_refresh_verified_with_new_sqlite_pack")
        self.assertEqual(probe["live_raw_snapshot_sha256"], "d4b3f7baf3b278d404bedc512e57bc0cf007b1b95114da0ad1d5a13d160800bf")
        self.assertEqual(probe["page_url_changed_brands"], ["Porsche"])
        self.assertEqual(probe["vag_page_url_changed_groups"], 13)
        self.assertEqual(probe["vag_value_or_unit_changed_groups"], 0)
        self.assertEqual(probe["vag_verified_at_changed_groups"], 0)
        self.assertEqual(probe["source_rows_added"], 354)
        self.assertEqual(probe["source_rows_removed"], 354)
        self.assertEqual(probe["source_rows_net_change"], 0)
        self.assertEqual(probe["vag_rows_added"], 13)
        self.assertEqual(probe["vag_rows_removed"], 13)
        self.assertEqual(probe["vag_rows_net_change"], 0)
        self.assertEqual(probe["source_row_count"], 44272)
        self.assertEqual(probe["model_count"], 611)
        self.assertEqual(probe["vag_row_count"], 948)
        self.assertEqual(probe["vag_model_count"], 26)
        self.assertEqual(probe["full_row_multiset_sha256"], "af09d2f806e22e294193f7b50faefc9581743427946be5f770fc671d2209e54f")
        self.assertEqual(probe["vag_row_multiset_sha256"], "6826b00fbab01c356ec52067e9829441e1c12a8b8c31cf981ab71cceb4f068d0")
        self.assertTrue(probe["row_order_changed"])
        self.assertFalse(probe["exact_row_multiset_unchanged"])
        self.assertFalse(probe["exact_vag_subset_unchanged"])
        self.assertTrue(probe["semantic_rows_unchanged_excluding_page_url"])

    def test_pinned_pack_and_production_boundary_remain_unchanged(self) -> None:
        self.assertEqual(self.pack["source_snapshot_sha256"], "d4b3f7baf3b278d404bedc512e57bc0cf007b1b95114da0ad1d5a13d160800bf")
        self.assertTrue(self.pack["pinned_snapshot_retained"])
        self.assertEqual(self.pack["database_sha256"], "8536c2a545115334803733ed037d714e6b80bfdd65236bef7c72108a7c977a76")
        self.assertEqual(self.pack["artifact_sha256"], "750ed171598bd91fc463ccccb078ed2aee839b360adbb91a3e49e4a5bfd34bba")
        self.assertEqual(self.pack["artifact_id"], 13736057820)
        self.assertEqual(self.pack["artifact_run_id"], 42757593051)
        self.assertEqual(self.pack["artifact_run_number"], 126)
        self.assertEqual(self.pack["source_row_hashes_verified"], 948)
        self.assertIs(self.pack["source_row_number_mapping_verified"], True)
        self.assertEqual(self.pack["sqlite_integrity_check"], "ok")
        self.assertEqual(self.pack["foreign_key_violations"], 0)
        self.assertEqual(self.pack["full_row_multiset_sha256"], "af09d2f806e22e294193f7b50faefc9581743427946be5f770fc671d2209e54f")
        self.assertEqual(self.pack["vag_row_multiset_sha256"], "6826b00fbab01c356ec52067e9829441e1c12a8b8c31cf981ab71cceb4f068d0")
        self.assertEqual(self.pack["previous_verified_pack"]["source_snapshot_sha256"], "5b82f00adee26d165cc187e27952f9b2d9a2f3e6c6da216f3030b72cacac370a")
        self.assertFalse(self.entry["data_ingested"])
        self.assertFalse(self.entry["product_import_allowed"])
        self.assertFalse(self.entry["applicability"]["exact_vehicle_fitment"])
        self.assertFalse(self.entry["applicability"]["exact_engine_gearbox_pair"])
        self.assertFalse(self.entry["applicability"]["ru_eaeu"])
        self.assertEqual(self.entry["market_scope"], ["UNKNOWN"])

    def test_pinned_page_url_refresh_requires_new_pack_and_keeps_fitment_quarantined(self) -> None:
        probe = self.pack["latest_live_probe"]
        self.assertEqual(probe["live_raw_snapshot_sha256"], "d4b3f7baf3b278d404bedc512e57bc0cf007b1b95114da0ad1d5a13d160800bf")
        self.assertEqual(probe["previous_pinned_snapshot_sha256"], "5b82f00adee26d165cc187e27952f9b2d9a2f3e6c6da216f3030b72cacac370a")
        self.assertEqual(probe["full_row_multiset_sha256"], "af09d2f806e22e294193f7b50faefc9581743427946be5f770fc671d2209e54f")
        self.assertEqual(probe["vag_row_multiset_sha256"], "6826b00fbab01c356ec52067e9829441e1c12a8b8c31cf981ab71cceb4f068d0")
        self.assertTrue(probe["semantic_rows_unchanged_excluding_page_url"])
        self.assertEqual(probe["retrieved_at_utc"], "2026-11-10T04:43:09.162254+00:00")
        self.assertEqual(self.pack["latest_snapshot_refresh_status"], "verified_research_only_pack_built_for_latest_page_url_refresh_snapshot")
        self.assertEqual(self.entry["data_revision"], "CarDir open-data snapshot 2026-11-09; retrieved 2026-11-10T04:37:02Z; SHA-256 d4b3f7baf3b278d404bedc512e57bc0cf007b1b95114da0ad1d5a13d160800bf")
        self.assertFalse(self.entry["data_ingested"])
        self.assertFalse(self.entry["product_import_allowed"])
        self.assertEqual(self.entry["market_scope"], ["UNKNOWN"])

if __name__ == "__main__":
    unittest.main()
