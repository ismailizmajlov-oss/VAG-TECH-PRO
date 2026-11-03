#!/usr/bin/env python3
"""Fail-closed verifier for the VehiclesDB VAG identity candidate SQLite pack."""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise SystemExit(f"Invalid JSON object: {path}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pack-dir", type=Path, required=True)
    parser.add_argument("--lock", type=Path, required=True)
    args = parser.parse_args()

    root = args.pack_dir.resolve()
    manifest = read_json(root / "manifest.json")
    lock = read_json(args.lock)
    upstream = read_json(root / "UPSTREAM-MANIFEST.json")

    if manifest.get("status") != "identity_candidate_pack_verified":
        raise SystemExit("Pack status is not verified")
    if manifest.get("dataset_license") != "CC-BY-4.0":
        raise SystemExit("Unexpected dataset license")
    if manifest.get("attribution", {}).get("required") is not True:
        raise SystemExit("Required VehiclesDB attribution is missing")
    if manifest.get("attribution", {}).get("text") != "Vehicle data by VehiclesDB":
        raise SystemExit("VehiclesDB attribution text mismatch")
    if manifest.get("ru_evidence_present") is not False or manifest.get("fitment_claim") is not False:
        raise SystemExit("Unsafe Russian-market or fitment claim")
    if manifest.get("generation_data_included") is not False:
        raise SystemExit("Identity pack must not claim generation data")
    if manifest.get("model_year_data_included") is not False:
        raise SystemExit("Identity pack must not claim model-year data")
    if manifest.get("engine_codes_included") is not False or manifest.get("gearbox_codes_included") is not False:
        raise SystemExit("Identity pack must not claim engine/gearbox codes")
    if upstream.get("version") != lock.get("expected_version"):
        raise SystemExit("Upstream manifest version mismatch")
    if upstream.get("license") != "CC-BY-4.0" or upstream.get("edition") != "open":
        raise SystemExit("Upstream manifest license/edition mismatch")

    attribution = (root / "ATTRIBUTION.md").read_text(encoding="utf-8-sig")
    license_text = (root / "LICENSE.txt").read_text(encoding="utf-8-sig")
    if "Vehicle data by" not in attribution or "upstream notices below are UNCONDITIONAL" not in attribution:
        raise SystemExit("Required VehiclesDB and upstream attribution notices are absent")
    if "Creative Commons Attribution 4.0 International" not in license_text or "even commercially" not in license_text.lower():
        raise SystemExit("CC BY 4.0 commercial-use license text is absent")

    db_path = root / manifest["database_file"]
    if sha256_file(db_path) != manifest["database_sha256"]:
        raise SystemExit("SQLite SHA-256 does not match pack manifest")
    for filename, expected in (
        ("UPSTREAM-MANIFEST.json", manifest["source_snapshot_sha256"]["manifest.json"]),
        ("LICENSE.txt", manifest["source_snapshot_sha256"]["LICENSE"]),
        ("ATTRIBUTION.md", manifest["source_snapshot_sha256"]["ATTRIBUTION.md"]),
    ):
        if sha256_file(root / filename) != expected:
            raise SystemExit(f"Source snapshot hash mismatch: {filename}")

    uri = f"file:{db_path.resolve().as_posix()}?mode=ro"
    db = sqlite3.connect(uri, uri=True)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA query_only=ON")
    if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        raise SystemExit("SQLite integrity_check failed")
    if db.execute("PRAGMA foreign_key_check").fetchall():
        raise SystemExit("SQLite foreign_key_check failed")

    required_tables = {
        "dataset_provenance", "source_file_artifacts", "source_registry",
        "model_candidates", "model_market_evidence",
    }
    tables = {
        row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    if not required_tables.issubset(tables):
        raise SystemExit(f"Missing tables: {sorted(required_tables - tables)}")
    if {"engine_codes", "transmission_codes", "ecu_units", "dtc_codes"} & tables:
        raise SystemExit("Identity candidate pack must not contain technical fitment tables")

    provenance = db.execute("SELECT * FROM dataset_provenance WHERE provenance_id=1").fetchone()
    if provenance is None:
        raise SystemExit("Dataset provenance row is missing")
    if provenance["dataset_version"] != lock["expected_version"] or provenance["dataset_license"] != "CC-BY-4.0":
        raise SystemExit("Dataset provenance version/license mismatch")
    if provenance["ru_evidence_present"] != 0 or provenance["fitment_claim"] != 0:
        raise SystemExit("Dataset provenance contains an unsafe claim")

    allowed = lock["approved_source_license_map"]
    sources = db.execute("SELECT * FROM source_registry ORDER BY source_id").fetchall()
    source_ids = {row["source_id"] for row in sources}
    if not source_ids or not source_ids.issubset(set(allowed)):
        raise SystemExit("Pack includes an unapproved or empty source registry")
    for row in sources:
        if row["upstream_license"] != allowed[row["source_id"]]:
            raise SystemExit(f"Source license mismatch: {row['source_id']}")
        if row["rights_status"] != "approved_by_published_license":
            raise SystemExit(f"Source rights are not approved: {row['source_id']}")
        if row["country_code"] == "ru":
            raise SystemExit("Russian market evidence must not be inferred from this dataset")

    bad_models = db.execute(
        """SELECT count(*) FROM model_candidates
           WHERE kind NOT IN ('car','van')
              OR make_slug NOT IN ('volkswagen','audi','skoda','seat','cupra')
              OR applicability_precision<>'make_model_name_only'
              OR verification_status<>'identity_candidate'
              OR fitment_status<>'not_established'
              OR year_start IS NOT NULL OR year_end IS NOT NULL"""
    ).fetchone()[0]
    if bad_models:
        raise SystemExit(f"Unsafe model candidate rows: {bad_models}")
    bad_evidence = db.execute(
        """SELECT count(*) FROM model_market_evidence
           WHERE country_code='ru'
              OR applicability_precision<>'market_presence_only'
              OR verification_status<>'source_published_presence_evidence'
              OR model_year_start IS NOT NULL OR model_year_end IS NOT NULL"""
    ).fetchone()[0]
    if bad_evidence:
        raise SystemExit(f"Unsafe market evidence rows: {bad_evidence}")
    invalid_refs = db.execute(
        """SELECT count(*) FROM model_market_evidence e
           LEFT JOIN source_registry s ON s.source_id=e.source_id
           WHERE s.source_id IS NULL OR s.country_code<>e.country_code"""
    ).fetchone()[0]
    if invalid_refs:
        raise SystemExit(f"Market evidence/source mismatches: {invalid_refs}")

    counts = {
        "sources": db.execute("SELECT count(*) FROM source_registry").fetchone()[0],
        "source_files": db.execute("SELECT count(*) FROM source_file_artifacts").fetchone()[0],
        "models": db.execute("SELECT count(*) FROM model_candidates").fetchone()[0],
        "market_evidence": db.execute("SELECT count(*) FROM model_market_evidence").fetchone()[0],
    }
    if counts != manifest["counts"]:
        raise SystemExit(f"Manifest/database count mismatch: {counts} != {manifest['counts']}")
    if counts["source_files"] != 4 or counts["models"] < 1 or counts["market_evidence"] < 1:
        raise SystemExit("Unexpected source-file/model/evidence counts")
    countries = sorted(row[0] for row in db.execute(
        "SELECT DISTINCT country_code FROM model_market_evidence ORDER BY country_code"
    ))
    if countries != manifest["market_scope_countries"] or "ru" in countries or "th" in countries:
        raise SystemExit("Market scope summary mismatch or prohibited market found")
    artifact_rows = db.execute("SELECT * FROM source_file_artifacts").fetchall()
    if len(artifact_rows) != 4 or any(len(row["sha256"]) != 64 or row["byte_size"] <= 0 for row in artifact_rows):
        raise SystemExit("Source artifact provenance rows are incomplete")

    db.close()
    result = {
        "status": "verified",
        "database_sha256": manifest["database_sha256"],
        "dataset_version": manifest["dataset_version"],
        "license": manifest["dataset_license"],
        "counts": counts,
        "market_scope_countries": countries,
        "ru_evidence_present": False,
        "applicability_precision": "make_model_name_only",
        "fitment_claim": False,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
