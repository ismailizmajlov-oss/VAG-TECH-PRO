import csv
import hashlib
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_kba_de_vag_stock_research_pack.py"
spec = importlib.util.spec_from_file_location("kba_builder", SCRIPT)
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)

class KbaResearchPackTests(unittest.TestCase):
    def setUp(self):
        self.temp = Path(tempfile.mkdtemp(prefix="kba-pack-test-"))
        self.csv_path = self.temp / "source.csv"
        self.manifest_path = self.temp / "source-manifest.json"
        self.output = self.temp / "out"
        rows = [
            ["01.01.2026","VOLKSWAGEN (D)"," Golf ","0603","Berlin","100","", "1"],
            ["01.01.2026","AUDI (D)","A4","0588","Hamburg","80","", "2"],
            ["01.01.2025","AUDI (H)","A3","0588","Bayern","50","", "3"],
            ["01.01.2025","SKODA (CZ)","Octavia","8004","Sachsen","60","", "4"],
            ["01.01.2024","SEAT (E)","Leon","7593","Berlin","30","", "5"],
            ["01.01.2024","PORSCHE","911","0583","Hessen","20","", "6"],
            ["01.01.2023","BENTLEY (UK)","Continental","2091","Berlin","3","", "7"],
            ["01.01.2023","LAMBORGHINI (I)","Urus","4026","Bayern","2","", "8"],
            ["01.01.2026","Audi supplier GmbH","not VAG","X","Berlin","999","", "9"],
        ]
        with self.csv_path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(builder.COLUMNS)
            writer.writerows(rows)
        payload = self.csv_path.read_bytes()
        labels = ["VOLKSWAGEN (D)","AUDI (D)","AUDI (H)","SKODA (CZ)","SEAT (E)","PORSCHE","BENTLEY (UK)","LAMBORGHINI (I)"]
        self.source_manifest = {
            "source_id": builder.SOURCE_ID,
            "rights": {
                "rights_status": "approved_by_published_DL_DE_BY_2_0",
                "commercial_use_allowed": True, "display_allowed": True,
                "offline_cache_allowed": True, "bulk_reuse_allowed": True,
                "redistribution_allowed": True, "attribution_required": True
            },
            "snapshot": {
                "status": "source_snapshot_acquired_schema_verified", "downloaded": True,
                "source_snapshot_sha256": hashlib.sha256(payload).hexdigest(),
                "file_bytes": len(payload), "source_row_count": 9, "filtered_vag_row_count": 8,
                "vag_manufacturer_labels": labels, "observed_columns": builder.COLUMNS,
                "source_revision": "fixture-r1", "downloaded_at_utc": "2026-11-07T00:00:00Z",
                "manufacturer_label_count": 8, "unique_make_trade_name_pairs": 8,
                "unique_make_type_key_pairs": 8, "unique_make_trade_type_reference_date_tuples": 8,
                "unique_federal_states": 5, "temporal_coverage_observed": ["2023-01-01","2026-01-01"]
            }
        }
        self.manifest_path.write_text(json.dumps(self.source_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        builder.build(self.csv_path, self.manifest_path, self.output, SCRIPT)

    def tearDown(self):
        shutil.rmtree(self.temp, ignore_errors=True)

    def test_build_verifies_counts_hashes_and_exact_market_scope(self):
        result = builder.verify(self.output)
        self.assertEqual(result["status"], "verified_research_only")
        self.assertEqual(result["counts"]["source_rows"], 9)
        self.assertEqual(result["counts"]["vag_stock_observations"], 8)
        self.assertEqual(result["counts"]["manufacturer_labels"], 8)
        self.assertEqual(result["counts"]["reference_dates"], ["2023-01-01","2024-01-01","2025-01-01","2026-01-01"])

    def test_no_fuzzy_or_substring_make_matching(self):
        import sqlite3
        db = sqlite3.connect(self.output / "kba-de-vag-stock-research.sqlite")
        try:
            makes = [row[0] for row in db.execute("SELECT source_value FROM manufacturers ORDER BY source_value")]
            self.assertEqual(len(makes), 8)
            self.assertNotIn("Audi supplier GmbH", makes)
        finally:
            db.close()

    def test_source_row_hash_uses_unmodified_parsed_fields(self):
        import sqlite3
        db = sqlite3.connect(self.output / "kba-de-vag-stock-research.sqlite")
        try:
            actual = db.execute("SELECT source_record_sha256 FROM stock_observations WHERE source_row_number=1").fetchone()[0]
            raw = dict(zip(builder.COLUMNS, ["01.01.2026","VOLKSWAGEN (D)"," Golf ","0603","Berlin","100","","1"]))
            self.assertEqual(actual, builder.sha256_bytes(builder.canonical_bytes(raw)))
            trade_name = db.execute("SELECT source_value FROM trade_names WHERE source_value=' Golf '").fetchone()
            self.assertIsNotNone(trade_name)
        finally:
            db.close()

    def test_research_view_never_claims_engine_gearbox_or_ru_fitment(self):
        import sqlite3
        db = sqlite3.connect(self.output / "kba-de-vag-stock-research.sqlite")
        try:
            columns = {row[1] for row in db.execute("PRAGMA table_info(v_stock_observations)")}
            for name in ("source_revision","source_snapshot_sha256","market_scope","applicability_precision","review_status","exact_engine_gearbox_pair","ru_eaeu_applicability"):
                self.assertIn(name, columns)
            self.assertEqual(db.execute("SELECT count(*) FROM v_stock_observations WHERE market_scope!='DE' OR exact_engine_gearbox_pair!=0 OR ru_eaeu_applicability!=0").fetchone()[0], 0)
            tables = [row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")]
            self.assertFalse(any("pair" in name.lower() for name in tables))
        finally:
            db.close()

    def test_missing_rights_or_snapshot_hash_fails_closed(self):
        bad = dict(self.source_manifest)
        bad["rights"] = dict(bad["rights"])
        bad["rights"]["redistribution_allowed"] = False
        self.manifest_path.write_text(json.dumps(bad), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "permission"):
            builder.verify_source(self.csv_path, self.manifest_path)
        bad["rights"]["redistribution_allowed"] = True
        bad["snapshot"] = dict(bad["snapshot"])
        bad["snapshot"]["source_snapshot_sha256"] = "0" * 64
        self.manifest_path.write_text(json.dumps(bad), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            builder.verify_source(self.csv_path, self.manifest_path)

if __name__ == "__main__":
    unittest.main()
