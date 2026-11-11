#!/usr/bin/env python3
"""Regression tests for licensed, descriptor-only EAEU OTTS SQLite evidence."""
from pathlib import Path
import sqlite3
from contextlib import closing
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BASE_SCHEMA = ROOT / "data/sql/vehicle-catalog.sql"
OTTS_SCHEMA = ROOT / "data/sql/otts-type-approval-evidence.sql"
NOW = "2026-11-03T00:00:00Z"
H_LICENSE = "a" * 64
H_SOURCE = "b" * 64
H_RECORD = "c" * 64
H_DOCUMENT = "d" * 64


def expect_integrity_error(db, operation, label):
    try:
        operation()
    except sqlite3.IntegrityError:
        return
    raise AssertionError(f"{label}: operation unexpectedly succeeded")


def insert_source(db, source_id, license_status, redistribution_allowed):
    db.execute(
        """INSERT INTO vehicle_catalog_sources
           (source_id,publisher,source_title,source_url,market_scope,
            license_status,redistribution_allowed,reuse_scope,checked_at_utc)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (source_id, "Test fixture only", "Synthetic fixture",
         "https://example.invalid/source", "RU", license_status,
         redistribution_allowed, "synthetic test fixture only", NOW),
    )


def insert_rights(db, source_id, *, pdf_allowed=0, structured_allowed=1, status="approved"):
    db.execute(
        """INSERT INTO vehicle_catalog_source_rights
           (source_id,rights_status,license_name,license_url,license_text_sha256,
            commercial_use_allowed,display_allowed,offline_cache_allowed,
            bulk_reuse_allowed,store_structured_data_allowed,pdf_redistribution_allowed,
            attribution_required,attribution_text,rights_revision,reviewed_at_utc)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (source_id, status, "CC0-1.0 test fixture",
         "https://creativecommons.org/publicdomain/zero/1.0/",
         H_LICENSE, 1, 1, 1, 1, structured_allowed, pdf_allowed, 0, None,
         "synthetic-rights-fixture-v1", NOW),
    )


def test_structured_data_rights_are_required(db):
    insert_source(db, "no-structured", "open_license", 1)
    expect_integrity_error(
        db,
        lambda: insert_rights(db, "no-structured", structured_allowed=0),
        "structured-data storage right is required for approved OTTS reuse",
    )


def test_structured_data_rights_are_required_on_update(db):
    insert_source(db, "update-no-structured", "open_license", 1)
    insert_rights(db, "update-no-structured")
    expect_integrity_error(
        db,
        lambda: db.execute(
            "UPDATE vehicle_catalog_source_rights SET store_structured_data_allowed=0 WHERE source_id='update-no-structured'"
        ),
        "approved rights cannot drop structured-data storage permission",
    )
    state = db.execute(
        "SELECT rights_status, store_structured_data_allowed FROM vehicle_catalog_source_rights WHERE source_id='update-no-structured'"
    ).fetchone()
    assert state == ("approved", 1), state


def evidence_values(source_id, key, *, market="EAEU", cached=0, precision="type_approval_descriptor"):
    return (
        source_id, "RU", "OTTS", "TEST-OTTS-001", key, "revision-A",
        "EEC-Decision-232-amendment-52", NOW, "2030-01-01", "2035-01-01",
        "Synthetic Manufacturer", "TEST-MAKE", "TEST MODEL", "TEST-TYPE",
        "TEST-BASE", "Synthetic modification", "M1", "TEST-CLASS", "TEST-PLANT",
        "Approval scope fixture; no VINs stored",
        "TEST ENGINE MAKE/TYPE DESCRIPTOR", 1998, "TEST FUEL",
        "TEST ECU MARKING", "TEST PUMP MARKING", "TEST INJECTOR MARKING",
        "TEST TRANSMISSION DESCRIPTOR", "TEST CLUTCH DESCRIPTOR",
        "TEST GEARBOX MAKE/TYPE DESCRIPTOR", 7, "[]",
        "TEST TRANSFER CASE", "[]", "TEST FINAL DRIVE", "[]",
        market, precision, "Annex 14 / page 1 / row 1",
        "https://example.invalid/approval",
        "https://example.invalid/approval.pdf" if cached else None,
        cached, H_DOCUMENT if cached else None, "source-revision-fixture-v1",
        H_SOURCE, H_RECORD, NOW,
    )


def insert_evidence(db, source_id, key, review_status="candidate", **kwargs):
    values = evidence_values(source_id, key, **kwargs)
    columns = """source_id,member_state,approval_document_type,approval_number,
             source_record_key,approval_revision,form_revision,issue_date,
             valid_from,valid_to,manufacturer,make,commercial_name,vehicle_type,
             base_vehicle_or_chassis,modifications,vehicle_category,environmental_class,
             assembly_plant,approval_scope_note,engine_make_type_descriptor,
             engine_displacement_cc,engine_fuel_type,engine_control_unit_marking,
             fuel_pump_marking,injector_marking,transmission_type_descriptor,
             clutch_make_type_descriptor,gearbox_make_type_descriptor,gearbox_gear_count,
             gearbox_ratios_json,transfer_case_type_descriptor,transfer_case_ratios_json,
             final_drive_type_descriptor,final_drive_ratios_json,market_scope,
             applicability_precision,evidence_locator,source_url,document_reference_url,
             document_cached,document_sha256,source_revision,source_snapshot_sha256,
             record_sha256,retrieved_at_utc,review_status"""
    placeholders = ",".join("?" for _ in range(len(values) + 1))
    db.execute(
        f"INSERT INTO eaeu_otts_evidence ({columns}) VALUES ({placeholders})",
        (*values, review_status),
    )



def test_legacy_structured_rights_fail_closed(db):
    """Existing approved rows from pre-v2 databases must not bypass structured-data rights."""
    insert_source(db, "legacy-structured-source", "open_license", 1)
    insert_rights(db, "legacy-structured-source", pdf_allowed=1)
    insert_evidence(db, "legacy-structured-source", "legacy-structured-row", cached=1)
    evidence_id = db.execute(
        "SELECT approval_evidence_id FROM eaeu_otts_evidence WHERE source_record_key='legacy-structured-row'"
    ).fetchone()[0]

    # Simulate a pre-v2 database whose approved rights row acquired the new column
    # with its safe default (0), while old permissive triggers were still installed.
    insert_source(db, "legacy-insert-source", "open_license", 1)
    db.execute("DROP TRIGGER IF EXISTS validate_source_rights_approval_insert")
    db.execute("""CREATE TRIGGER validate_source_rights_approval_insert
        BEFORE INSERT ON vehicle_catalog_source_rights
        WHEN NEW.rights_status='approved'
        BEGIN
          SELECT CASE WHEN NEW.license_name IS NULL OR trim(NEW.license_name)=''
            THEN RAISE(ABORT, 'legacy insert guard fixture') END;
        END;""")
    db.execute("DROP TRIGGER IF EXISTS validate_source_rights_approval_update")
    db.execute("""CREATE TRIGGER validate_source_rights_approval_update
        BEFORE UPDATE ON vehicle_catalog_source_rights
        WHEN NEW.rights_status='approved'
        BEGIN
          SELECT CASE WHEN NEW.license_name IS NULL OR trim(NEW.license_name)=''
            THEN RAISE(ABORT, 'legacy update guard fixture') END;
        END;""")
    db.execute("DROP TRIGGER IF EXISTS demote_otts_after_rights_narrowing")
    db.execute("DROP TRIGGER IF EXISTS demote_otts_after_structured_rights_narrowing_v2")
    db.execute(
        "UPDATE vehicle_catalog_source_rights SET store_structured_data_allowed=0 WHERE source_id='legacy-structured-source'"
    )

    # Re-applying the current schema must add new guards even when legacy triggers/tables exist.
    db.executescript(OTTS_SCHEMA.read_text(encoding="utf-8"))

    expect_integrity_error(
        db,
        lambda: insert_rights(db, "legacy-insert-source", structured_allowed=0),
        "legacy approved-rights insert guard cannot bypass structured-data permission",
    )
    expect_integrity_error(
        db,
        lambda: db.execute(
            "UPDATE vehicle_catalog_source_rights SET rights_revision='legacy-bypass' WHERE source_id='legacy-structured-source'"
        ),
        "legacy approved-rights update guard cannot bypass structured-data permission",
    )

    expect_integrity_error(
        db,
        lambda: insert_evidence(db, "legacy-structured-source", "legacy-bypass-insert"),
        "legacy approved row without structured-data rights cannot import new evidence",
    )
    expect_integrity_error(
        db,
        lambda: db.execute(
            "UPDATE eaeu_otts_evidence SET document_cached=1 WHERE approval_evidence_id=?",
            (evidence_id,),
        ),
        "legacy approved row without structured-data rights cannot add or retain a cache through update",
    )

    db.execute(
        "UPDATE eaeu_otts_evidence SET review_status='source_checked', reviewed_at_utc=?, review_note=? WHERE approval_evidence_id=?",
        (NOW, "Legacy rights row migration fixture inspected.", evidence_id),
    )
    db.execute(
        "UPDATE eaeu_otts_evidence SET review_status='technically_verified', reviewed_at_utc=?, review_note=? WHERE approval_evidence_id=?",
        (NOW, "Descriptor fixture checked; structured-data rights are absent.", evidence_id),
    )
    expect_integrity_error(
        db,
        lambda: db.execute(
            "UPDATE eaeu_otts_evidence SET review_status='publication_approved', reviewed_at_utc=?, review_note=? WHERE approval_evidence_id=?",
            (NOW, "Attempted publication from a legacy rights row.", evidence_id),
        ),
        "legacy approved row without structured-data rights cannot publish",
    )

    # Re-granting the missing right is explicit and reviewable; subsequent revocation
    # must demote publication and clear any cached document reference.
    db.execute(
        "UPDATE vehicle_catalog_source_rights SET store_structured_data_allowed=1 WHERE source_id='legacy-structured-source'"
    )
    db.execute(
        "UPDATE eaeu_otts_evidence SET review_status='publication_approved', reviewed_at_utc=?, review_note=? WHERE approval_evidence_id=?",
        (NOW, "Structured-data permission explicitly restored for this fixture.", evidence_id),
    )
    db.execute(
        "UPDATE vehicle_catalog_source_rights SET rights_status='restricted', store_structured_data_allowed=0 WHERE source_id='legacy-structured-source'"
    )
    state = db.execute(
        "SELECT review_status, document_cached, document_reference_url, document_sha256 FROM eaeu_otts_evidence WHERE approval_evidence_id=?",
        (evidence_id,),
    ).fetchone()
    assert state == ("candidate", 0, None, None), state

def main():
    with tempfile.TemporaryDirectory() as tmp:
        with closing(sqlite3.connect(Path(tmp) / "catalog.sqlite")) as db:
            db.execute("PRAGMA foreign_keys=ON")
            db.executescript(BASE_SCHEMA.read_text(encoding="utf-8"))
            db.executescript(OTTS_SCHEMA.read_text(encoding="utf-8"))

            tables = {row[0] for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )}
            assert {"vehicle_catalog_source_rights", "eaeu_otts_evidence"} <= tables

            columns = {row[1].lower() for row in db.execute("PRAGMA table_info(eaeu_otts_evidence)")}
            assert not any("vin" in name for name in columns), columns
            assert "engine_code" not in columns and "transmission_code" not in columns, columns
            foreign_targets = {row[2] for row in db.execute("PRAGMA foreign_key_list(eaeu_otts_evidence)")}
            assert foreign_targets == {"vehicle_catalog_sources"}, foreign_targets

            # A permission-required FGIS-like source cannot approve rights or accept OTTS rows.
            insert_source(db, "blocked-source", "permission_required", 0)
            expect_integrity_error(
                db,
                lambda: insert_rights(db, "blocked-source"),
                "rights approval for permission-required source",
            )
            expect_integrity_error(
                db,
                lambda: insert_evidence(db, "blocked-source", "blocked-row"),
                "OTTS import from permission-required source",
            )

            # The database cannot accept rows that claim to have been reviewed before review occurs.
            insert_source(db, "licensed-source", "open_license", 1)
            test_structured_data_rights_are_required(db)
            test_structured_data_rights_are_required_on_update(db)
            insert_rights(db, "licensed-source", pdf_allowed=0)
            expect_integrity_error(
                db,
                lambda: insert_evidence(db, "licensed-source", "inserted-as-verified", review_status="technically_verified"),
                "direct insert as technically verified",
            )
            expect_integrity_error(
                db,
                lambda: insert_evidence(db, "licensed-source", "inserted-as-published", review_status="publication_approved"),
                "direct insert as publication approved",
            )

            # Licensed metadata can be stored as a candidate without PDF redistribution rights.
            insert_evidence(db, "licensed-source", "metadata-only-row")
            evidence_id = db.execute(
                "SELECT approval_evidence_id FROM eaeu_otts_evidence WHERE source_record_key='metadata-only-row'"
            ).fetchone()[0]
            # Direct state jumps and review transitions without evidence are rejected.
            expect_integrity_error(
                db,
                lambda: db.execute(
                    "UPDATE eaeu_otts_evidence SET review_status='technically_verified' WHERE approval_evidence_id=?",
                    (evidence_id,),
                ),
                "candidate-to-technical-verification shortcut",
            )
            expect_integrity_error(
                db,
                lambda: db.execute(
                    "UPDATE eaeu_otts_evidence SET review_status='publication_approved' WHERE approval_evidence_id=?",
                    (evidence_id,),
                ),
                "candidate-to-publication shortcut",
            )
            expect_integrity_error(
                db,
                lambda: db.execute(
                    "UPDATE eaeu_otts_evidence SET review_status='source_checked' WHERE approval_evidence_id=?",
                    (evidence_id,),
                ),
                "source check without timestamp and note",
            )
            db.execute(
                "UPDATE eaeu_otts_evidence SET review_status='source_checked', reviewed_at_utc=?, review_note=? WHERE approval_evidence_id=?",
                (NOW, "Approval record and evidence locator checked.", evidence_id),
            )
            db.execute(
                "UPDATE eaeu_otts_evidence SET review_status='technically_verified', reviewed_at_utc=?, review_note=? WHERE approval_evidence_id=?",
                (NOW, "Descriptor fields checked against the cited form; no factory fitment inferred.", evidence_id),
            )
            db.execute(
                "UPDATE eaeu_otts_evidence SET review_status='publication_approved', reviewed_at_utc=?, review_note=? WHERE approval_evidence_id=?",
                (NOW, "Metadata reuse rights and publication scope checked.", evidence_id),
            )

            # Published source facts cannot be silently edited while retaining publication status.
            expect_integrity_error(
                db,
                lambda: db.execute(
                    "UPDATE eaeu_otts_evidence SET commercial_name='Tampered after publication' WHERE approval_evidence_id=?",
                    (evidence_id,),
                ),
                "mutation of published OTTS evidence",
            )

            # A PDF cannot be cached when the license grants metadata rights only.
            expect_integrity_error(
                db,
                lambda: insert_evidence(db, "licensed-source", "cached-pdf-without-rights", cached=1),
                "PDF cache without PDF redistribution rights",
            )
            expect_integrity_error(
                db,
                lambda: db.execute(
                    "UPDATE eaeu_otts_evidence SET document_cached=1, document_reference_url=?, document_sha256=? WHERE approval_evidence_id=?",
                    ("https://example.invalid/approval.pdf", H_DOCUMENT, evidence_id),
                ),
                "PDF cache update without PDF redistribution rights",
            )

            # PDF rights can be granted separately; revoking them demotes records that cache PDFs.
            db.execute(
                "UPDATE vehicle_catalog_source_rights SET pdf_redistribution_allowed=1 WHERE source_id='licensed-source'"
            )
            db.execute(
                "UPDATE eaeu_otts_evidence SET review_status='candidate' WHERE approval_evidence_id=?",
                (evidence_id,),
            )
            db.execute(
                "UPDATE eaeu_otts_evidence SET document_cached=1, document_reference_url=?, document_sha256=? WHERE approval_evidence_id=?",
                ("https://example.invalid/approval.pdf", H_DOCUMENT, evidence_id),
            )
            db.execute(
                "UPDATE eaeu_otts_evidence SET review_status='source_checked', reviewed_at_utc=?, review_note=? WHERE approval_evidence_id=?",
                (NOW, "PDF cache rights and source reference checked.", evidence_id),
            )
            db.execute(
                "UPDATE eaeu_otts_evidence SET review_status='technically_verified', reviewed_at_utc=?, review_note=? WHERE approval_evidence_id=?",
                (NOW, "Descriptor content remains consistent with the cited form.", evidence_id),
            )
            db.execute(
                "UPDATE eaeu_otts_evidence SET review_status='publication_approved', reviewed_at_utc=?, review_note=? WHERE approval_evidence_id=?",
                (NOW, "PDF redistribution rights explicitly checked.", evidence_id),
            )
            db.execute(
                "UPDATE vehicle_catalog_source_rights SET pdf_redistribution_allowed=0 WHERE source_id='licensed-source'"
            )
            status = db.execute(
                "SELECT review_status FROM eaeu_otts_evidence WHERE approval_evidence_id=?",
                (evidence_id,),
            ).fetchone()[0]
            assert status == "candidate", status

            # Metadata-only publication remains possible when PDF rights are not granted.
            db.execute(
                "UPDATE eaeu_otts_evidence SET document_cached=0, document_reference_url=NULL, document_sha256=NULL WHERE approval_evidence_id=?",
                (evidence_id,),
            )
            db.execute("UPDATE eaeu_otts_evidence SET review_status='source_checked', reviewed_at_utc=?, review_note=? WHERE approval_evidence_id=?", (NOW, "Metadata-only source locator and reuse rights checked.", evidence_id))
            db.execute("UPDATE eaeu_otts_evidence SET review_status='technically_verified', reviewed_at_utc=?, review_note=? WHERE approval_evidence_id=?", (NOW, "Metadata-only descriptors reviewed; no PDF or exact vehicle fitment claimed.", evidence_id))
            db.execute(
                "UPDATE eaeu_otts_evidence SET review_status='publication_approved', reviewed_at_utc=?, review_note=? WHERE approval_evidence_id=?",
                (NOW, "Metadata-only publication rights and scope independently checked.", evidence_id),
            )

            # A separately licensed PDF may be cached, but revoking core rights clears its cache reference.
            db.execute(
                "UPDATE vehicle_catalog_source_rights SET pdf_redistribution_allowed=1 WHERE source_id='licensed-source'"
            )
            db.execute(
                "UPDATE eaeu_otts_evidence SET review_status='candidate' WHERE approval_evidence_id=?",
                (evidence_id,),
            )
            db.execute(
                "UPDATE eaeu_otts_evidence SET document_cached=1, document_reference_url=?, document_sha256=? WHERE approval_evidence_id=?",
                ("https://example.invalid/approval.pdf", H_DOCUMENT, evidence_id),
            )
            db.execute(
                "UPDATE eaeu_otts_evidence SET review_status='source_checked', reviewed_at_utc=?, review_note=? WHERE approval_evidence_id=?",
                (NOW, "Cached PDF reference and separate redistribution right checked.", evidence_id),
            )
            db.execute(
                "UPDATE eaeu_otts_evidence SET review_status='technically_verified', reviewed_at_utc=?, review_note=? WHERE approval_evidence_id=?",
                (NOW, "Approval descriptors checked before PDF-backed publication.", evidence_id),
            )
            db.execute(
                "UPDATE eaeu_otts_evidence SET review_status='publication_approved', reviewed_at_utc=?, review_note=? WHERE approval_evidence_id=?",
                (NOW, "PDF redistribution and offline caching rights checked.", evidence_id),
            )
            db.execute(
                "UPDATE vehicle_catalog_source_rights SET offline_cache_allowed=0, rights_status='restricted' WHERE source_id='licensed-source'"
            )
            state = db.execute(
                "SELECT review_status, document_cached, document_reference_url, document_sha256 FROM eaeu_otts_evidence WHERE approval_evidence_id=?",
                (evidence_id,),
            ).fetchone()
            assert state == ("candidate", 0, None, None), state

            # Cache removal remains possible after rights revocation; adding a cache is blocked.
            db.execute(
                "UPDATE eaeu_otts_evidence SET document_cached=0, document_reference_url=NULL, document_sha256=NULL WHERE approval_evidence_id=?",
                (evidence_id,),
            )
            expect_integrity_error(
                db,
                lambda: db.execute(
                    "UPDATE eaeu_otts_evidence SET document_cached=1, document_reference_url=?, document_sha256=? WHERE approval_evidence_id=?",
                    ("https://example.invalid/approval.pdf", H_DOCUMENT, evidence_id),
                ),
                "re-caching PDF after rights revocation",
            )
            db.execute(
                "UPDATE eaeu_otts_evidence SET review_status='source_checked', reviewed_at_utc=?, review_note=? WHERE approval_evidence_id=?",
                (NOW, "Re-review attempted after rights restriction.", evidence_id),
            )
            db.execute(
                "UPDATE eaeu_otts_evidence SET review_status='technically_verified', reviewed_at_utc=?, review_note=? WHERE approval_evidence_id=?",
                (NOW, "Technical descriptors remain unchanged, but reuse rights are restricted.", evidence_id),
            )
            expect_integrity_error(
                db,
                lambda: db.execute(
                    "UPDATE eaeu_otts_evidence SET review_status='publication_approved', reviewed_at_utc=?, review_note=? WHERE approval_evidence_id=?",
                    (NOW, "Attempted publication after rights revocation.", evidence_id),
                ),
                "publication after offline-cache rights revocation",
            )

            # Unknown market cannot be published, even when the source license is valid.
            insert_source(db, "licensed-source-2", "open_license", 1)
            insert_rights(db, "licensed-source-2", pdf_allowed=0)
            insert_evidence(db, "licensed-source-2", "unknown-market-row", market="UNKNOWN")
            unknown_id = db.execute(
                "SELECT approval_evidence_id FROM eaeu_otts_evidence WHERE source_record_key='unknown-market-row'"
            ).fetchone()[0]
            db.execute(
                "UPDATE eaeu_otts_evidence SET review_status='source_checked', reviewed_at_utc=?, review_note=? WHERE approval_evidence_id=?",
                (NOW, "Synthetic unknown-market approval record checked.", unknown_id),
            )
            db.execute(
                "UPDATE eaeu_otts_evidence SET review_status='technically_verified', reviewed_at_utc=?, review_note=? WHERE approval_evidence_id=?",
                (NOW, "Synthetic descriptor fields checked; market remains unknown.", unknown_id),
            )
            expect_integrity_error(
                db,
                lambda: db.execute(
                    "UPDATE eaeu_otts_evidence SET review_status='publication_approved' WHERE approval_evidence_id=?",
                    (unknown_id,),
                ),
                "publication with unknown market",
            )

            test_legacy_structured_rights_fail_closed(db)

            # OTTS descriptors never create or directly link factory engine/gearbox codes.
            assert db.execute("SELECT count(*) FROM engine_codes").fetchone()[0] == 0
            assert db.execute("SELECT count(*) FROM transmission_codes").fetchone()[0] == 0
            assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            assert db.execute("PRAGMA foreign_key_check").fetchall() == []

            print("PASS: OTTS descriptor-only schema, rights gate, PDF cache gate, revocation, market and provenance gates")


if __name__ == "__main__":
    main()
