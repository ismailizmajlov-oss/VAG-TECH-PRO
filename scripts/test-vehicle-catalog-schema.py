#!/usr/bin/env python3
"""Smoke tests for the VIN-free VAG vehicle catalog SQLite schema."""
from pathlib import Path
import sqlite3
from contextlib import closing
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "data/sql/vehicle-catalog.sql"

def main():
    with tempfile.TemporaryDirectory() as tmp:
        with closing(sqlite3.connect(Path(tmp) / "catalog.sqlite")) as db:
            db.execute("PRAGMA foreign_keys=ON")
            db.executescript(SCHEMA.read_text(encoding="utf-8"))

            tables = {r[0] for r in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )}
            required = {
                "vehicle_makes", "vehicle_models", "vehicle_generations",
                "vehicle_variants", "engine_codes", "transmission_codes",
                "vehicle_catalog_sources", "vehicle_catalog_evidence",
                "engine_fitments", "transmission_fitments", "powertrain_pair_evidence",
            }
            assert required <= tables, required - tables

            # Schema is explicitly VIN-free.
            for table in required:
                cols = {r[1].lower() for r in db.execute(f"PRAGMA table_info({table})")}
                assert not any("vin" in c for c in cols), (table, cols)

            db.execute("""INSERT INTO vehicle_catalog_sources
                (source_id,publisher,source_title,source_url,market_scope,
                 license_status,redistribution_allowed,reuse_scope,checked_at_utc)
                VALUES ('test','Test','Fixture','https://example.invalid','EU',
                        'open_license',1,'test only','2026-11-03T00:00:00Z')""")
            db.execute("""INSERT INTO vehicle_makes
                (make_key,display_name,created_at_utc)
                VALUES ('volkswagen','Volkswagen','2026-11-03T00:00:00Z')""")
            make_id = db.execute("SELECT make_id FROM vehicle_makes").fetchone()[0]
            db.execute("""INSERT INTO vehicle_models(make_id,model_key,display_name)
                VALUES (?, 'fixture-model', 'Fixture Model')""", (make_id,))
            model_id = db.execute("SELECT model_id FROM vehicle_models").fetchone()[0]
            db.execute("""INSERT INTO vehicle_generations
                (model_id,generation_key,market_scope) VALUES (?, 'fixture-gen','EU')""", (model_id,))
            gen_id = db.execute("SELECT generation_id FROM vehicle_generations").fetchone()[0]
            db.execute("""INSERT INTO vehicle_variants
                (generation_id,variant_key,market_scope) VALUES (?, 'fixture-variant','EU')""", (gen_id,))
            variant_id = db.execute("SELECT variant_id FROM vehicle_variants").fetchone()[0]
            db.execute("""INSERT INTO engine_codes(engine_code) VALUES ('TEST')""")
            engine_id = db.execute("SELECT engine_id FROM engine_codes").fetchone()[0]
            db.execute("""INSERT INTO transmission_codes(transmission_code) VALUES ('TEST-GEARBOX')""")
            trans_id = db.execute("SELECT transmission_id FROM transmission_codes").fetchone()[0]

            # Unproven fitment cannot be inserted.
            try:
                db.execute("INSERT INTO engine_fitments(variant_id,engine_id,evidence_id) VALUES (?,?,999)", (variant_id,engine_id))
                raise AssertionError("missing evidence unexpectedly accepted")
            except sqlite3.IntegrityError:
                pass

            db.execute("""INSERT INTO vehicle_catalog_evidence
                (source_id,document_id,retrieved_at_utc,evidence_locator,claim_type)
                VALUES ('test','fixture','2026-11-03T00:00:00Z','table 1','engine_transmission_pair')""")
            evidence_id = db.execute("SELECT evidence_id FROM vehicle_catalog_evidence").fetchone()[0]
            db.execute("INSERT INTO engine_fitments(variant_id,engine_id,evidence_id) VALUES (?,?,?)",
                       (variant_id,engine_id,evidence_id))
            db.execute("INSERT INTO transmission_fitments(variant_id,transmission_id,evidence_id) VALUES (?,?,?)",
                       (variant_id,trans_id,evidence_id))
            db.execute("""INSERT INTO powertrain_pair_evidence
                (variant_id,engine_id,transmission_id,evidence_id) VALUES (?,?,?,?)""",
                       (variant_id,engine_id,trans_id,evidence_id))

            # Explicitly unlicensed source cannot publish.
            db.execute("""UPDATE vehicle_catalog_sources SET redistribution_allowed=0,
                license_status='proprietary' WHERE source_id='test'""")
            try:
                db.execute("""UPDATE vehicle_catalog_evidence SET review_status='publication_approved'
                    WHERE evidence_id=?""", (evidence_id,))
                raise AssertionError("unlicensed publication unexpectedly accepted")
            except sqlite3.IntegrityError:
                pass

            assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            assert db.execute("PRAGMA foreign_key_check").fetchall() == []
            db.close()  # Windows cannot remove the temporary SQLite file while the handle is open.
            print("PASS: schema, VIN-free columns, evidence gates, pair gate, rights gate, integrity")

if __name__ == "__main__":
    main()
