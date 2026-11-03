#!/usr/bin/env python3
"""Fail-closed verifier for the isolated ODbL VAG candidate SQLite pack."""
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
    parser.add_argument("--db", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--lock", required=True, type=Path)
    parser.add_argument("--license", required=True, type=Path)
    args = parser.parse_args()

    lock = read_json(args.lock)
    manifest = read_json(args.manifest)
    if manifest.get("status") != "research_only" or manifest.get("production_import") is not False:
        raise SystemExit("ODbL candidate pack must remain research-only")
    if manifest.get("license") != "ODbL-1.0" or manifest.get("share_alike") != "ODbL-1.0":
        raise SystemExit("ODbL share-alike license metadata mismatch")
    if manifest.get("share_alike_required") is not True:
        raise SystemExit("ODbL share-alike obligation is missing")
    if manifest.get("market_scope") != "UNKNOWN":
        raise SystemExit("Unknown market scope must not be replaced with a market claim")
    if manifest.get("exact_vehicle_fitment") is not False:
        raise SystemExit("Candidate pack must not claim exact vehicle fitment")
    if manifest.get("engine_codes_included") is not False or manifest.get("gearbox_codes_included") is not False:
        raise SystemExit("Candidate pack must not claim factory engine/gearbox codes")
    if manifest.get("ecu_fitment_included") is not False:
        raise SystemExit("Candidate pack must not claim ECU fitment")
    if manifest.get("rights_status") != "upstream_declared_ODbL_1_0":
        raise SystemExit("Upstream license declaration is missing")
    if manifest.get("rights_review_status") != "research_only_upstream_provenance_not_independently_verified":
        raise SystemExit("Upstream provenance review limitation is missing")
    if manifest.get("counts") != lock.get("expected_counts"):
        raise SystemExit("Pack record counts do not match the pinned lock")

    license_text = args.license.read_text(encoding="utf-8-sig")
    normalized_license = " ".join(license_text.split()).lower()
    for phrase in (
        "open database license (odbl) v1.0",
        "opendatacommons.org/licenses/odbl/1-0/",
        "share-alike",
        "autoevolution.com",
    ):
        if phrase not in normalized_license:
            raise SystemExit(f"ODbL license file is missing required term: {phrase}")
    if sha256_file(args.license) != manifest.get("license_sha256"):
        raise SystemExit("ODbL license file SHA-256 mismatch")

    if sha256_file(args.db) != manifest.get("database_sha256"):
        raise SystemExit("SQLite SHA-256 does not match manifest")
    uri = f"file:{args.db.resolve().as_posix()}?mode=ro"
    db = sqlite3.connect(uri, uri=True)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA query_only=ON")
    if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        raise SystemExit("SQLite integrity_check failed")
    if db.execute("PRAGMA foreign_key_check").fetchall():
        raise SystemExit("SQLite foreign_key_check failed")

    required_tables = {
        "research_sources", "source_file_artifacts", "make_candidates",
        "model_candidates", "generation_candidates", "engine_variant_candidates",
    }
    tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if not required_tables.issubset(tables):
        raise SystemExit(f"Missing tables: {sorted(required_tables - tables)}")
    if {"dtc_codes", "technical_documents", "repair_procedures", "wiring_diagrams"} & tables:
        raise SystemExit("Research candidate database must not masquerade as technical repair data")

    counts = {
        "makes": db.execute("SELECT count(*) FROM make_candidates").fetchone()[0],
        "models": db.execute("SELECT count(*) FROM model_candidates").fetchone()[0],
        "generations": db.execute("SELECT count(*) FROM generation_candidates").fetchone()[0],
        "engine_variants": db.execute("SELECT count(*) FROM engine_variant_candidates").fetchone()[0],
    }
    if counts != manifest["counts"]:
        raise SystemExit(f"SQLite counts mismatch: {counts} != {manifest['counts']}")
    if counts != lock["expected_counts"]:
        raise SystemExit(f"SQLite counts differ from lock: {counts} != {lock['expected_counts']}")

    sources = db.execute("SELECT * FROM research_sources ORDER BY source_id").fetchall()
    if len(sources) != len(lock["brands"]):
        raise SystemExit("Unexpected number of brand source records")
    source_hashes = manifest["source_sha256"]
    for row in sources:
        if row["license"] != "ODbL-1.0" or row["share_alike"] != "ODbL-1.0":
            raise SystemExit(f"ODbL license/share-alike mismatch: {row['source_id']}")
        if row["rights_status"] != "upstream_declared_ODbL_1_0":
            raise SystemExit(f"Unexpected rights status: {row['source_id']}")
        if row["rights_review_status"] != "research_only_upstream_provenance_not_independently_verified":
            raise SystemExit(f"Missing provenance limitation: {row['source_id']}")
        if row["market_scope"] != "UNKNOWN" or row["publication_status"] != "research_only":
            raise SystemExit(f"Unsafe source market/publication status: {row['source_id']}")
        brand = row["source_id"].split("-")[1]
        if brand not in source_hashes or row["source_sha256"] != source_hashes[brand]:
            raise SystemExit(f"Source file hash mismatch: {row['source_id']}")
        if row["license_sha256"] != manifest["license_sha256"]:
            raise SystemExit(f"License hash mismatch: {row['source_id']}")
        if row["upstream_revision"] != lock["revision"]:
            raise SystemExit(f"Revision mismatch: {row['source_id']}")

    bad_candidates = db.execute(
        """SELECT
             (SELECT count(*) FROM make_candidates
               WHERE market_scope<>'UNKNOWN' OR review_status<>'candidate'
                  OR applicability_precision<>'make_name_candidate')
           + (SELECT count(*) FROM model_candidates
               WHERE market_scope<>'UNKNOWN' OR review_status<>'candidate'
                  OR applicability_precision<>'model_name_candidate')
           + (SELECT count(*) FROM generation_candidates
               WHERE market_scope<>'UNKNOWN' OR review_status<>'candidate'
                  OR applicability_precision<>'generation_name_candidate')
           + (SELECT count(*) FROM engine_variant_candidates
               WHERE market_scope<>'UNKNOWN' OR review_status<>'candidate'
                  OR applicability_precision<>'engine_variant_description_only'
                  OR engine_code IS NOT NULL OR gearbox_code IS NOT NULL
                  OR code_extraction_status<>'not_provided')"""
    ).fetchone()[0]
    if bad_candidates:
        raise SystemExit(f"Unsafe candidate status/applicability rows: {bad_candidates}")

    artifacts = db.execute("SELECT * FROM source_file_artifacts ORDER BY relative_path").fetchall()
    expected_files = manifest["source_files"]
    if len(artifacts) != len(expected_files):
        raise SystemExit("Source artifact count mismatch")
    seen = set()
    for row in artifacts:
        expected = expected_files.get(row["relative_path"])
        if expected is None:
            raise SystemExit(f"Untracked source file artifact: {row['relative_path']}")
        if row["sha256"] != expected["sha256"] or row["byte_size"] != expected["byte_size"]:
            raise SystemExit(f"Source file hash/size mismatch: {row['relative_path']}")
        if row["file_kind"] != expected["file_kind"] or row["source_url"] != expected["source_url"]:
            raise SystemExit(f"Source file metadata mismatch: {row['relative_path']}")
        seen.add(row["relative_path"])
    if seen != set(expected_files):
        raise SystemExit("One or more source file artifacts are missing")
    if manifest["license_file"] not in expected_files:
        raise SystemExit("License file is absent from the source manifest")

    db.close()
    print(json.dumps({
        "status": "verified_research_only",
        "license": "ODbL-1.0",
        "share_alike_required": True,
        "counts": counts,
        "market_scope": "UNKNOWN",
        "engine_codes": "not_provided",
        "gearbox_codes": "not_provided",
        "exact_vehicle_fitment": False,
        "database_sha256": manifest["database_sha256"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
