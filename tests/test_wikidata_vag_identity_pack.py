from __future__ import annotations

import importlib.util
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_wikidata_vag_identity_pack.py"
SNAPSHOT = ROOT / "data" / "source-snapshots" / "wikidata-vag-identity-cc0.json"
LOCK = ROOT / "data" / "source-manifests" / "wikidata-vag-identity-cc0.lock.json"

spec = importlib.util.spec_from_file_location("wikidata_pack", SCRIPT)
MODULE = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(MODULE)


class WikidataIdentityPackTests(unittest.TestCase):
    def test_builds_pinned_cc0_candidate_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "pack"
            manifest = MODULE.build_pack(SNAPSHOT, LOCK, output)
            disk_manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(disk_manifest, manifest)
            self.assertEqual(manifest["pack_id"], "wikidata-vag-identity-cc0")
            self.assertEqual(manifest["data_license"], "CC0-1.0")
            self.assertEqual(manifest["counts"]["total"], 20)
            self.assertEqual(manifest["market_scope"], "UNKNOWN")
            self.assertFalse(manifest["exact_vehicle_fitment"])
            self.assertFalse(manifest["engine_fitment"])
            self.assertFalse(manifest["transmission_fitment"])
            self.assertFalse(manifest["ecu_fitment"])
            self.assertEqual(len(manifest["database_sha256"]), 64)
            self.assertEqual(len(manifest["source_snapshot_sha256"]), 64)
            self.assertEqual(len(manifest["source_manifest_sha256"]), 64)
            db = sqlite3.connect(output / "wikidata-vag-identity.sqlite")
            try:
                self.assertEqual(db.execute("PRAGMA integrity_check").fetchone()[0], "ok")
                self.assertEqual(db.execute("SELECT count(*) FROM identity_candidates").fetchone()[0], 20)
                self.assertEqual(db.execute("SELECT count(*) FROM identity_candidates WHERE market_scope!='UNKNOWN'").fetchone()[0], 0)
                self.assertEqual(db.execute("SELECT count(*) FROM identity_candidates WHERE exact_vehicle_fitment!=0 OR engine_fitment!=0 OR transmission_fitment!=0 OR ecu_fitment!=0").fetchone()[0], 0)
                self.assertEqual(db.execute("SELECT count(*) FROM identity_candidates WHERE source_revision_id IS NULL OR source_url=''").fetchone()[0], 0)
            finally:
                db.close()

    def test_does_not_infer_missing_or_ambiguous_year_ranges(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "pack"
            MODULE.build_pack(SNAPSHOT, LOCK, output)
            db = sqlite3.connect(output / "wikidata-vag-identity.sqlite")
            try:
                passat_b8 = db.execute("SELECT year_start,year_end,date_evidence FROM identity_candidates WHERE qid='Q15305561'").fetchone()
                self.assertEqual(passat_b8[:2], (None, None))
                self.assertIn("multiple plant/body-style", passat_b8[2])
                a3_8v = db.execute("SELECT year_start,year_end FROM identity_candidates WHERE qid='Q758738'").fetchone()
                self.assertEqual(a3_8v, (None, None))
                octavia_ii = db.execute("SELECT year_start,year_end FROM identity_candidates WHERE qid='Q392018'").fetchone()
                self.assertEqual(octavia_ii, (2004, None))
            finally:
                db.close()

    def test_rejects_missing_rights_or_promoted_fitment(self):
        snapshot = MODULE.load_json(SNAPSHOT)
        lock = MODULE.load_json(LOCK)
        bad_lock = dict(lock)
        bad_lock["rights"] = dict(lock["rights"], offline_cache_allowed=False)
        with self.assertRaisesRegex(ValueError, "offline_cache_allowed"):
            MODULE.validate_snapshot(snapshot, bad_lock)
        bad_snapshot = json.loads(json.dumps(snapshot))
        bad_snapshot["records"][0]["engine_fitment"] = True
        with self.assertRaisesRegex(ValueError, "engine_fitment"):
            MODULE.validate_snapshot(bad_snapshot, lock)

    def test_rejects_duplicate_qids_and_revision_mismatch(self):
        snapshot = MODULE.load_json(SNAPSHOT)
        lock = MODULE.load_json(LOCK)
        duplicate = json.loads(json.dumps(snapshot))
        duplicate["records"].append(dict(duplicate["records"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate Wikidata QID"):
            MODULE.validate_snapshot(duplicate, lock)
        wrong_revision = json.loads(json.dumps(snapshot))
        wrong_revision["records"][0]["source_url"] = "https://www.wikidata.org/wiki/Q1361914"
        with self.assertRaisesRegex(ValueError, "Source URL/revision mismatch"):
            MODULE.validate_snapshot(wrong_revision, lock)


if __name__ == "__main__":
    unittest.main()
