#!/usr/bin/env python3
"""Fail-closed tests for the VIN-free vehicle catalog evidence and fitment gates."""
from pathlib import Path
import sqlite3
from contextlib import closing
import tempfile

ROOT = Path(__file__).resolve().parents[1]
VEHICLE_SCHEMA = ROOT / "data/sql/vehicle-catalog.sql"
OTTS_SCHEMA = ROOT / "data/sql/otts-type-approval-evidence.sql"
HASH_A = "a" * 64
HASH_B = "b" * 64

def must_reject(db, sql, params=(), label="operation"):
    try:
        db.execute(sql, params)
    except sqlite3.IntegrityError:
        return
    raise AssertionError(f"{label} unexpectedly accepted")

def insert_evidence(db, source_id, *, claim="engine_transmission_pair",
                    precision="exact_pairing", market="EU", revision="rev-1",
                    digest=HASH_B):
    db.execute("""INSERT INTO vehicle_catalog_evidence
        (source_id,document_id,document_revision,retrieved_at_utc,evidence_locator,
         source_sha256,market_scope,applicability_precision,claim_type)
        VALUES (?,?,?,'2026-11-11T00:00:00Z','document/variant/1',?,?,?,?)""",
        (source_id,"approval-1",revision,digest,market,precision,claim))
    return db.execute("SELECT last_insert_rowid()").fetchone()[0]

def main():
    with tempfile.TemporaryDirectory() as tmp:
        with closing(sqlite3.connect(Path(tmp) / "catalog.sqlite")) as db:
            db.execute("PRAGMA foreign_keys=ON")
            db.executescript(VEHICLE_SCHEMA.read_text(encoding="utf-8"))
            db.executescript(OTTS_SCHEMA.read_text(encoding="utf-8"))

            tables = {r[0] for r in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )}
            required = {
                "vehicle_makes", "vehicle_models", "vehicle_generations",
                "vehicle_variants", "engine_codes", "transmission_codes",
                "vehicle_catalog_sources", "vehicle_catalog_source_rights",
                "vehicle_catalog_evidence", "engine_fitments",
                "transmission_fitments", "powertrain_pair_evidence",
            }
            assert required <= tables, required - tables

            for table in required:
                cols = {r[1].lower() for r in db.execute(f"PRAGMA table_info({table})")}
                assert not any("vin" in c for c in cols), (table, cols)

            db.execute("""INSERT INTO vehicle_catalog_sources
                (source_id,publisher,source_title,source_url,source_version,market_scope,
                 license_status,license_name,redistribution_allowed,reuse_scope,checked_at_utc)
                VALUES ('test','Test','Fixture','https://example.invalid','rev-1','EU',
                        'open_license','CC0-1.0',1,'test fixture','2026-11-11T00:00:00Z')""")
            db.execute("""INSERT INTO vehicle_catalog_source_rights
                (source_id,rights_status,license_name,license_url,license_text_sha256,
                 commercial_use_allowed,display_allowed,offline_cache_allowed,bulk_reuse_allowed,
                 redistribution_allowed,rights_revision,reviewed_at_utc)
                VALUES ('test','approved','CC0-1.0','https://creativecommons.org/publicdomain/zero/1.0/',
                        ?,1,1,1,1,1,'CC0-1.0','2026-11-11T00:00:00Z')""", (HASH_A,))

            db.execute("""INSERT INTO vehicle_makes
                (make_key,display_name,status,created_at_utc)
                VALUES ('volkswagen','Volkswagen','verified','2026-11-11T00:00:00Z')""")
            make_id = db.execute("SELECT make_id FROM vehicle_makes").fetchone()[0]
            db.execute("""INSERT INTO vehicle_models(make_id,model_key,display_name,status)
                VALUES (?, 'fixture-model', 'Fixture Model','verified')""", (make_id,))
            model_id = db.execute("SELECT model_id FROM vehicle_models").fetchone()[0]
            db.execute("""INSERT INTO vehicle_generations
                (model_id,generation_key,market_scope,status)
                VALUES (?, 'fixture-gen','EU','verified')""", (model_id,))
            gen_id = db.execute("SELECT generation_id FROM vehicle_generations").fetchone()[0]
            db.execute("""INSERT INTO vehicle_variants
                (generation_id,variant_key,market_scope,status)
                VALUES (?, 'fixture-variant','EU','verified')""", (gen_id,))
            variant_id = db.execute("SELECT variant_id FROM vehicle_variants").fetchone()[0]
            db.execute("""INSERT INTO engine_codes(engine_code,status) VALUES ('TEST','verified')""")
            engine_id = db.execute("SELECT engine_id FROM engine_codes").fetchone()[0]
            db.execute("""INSERT INTO transmission_codes(transmission_code,status)
                VALUES ('TEST-GEARBOX','verified')""")
            trans_id = db.execute("SELECT transmission_id FROM transmission_codes").fetchone()[0]

            # Missing evidence and unreviewed candidate evidence must both fail.
            must_reject(db,
                "INSERT INTO engine_fitments(variant_id,engine_id,evidence_id) VALUES (?,?,999)",
                (variant_id,engine_id), "missing evidence")
            evidence_id = insert_evidence(db, "test")
            must_reject(db,
                "INSERT INTO engine_fitments(variant_id,engine_id,evidence_id) VALUES (?,?,?)",
                (variant_id,engine_id,evidence_id), "candidate engine fitment")
            must_reject(db,
                "INSERT INTO transmission_fitments(variant_id,transmission_id,evidence_id) VALUES (?,?,?)",
                (variant_id,trans_id,evidence_id), "candidate transmission fitment")
            must_reject(db,
                "INSERT INTO powertrain_pair_evidence(variant_id,engine_id,transmission_id,evidence_id) VALUES (?,?,?,?)",
                (variant_id,engine_id,trans_id,evidence_id), "candidate powertrain pair")
            must_reject(db,
                "UPDATE vehicle_catalog_evidence SET review_status='publication_approved',reviewer_note='skip review',reviewed_at_utc='2026-11-11T00:00:00Z' WHERE evidence_id=?",
                (evidence_id,), "candidate-to-publication bypass")

            # A reviewed row requires source revision, source hash, market, precision and reviewer evidence.
            db.execute("""UPDATE vehicle_catalog_evidence SET review_status='source_checked',
                reviewer_note='Primary document and variant section checked.',
                reviewed_at_utc='2026-11-11T00:01:00Z' WHERE evidence_id=?""", (evidence_id,))
            db.execute("""UPDATE vehicle_catalog_evidence SET review_status='technically_verified',
                reviewer_note='Same approval variant explicitly lists this engine and gearbox pair.',
                reviewed_at_utc='2026-11-11T00:02:00Z' WHERE evidence_id=?""", (evidence_id,))

            db.execute("INSERT INTO engine_fitments(variant_id,engine_id,evidence_id) VALUES (?,?,?)",
                       (variant_id,engine_id,evidence_id))
            db.execute("INSERT INTO transmission_fitments(variant_id,transmission_id,evidence_id) VALUES (?,?,?)",
                       (variant_id,trans_id,evidence_id))
            db.execute("""INSERT INTO powertrain_pair_evidence
                (variant_id,engine_id,transmission_id,evidence_id) VALUES (?,?,?,?)""",
                (variant_id,engine_id,trans_id,evidence_id))

            # Verified evidence is immutable until explicitly demoted.
            must_reject(db,
                "UPDATE vehicle_catalog_evidence SET source_sha256=? WHERE evidence_id=?",
                ("c"*64,evidence_id), "verified evidence mutation")
            db.execute("""UPDATE vehicle_catalog_evidence SET review_status='publication_approved',
                reviewer_note='Second technical review completed.',
                reviewed_at_utc='2026-11-11T00:03:00Z' WHERE evidence_id=?""", (evidence_id,))

            # Rights revocation demotes the evidence and removes active fitment links.
            db.execute("""UPDATE vehicle_catalog_source_rights SET rights_status='restricted',
                display_allowed=0,reviewed_at_utc=NULL WHERE source_id='test'""")
            status = db.execute("SELECT review_status FROM vehicle_catalog_evidence WHERE evidence_id=?",
                                (evidence_id,)).fetchone()[0]
            assert status == "candidate", status
            assert db.execute("SELECT count(*) FROM engine_fitments").fetchone()[0] == 0
            assert db.execute("SELECT count(*) FROM transmission_fitments").fetchone()[0] == 0
            assert db.execute("SELECT count(*) FROM powertrain_pair_evidence").fetchone()[0] == 0

            # A permission-required source cannot be technically verified even with a complete-looking claim.
            db.execute("""INSERT INTO vehicle_catalog_sources
                (source_id,publisher,source_title,source_url,source_version,market_scope,
                 license_status,license_name,redistribution_allowed,reuse_scope,checked_at_utc)
                VALUES ('blocked','Test','Blocked fixture','https://example.invalid','rev-1','EU',
                        'permission_required','Permission required',0,'not reusable','2026-11-11T00:00:00Z')""")
            db.execute("""INSERT INTO vehicle_catalog_source_rights(source_id,rights_status,rights_revision)
                VALUES ('blocked','permission_required','not-reviewed')""")
            blocked_id = insert_evidence(db, "blocked")
            db.execute("""UPDATE vehicle_catalog_evidence SET review_status='source_checked',
                reviewer_note='Source record inspected; reuse permission is absent.',
                reviewed_at_utc='2026-11-11T00:04:00Z' WHERE evidence_id=?""", (blocked_id,))
            must_reject(db,
                "UPDATE vehicle_catalog_evidence SET review_status='technically_verified',
                 reviewer_note='Not allowed without rights.',reviewed_at_utc='2026-11-11T00:05:00Z'
                 WHERE evidence_id=?",
                (blocked_id,), "verification without source rights")

            assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            assert db.execute("PRAGMA foreign_key_check").fetchall() == []
            print("PASS: candidate quarantine, exact-market evidence, rights gate, immutable review, pair integrity and rights revocation")

if __name__ == "__main__":
    main()
