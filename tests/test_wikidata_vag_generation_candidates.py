import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_wikidata_vag_generation_candidates as builder


class WikidataVagGenerationCandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture_path = ROOT / "tests" / "fixtures" / "wikidata-vag-generation-sample.json"
        cls.fixture = json.loads(cls.fixture_path.read_text(encoding="utf-8"))

    def build_fixture_pack(self, payload=None):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        output = Path(tmp.name) / "pack"
        snapshot = builder.canonical_json(payload or self.fixture)
        manifest = builder.build_pack(snapshot, output)
        return output, manifest

    def test_model_series_members_are_candidates_not_verified_generations(self):
        output, manifest = self.build_fixture_pack()
        verified = builder.verify_pack(output)
        self.assertEqual(verified["pack_id"], manifest["pack_id"])
        self.assertEqual(manifest["counts"]["member_entities"], 1)
        self.assertEqual(manifest["counts"]["model_member_links"], 1)
        self.assertEqual(manifest["counts"]["source_bindings"], 2)
        self.assertEqual(manifest["scope"]["generation_entities"], 1)
        self.assertFalse(manifest["scope"]["generation_verified"])
        self.assertFalse(manifest["scope"]["exact_vehicle_fitment"])
        self.assertEqual(manifest["scope"]["market_scope"], "UNKNOWN")
        self.assertEqual(manifest["scope"]["applicability_precision"], "series_member_candidate")

        db = sqlite3.connect(output / "wikidata-vag-generations.sqlite")
        try:
            row = db.execute(
                """SELECT member_qid,model_qid,member_label_en,member_label_ru,
                          relation_properties_json,manufacturer_relation_status,
                          market_scope,applicability_precision,review_status,
                          generation_verified,exact_vehicle_fitment,
                          engine_code_fitment,transmission_code_fitment,ecu_fitment,
                          dtc_fitment,repair_procedure_fitment,diagnostic_execution_allowed,
                          production_years_inferred,source_record_sha256
                   FROM model_series_member_candidates"""
            ).fetchone()
            self.assertEqual(row[0:4], ("Q20760348", "Q758729", "Audi A4 B9", "Audi A4 B9"))
            self.assertEqual(json.loads(row[4]), ["P179", "P527"])
            self.assertEqual(row[5], "match")
            self.assertEqual(row[6:9], ("UNKNOWN", "series_member_candidate", "candidate"))
            self.assertEqual(row[9:18], (0, 0, 0, 0, 0, 0, 0, 0, 0))
            self.assertEqual(len(row[18]), 64)
            self.assertEqual(db.execute("SELECT count(*) FROM series_member_source_bindings").fetchone()[0], 2)
            self.assertEqual(db.execute("SELECT count(*) FROM series_member_date_statements").fetchone()[0], 4)
            self.assertEqual(db.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            self.assertEqual(db.execute("PRAGMA foreign_key_check").fetchall(), [])
        finally:
            db.close()

    def test_cc0_rights_and_parent_model_provenance_are_retained(self):
        output, manifest = self.build_fixture_pack()
        self.assertEqual(manifest["data_license"], "CC0-1.0")
        self.assertEqual(manifest["rights_status"], "approved_by_published_license")
        for flag in (
            "commercial_use_allowed", "display_allowed", "offline_cache_allowed",
            "bulk_reuse_allowed", "redistribution_allowed"
        ):
            self.assertTrue(manifest[flag])
        self.assertEqual(manifest["parent_model_pack"]["source_revision"], "wikidata-snapshot-fixture")
        self.assertEqual(manifest["parent_model_pack"]["source_snapshot_sha256"], "a" * 64)
        self.assertEqual(manifest["parent_model_pack"]["database_sha256"], "b" * 64)
        self.assertEqual(len(manifest["source_snapshot_sha256"]), 64)
        self.assertEqual(len(manifest["source_query_sha256"]), 64)
        self.assertEqual(len(manifest["database_sha256"]), 64)

    def test_unknown_parent_model_is_rejected(self):
        payload = json.loads(json.dumps(self.fixture))
        payload["results"]["bindings"][0]["model"]["value"] = "http://www.wikidata.org/entity/Q999999"
        with self.assertRaisesRegex(ValueError, "outside the pinned parent pack"):
            builder.parse_snapshot(builder.canonical_json(payload))

    def test_unknown_relationship_property_is_rejected(self):
        payload = json.loads(json.dumps(self.fixture))
        payload["results"]["bindings"][0]["relation"]["value"] = "P999"
        with self.assertRaisesRegex(ValueError, "invalid series relationship"):
            builder.parse_snapshot(builder.canonical_json(payload))

    def test_parent_manufacturer_mismatch_remains_candidate_and_is_flagged(self):
        payload = json.loads(json.dumps(self.fixture))
        for binding in payload["results"]["bindings"]:
            binding["memberManufacturer"]["value"] = "http://www.wikidata.org/entity/Q999"
        output, manifest = self.build_fixture_pack(payload)
        db = sqlite3.connect(output / "wikidata-vag-generations.sqlite")
        try:
            row = db.execute(
                "SELECT manufacturer_relation_status,generation_verified,exact_vehicle_fitment FROM model_series_member_candidates"
            ).fetchone()
            self.assertEqual(row, ("mismatch", 0, 0))
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
