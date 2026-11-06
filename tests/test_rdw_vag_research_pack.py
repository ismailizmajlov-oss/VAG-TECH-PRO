from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from scripts import build_rdw_vag_research_pack as rdw

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "data/source-manifests/rdw-eu-vag-type-approval-open-data.json"


class RdwVagResearchPackTests(unittest.TestCase):
    def setUp(self):
        self.source_bytes = MANIFEST_PATH.read_bytes()
        self.source = json.loads(self.source_bytes.decode("utf-8-sig"))
        self.key = (
            "e1*2018/858*00403*07",
            "ACDUCAX0",
            "FD6FD6DD002PR4VNB50OO",
            "0",
        )
        self.datasets = {
            "registration": [{
                "merk": "VOLKSWAGEN",
                "handelsbenaming": "TAYRON",
                "typegoedkeuringsnummer": self.key[0],
                "variant": self.key[1],
                "uitvoering": self.key[2],
                "volgnummer_wijziging_eu_typegoedkeuring": self.key[3],
                "voertuigsoort": "Personenauto",
                "registration_count": "3",
            }],
            "tgk_drive": [{
                "typegoedkeuringsnummer": self.key[0],
                "codevarianttgk": self.key[1],
                "codeuitvoeringtgk": self.key[2],
                "volgnummerrevisieuitvoering": self.key[3],
                "motorcode": "DUC",
                "typegoedkeuringsnummermotor": "E1*2018/858*00403*07",
                "aantalcilinders": "4",
                "cilinderinhoud": "1498",
            }],
            "tgk_gearbox": [{
                "typegoedkeuringsnummer": self.key[0],
                "codevarianttgk": self.key[1],
                "codeuitvoeringtgk": self.key[2],
                "volgnummerrevisieuitvoering": self.key[3],
                "codetypeversnellingsbak": "A",
            }],
            "tgk_base": [{
                "typegoedkeuringsnummer": self.key[0],
                "codevarianttgk": self.key[1],
                "codeuitvoeringtgk": self.key[2],
                "volgnummerrevisieuitvoering": self.key[3],
                "begindatumrevisieuitvoering": "2026-07-31",
                "voertuigcategorie": "M1",
            }],
            "tgk_make": [{
                "typegoedkeuringsnummer": self.key[0],
                "codevarianttgk": self.key[1],
                "codeuitvoeringtgk": self.key[2],
                "volgnummerrevisieuitvoering": self.key[3],
                "merkcoderdw": "VWVP",
            }],
            "tgk_trade_name": [{
                "typegoedkeuringsnummer": self.key[0],
                "codevariantgk": self.key[1],
                "codeuitvoeringtgk": self.key[2],
                "volgnummerrevisieuitvoering": self.key[3],
                "handelsbenamingfabrikant": "TAYRON",
                "typeaanduidingfabrikant": "R4",
            }],
        }
        self.metadata = {
            name: {
                "rows_updated_at": f"2026-11-06T00:00:0{i}Z",
                "view_last_modified": None,
                "columns_sha256": "a" * 64,
            }
            for i, name in enumerate(rdw.DATASETS, start=1)
        }

    def test_pack_builds_hashed_sqlite_with_separate_engine_and_gearbox_candidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = rdw.build_pack(Path(tmp) / "pack", self.source, self.source_bytes, self.datasets, self.metadata)
            self.assertEqual(report["status"], "verified_research_only")
            self.assertFalse(report["ru_eaeu_applicability"])
            self.assertFalse(report["exact_engine_gearbox_pair_claim"])
            pack = Path(tmp) / "pack"
            manifest = json.loads((pack / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["market_scope"], ["NL"])
            self.assertEqual(manifest["counts"]["source_files"], 6)
            self.assertEqual(manifest["counts"]["approval_scopes"], 1)
            self.assertEqual(manifest["counts"]["engine_candidates"], 1)
            self.assertEqual(manifest["counts"]["gearbox_classifications"], 1)
            db = sqlite3.connect(pack / "rdw-vag-research.sqlite")
            try:
                tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                self.assertNotIn("engine_gearbox_pairs", tables)
                self.assertFalse(any("pair" in name.lower() for name in tables))
                self.assertEqual(db.execute("SELECT engine_designation FROM engine_designation_candidates").fetchone()[0], "DUC")
                self.assertEqual(db.execute("SELECT gearbox_type_classification FROM gearbox_classifications").fetchone()[0], "A")
                self.assertEqual(db.execute("SELECT count(*) FROM engine_designation_candidates WHERE verification_status='rdw_engine_designation_candidate_not_oem_confirmed'").fetchone()[0], 1)
                self.assertEqual(db.execute("SELECT count(*) FROM gearbox_classifications WHERE verification_status='rdw_approval_gearbox_classification_not_vag_code'").fetchone()[0], 1)
                self.assertEqual(db.execute("SELECT count(*) FROM approval_scope WHERE model_year IS NOT NULL OR generation IS NOT NULL").fetchone()[0], 0)
                self.assertEqual(db.execute("SELECT count(*) FROM source_file_artifacts").fetchone()[0], 6)
                self.assertEqual(db.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            finally:
                db.close()

    def test_rights_gate_fails_closed(self):
        bad = json.loads(json.dumps(self.source))
        bad["rights"]["offline_cache_allowed"] = False
        with self.assertRaisesRegex(ValueError, "offline_cache_allowed"):
            rdw.validate_source_manifest(bad)

    def test_wrong_market_or_production_import_fails_closed(self):
        bad = json.loads(json.dumps(self.source))
        bad["market_scope"] = ["RU"]
        with self.assertRaisesRegex(ValueError, "NL-scoped"):
            rdw.validate_source_manifest(bad)
        bad = json.loads(json.dumps(self.source))
        bad["import_policy"]["production_import"] = True
        with self.assertRaisesRegex(ValueError, "research-only"):
            rdw.validate_source_manifest(bad)

    def test_forbidden_registration_and_personal_fields_are_rejected_recursively(self):
        with self.assertRaisesRegex(ValueError, "kenteken"):
            rdw.reject_forbidden_fields({"safe": [{"kenteken": "XX-123-X"}]})
        with self.assertRaisesRegex(ValueError, "vin"):
            rdw.reject_forbidden_fields({"Vehicle": {"VIN": "not-stored"}})

    def test_exact_scope_requires_approval_variant_version_and_revision(self):
        self.assertEqual(rdw.scope_key({
            "typegoedkeuringsnummer": self.key[0],
            "codevarianttgk": self.key[1],
            "codeuitvoeringtgk": self.key[2],
            "volgnummerrevisieuitvoering": self.key[3],
        }, "codevarianttgk"), self.key)
        self.assertIsNone(rdw.scope_key({
            "typegoedkeuringsnummer": self.key[0],
            "codevarianttgk": self.key[1],
            "codeuitvoeringtgk": "",
            "volgnummerrevisieuitvoering": self.key[3],
        }, "codevarianttgk"))

    def test_soql_literal_escapes_quotes_and_dataset_ids_are_constrained(self):
        self.assertEqual(rdw.soql_literal("A'B"), "'A''B'")
        with self.assertRaisesRegex(ValueError, "Invalid RDW dataset id"):
            rdw.build_soda_url("m9d7-ebf2/evil", {"$limit": "1"})
        url = rdw.build_soda_url("m9d7-ebf2", {"$select": "merk,handelsbenaming", "$limit": "1"})
        self.assertIn("%24select", url)
        self.assertNotIn("kenteken", url.lower())

    def test_child_row_without_exact_registration_scope_is_rejected(self):
        bad_datasets = json.loads(json.dumps(self.datasets))
        bad_datasets["tgk_drive"][0]["codeuitvoeringtgk"] = "OTHER"
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "no exact matching registration approval scope"):
                rdw.build_pack(Path(tmp) / "pack", self.source, self.source_bytes, bad_datasets, self.metadata)


if __name__ == "__main__":
    unittest.main()
