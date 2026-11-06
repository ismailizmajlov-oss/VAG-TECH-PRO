from __future__ import annotations

import importlib.util
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location(
    "build_rdw_vag_type_approval_pack",
    ROOT / "scripts" / "build_rdw_vag_type_approval_pack.py",
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def fixture_rows():
    key = {
        "typegoedkeuringsnummer": "e1*2018/858*00403*07",
        "variant": "ACDUCAX0",
        "version": "FD6FD6DD002PR4VNB50OO",
        "revision": "0",
    }
    registration = {
        "merk": "VOLKSWAGEN",
        "handelsbenaming": "TAYRON",
        "typegoedkeuringsnummer": key["typegoedkeuringsnummer"],
        "variant": key["variant"],
        "uitvoering": key["version"],
        "volgnummer_wijziging_eu_typegoedkeuring": key["revision"],
        "voertuigsoort": "Personenauto",
        "cilinderinhoud": "1498",
        "aantal_cilinders": "4",
    }
    drive = {
        "typegoedkeuringsnummer": key["typegoedkeurungsnummer"] if "typegoedkeurungsnummer" in key else key["typegoedkeuringsnummer"],
        "codevarianttgk": key["variant"],
        "codeuitvoeringtgk": key["version"],
        "volgnummerrevisieuitvoering": key["revision"],
        "motorcode": "DUC",
        "typegoedkeuringsnummermotor": "e1*2018/858*00403*07-ENG",
        "aantalcilinders": "4",
        "cilinderinhoud": "1498",
    }
    gearbox = {
        "typegoedkeurungsnummer": key["typegoedkeurungsnummer"],
        "codevarianttgk": key["variant"],
        "codeuitvoeringtgk": key["version"],
        "volgnummerrevisieuitvoering": key["revision"],
        "codetypeversnellingsbak": "A",
    }
    gearbox["typegoedkeurungsnummer"] = gearbox.pop("typegoedkeurungsnummer")
    base = {
        "typegoedkeurungsnummer": key["typegoedkeurungsnummer"],
        "codevarianttgk": key["variant"],
        "codeuitvoeringtgk": key["version"],
        "volgnummerrevisieuitvoering": key["revision"],
        "begindatumrevisieuitvoering": "2026-07-31",
        "voertuigcategorie": "M1",
    }
    make = {
        "typegoedkeurungsnummer": key["typegoedkeurungsnummer"],
        "codevarianttgk": key["variant"],
        "codeuitvoeringtgk": key["version"],
        "volgnummerrevisieuitvoering": key["revision"],
        "merkcoderdw": "VOLK",
    }
    trade_name = {
        "typegoedkeurungsnummer": key["typegoedkeurungsnummer"],
        "codevariantgk": key["variant"],
        "codeuitvoeringtgk": key["version"],
        "volgnummerrevisieuitvoering": key["revision"],
        "handelsbenamingfabrikant": "TAYRON",
        "typeaanduidingfabrikant": "R4",
    }
    records = {
        "registered_vehicle_identity": registration,
        "tgk_drive": drive,
        "tgk_gearbox": gearbox,
        "tgk_base": base,
        "tgk_make": make,
        "tgk_trade_name": trade_name,
    }
    projections = {}
    for name, record in records.items():
        projections[name] = [{
            "scope_id": MODULE.scope_id_for(key),
            "record": record,
            "source_row_sha256": MODULE.sha256_json(record),
        }]
    dataset_ids = {
        "registered_vehicle_identity": "m9d7-ebf2",
        "tgk_drive": "4by9-ammk",
        "tgk_gearbox": "7rjk-eycs",
        "tgk_base": "byxc-wwua",
        "tgk_make": "kyri-nuah",
        "tgk_trade_name": "x5v3-sewk",
    }
    file_entries = []
    for name, dataset_id in dataset_ids.items():
        file_entries.append({
            "dataset_name": name,
            "dataset_id": dataset_id,
            "title": name,
            "catalog_url": "https://data.overheid.nl/",
            "api_url": "https://opendata.rdw.nl/",
            "license": "CC0-1.0",
            "source_revision": "2026-11-06T00:00:00Z",
            "query_sha256": "a" * 64,
            "projection_sha256": "b" * 64,
            "row_count": len(projections[name]),
        })
    context = {"approval_scope_keys": [key]}
    return key, projections, file_entries, context


class RDWVagTypeApprovalPackTests(unittest.TestCase):
    def test_source_rights_and_exact_six_dataset_contract(self):
        manifest, makes = MODULE.load_rights_inputs()
        contracts = MODULE.metadata_contracts(manifest)
        self.assertEqual(len(contracts), 6)
        self.assertIn("VOLKSWAGEN", makes)
        self.assertTrue(all(item["license"] == "CC0 1.0" for item in manifest["data_products"].values()))
        self.assertFalse(manifest["rights"].get("production_import_allowed", False))
        self.assertFalse(any("vin" in field.lower() or "kenteken" in field.lower() for field in MODULE.REGISTRATION_FIELDS))

    def test_make_normalization_handles_dutch_diacritics(self):
        self.assertEqual(MODULE.normalize_make("ŠKODA"), "SKODA")
        self.assertEqual(MODULE.normalize_make("VOLKSWAGEN"), "VOLKSWAGEN")

    def test_distinct_query_uses_socrata_distinct_syntax(self):
        with patch.object(MODULE, "fetch_json", return_value=[{"merk": "VOLKSWAGEN"}]) as mocked:
            rows = MODULE.query_all(
                "m9d7-ebf2",
                select_fields=["merk"],
                where="typegoedkeuringsnummer IS NOT NULL",
                order="merk",
                distinct=True,
                page_size=5,
            )
        self.assertEqual(rows, [{"merk": "VOLKSWAGEN"}])
        query = parse_qs(urlsplit(mocked.call_args.args[0]).query)
        self.assertEqual(query["$select"], ["distinct merk"])

    def test_scope_key_is_exact_and_revision_sensitive(self):
        key, projections, _, _ = fixture_rows()
        self.assertEqual(
            MODULE.scope_id_for(key),
            projections["registered_vehicle_identity"][0]["scope_id"],
        )
        changed = dict(key)
        changed["revision"] = "1"
        self.assertNotEqual(MODULE.scope_id_for(key), MODULE.scope_id_for(changed))

    def test_sqlite_keeps_engine_and_gearbox_as_separate_candidates(self):
        key, projections, file_entries, context = fixture_rows()
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "rdw.sqlite"
            counts = MODULE.create_database(
                database,
                projections,
                file_entries,
                context,
                "c" * 64,
            )
            self.assertEqual(counts["approval_scope"], 1)
            self.assertEqual(counts["tgk_drive"], 1)
            self.assertEqual(counts["tgk_gearbox"], 1)
            connection = sqlite3.connect(database)
            connection.row_factory = sqlite3.Row
            try:
                self.assertEqual(connection.execute("PRAGMA integrity_check").fetchone()[0], "ok")
                self.assertEqual(connection.execute("SELECT motorcode_candidate FROM tgk_drive").fetchone()[0], "DUC")
                self.assertEqual(connection.execute("SELECT gearbox_type_classification_candidate FROM tgk_gearbox").fetchone()[0], "A")
                names = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view')")}
                self.assertFalse(any("pair" in name.lower() for name in names))
                scope = connection.execute("SELECT * FROM approval_scope").fetchone()
                self.assertIsNone(scope["model_year"])
                self.assertIsNone(scope["generation"])
                self.assertEqual(scope["market_scope"], "NL")
                self.assertEqual(scope["exact_engine_gearbox_pair"], 0)
                self.assertEqual(connection.execute("SELECT count(*) FROM source_registry").fetchone()[0], 6)
            finally:
                connection.close()

    def test_sqlite_verifier_rejects_tampered_source_row_hash(self):
        _, projections, file_entries, context = fixture_rows()
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "rdw.sqlite"
            MODULE.create_database(database, projections, file_entries, context, "c" * 64)
            connection = sqlite3.connect(database)
            try:
                connection.execute(
                    "UPDATE tgk_drive SET raw_record_json=?",
                    (json.dumps({"motorcode": "TAMPERED"}, separators=(",", ":")),),
                )
                connection.commit()
                with self.assertRaisesRegex(RuntimeError, "source-row SHA-256 mismatch"):
                    MODULE.validate_database(connection)
            finally:
                connection.close()

    def test_sqlite_import_rejects_forbidden_registration_identity_field(self):
        key, projections, file_entries, context = fixture_rows()
        bad = dict(projections)
        item = dict(bad["registered_vehicle_identity"][0])
        record = dict(item["record"])
        record["kenteken"] = "XX-000-X"
        item["record"] = record
        item["source_row_sha256"] = MODULE.sha256_json(record)
        bad["registered_vehicle_identity"] = [item]
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "rdw.sqlite"
            with self.assertRaisesRegex(ValueError, "Forbidden identity/personal-data field"):
                MODULE.create_database(database, bad, file_entries, context, "c" * 64)
            connection = sqlite3.connect(database)
            try:
                self.assertEqual(connection.execute("SELECT count(*) FROM registration_observation").fetchone()[0], 0)
            finally:
                connection.close()


if __name__ == "__main__":
    unittest.main()
