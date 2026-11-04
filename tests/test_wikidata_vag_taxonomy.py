from __future__ import annotations
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_wikidata_vag_taxonomy as builder

FIXTURE = ROOT / "tests" / "fixtures" / "wikidata-vag-taxonomy-sample.json"

class WikidataVagTaxonomyTests(unittest.TestCase):
    def test_fixture_builds_cc0_candidate_identity_pack(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "pack"
            manifest = builder.build_pack(FIXTURE.read_bytes(), out, "2026-11-04T00:00:00Z")
            verified = builder.verify_pack(out)
            self.assertEqual(manifest["pack_id"], verified["pack_id"])
            self.assertEqual(manifest["counts"]["model_entities"], 3)
            self.assertEqual(manifest["counts"]["source_bindings"], 3)
            self.assertEqual(manifest["counts"]["manufacturers"], 3)
            self.assertEqual(manifest["data_license"], "CC0-1.0")
            self.assertEqual(manifest["rights_status"], "approved_by_published_license")
            self.assertEqual(manifest["scope"]["market_scope"], "UNKNOWN")
            self.assertEqual(manifest["scope"]["applicability_precision"], "candidate_identity_only")
            self.assertFalse(manifest["scope"]["exact_vehicle_fitment"])
            self.assertFalse(manifest["scope"]["generation_verified"])
            self.assertFalse(manifest["scope"]["engine_code_fitment"])
            self.assertFalse(manifest["scope"]["transmission_code_fitment"])
            self.assertFalse(manifest["scope"]["ecu_fitment"])
            self.assertFalse(manifest["scope"]["dtc_fitment"])
            self.assertFalse(manifest["scope"]["repair_procedure_fitment"])
            self.assertFalse(manifest["scope"]["diagnostic_execution_allowed"])
            self.assertFalse(manifest["scope"]["production_years_inferred"])

    def test_sqlite_has_only_identity_and_provenance_tables(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "pack"
            builder.build_pack(FIXTURE.read_bytes(), out, "2026-11-04T00:00:00Z")
            db = sqlite3.connect(f"file:{out / 'wikidata-vag-taxonomy.sqlite'}?mode=ro", uri=True)
            try:
                self.assertEqual(db.execute("PRAGMA integrity_check").fetchone()[0], "ok")
                self.assertEqual(db.execute("PRAGMA foreign_key_check").fetchall(), [])
                self.assertEqual(db.execute("SELECT count(*) FROM vehicle_model_entities").fetchone()[0], 3)
                self.assertEqual(db.execute("SELECT count(*) FROM source_bindings").fetchone()[0], 3)
                self.assertEqual(db.execute("SELECT count(*) FROM model_date_statements").fetchone()[0], 3)
                self.assertEqual(db.execute("SELECT count(*) FROM vehicle_model_entities WHERE market_scope!='UNKNOWN' OR review_status!='candidate' OR exact_vehicle_fitment!=0 OR generation_verified!=0").fetchone()[0], 0)
                forbidden = db.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name IN ('engines','transmissions','ecu','dtc','repair_procedures','wiring_diagrams','pinouts','torque_specs','adaptations')").fetchone()[0]
                self.assertEqual(forbidden, 0)
            finally:
                db.close()

    def test_provenance_hashes_and_cc0_rights_are_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "pack"
            manifest = builder.build_pack(FIXTURE.read_bytes(), out, "2026-11-04T00:00:00Z")
            db = sqlite3.connect(f"file:{out / 'wikidata-vag-taxonomy.sqlite'}?mode=ro", uri=True)
            try:
                rows = db.execute("SELECT model_qid,manufacturer_qid,source_record_sha256,source_revision,source_snapshot_sha256,source_query_sha256 FROM vehicle_model_entities").fetchall()
                self.assertTrue(all(len(row[2]) == 64 for row in rows))
                self.assertTrue(all(row[3] == manifest["source_revision"] for row in rows))
                self.assertTrue(all(row[4] == manifest["source_snapshot_sha256"] for row in rows))
                self.assertTrue(all(row[5] == manifest["source_query_sha256"] for row in rows))
                rights = db.execute("SELECT license_id,rights_status,commercial_use_allowed,display_allowed,offline_cache_allowed,bulk_reuse_allowed,redistribution_allowed,attribution_required,attribution_recommended,share_alike_required FROM source_registry").fetchone()
                self.assertEqual(rights, ("CC0-1.0","approved_by_published_license",1,1,1,1,1,0,1,0))
            finally:
                db.close()

    def test_snapshot_parser_rejects_unapproved_manufacturer_and_empty_results(self):
        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        payload["results"]["bindings"][0]["manufacturerLabel"]["value"] = "Autoevolution"
        with self.assertRaises(ValueError):
            builder.parse_snapshot(json.dumps(payload).encode("utf-8"))
        with self.assertRaises(ValueError):
            builder.parse_snapshot(b'{"results":{"bindings":[]}}')

if __name__ == "__main__":
    unittest.main()
