#!/usr/bin/env python3
"""Offline unit and pack-integrity tests for the RDW CC0 acquisition builder."""
from __future__ import annotations

import argparse
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_rdw_type_approval_pack as builder


class RDWBuilderTests(unittest.TestCase):
    def test_make_code_normalization(self) -> None:
        self.assertEqual(builder.normalize_make_code("Škoda Auto"), "KODAAUTO")
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
        raw = b"Typegoedkeuringsnummer,Motorcode\\r\\ne1*abc,EA888\\r\\n"
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
