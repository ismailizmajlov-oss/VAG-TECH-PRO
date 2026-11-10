#!/usr/bin/env python3
"""Unit tests for the isolated OwnerSpecs CC BY-SA VAG research pack."""
import json
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_MANIFEST = ROOT / "data/source-manifests/ownerspecs-verified-vehicle-specs-cc-by-sa-4.0.json"

from scripts.build_ownerspecs_vag_research_pack import build_pack, verify_pack


PROVENANCE_KINDS = {
    "oem_portal": "Manufacturer owner's manual / OEM portal",
    "workshop_dataset": "Professional workshop technical dataset",
    "official_open_data": "Government vehicle registry / open data",
    "first_party_scan": "First-party photo of the vehicle's own placard / type plate",
}


def fixture_dataset():
    return {
        "dataset": "ownerspecs.com — verified vehicle specifications",
        "license": "CC BY-SA 4.0",
        "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
        "attribution": "ownerspecs.com — https://ownerspecs.com",
        "attribution_required": True,
        "provenance_kinds": PROVENANCE_KINDS,
        "generation_count": 2,
        "generations": [
            {
                "brand": "Audi",
                "model": "A1",
                "generation": "A1 (GB)",
                "generation_slug": "a1-gb-hatch-2019-present",
                "url": "https://ownerspecs.com/audi/a1-gb-hatch-2019-present",
                "year_start": 2018,
                "year_end": None,
                "body_type": "Hatchback",
                "dimensions_mm": {"length": 4029, "width": 1740},
                "fuel_tank_l": 40,
                "verified_datapoints": 2,
                "specifications": [
                    {
                        "field": "engine_code",
                        "label": "Engine Code",
                        "value": "EA211 1.0 TSI",
                        "unit": None,
                        "is_range": False,
                        "sources": 1,
                        "provenance": ["oem_portal"],
                    },
                    {
                        "field": "engine_oil_capacity",
                        "label": "Engine Oil Capacity",
                        "value": 4.3,
                        "unit": "L",
                        "is_range": False,
                        "sources": 1,
                        "provenance": ["workshop_dataset"],
                    },
                ],
                "masses": [],
                "tyres": [],
            },
            {
                "brand": "Toyota",
                "model": "Corolla",
                "generation": "Corolla XII",
                "generation_slug": "corolla-xii",
                "url": "https://ownerspecs.com/toyota/corolla-xii",
                "year_start": 2019,
                "year_end": None,
                "body_type": "Sedan",
                "dimensions_mm": {},
                "fuel_tank_l": None,
                "verified_datapoints": 1,
                "specifications": [
                    {
                        "field": "engine_oil_capacity",
                        "label": "Engine Oil Capacity",
                        "value": 4.0,
                        "unit": "L",
                        "is_range": False,
                        "sources": 1,
                        "provenance": ["oem_portal"],
                    }
                ],
                "masses": [],
                "tyres": [],
            },
        ],
    }


class OwnerSpecsResearchPackTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.output = self.root / "pack"
        self.output.mkdir()
        self.source_manifest = self.root / "source-manifest.json"
        source = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
        source["snapshot"]["json_descriptor_generation_count"] = 2
        source["snapshot"]["html_page_generation_count"] = 2
        source["snapshot"]["html_page_verified_datapoint_count"] = 3
        source["snapshot"]["source_snapshot_sha256"] = None
        source["snapshot"]["source_file_bytes"] = None
        source["snapshot"]["status"] = "not_acquired_snapshot_pending"
        self.source_manifest.write_text(
            json.dumps(source, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        self.source_json = self.root / "dataset.json"
        self.source_json.write_text(
            json.dumps(fixture_dataset(), ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_builds_separate_vag_only_cc_by_sa_pack_with_hashes(self):
        manifest = build_pack(self.source_json, self.source_manifest, self.output)
        self.assertEqual(manifest["status"], "verified_research_only")
        self.assertEqual(manifest["license"]["id"], "CC-BY-SA-4.0")
        self.assertEqual(manifest["counts"]["all_source_generations"], 2)
        self.assertEqual(manifest["counts"]["all_source_verified_datapoints"], 3)
        self.assertEqual(manifest["counts"]["vag_generations"], 1)
        self.assertEqual(manifest["counts"]["vag_facts"], 2)
        self.assertEqual(manifest["market_scope"], ["UNKNOWN"])
        self.assertFalse(manifest["critical_technical_values_publishable"])
        self.assertFalse(manifest["exact_engine_gearbox_pair"])
        verified = verify_pack(self.output, self.source_manifest)
        self.assertEqual(verified["source_snapshot_sha256"], manifest["source_snapshot_sha256"])
        db = sqlite3.connect(f"file:{self.output / 'ownerspecs-vag-research.sqlite'}?mode=ro", uri=True)
        try:
            self.assertEqual(db.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            self.assertEqual(db.execute("SELECT count(*) FROM generations").fetchone()[0], 1)
            self.assertEqual(db.execute("SELECT count(*) FROM facts").fetchone()[0], 2)
            self.assertEqual(db.execute("SELECT DISTINCT market_scope FROM facts").fetchall(), [("UNKNOWN",)])
            self.assertEqual(db.execute("SELECT count(*) FROM facts WHERE primary_document_url IS NOT NULL OR primary_document_revision IS NOT NULL").fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT count(*) FROM facts WHERE critical_value_publishable != 0 OR exact_engine_gearbox_pair != 0").fetchone()[0], 0)
        finally:
            db.close()

    def test_rejects_generation_datapoint_count_mismatch(self):
        dataset = fixture_dataset()
        dataset["generations"][0]["verified_datapoints"] = 9
        self.source_json.write_text(json.dumps(dataset, ensure_ascii=False), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "per-generation verified_datapoints mismatch"):
            build_pack(self.source_json, self.source_manifest, self.output)

    def test_rejects_unreviewed_or_missing_sharealike_rights(self):
        source = json.loads(self.source_manifest.read_text(encoding="utf-8"))
        source["rights"]["share_alike_required"] = False
        self.source_manifest.write_text(json.dumps(source, ensure_ascii=False), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "rights/Share-Alike/attribution gate"):
            build_pack(self.source_json, self.source_manifest, self.output)

    def test_rejects_source_snapshot_hash_mismatch(self):
        source = json.loads(self.source_manifest.read_text(encoding="utf-8"))
        source["snapshot"]["source_snapshot_sha256"] = "0" * 64
        self.source_manifest.write_text(json.dumps(source, ensure_ascii=False), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "differs from the pinned manifest"):
            build_pack(self.source_json, self.source_manifest, self.output)

    def test_does_not_overwrite_existing_database(self):
        self.output.mkdir(exist_ok=True)
        (self.output / "ownerspecs-vag-research.sqlite").write_bytes(b"sentinel")
        with self.assertRaises(FileExistsError):
            build_pack(self.source_json, self.source_manifest, self.output)
        self.assertEqual((self.output / "ownerspecs-vag-research.sqlite").read_bytes(), b"sentinel")


if __name__ == "__main__":
    unittest.main()
