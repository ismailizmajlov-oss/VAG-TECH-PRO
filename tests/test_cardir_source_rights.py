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

    def test_live_csv_change_is_order_only_and_exact_multiset_is_unchanged(self) -> None:
        probe = self.probe
        self.assertEqual(probe["status"], "observed_unpinned_live_csv_order_change_only")
        self.assertTrue(probe["row_order_changed"])
        self.assertTrue(probe["exact_row_multiset_unchanged"])
        self.assertTrue(probe["exact_vag_subset_unchanged"])
        self.assertEqual(probe["source_rows_added"], 0)
        self.assertEqual(probe["source_rows_removed"], 0)
        self.assertEqual(probe["vag_rows_added"], 0)
        self.assertEqual(probe["vag_rows_removed"], 0)
        self.assertEqual(probe["source_row_count"], 44272)
        self.assertEqual(probe["model_count"], 611)
        self.assertEqual(probe["vag_row_count"], 948)
        self.assertEqual(probe["vag_model_count"], 26)
        self.assertEqual(
            probe["full_row_multiset_sha256"],
            "d147ca79d44472bc049d2dfd600a9a87ac5f1c7db6c2f21fc1b9f0e77fd02a74",
        )
        self.assertEqual(
            probe["vag_row_multiset_sha256"],
            "ded1df125225426b5bfae4377a7309c73453f7f7fc3800babe07633107c8a20b",
        )

    def test_pinned_pack_and_production_boundary_remain_unchanged(self) -> None:
        self.assertEqual(
            self.pack["source_snapshot_sha256"],
            "30f502729f08fa7a061ab0f6c19f62eab6385dea646c15878b8c3430b4b064f4",
        )
        self.assertTrue(self.pack["pinned_snapshot_retained"])
        self.assertFalse(self.entry["data_ingested"])
        self.assertFalse(self.entry["product_import_allowed"])
        self.assertFalse(self.entry["applicability"]["exact_vehicle_fitment"])
        self.assertFalse(self.entry["applicability"]["exact_engine_gearbox_pair"])
        self.assertFalse(self.entry["applicability"]["ru_eaeu"])
        self.assertEqual(self.entry["market_scope"], ["UNKNOWN"])

    def test_pinned_order_only_refresh_requires_new_pack_and_keeps_fitment_quarantined(self) -> None:
        probe = self.pack["latest_live_probe"]
        self.assertEqual(probe["live_raw_snapshot_sha256"], "5b82f00adee26d165cc187e27952f9b2d9a2f3e6c6da216f3030b72cacac370a")
        self.assertEqual(probe["full_row_multiset_sha256"], "d147ca79d44472bc049d2dfd600a9a87ac5f1c7db6c2f21fc1b9f0e77fd02a74")
        self.assertEqual(probe["vag_row_multiset_sha256"], "ded1df125225426b5bfae4377a7309c73453f7f7fc3800babe07633107c8a20b")
        self.assertTrue(probe["exact_row_multiset_unchanged"])
        self.assertTrue(probe["exact_vag_subset_unchanged"])
        self.assertEqual(self.pack["latest_snapshot_refresh_status"], "new_exact_source_snapshot_pinned_sqlite_rebuild_pending")
        self.assertEqual(self.entry["data_revision"], "CarDir open-data snapshot 2026-11-09; retrieved 2026-11-10T03:11:09Z; SHA-256 5b82f00adee26d165cc187e27952f9b2d9a2f3e6c6da216f3030b72cacac370a")
        self.assertFalse(self.entry["data_ingested"])
        self.assertFalse(self.entry["product_import_allowed"])
        self.assertEqual(self.entry["market_scope"], ["UNKNOWN"])


if __name__ == "__main__":
    unittest.main()
