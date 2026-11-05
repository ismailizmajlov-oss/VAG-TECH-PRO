import json
import sqlite3
import unittest
from pathlib import Path

from scripts.build_astra_ch_tas_pack import (
    ATTRIBUTION,
    _check_rights,
    _create_schema,
    canonical_row_sha256,
    is_vag_make,
    resolve_scope_link,
)


ROOT = Path(__file__).resolve().parents[1]


class AstraChTasPackTests(unittest.TestCase):
    def test_exact_make_filter_does_not_accept_similar_labels(self):
        self.assertTrue(is_vag_make("AUDI"))
        self.assertTrue(is_vag_make("vw"))
        self.assertTrue(is_vag_make("ŠKODA"))
        self.assertFalse(is_vag_make("Volkswagen Commercial Vehicles"))
        self.assertFalse(is_vag_make("VW Nutzfahrzeuge"))
        self.assertFalse(is_vag_make("Audi AG"))

    def test_row_hash_is_canonical_and_stable(self):
        self.assertEqual(
            canonical_row_sha256({"makeName": "AUDI", "approval": "1AB"}),
            canonical_row_sha256({"approval": "1AB", "makeName": "AUDI"}),
        )
        self.assertNotEqual(
            canonical_row_sha256({"makeName": "AUDI", "approval": "1AB"}),
            canonical_row_sha256({"makeName": "VW", "approval": "1AB"}),
        )

    def test_exact_version_link_requires_unique_exact_scope(self):
        index = {
            ("1AB701", "AUDI"): [
                {"approval_row_id": 11, "version": "C4-AEL"},
                {"approval_row_id": 12, "version": "C4-ABC"},
            ]
        }
        self.assertEqual(
            resolve_scope_link(index, "1AB701", "AUDI", "C4-AEL"),
            (11, "linked_exact_approval_version"),
        )
        self.assertEqual(
            resolve_scope_link(index, "1AB701", "AUDI", "C4"),
            (None, "no_exact_version_match"),
        )

    def test_wildcard_is_preserved_as_wildcard_not_exact_fitment(self):
        index = {("1XZ904", "CUPRA"): [{"approval_row_id": 21, "version": "*"}]}
        self.assertEqual(
            resolve_scope_link(index, "1XZ904", "CUPRA", "*"),
            (21, "linked_wildcard_approval_variant"),
        )

    def test_ambiguous_duplicate_approval_version_is_not_linked(self):
        index = {
            ("1AB701", "AUDI"): [
                {"approval_row_id": 11, "version": "AEL"},
                {"approval_row_id": 12, "version": "AEL"},
            ]
        }
        self.assertEqual(
            resolve_scope_link(index, "1AB701", "AUDI", "AEL"),
            (None, "ambiguous_approval_version"),
        )

    def test_missing_or_non_exact_scope_is_not_linked(self):
        index = {("1AB701", "AUDI"): [{"approval_row_id": 11, "version": ""}]}
        self.assertEqual(
            resolve_scope_link(index, "1AB701", "AUDI", ""),
            (None, "version_scope_missing"),
        )
        self.assertEqual(
            resolve_scope_link(index, "1AB701", "AUDI", "C4 / C4B Motor: AEL/103 kW"),
            (None, "no_exact_version_match"),
        )
        self.assertEqual(
            resolve_scope_link(index, "1ZZ999", "AUDI", "AEL"),
            (None, "approval_record_missing"),
        )

    def test_manifest_rights_and_market_gate(self):
        manifest = json.loads(
            (ROOT / "data/source-manifests/astra-ch-tas-open-data.json").read_text(encoding="utf-8")
        )
        _check_rights(manifest)
        self.assertEqual(manifest["rights"]["attribution"], ATTRIBUTION)
        self.assertEqual(manifest["market_scope"], ["CH"])
        self.assertFalse(manifest["import_policy"]["production_import"])
        self.assertFalse(manifest["import_policy"]["ru_eaeu_applicability"])
        self.assertEqual(manifest["snapshot"]["vag_emissions_gearbox_rows"]["total"], 53414)

    def test_schema_enforces_ch_only_and_never_claims_factory_codes(self):
        db = sqlite3.connect(":memory:")
        _create_schema(db)
        db.execute(
            """INSERT INTO source_files VALUES(
               'passenger_cars','https://example.invalid/index.xlsb','index.xlsb',1,?,
               '2026-10-29','approved_by_published_ogd_terms','CH')""",
            ("a" * 64,),
        )
        with self.assertRaises(sqlite3.IntegrityError):
            db.execute(
                """INSERT INTO type_approval_records(
                source_file_key,source_row_number,source_row_sha256,source_record_locator,
                market_scope,approval_number,make_name,approval_gearbox_classes_json
                ) VALUES('passenger_cars',2,?,'row', 'RU','1AB','AUDI','[]')""",
                ("b" * 64,),
            )
        with self.assertRaises(sqlite3.IntegrityError):
            db.execute(
                """INSERT INTO engine_gearbox_scope_links(
                approval_row_id,gearbox_row_id,engine_type_designation,swiss_gearbox_type,
                version_scope,relation_precision,factory_vag_gearbox_code_claim
                ) VALUES(1,1,'AEL','m6','*','approval_variant_wildcard',1)"""
            )
        table_names = {
            row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        self.assertFalse(any("dtc" in name.lower() for name in table_names))
        db.close()


if __name__ == "__main__":
    unittest.main()
