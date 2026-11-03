#!/usr/bin/env python3
"""Offline unit and pack-integrity tests for the RDW CC0 acquisition builder."""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_rdw_type_approval_pack as builder


class RDWBuilderTests(unittest.TestCase):
    def test_make_code_normalization(self) -> None:
        self.assertEqual(builder.normalize_make_code("Škoda Auto"), "SKODAAUTO")
        self.assertEqual(builder.normalize_make_code("Volkswagen AG"), "VOLKSWAGENAG")

    def test_vag_make_aliases(self) -> None:
        aliases = {"VOLKSWAGEN": "Volkswagen", "AUDI": "Audi", "SKODA": "Škoda"}
        self.assertEqual(builder.make_name_for_code("Volkswagen", aliases), "Volkswagen")
        self.assertEqual(builder.make_name_for_code("AUDI", aliases), "Audi")
        self.assertEqual(builder.make_name_for_code("Skoda", aliases), "Škoda")
        self.assertIsNone(builder.make_name_for_code("TOYOTA", aliases))

    def test_variant_key_is_exact_and_case_normalized(self) -> None:
        row = {
            "Typegoedkeuringsnummer": "e1*2007/46*1234*01",
            "CodeVariantTgk": "AB",
            "CodeUitvoeringTgk": "CD",
            "VolgnummerRevisieUitvoering": "2",
        }
        self.assertEqual(builder.variant_key(row), ("e1*2007/46*1234*01", "ab", "cd", "2"))

    def test_variant_key_accepts_published_gk_alias(self) -> None:
        row = {
            "typegoedkeuringsnummer": "e1*2007/46*1234*01",
            "codevariantgk": "AB",
            "codeuitvoeringtgk": "CD",
            "volgnummerrevisieuitvoering": "2",
        }
        self.assertEqual(builder.variant_key(row), ("e1*2007/46*1234*01", "ab", "cd", "2"))

    def test_variant_key_rejects_incomplete_key(self) -> None:
        self.assertIsNone(builder.variant_key({"typegoedkeuringsnummer": "e1"}))

    def test_csv_reader_preserves_source_fields(self) -> None:
        raw = b"Typegoedkeuringsnummer,Motorcode\r\ne1*abc,EA888\r\n"
        rows, headers = builder.read_csv_rows(raw, "fixture", 10)
        self.assertEqual(headers, ["Typegoedkeuringsnummer", "Motorcode"])
        self.assertEqual(rows[0]["Motorcode"], "EA888")

    def test_view_metadata_requires_pinned_id_and_columns(self) -> None:
        raw = json.dumps({
            "id": "4by9-ammk",
            "rowsUpdatedAt": 1760000000,
            "columns": [
                {"fieldName": "typegoedkeuringsnummer"},
                {"fieldName": "codevarianttgk"},
                {"fieldName": "codeuitvoeringtgk"},
                {"fieldName": "volgnummerrevisieuitvoering"},
            ],
        }).encode()
        dataset = {
            "dataset_id": "rdw-tgk-aandrijving-uitvoering",
            "view_id": "4by9-ammk",
            "required_fields": [
                "typegoedkeuringsnummer", "codevarianttgk",
                "codeuitvoeringtgk", "volgnummerrevisieuitvoering",
            ],
        }
        metadata, revision = builder.validate_view_metadata(raw, dataset)
        self.assertEqual(metadata["id"], "4by9-ammk")
        self.assertEqual(revision, "1760000000")

    def test_non_allowlisted_hosts_are_blocked(self) -> None:
        with self.assertRaises(ValueError):
            builder.safe_fetch("https://example.com/data.csv", 1000, 1, "text/csv")

    def test_manifest_keeps_rd_w_market_out_of_ru(self) -> None:
        manifest = json.loads((ROOT / "data/source-manifests/rdw-eu-type-approval-cc0.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["market_scope"], "NL_EU_TYPE_APPROVAL_REGISTER")
        self.assertFalse(manifest["applicability_policy"]["russian_or_eaeu_fitment"])
        self.assertTrue(manifest["rights_evidence"]["commercial_use"].startswith("confirmed_by_dataset_specific_CC0"))

    def test_pack_integrity_when_requested(self) -> None:
        pack_dir = getattr(self, "pack_dir", None)
        if pack_dir is None:
            self.skipTest("No CI pack directory supplied")
        result = builder.verify_pack(Path(pack_dir))
        self.assertEqual(result["status"], "verified")
        self.assertFalse(result["exact_vehicle_fitment"])


    def test_build_database_commits_rows_before_close(self) -> None:
        dataset_specs = [
            ("rdw-tgk-basis-uitvoering", "approval_variant_base", "byxc-wwua"),
            ("rdw-tgk-merk-uitvoering", "approval_variant_make_anchor", "kyri-nuah"),
            ("rdw-tgk-aandrijving-uitvoering", "engine_type_approval_candidates", "4by9-ammk"),
            ("rdw-tgk-handelsbenaming-fabrikant", "manufacturer_trade_name_candidates", "x5v3-sewk"),
            ("rdw-tgk-versnelling-uitvoering", "gearbox_type_approval_candidates", "7rjk-eycs"),
        ]
        datasets = [
            {
                "dataset_id": dataset_id,
                "purpose": purpose,
                "title": dataset_id,
                "dataset_page": "https://data.overheid.nl/",
                "view_id": view_id,
            }
            for dataset_id, purpose, view_id in dataset_specs
        ]
        snapshots = {}
        for index, (dataset_id, _, view_id) in enumerate(dataset_specs, start=1):
            digest = str(index) * 64
            snapshots[dataset_id] = {
                "source_revision": "fixture-revision-1",
                "metadata_sha256": digest,
                "view_metadata": {
                    "relative_path": f"upstream/{view_id}.metadata.json",
                    "source_url": f"https://opendata.rdw.nl/api/views/{view_id}.json",
                    "byte_size": 1,
                    "sha256": digest,
                },
                "license_evidence_page": {
                    "relative_path": f"upstream/{view_id}.license.html",
                    "source_url": "https://data.overheid.nl/",
                    "byte_size": 1,
                    "sha256": digest,
                },
                "csv_snapshots": [],
            }
        snapshots["__license__"] = {
            "license_text": {
                "relative_path": "LICENSES/CC0-1.0-legalcode.txt",
                "source_url": "https://creativecommons.org/publicdomain/zero/1.0/legalcode",
                "byte_size": 1,
                "sha256": "f" * 64,
            }
        }

        key = {
            "typegoedkeuringsnummer": "e1*2007/46*1234*01",
            "codevarianttgk": "AB",
            "codeuitvoeringtgk": "CD",
            "volgnummerrevisieuitvoering": "1",
        }
        rows_by_dataset = {dataset_id: [] for dataset_id, _, _ in dataset_specs}
        rows_by_dataset["rdw-tgk-merk-uitvoering"] = [{**key, "merkcoderdw": "VOLKSWAGEN"}]
        rows_by_dataset["rdw-tgk-basis-uitvoering"] = [{**key, "fixture_base_field": "base"}]
        rows_by_dataset["rdw-tgk-aandrijving-uitvoering"] = [{**key, "motorcode": "RDW-CANDIDATE"}]
        rows_by_dataset["rdw-tgk-handelsbenaming-fabrikant"] = [
            {**key, "handelsbenamingfabrikant": "Golf", "typeaanduidingfabrikant": "Type A"}
        ]
        rows_by_dataset["rdw-tgk-versnelling-uitvoering"] = [
            {**key, "codetypeversnellingsbak": "RDW-GB-CANDIDATE"}
        ]
        manifest = {
            "source_id": "rdw-fixture",
            "publisher": "RDW fixture",
            "dataset_license": "CC0-1.0",
            "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
            "datasets": datasets,
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "rdw.sqlite"
            counts = builder.build_database(
                db_path,
                manifest,
                snapshots,
                rows_by_dataset,
                {"VOLKSWAGEN": "Volkswagen"},
                {"VOLKSWAGEN": 1},
            )
            self.assertEqual(
                counts,
                {
                    "vag_type_approval_variants": 1,
                    "base_variant_evidence": 1,
                    "engine_candidates": 1,
                    "gearbox_type_candidates": 1,
                    "manufacturer_trade_names": 1,
                },
            )
            db = sqlite3.connect(db_path)
            try:
                persisted = {
                    table: db.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
                    for table in (
                        "vag_type_approval_variants",
                        "base_variant_evidence",
                        "engine_candidates",
                        "gearbox_type_candidates",
                        "manufacturer_trade_names",
                    )
                }
                self.assertEqual(db.execute("PRAGMA integrity_check").fetchone()[0], "ok")
                self.assertEqual(db.execute("PRAGMA foreign_key_check").fetchall(), [])
            finally:
                db.close()
            self.assertEqual(persisted, counts)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pack-dir", type=Path)
    args = parser.parse_args()
    RDWBuilderTests.pack_dir = args.pack_dir
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(RDWBuilderTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
