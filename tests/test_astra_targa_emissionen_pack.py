import csv
import sqlite3
import tempfile
import unittest
from pathlib import Path

from scripts.build_astra_targa_emissionen_vag_research_pack import (
    REQUIRED_HEADERS,
    build_database,
    canonical_row_sha256,
    is_vag_make,
    resolve_header_positions,
)

COLUMN_COUNT = 65


def make_header():
    values = [f"field_{i}" for i in range(COLUMN_COUNT)]
    names = {
        0: "TG-Code", 1: "Marke", 2: "Typ", 9: "Getriebe",
        10: "iAchse", 13: "Motormarke", 14: "Motortyp",
        15: "Bauart", 16: "Treibstoff", 19: "Hubraum",
        20: "Leistung", 21: "Leistung_bei_n_min",
        22: "Drehmoment", 23: "Drehmoment_bei_n_min",
        24: "Abgasreinigung", 26: "Antrieb",
        28: "Emissionscode", 59: "Homologationsdatum",
    }
    for index, value in names.items():
        values[index] = value
    return values


def make_row(make, engine, gearbox):
    values = [""] * COLUMN_COUNT
    positions = resolve_header_positions(make_header())
    values[positions["approval_number"]] = "1AB701"
    values[positions["make"]] = make
    values[positions["type"]] = "A6 Quattro"
    values[positions["gearbox"]] = gearbox
    values[positions["final_drive_ratio"]] = "'4.11"
    values[positions["engine_make"]] = "AUDI"
    values[positions["engine_type"]] = engine
    values[positions["engine_construction"]] = "4-Takt / 5 / Reihe-T-DI"
    values[positions["fuel"]] = "D"
    values[positions["displacement_cc"]] = "2459"
    values[positions["power_kw"]] = "103"
    values[positions["power_rpm"]] = "3500"
    values[positions["torque_nm"]] = "290"
    values[positions["torque_rpm"]] = "2500"
    values[positions["emission_control"]] = "K"
    values[positions["drive"]] = "A"
    values[positions["emissions_code"]] = "EURO2"
    values[positions["homologation_date"]] = "19950918"
    return values


class AstraTargaEmissionenPackTests(unittest.TestCase):
    def test_exact_make_filter_and_dynamic_65_column_header(self):
        self.assertTrue(is_vag_make("AUDI"))
        self.assertTrue(is_vag_make("ŠKODA"))
        self.assertTrue(is_vag_make("vw"))
        self.assertFalse(is_vag_make("Audi AG"))
        self.assertFalse(is_vag_make("VW Nutzfahrzeuge"))
        positions = resolve_header_positions(make_header())
        self.assertEqual(positions["approval_number"], 0)
        self.assertEqual(positions["gearbox"], 9)
        self.assertEqual(positions["engine_type"], 14)
        self.assertEqual(positions["homologation_date"], 59)

    def test_required_header_contract_is_not_empty(self):
        self.assertIn("power_rpm", REQUIRED_HEADERS)
        self.assertIn("torque_rpm", REQUIRED_HEADERS)
        self.assertIn("gearbox", REQUIRED_HEADERS)

    def test_database_preserves_source_defined_variant_rows_without_oem_pair_claim(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "emissionen.txt"
            database = root / "emissionen.sqlite"
            with source.open("w", encoding="cp1252", newline="") as handle:
                writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
                writer.writerow(make_header())
                writer.writerow(make_row("AUDI", "AEL", "m6"))
                writer.writerow(make_row("VW", "ABF", "m5"))
                writer.writerow(make_row("VW GROUP", "ABF", "m5"))
            source_meta = {
                "file_sha256": "a" * 64,
                "source_revision": "Thu, 30 Jul 2026 09:22:59 GMT",
                "etag": '"438c3dc-657d09e3d7852"',
                "file_size_bytes": source.stat().st_size,
            }
            report = build_database(source, database, source_meta)
            self.assertEqual(report["counts"]["approval_powertrain_variant_rows"], 2)
            self.assertEqual(report["counts"]["source_defined_variant_link_rows"], 2)
            self.assertEqual(report["counts"]["exact_vag_factory_code_pair_rows"], 0)
            self.assertEqual(report["make_counts"], {"AUDI": 1, "VW": 1})
            self.assertEqual(report["sqlite_integrity_check"], "ok")
            db = sqlite3.connect(database)
            self.assertEqual(db.execute("SELECT count(*) FROM source_files").fetchone()[0], 1)
            self.assertEqual(db.execute("SELECT count(*) FROM pack_metadata").fetchone()[0], 14)
            row = db.execute("""
              SELECT engine_type_raw,gearbox_classification_raw,source_defined_variant_link,
                     exact_vag_factory_code_pair,market_scope,applicability_precision
              FROM approval_powertrain_variant_rows ORDER BY id LIMIT 1
            """).fetchone()
            self.assertEqual(row, ("AEL", "m6", 1, 0, "CH", "CH_type_approval_gearbox_variant_row"))
            names = {item[0] for item in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            self.assertNotIn("engine_gearbox_pairs", names)
            self.assertFalse(any("pair" in name.casefold() for name in names))
            self.assertEqual(db.execute("SELECT count(*) FROM approval_powertrain_variant_rows WHERE ru_eaeu_applicability<>0").fetchone()[0], 0)
            db.close()

    def test_source_row_hash_is_stable(self):
        row = make_row("AUDI", "AEL", "m6")
        self.assertEqual(canonical_row_sha256(row), canonical_row_sha256(list(row)))


if __name__ == "__main__":
    unittest.main()
