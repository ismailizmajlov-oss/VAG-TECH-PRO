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

    def test_batched_snapshot_preserves_each_query_and_result_hash(self):
        payload = json.loads(json.dumps(self.fixture))
        bindings = payload.pop("results")["bindings"]
        batch_query = payload["query"]
        payload["query_batch_size"] = 50
        payload["query"] = "# batch 1/1\n" + batch_query + "\n"
        payload["query_batches"] = [{
            "batch_index": 1,
            "model_qids": ["Q758729"],
            "query_sha256": builder.sha256(batch_query.encode("utf-8")),
            "result_count": len(bindings),
            "results": {"results": {"bindings": bindings}},
            "query": batch_query,
        }]
        output, manifest = self.build_fixture_pack(payload)
        self.assertEqual(manifest["query_batches"], 1)
        self.assertEqual(manifest["query_batch_size"], 50)
        self.assertFalse(manifest["limit_reached"])
        builder.verify_pack(output)

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
        self.assertEqual(manifest["parent_model_pack"]["car_model_series_entities"], 1)
        self.assertEqual(manifest["parent_model_pack"]["car_model_entities"], 0)
        self.assertEqual(manifest["parent_model_pack"]["source_snapshot_sha256"], "a" * 64)
        self.assertEqual(manifest["parent_model_pack"]["database_sha256"], "b" * 64)
        self.assertEqual(len(manifest["source_snapshot_sha256"]), 64)
        self.assertEqual(len(manifest["source_query_sha256"]), 64)
        self.assertEqual(len(manifest["database_sha256"]), 64)

    def test_latest_model_pack_retains_series_entity_types(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pack_dir = root / builder.MODEL_PACK_ROOT / "fixture"
            pack_dir.mkdir(parents=True)
            db_path = pack_dir / "wikidata-vag-taxonomy.sqlite"
            db = sqlite3.connect(db_path)
            try:
                db.execute("""CREATE TABLE vehicle_model_entities (
                    model_qid TEXT, manufacturer_qid TEXT, model_label_en TEXT,
                    model_label_ru TEXT, manufacturer_label_en TEXT, entity_types_json TEXT
                )""")
                db.execute(
                    "INSERT INTO vehicle_model_entities VALUES (?,?,?,?,?,?)",
                    ("Q758729","Q23317","Audi A4","Ауди A4","Audi AG",
                     json.dumps([{"model_type_qid":"Q59773381","model_type_label_en":"car model series","entity_class_qid":"Q59773381"}])),
                )
                db.commit()
            finally:
                db.close()
            parent_manifest = {
                "source_id":"wikidata-vag-model-taxonomy",
                "data_license":"CC0-1.0",
                "built_at_utc":"2026-11-06T00:00:00Z",
                "pack_id":"wikidata-vag-model-taxonomy-cc0-fixture",
                "snapshot_id":"fixture",
                "source_revision":"wikidata-snapshot-fixture",
                "source_snapshot_sha256":"a"*64,
                "database_sha256":builder.sha256(db_path.read_bytes()),
                "counts":{"model_entities":1,"car_model_entities":0,"car_model_series_entities":1},
            }
            (pack_dir / "manifest.json").write_text(json.dumps(parent_manifest), encoding="utf-8")
            manifest, _, models = builder.latest_model_pack(root)
            self.assertEqual(manifest["counts"]["car_model_series_entities"], 1)
            self.assertEqual(models[0]["entity_types"][0]["entity_class_qid"], "Q59773381")

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
