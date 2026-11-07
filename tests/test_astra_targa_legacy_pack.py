import csv
import hashlib
import sqlite3
import tempfile
import unittest
from pathlib import Path

from scripts.build_astra_targa_legacy_vag_research_pack import (
    FIELDS,
    HEADER_CHECKS,
    build_database,
    canonical_row_sha256,
    create_schema,
    is_vag_make,
    validate_header,
)

COLUMN_COUNT = 223


def make_header():
    values = [f"field_{index}" for index in range(COLUMN_COUNT)]
    names = {
        0: "Typengenehmigungsnummer",
        1: "Typengenehmigung erteilt",
        6: "01 Fahrzeugart",
        9: "03 Fahrzeugklasse",
        10: "04 Marke",
        11: "04 Typ",
        12: "05 Typ; Variante/Version",
        17: "09 EU-Gesamtgenehmigung",
        26: "18 Getriebe 1",
        59: "25 Motor Marke",
        60: "25 Motor Typ",
        75: "34 Motorkennzeichen",
    }
    for index, value in names.items():
        values[index] = value
    return values


def make_record(make, approval, engine_marking, gearbox):
    row = [""] * COLUMN_COUNT
    row[FIELDS["approval_number"]] = approval
    row[FIELDS["approval_date"]] = "19950918"
    row[FIELDS["vehicle_group"]] = "10"
    row[FIELDS["vehicle_class"]] = "M1"
    row[FIELDS["make"]] = make
    row[FIELDS["type"]] = "A6 Quattro"
    row[FIELDS["variant_version"]] = "C4 / C4B Motor: AEL/103 kW"
    row[FIELDS["gearbox_1"]] = gearbox
    row[FIELDS["gearbox_1_ratio"]] = "4,11"
    row[FIELDS["engine_make"]] = make
    row[FIELDS["engine_type"]] = engine_marking
    row[FIELDS["fuel"]] = "D"
    row[FIELDS["displacement_cc"]] = "2459"
    row[FIELDS["power_kw"]] = "103"
    row[FIELDS["engine_marking"]] = engine_marking
    return row


class AstraTargaLegacyPackTests(unittest.TestCase):
    def test_exact_make_allowlist_does_not_use_fuzzy_matching(self):
        self.assertTrue(is_vag_make("AUDI"))
        self.assertTrue(is_vag_make("vw"))
        self.assertTrue(is_vag_make("ŠKODA"))
        self.assertTrue(is_vag_make("SKODA"))
        self.assertFalse(is_vag_make("Audi AG"))
        self.assertFalse(is_vag_make("Volkswagen Commercial Vehicles"))
        self.assertFalse(is_vag_make("VW Nutzfahrzeuge"))
        self.assertFalse(is_vag_make("AUDI SPORT"))

    def test_published_header_positions_are_checked(self):
        validate_header(make_header())
        header = make_header()
        header[FIELDS["engine_marking"]] = "not the engine marking field"
        with self.assertRaisesRegex(ValueError, "header mismatch"):
            validate_header(header)

    def test_canonical_row_hash_is_stable_and_changes_with_source_values(self):
        row = make_record("AUDI", "1AB701", "AEL", "m6")
        self.assertEqual(canonical_row_sha256(row), canonical_row_sha256(list(row)))
        changed = list(row)
        changed[FIELDS["gearbox_1"]] = "a4"
        self.assertNotEqual(canonical_row_sha256(row), canonical_row_sha256(changed))

    def test_partial_final_batch_is_not_dropped_and_no_pair_table_is_created(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "TG-Automobil.txt"
            database = root / "research.sqlite"
            with source.open("w", encoding="cp1252", newline="") as handle:
                writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
                writer.writerow(make_header())
                writer.writerow(make_record("AUDI", "1AB701", "AEL", "m6"))
                writer.writerow(make_record("VW", "3VW123", "AEL", "m5"))
            source_meta = {
                "file_sha256": "a" * 64,
                "source_revision": "Thu, 30 Jul 2026 09:22:48 GMT",
                "etag": '"133ef745-657d09d960472"',
                "file_size_bytes": source.stat().st_size,
            }
            report = build_database(source, database, source_meta)
            self.assertEqual(report["counts"]["approval_records"], 2)
            self.assertEqual(report["counts"]["engine_marking_candidates"], 2)
            self.assertEqual(report["counts"]["gearbox_classifications"], 2)
            self.assertEqual(report["counts"]["exact_engine_gearbox_pair_rows"], 0)
            self.assertEqual(report["make_counts"], {"AUDI": 1, "VW": 1})
            self.assertEqual(report["sqlite_integrity_check"], "ok")
            db = sqlite3.connect(database)
            names = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            self.assertFalse(any("pair" in name.casefold() for name in names))
            self.assertEqual(db.execute("SELECT count(*) FROM type_approval_records WHERE market_scope='CH'").fetchone()[0], 2)
            self.assertEqual(db.execute("SELECT count(*) FROM source_files").fetchone()[0], 1)
            self.assertEqual(db.execute("SELECT count(*) FROM pack_metadata").fetchone()[0], 15)
            self.assertEqual(db.execute("SELECT value FROM pack_metadata WHERE key='source_file_sha256'").fetchone()[0], "a" * 64)
            self.assertEqual(db.execute("SELECT count(*) FROM type_approval_records WHERE ru_eaeu_applicability_claim<>0").fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT count(*) FROM engine_marking_candidates WHERE candidate_status='unverified_source_engine_marking'").fetchone()[0], 2)
            self.assertEqual(db.execute("SELECT count(*) FROM gearbox_classifications WHERE classification_status='raw_approval_classification_not_vag_gearbox_code'").fetchone()[0], 2)
            db.close()

    def test_schema_rejects_non_ch_and_pair_claims(self):
        db = sqlite3.connect(":memory:")
        create_schema(db)
        with self.assertRaises(sqlite3.IntegrityError):
            db.execute("""
              INSERT INTO type_approval_records(
                source_row_number,source_row_sha256,source_record_locator,source_file_sha256,
                market_scope,approval_number_raw,make_raw,make_normalized,
                applicability_precision,technical_identity_status
              ) VALUES(1,?,'row',?,'RU','1AB','AUDI','AUDI','CH_type_approval_record','candidate')
            """, ("a" * 64, "b" * 64))
        with self.assertRaises(sqlite3.IntegrityError):
            db.execute("""
              INSERT INTO type_approval_records(
                source_row_number,source_row_sha256,source_record_locator,source_file_sha256,
                market_scope,approval_number_raw,make_raw,make_normalized,
                applicability_precision,technical_identity_status,exact_engine_gearbox_pair_claim
              ) VALUES(1,?,'row',?,'CH','1AB','AUDI','AUDI','CH_type_approval_record','candidate',1)
            """, ("a" * 64, "b" * 64))
        db.close()


if __name__ == "__main__":
    unittest.main()
