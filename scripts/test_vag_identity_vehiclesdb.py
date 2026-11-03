#!/usr/bin/env python3
"""Synthetic fixture tests for the VehiclesDB VAG identity pack builder and verifier."""
from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts" / "build_vag_identity_vehiclesdb.py"
VERIFIER = ROOT / "scripts" / "verify_vag_identity_vehiclesdb.py"


def write_fixture(root: Path) -> dict[str, Path]:
    root.mkdir(parents=True, exist_ok=True)
    source_db = root / "catalog.sqlite"
    db = sqlite3.connect(source_db)
    db.executescript("""
      PRAGMA foreign_keys=ON;
      CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
      CREATE TABLE makes(id TEXT NOT NULL,kind TEXT NOT NULL,name TEXT NOT NULL,PRIMARY KEY(id,kind));
      CREATE TABLE models(
        id TEXT NOT NULL,kind TEXT NOT NULL,make_id TEXT NOT NULL,slug TEXT NOT NULL,name TEXT NOT NULL,
        body_types TEXT,regions TEXT,global_popularity_decile INTEGER,mass_popularity_decile INTEGER,
        PRIMARY KEY(id,kind)
      );
      CREATE TABLE availability(
        model_id TEXT NOT NULL,kind TEXT NOT NULL,country TEXT NOT NULL,evidence TEXT NOT NULL,source TEXT NOT NULL,
        PRIMARY KEY(model_id,kind,country,source)
      );
      INSERT INTO meta VALUES('version','test-1');
      INSERT INTO makes VALUES('volkswagen','car','Volkswagen');
      INSERT INTO makes VALUES('audi','car','Audi');
      INSERT INTO makes VALUES('skoda','car','Škoda');
      INSERT INTO models VALUES('volkswagen/golf','car','volkswagen','golf','Golf','["hatchback"]','["eu"]',NULL,NULL);
      INSERT INTO models VALUES('audi/a4','car','audi','a4','A4','["sedan","wagon"]','["eu"]',NULL,NULL);
      INSERT INTO models VALUES('skoda/octavia','car','skoda','octavia','Octavia','["liftback","wagon"]','["eu"]',NULL,NULL);
      INSERT INTO availability VALUES('volkswagen/golf','car','de','registration','de_kba_fz10');
      INSERT INTO availability VALUES('audi/a4','car','ua','registration','ua_mvs');
      INSERT INTO availability VALUES('skoda/octavia','car','il','registration','il_mot');
    """)
    db.commit()
    assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    db.close()

    manifest = {
        "version": "test-1",
        "edition": "open",
        "license": "CC-BY-4.0",
        "attribution": {
            "required": True,
            "text": "Vehicle data by VehiclesDB",
            "url": "https://vehiclesdb.com",
        },
        "countries": ["de", "ua", "il"],
        "kinds": {
            "car": {"makes": 3, "models": 3},
            "van": {"makes": 0, "models": 0},
        },
        "sources": [
            {
                "id": "de_kba_fz10", "country": "de", "name": "German KBA test register",
                "url": "https://example.invalid/de", "license": "DL-DE-BY-2.0",
                "license_url": "https://example.invalid/de-license", "evidence": "registration",
            },
            {
                "id": "ua_mvs", "country": "ua", "name": "Ukrainian MVS test register",
                "url": "https://example.invalid/ua", "license": "CC-BY-4.0",
                "license_url": "https://example.invalid/ua-license", "evidence": "registration",
            },
            {
                "id": "il_mot", "country": "il", "name": "Excluded Israel test source",
                "url": "https://example.invalid/il", "license": "facts-credit-data.gov.il-terms-of-use",
                "license_url": "https://example.invalid/il-license", "evidence": "registration",
            },
        ],
    }
    manifest_path = root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    attribution_path = root / "ATTRIBUTION.md"
    attribution_path.write_text(
        "Vehicle data by [VehiclesDB](https://vehiclesdb.com). "
        "The upstream notices below are UNCONDITIONAL and must be retained.\n",
        encoding="utf-8",
    )
    license_path = root / "LICENSE"
    license_path.write_text(
        "Creative Commons Attribution 4.0 International (CC-BY-4.0)\n"
        "You are free to share and adapt the material for any purpose, even commercially, "
        "provided you give appropriate credit.\n",
        encoding="utf-8",
    )
    lock = {
        "dataset_id": "test-vehiclesdb-vag-identity",
        "publisher": "VehiclesDB",
        "repository": "https://github.com/vehiclesdb/vehiclesdb",
        "upstream_tag": "vtest-1",
        "expected_version": "test-1",
        "data_license": "CC-BY-4.0",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "attribution": {
            "required": True,
            "text": "Vehicle data by VehiclesDB",
            "url": "https://vehiclesdb.com",
            "display_form": "Vehicle data by VehiclesDB (vehiclesdb.com)",
        },
        "scope": {
            "makes": ["volkswagen", "audi", "skoda", "seat", "cupra"],
            "kinds": ["car", "van"],
        },
        "approved_source_license_map": {
            "de_kba_fz10": "DL-DE-BY-2.0",
            "ua_mvs": "CC-BY-4.0",
        },
        "excluded_source_reasons": {
            "il_mot": "Source-specific terms are excluded in this test fixture."
        },
    }
    lock_path = root / "lock.json"
    lock_path.write_text(json.dumps(lock, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "source_db": source_db,
        "manifest": manifest_path,
        "attribution": attribution_path,
        "license": license_path,
        "lock": lock_path,
    }


def run_builder(paths: dict[str, Path], output_dir: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable, str(BUILDER),
            "--lock", str(paths["lock"]),
            "--source-db", str(paths["source_db"]),
            "--manifest", str(paths["manifest"]),
            "--attribution", str(paths["attribution"]),
            "--license", str(paths["license"]),
            "--output-dir", str(output_dir),
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def main() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        paths = write_fixture(root / "fixture")
        output = root / "pack"
        build = run_builder(paths, output)
        if build.returncode:
            raise AssertionError(f"builder failed\n{build.stdout}\n{build.stderr}")

        verify = subprocess.run(
            [sys.executable, str(VERIFIER), "--pack-dir", str(output), "--lock", str(paths["lock"])],
            capture_output=True, text=True, check=False,
        )
        if verify.returncode:
            raise AssertionError(f"verifier failed\n{verify.stdout}\n{verify.stderr}")

        manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["counts"] == {
            "sources": 2, "source_files": 4, "models": 2, "market_evidence": 2
        }, manifest["counts"]
        assert manifest["market_scope_countries"] == ["de", "ua"]
        assert manifest["excluded_evidence_rows"] == {"il_mot": 1}
        db = sqlite3.connect(output / "vag-identity-vehiclesdb.sqlite")
        assert db.execute("SELECT count(*) FROM model_candidates WHERE year_start IS NOT NULL OR year_end IS NOT NULL").fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM model_market_evidence WHERE country_code='ru'").fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM model_candidates WHERE fitment_status<>'not_established'").fetchone()[0] == 0
        db.close()

        # A future source revision that adds RU evidence must fail closed.
        bad_manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
        bad_manifest["countries"].append("ru")
        bad_manifest_path = root / "bad-manifest.json"
        bad_manifest_path.write_text(json.dumps(bad_manifest), encoding="utf-8")
        bad_paths = dict(paths)
        bad_paths["manifest"] = bad_manifest_path
        bad_output = root / "bad-pack"
        rejected = run_builder(bad_paths, bad_output)
        assert rejected.returncode != 0, "RU source coverage unexpectedly passed the gate"
        assert not bad_output.exists(), "Rejected build left a partial output directory"

        # A source license drift must also fail closed.
        bad_manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
        bad_manifest["sources"][0]["license"] = "unknown-license"
        bad_manifest_path.write_text(json.dumps(bad_manifest), encoding="utf-8")
        bad_paths["manifest"] = bad_manifest_path
        rejected = run_builder(bad_paths, root / "license-drift-pack")
        assert rejected.returncode != 0, "Source license drift unexpectedly passed the gate"

    print("PASS: CC-BY attribution, source license allowlist, excluded-source quarantine, market scope, fitment boundary, SQLite integrity")


if __name__ == "__main__":
    main()
