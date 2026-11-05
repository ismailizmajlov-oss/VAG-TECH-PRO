#!/usr/bin/env python3
"""Synthetic safety tests for the VehiclesDB VAG identity-candidate pack."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vag_identity_vehiclesdb_common import build_pack, verify_pack


def fixture(root: Path) -> tuple[Path, Path, Path, Path, Path]:
    source_dir = root / "source"
    source_dir.mkdir(parents=True)
    source_db = source_dir / "catalog.sqlite"
    db = sqlite3.connect(source_db)
    db.executescript("""
    CREATE TABLE makes(kind TEXT,id TEXT,name TEXT,PRIMARY KEY(kind,id));
    CREATE TABLE models(kind TEXT,id TEXT,make_id TEXT,slug TEXT,name TEXT,PRIMARY KEY(kind,id));
    CREATE TABLE availability(kind TEXT,model_id TEXT,country TEXT,evidence TEXT,source TEXT,PRIMARY KEY(kind,model_id,country,source));
    """)
    makes = [
        ("car", "volkswagen", "Volkswagen"),
        ("car", "audi", "Audi"),
        ("car", "toyota", "Toyota"),
    ]
    db.executemany("INSERT INTO makes VALUES(?,?,?)", makes)
    models = [
        ("car", "volkswagen/golf", "volkswagen", "golf", "Golf"),
        ("car", "audi/a4", "audi", "a4", "A4"),
        ("car", "volkswagen/passat", "volkswagen", "passat", "Passat"),
        ("car", "toyota/corolla", "toyota", "corolla", "Corolla"),
    ]
    db.executemany("INSERT INTO models VALUES(?,?,?,?,?)", models)
    availability = [
        ("car", "volkswagen/golf", "nl", "registration", "nl_rdw"),
        ("car", "audi/a4", "us", "approval", "us_fueleconomy"),
        ("car", "volkswagen/passat", "th", "registration", "th_dlt"),
        ("car", "toyota/corolla", "nl", "registration", "nl_rdw"),
    ]
    db.executemany("INSERT INTO availability VALUES(?,?,?,?,?)", availability)
    db.commit()
    db.close()

    upstream_manifest = source_dir / "manifest.json"
    upstream_manifest.write_text(json.dumps({
        "version": "2026.10.3",
        "license": "CC-BY-4.0",
        "countries": ["nl", "us", "th"],
        "sources": [
            {"id": "nl_rdw", "country": "nl", "name": "Dutch vehicle register", "url": "https://example.invalid/nl", "license": "CC0-1.0", "license_url": "https://example.invalid/nl-license", "evidence": "registration"},
            {"id": "us_fueleconomy", "country": "us", "name": "US fuel economy catalog", "url": "https://example.invalid/us", "license": "US-PD", "license_url": "https://example.invalid/us-license", "evidence": "approval"},
            {"id": "th_dlt", "country": "th", "name": "Thai DLT", "url": "https://example.invalid/th", "license": "TH-OpenDataCommon", "license_url": "https://example.invalid/th-license", "evidence": "registration"},
        ],
    }, indent=2), encoding="utf-8")
    attribution = source_dir / "ATTRIBUTION.md"
    attribution.write_text("Vehicle data by VehiclesDB (https://vehiclesdb.com). Upstream notices retained.", encoding="utf-8")
    license_file = source_dir / "LICENSE"
    license_file.write_text(
        "Creative Commons Attribution 4.0 International (CC-BY-4.0). "
        "You are free to share and adapt the material for any purpose, even commercially.",
        encoding="utf-8",
    )
    expected_source_files = {
        "catalog.sqlite": {"byte_size": source_db.stat().st_size, "sha256": hashlib.sha256(source_db.read_bytes()).hexdigest()},
        "manifest.json": {"byte_size": upstream_manifest.stat().st_size, "sha256": hashlib.sha256(upstream_manifest.read_bytes()).hexdigest()},
        "ATTRIBUTION.md": {"byte_size": attribution.stat().st_size, "sha256": hashlib.sha256(attribution.read_bytes()).hexdigest()},
        "LICENSE": {"byte_size": license_file.stat().st_size, "sha256": hashlib.sha256(license_file.read_bytes()).hexdigest()},
    }
    lock = root / "lock.json"
    lock.write_text(json.dumps({
        "schema_version": 1,
        "dataset_id": "vehiclesdb-vag-identity-cc-by-4.0",
        "publisher": "VehiclesDB",
        "repository": "https://github.com/vehiclesdb/vehiclesdb",
        "upstream_tag": "v2026.10.3",
        "expected_version": "2026.10.3",
        "data_license": "CC-BY-4.0",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "attribution": {"required": True, "text": "Vehicle data by VehiclesDB", "url": "https://vehiclesdb.com"},
        "scope": {"makes": ["volkswagen", "audi"], "kinds": ["car"]},
        "approved_source_license_map": {"nl_rdw": "CC0-1.0", "us_fueleconomy": "US-PD"},
        "excluded_source_reasons": {"th_dlt": "Thailand is outside the product market scope."},
        "not_in_release_sources": {"ro_drpciv": "Not present in pinned release manifest."},
        "expected_source_files": expected_source_files,
        "expected_counts": {"sources": 2, "source_files": 4, "models": 2, "market_evidence": 2},
    }, indent=2), encoding="utf-8")
    return lock, source_db, upstream_manifest, attribution, license_file


class VehiclesDBIdentityPackTests(unittest.TestCase):
    def test_build_and_verify_keeps_only_scoped_vag_identity_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lock, source_db, upstream, attribution, license_file = fixture(root)
            output = root / "pack"
            result = build_pack(lock, source_db, upstream, attribution, license_file, output)
            verified = verify_pack(output, lock)
            self.assertEqual(result["counts"], {"sources": 2, "source_files": 4, "models": 2, "market_evidence": 2})
            self.assertEqual(verified["status"], "verified_identity_candidate_pack")
            self.assertEqual(verified["market_scope_countries"], ["nl", "us"])
            self.assertEqual(verified["not_in_release_sources"], ["ro_drpciv"])
            pack_manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(pack_manifest["not_in_release_sources"], {"ro_drpciv": "Not present in pinned release manifest."})
            db = sqlite3.connect(output / "vag-identity-vehiclesdb.sqlite")
            try:
                self.assertEqual(db.execute("SELECT count(*) FROM model_candidates WHERE make_slug='toyota'").fetchone()[0], 0)
                self.assertEqual(db.execute("SELECT count(*) FROM model_market_evidence WHERE country_code IN ('ru','th')").fetchone()[0], 0)
                self.assertEqual(db.execute("SELECT count(*) FROM model_candidates WHERE fitment_status<>'not_established' OR year_start IS NOT NULL OR year_end IS NOT NULL").fetchone()[0], 0)
            finally:
                db.close()

    def test_upstream_source_file_hash_drift_is_rejected_before_pack_build(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lock, source_db, upstream, attribution, license_file = fixture(root)
            with source_db.open("ab") as stream:
                stream.write(b"unexpected upstream mutation")
            with self.assertRaisesRegex(ValueError, "pinned source file mismatch: catalog.sqlite"):
                build_pack(lock, source_db, upstream, attribution, license_file, root / "pack")

    def test_pack_verifier_rejects_source_snapshot_drift_against_upstream_pin(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lock, source_db, upstream, attribution, license_file = fixture(root)
            output = root / "pack"
            build_pack(lock, source_db, upstream, attribution, license_file, output)
            with (output / "source-snapshot" / "catalog.sqlite").open("ab") as stream:
                stream.write(b"post-build tamper")
            with self.assertRaisesRegex(ValueError, "pinned source file mismatch: catalog.sqlite"):
                verify_pack(output, lock)

    def test_missing_source_file_pins_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lock, source_db, upstream, attribution, license_file = fixture(root)
            lock_data = json.loads(lock.read_text(encoding="utf-8"))
            lock_data.pop("expected_source_files")
            lock.write_text(json.dumps(lock_data), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "expected source-file pins"):
                build_pack(lock, source_db, upstream, attribution, license_file, root / "pack")

    def test_not_in_release_source_cannot_appear_in_pinned_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lock, source_db, upstream, attribution, license_file = fixture(root)
            upstream_data = json.loads(upstream.read_text(encoding="utf-8"))
            upstream_data["sources"].append({"id": "ro_drpciv", "country": "ro", "license": "CC-BY-4.0"})
            upstream.write_text(json.dumps(upstream_data), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "marked not in pinned release is present"):
                build_pack(lock, source_db, upstream, attribution, license_file, root / "pack")

    def test_license_drift_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lock, source_db, upstream, attribution, license_file = fixture(root)
            lock_data = json.loads(lock.read_text(encoding="utf-8"))
            lock_data["approved_source_license_map"]["nl_rdw"] = "CC-BY-4.0"
            lock.write_text(json.dumps(lock_data), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "source license"):
                build_pack(lock, source_db, upstream, attribution, license_file, root / "pack")

    def test_tampered_attribution_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lock, source_db, upstream, attribution, license_file = fixture(root)
            output = root / "pack"
            build_pack(lock, source_db, upstream, attribution, license_file, output)
            (output / "ATTRIBUTION.md").write_text("Missing attribution", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "attribution"):
                verify_pack(output, lock)

    def test_non_empty_output_is_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lock, source_db, upstream, attribution, license_file = fixture(root)
            output = root / "pack"
            output.mkdir()
            (output / "keep.txt").write_text("preserve", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                build_pack(lock, source_db, upstream, attribution, license_file, output)
            self.assertEqual((output / "keep.txt").read_text(encoding="utf-8"), "preserve")


if __name__ == "__main__":
    unittest.main(verbosity=2)
