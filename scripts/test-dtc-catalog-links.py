#!/usr/bin/env python3
"""Integration test for VIN-free DTC-to-vehicle applicability links."""
from pathlib import Path
import sqlite3
from contextlib import closing
import tempfile

ROOT = Path(__file__).resolve().parents[1]

def main():
    with tempfile.TemporaryDirectory() as tmp:
        with closing(sqlite3.connect(Path(tmp) / "integration.sqlite")) as db:
            db.execute("PRAGMA foreign_keys=ON")
            for rel in ("data/sql/oem-dtc-index.sql",
                        "data/sql/vehicle-catalog.sql",
                        "data/sql/dtc-catalog-links.sql"):
                db.executescript((ROOT / rel).read_text(encoding="utf-8"))

            now = "2026-11-03T00:00:00Z"
            db.execute("""INSERT INTO source_documents
                (source_id,publisher,document_id,document_type,revision,market_scope,
                 license_status,reuse_scope,redistribution_allowed,retrieved_at_utc)
                VALUES ('fixture','Fixture Publisher','DOC-1','dtc_table','1','RU',
                        'open_license','test fixture',1,?)""", (now,))
            source_doc = db.execute("SELECT source_document_id FROM source_documents").fetchone()[0]
            db.execute("""INSERT INTO oem_dtc_index
                (dtc_code,dtc_namespace,manufacturer,market_scope,source_document_id,
                 evidence_locator,applicability_level,source_claim_hash,created_at_utc)
                VALUES ('P1234','manufacturer_specific_vag','VOLKSWAGEN','RU',?,
                        'page 1 table 1','exact_ecu_hw_sw',?,?)""",
                (source_doc, "a"*64, now))
            dtc_id = db.execute("SELECT oem_dtc_id FROM oem_dtc_index").fetchone()[0]

            db.execute("""INSERT INTO vehicle_catalog_sources
                (source_id,publisher,source_title,source_url,market_scope,license_status,
                 redistribution_allowed,reuse_scope,checked_at_utc)
                VALUES ('fixture','Fixture','Fixture','https://example.invalid','RU',
                        'open_license',1,'test fixture',?)""", (now,))
            db.execute("""INSERT INTO vehicle_makes(make_key,display_name,created_at_utc)
                VALUES ('vw','Volkswagen',?)""", (now,))
            make_id = db.execute("SELECT make_id FROM vehicle_makes").fetchone()[0]
            db.execute("INSERT INTO vehicle_models(make_id,model_key,display_name) VALUES (?, 'golf','Golf')",
                       (make_id,))
            model_id = db.execute("SELECT model_id FROM vehicle_models").fetchone()[0]
            db.execute("""INSERT INTO vehicle_generations(model_id,generation_key,market_scope)
                VALUES (?, 'fixture-gen','RU')""", (model_id,))
            gen_id = db.execute("SELECT generation_id FROM vehicle_generations").fetchone()[0]
            db.execute("""INSERT INTO vehicle_variants(generation_id,variant_key,market_scope)
                VALUES (?, 'fixture-variant','RU')""", (gen_id,))
            variant_id = db.execute("SELECT variant_id FROM vehicle_variants").fetchone()[0]

            db.execute("""INSERT INTO vehicle_catalog_evidence
                (source_id,document_id,retrieved_at_utc,evidence_locator,claim_type,review_status)
                VALUES ('fixture','DOC-2',?,'page 2 table 3','dtc_applicability','technically_verified')""",
                (now,))
            evidence_id = db.execute("SELECT evidence_id FROM vehicle_catalog_evidence").fetchone()[0]
            db.execute("""INSERT INTO oem_dtc_vehicle_applicability
                (oem_dtc_id,variant_id,evidence_id,market_scope,applicability_level)
                VALUES (?, ?, ?, 'RU', 'variant_only')""", (dtc_id, variant_id, evidence_id))

            db.execute("""INSERT INTO vehicle_catalog_evidence
                (source_id,document_id,retrieved_at_utc,evidence_locator,claim_type,review_status)
                VALUES ('fixture','DOC-3',?,'page 3','generation','technically_verified')""", (now,))
            wrong_evidence = db.execute("SELECT max(evidence_id) FROM vehicle_catalog_evidence").fetchone()[0]
            try:
                db.execute("""INSERT INTO oem_dtc_vehicle_applicability
                    (oem_dtc_id,variant_id,evidence_id,market_scope,applicability_level)
                    VALUES (?, ?, ?, 'RU', 'variant_only')""", (dtc_id, variant_id, wrong_evidence))
                raise AssertionError("wrong evidence type unexpectedly accepted")
            except sqlite3.IntegrityError:
                pass

            assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            assert db.execute("PRAGMA foreign_key_check").fetchall() == []
            assert db.execute("SELECT count(*) FROM oem_dtc_vehicle_applicability").fetchone()[0] == 1
            print("PASS: DTC bridge, explicit applicability evidence, FK and integrity guards")

if __name__ == "__main__":
    main()
