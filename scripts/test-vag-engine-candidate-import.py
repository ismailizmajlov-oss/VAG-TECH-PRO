#!/usr/bin/env python3
"""Synthetic tests for the isolated ODbL VAG candidate importer and verifier."""
from __future__ import annotations

import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMPORTER = ROOT / "scripts" / "import_vag_engine_candidates.py"
VERIFIER = ROOT / "scripts" / "verify_vag_engine_candidate_import.py"
BRANDS = ("audi", "volkswagen", "skoda", "seat", "cupra")
REVISION = "ee99776470a45214bf524cdfe22e5dbf4bd67f93"
LICENSE_TEXT = (
    "Open Database License (ODbL) v1.0\n"
    "Canonical license: https://opendatacommons.org/licenses/odbl/1-0/\n"
    "The database is available under the ODbL share-alike terms. "
    "The source data was compiled from autoevolution.com.\n"
)


def fixture(root: Path) -> tuple[Path, Path]:
    input_dir = root / "input"
    input_dir.mkdir(parents=True)
    for brand in BRANDS:
        data = {
            "group": brand,
            "makes": [{
                "name": brand.title(),
                "models": [{
                    "name": "Fixture",
                    "yearStart": 2000,
                    "yearEnd": 2005,
                    "generations": [{
                        "name": "Fixture Gen",
                        "yearStart": 2000,
                        "yearEnd": 2005,
                        "bodyType": "hatchback",
                        "engines": [{
                            "label": "2.0L TDI 6-speed manual (140 HP)",
                            "fuelType": "Diesel",
                            "cylinders": 4,
                            "displacementCc": 1968,
                            "powerHp": 140,
                            "torqueNm": 320,
                            "transmission": "6-speed manual",
                            "drivetrain": "Front Wheel Drive",
                            "specs": {"ENGINE SPECS / Power": "140 HP"},
                        }],
                    }],
                }],
            }],
        }
        (input_dir / f"{brand}.json").write_text(
            json.dumps(data, ensure_ascii=False), encoding="utf-8"
        )
    (input_dir / "LICENSE-DATA").write_text(LICENSE_TEXT, encoding="utf-8")

    lock = {
        "schema_version": 1,
        "source_id_prefix": "vag",
        "publisher": "gor3a",
        "dataset": "vehicle-makes-models",
        "repository_url": "https://github.com/gor3a/vehicle-makes-models",
        "revision": REVISION,
        "upstream_source": "autoevolution.com (as declared by upstream)",
        "license": "ODbL-1.0",
        "license_url": "https://opendatacommons.org/licenses/odbl/1-0/",
        "license_file": "LICENSE-DATA",
        "attribution": "Credit gor3a/vehicle-makes-models and autoevolution.com; link source and note changes.",
        "share_alike_required": True,
        "market_scope": "UNKNOWN",
        "brands": list(BRANDS),
        "source_files": {brand: f"data/json/{brand}.json" for brand in BRANDS},
        "expected_counts": {"makes": 5, "models": 5, "generations": 5, "engine_variants": 5},
        "applicability_policy": {
            "make": "make_name_candidate",
            "model": "model_name_candidate",
            "generation": "generation_name_candidate",
            "engine_variant": "engine_variant_description_only",
            "exact_vehicle_fitment": False,
            "exact_engine_codes_included": False,
            "exact_gearbox_codes_included": False,
            "market_scope_unknown": True,
            "review_status": "candidate",
            "production_import": False,
        },
    }
    lock_path = root / "lock.json"
    lock_path.write_text(json.dumps(lock, ensure_ascii=False, indent=2), encoding="utf-8")
    return input_dir, lock_path


def run_import(input_dir: Path, lock: Path, output: Path, manifest: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable, str(IMPORTER),
            "--lock", str(lock),
            "--input-dir", str(input_dir),
            "--output", str(output),
            "--manifest", str(manifest),
        ],
        capture_output=True, text=True, check=False,
    )


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        input_dir, lock = fixture(root)
        output = root / "artifacts" / "research.sqlite"
        manifest = root / "artifacts" / "research.manifest.json"
        run = run_import(input_dir, lock, output, manifest)
        if run.returncode:
            raise AssertionError(f"importer failed\nSTDOUT:\n{run.stdout}\nSTDERR:\n{run.stderr}")

        verify = subprocess.run(
            [
                sys.executable, str(VERIFIER),
                "--db", str(output),
                "--manifest", str(manifest),
                "--lock", str(lock),
                "--license", str(output.parent / "LICENSE-DATA"),
            ],
            capture_output=True, text=True, check=False,
        )
        if verify.returncode:
            raise AssertionError(f"verifier failed\nSTDOUT:\n{verify.stdout}\nSTDERR:\n{verify.stderr}")

        db = sqlite3.connect(output)
        assert db.execute("SELECT count(*) FROM model_candidates").fetchone()[0] == 5
        assert db.execute("SELECT count(*) FROM generation_candidates").fetchone()[0] == 5
        assert db.execute("SELECT count(*) FROM engine_variant_candidates").fetchone()[0] == 5
        row = db.execute(
            "SELECT engine_code,gearbox_code,code_extraction_status,market_scope,applicability_precision "
            "FROM engine_variant_candidates LIMIT 1"
        ).fetchone()
        assert row == (None, None, "not_provided", "UNKNOWN", "engine_variant_description_only"), row
        assert db.execute(
            "SELECT count(*) FROM engine_variant_candidates "
            "WHERE engine_code IS NOT NULL OR gearbox_code IS NOT NULL"
        ).fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM source_file_artifacts").fetchone()[0] == 6
        assert db.execute("SELECT count(*) FROM research_sources").fetchone()[0] == 5
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
        db.close()

        # A license file that no longer confirms ODbL must stop the import.
        bad_license_dir = root / "bad-license-input"
        shutil.copytree(input_dir, bad_license_dir)
        (bad_license_dir / "LICENSE-DATA").write_text("MIT License\n", encoding="utf-8")
        bad_output = root / "bad-license" / "research.sqlite"
        bad_manifest = root / "bad-license" / "research.manifest.json"
        rejected = run_import(bad_license_dir, lock, bad_output, bad_manifest)
        assert rejected.returncode != 0, "Invalid license unexpectedly passed the import gate"
        assert not bad_output.exists() and not bad_manifest.exists()

        # Explicit engine/gearbox code fields require manual review and are not silently discarded.
        bad_code_dir = root / "bad-code-input"
        shutil.copytree(input_dir, bad_code_dir)
        bad_payload = json.loads((bad_code_dir / "audi.json").read_text(encoding="utf-8"))
        bad_payload["makes"][0]["models"][0]["generations"][0]["engines"][0]["engineCode"] = "TEST"
        (bad_code_dir / "audi.json").write_text(json.dumps(bad_payload), encoding="utf-8")
        rejected = run_import(
            bad_code_dir, lock, root / "bad-code" / "research.sqlite",
            root / "bad-code" / "research.manifest.json",
        )
        assert rejected.returncode != 0, "New upstream engine-code field unexpectedly passed"
        assert not (root / "bad-code" / "research.sqlite").exists()

    print("PASS: ODbL license gate, source hashes, share-alike metadata, UNKNOWN market, candidate applicability, no inferred codes, atomic rejection, SQLite integrity")


if __name__ == "__main__":
    main()
