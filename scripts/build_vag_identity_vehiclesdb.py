#!/usr/bin/env python3
"""Build an isolated, provenance-preserving VehiclesDB VAG identity candidate SQLite pack.

This pack contains make/model names and per-country presence evidence only.
It does not contain generations, model years, engine/gearbox codes, ECU fitment,
or exact vehicle fitment. It must remain separate from other differently licensed packs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ALLOWED_KINDS = {"car", "van"}
EXPECTED_DATA_LICENSE = "CC-BY-4.0"
ATTRIBUTION_TEXT = "Vehicle data by VehiclesDB"
REQUIRED_TABLES = {"makes", "models", "availability", "meta"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name}: JSON root must be an object")
    return value


def validate_upstream_documents(
    lock: dict[str, Any], upstream_manifest: dict[str, Any], license_text: str, attribution_text: str
) -> None:
    if upstream_manifest.get("version") != lock.get("expected_version"):
        raise ValueError(
            f"VehiclesDB version mismatch: {upstream_manifest.get('version')} != {lock.get('expected_version')}"
        )
    if upstream_manifest.get("edition") != "open":
        raise ValueError("Only the public open VehiclesDB edition may be imported")
    if upstream_manifest.get("license") != EXPECTED_DATA_LICENSE or lock.get("data_license") != EXPECTED_DATA_LICENSE:
        raise ValueError("VehiclesDB data license is not the pinned CC-BY-4.0 license")
    attribution = upstream_manifest.get("attribution")
    if not isinstance(attribution, dict):
        raise ValueError("VehiclesDB attribution object is missing")
    if attribution.get("required") is not True:
        raise ValueError("VehiclesDB attribution requirement unexpectedly changed")
    if attribution.get("text") != ATTRIBUTION_TEXT or attribution.get("url") != "https://vehiclesdb.com":
        raise ValueError("VehiclesDB attribution identity changed; manual review required")
    if "Creative Commons Attribution 4.0 International" not in license_text:
        raise ValueError("The upstream LICENSE file does not identify CC BY 4.0")
    normalized_license = " ".join(license_text.split()).lower()
    if "even commercially" not in normalized_license:
        raise ValueError("The upstream LICENSE file no longer confirms commercial reuse")
    if "VehiclesDB" not in attribution_text or "https://vehiclesdb.com" not in attribution_text or "upstream notices below are UNCONDITIONAL" not in attribution_text:
        raise ValueError("The upstream attribution file is incomplete")
    countries = upstream_manifest.get("countries")
    if not isinstance(countries, list) or "ru" in {str(x).lower() for x in countries}:
        raise ValueError("Unexpected Russian-market coverage; stop and review before import")
    if not isinstance(upstream_manifest.get("sources"), list):
        raise ValueError("Upstream source registry is missing")


def source_map(lock: dict[str, Any], upstream_manifest: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    expected = lock.get("approved_source_license_map")
    excluded = lock.get("excluded_source_reasons")
    if not isinstance(expected, dict) or not isinstance(excluded, dict):
        raise ValueError("Lock file must contain approved and excluded source maps")
    published = {str(row.get("id")): row for row in upstream_manifest["sources"] if isinstance(row, dict)}
    if len(published) != len(upstream_manifest["sources"]):
        raise ValueError("Duplicate or malformed source IDs in upstream manifest")
    allowed: dict[str, dict[str, Any]] = {}
    for source_id, expected_license in expected.items():
        row = published.get(source_id)
        if row is None:
            raise ValueError(f"Pinned source disappeared from upstream manifest: {source_id}")
        if row.get("license") != expected_license:
            raise ValueError(
                f"License drift for {source_id}: {row.get('license')} != {expected_license}"
            )
        country = str(row.get("country") or "").lower()
        if not country or country == "ru":
            raise ValueError(f"Invalid or newly Russian market scope for {source_id}: {country!r}")
        allowed[source_id] = row
    for source_id in excluded:
        if source_id in expected:
            raise ValueError(f"Source cannot be both approved and excluded: {source_id}")
    return allowed, {source_id: published[source_id] for source_id in excluded if source_id in published}


def sqlite_readonly(path: Path) -> sqlite3.Connection:
    uri = f"file:{path.resolve().as_posix()}?mode=ro"
    db = sqlite3.connect(uri, uri=True)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA query_only=ON")
    return db


def table_names(db: sqlite3.Connection) -> set[str]:
    return {
        row[0]
        for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    }


def source_catalog_counts(db: sqlite3.Connection, upstream_manifest: dict[str, Any]) -> None:
    tables = table_names(db)
    if not REQUIRED_TABLES.issubset(tables):
        raise ValueError(f"VehiclesDB SQLite schema mismatch: missing {sorted(REQUIRED_TABLES - tables)}")
    for table, required in {
        "makes": {"id", "kind", "name"},
        "models": {"id", "kind", "make_id", "slug", "name", "body_types", "regions"},
        "availability": {"model_id", "kind", "country", "evidence", "source"},
        "meta": {"key", "value"},
    }.items():
        columns = {row[1] for row in db.execute(f'PRAGMA table_info("{table}")')}
        if not required.issubset(columns):
            raise ValueError(f"VehiclesDB {table} schema mismatch: missing {sorted(required - columns)}")
    if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        raise ValueError("Upstream VehiclesDB SQLite integrity_check failed")
    if db.execute("PRAGMA foreign_key_check").fetchall():
        raise ValueError("Upstream VehiclesDB SQLite foreign_key_check failed")
    meta = {row["key"]: row["value"] for row in db.execute("SELECT key,value FROM meta")}
    if "version" in meta and meta["version"] != upstream_manifest.get("version"):
        raise ValueError("VehiclesDB SQLite meta version does not match the pinned manifest")
    for kind in ALLOWED_KINDS:
        expected = int(upstream_manifest.get("kinds", {}).get(kind, {}).get("models", -1))
        actual = db.execute("SELECT count(*) FROM models WHERE kind=?", (kind,)).fetchone()[0]
        if expected < 0 or actual != expected:
            raise ValueError(f"VehiclesDB {kind} model count mismatch: {actual} != {expected}")


def create_output_schema(db: sqlite3.Connection) -> None:
    db.executescript("""
    PRAGMA foreign_keys=ON;
    CREATE TABLE dataset_provenance (
      provenance_id INTEGER PRIMARY KEY CHECK(provenance_id=1),
      dataset_id TEXT NOT NULL,
      publisher TEXT NOT NULL,
      repository_url TEXT NOT NULL,
      upstream_tag TEXT NOT NULL,
      dataset_version TEXT NOT NULL,
      dataset_license TEXT NOT NULL CHECK(dataset_license='CC-BY-4.0'),
      license_url TEXT NOT NULL,
      attribution_required INTEGER NOT NULL CHECK(attribution_required=1),
      attribution_text TEXT NOT NULL,
      attribution_url TEXT NOT NULL,
      catalog_sqlite_sha256 TEXT NOT NULL CHECK(length(catalog_sqlite_sha256)=64),
      upstream_manifest_sha256 TEXT NOT NULL CHECK(length(upstream_manifest_sha256)=64),
      license_sha256 TEXT NOT NULL CHECK(length(license_sha256)=64),
      attribution_sha256 TEXT NOT NULL CHECK(length(attribution_sha256)=64),
      built_at_utc TEXT NOT NULL,
      ru_evidence_present INTEGER NOT NULL CHECK(ru_evidence_present=0),
      fitment_claim INTEGER NOT NULL CHECK(fitment_claim=0)
    );

    CREATE TABLE source_file_artifacts (
      artifact_id INTEGER PRIMARY KEY,
      relative_path TEXT NOT NULL,
      artifact_kind TEXT NOT NULL CHECK(artifact_kind IN ('sqlite','manifest','license','attribution')),
      byte_size INTEGER NOT NULL CHECK(byte_size>0),
      sha256 TEXT NOT NULL CHECK(length(sha256)=64),
      source_url TEXT NOT NULL,
      UNIQUE(relative_path, artifact_kind)
    );

    CREATE TABLE source_registry (
      source_id TEXT PRIMARY KEY,
      country_code TEXT NOT NULL CHECK(length(country_code)=2 AND country_code<>'ru'),
      source_name TEXT NOT NULL,
      source_url TEXT NOT NULL,
      upstream_license TEXT NOT NULL,
      upstream_license_url TEXT NOT NULL,
      evidence_kind TEXT,
      rights_status TEXT NOT NULL CHECK(rights_status='approved_by_published_license'),
      upstream_attribution_required INTEGER NOT NULL CHECK(upstream_attribution_required IN (0,1)),
      source_notice_preserved INTEGER NOT NULL DEFAULT 1 CHECK(source_notice_preserved=1),
      attribution_notice_file TEXT NOT NULL DEFAULT 'ATTRIBUTION.md'
    );

    CREATE TABLE model_candidates (
      model_candidate_id INTEGER PRIMARY KEY,
      source_model_id TEXT NOT NULL,
      kind TEXT NOT NULL CHECK(kind IN ('car','van')),
      make_slug TEXT NOT NULL,
      make_name TEXT NOT NULL,
      model_slug TEXT NOT NULL,
      model_name TEXT NOT NULL,
      body_types_raw TEXT,
      regions_raw TEXT,
      year_start INTEGER,
      year_end INTEGER,
      applicability_precision TEXT NOT NULL CHECK(applicability_precision='make_model_name_only'),
      verification_status TEXT NOT NULL CHECK(verification_status='identity_candidate'),
      fitment_status TEXT NOT NULL CHECK(fitment_status='not_established'),
      record_fingerprint_sha256 TEXT NOT NULL CHECK(length(record_fingerprint_sha256)=64),
      market_scope_summary_json TEXT NOT NULL,
      UNIQUE(kind,make_slug,model_slug),
      CHECK(year_start IS NULL AND year_end IS NULL)
    );

    CREATE TABLE model_market_evidence (
      evidence_id INTEGER PRIMARY KEY,
      model_candidate_id INTEGER NOT NULL REFERENCES model_candidates(model_candidate_id),
      country_code TEXT NOT NULL CHECK(length(country_code)=2 AND country_code<>'ru'),
      evidence_type TEXT NOT NULL CHECK(evidence_type IN ('registration','approval','sales')),
      source_id TEXT NOT NULL REFERENCES source_registry(source_id),
      applicability_precision TEXT NOT NULL CHECK(applicability_precision='market_presence_only'),
      verification_status TEXT NOT NULL CHECK(verification_status='source_published_presence_evidence'),
      model_year_start INTEGER,
      model_year_end INTEGER,
      UNIQUE(model_candidate_id,country_code,evidence_type,source_id),
      CHECK(model_year_start IS NULL AND model_year_end IS NULL)
    );

    CREATE INDEX idx_model_candidates_name ON model_candidates(make_slug,model_name);
    CREATE INDEX idx_model_evidence_country ON model_market_evidence(country_code,source_id);
    CREATE INDEX idx_model_evidence_model ON model_market_evidence(model_candidate_id);
    """)


def build(args: argparse.Namespace) -> dict[str, Any]:
    lock = read_json(args.lock)
    upstream_manifest = read_json(args.manifest)
    license_text = args.license.read_text(encoding="utf-8-sig")
    attribution_text = args.attribution.read_text(encoding="utf-8-sig")
    validate_upstream_documents(lock, upstream_manifest, license_text, attribution_text)
    allowed_sources, excluded_sources = source_map(lock, upstream_manifest)

    for path in (args.source_db, args.manifest, args.attribution, args.license):
        if not path.is_file() or path.stat().st_size <= 0:
            raise ValueError(f"Missing or empty input file: {path}")
    source_db = sqlite_readonly(args.source_db)
    source_catalog_counts(source_db, upstream_manifest)

    makes = source_db.execute(
        "SELECT id,kind,name FROM makes WHERE lower(id) IN (?,?,?,?,?) AND kind IN ('car','van') ORDER BY kind,id",
        tuple(lock["scope"]["makes"]),
    ).fetchall()
    if not makes:
        raise ValueError("No VAG makes from the pinned allowlist were found")
    make_rows = {(row["kind"], row["id"]): row["name"] for row in makes}

    source_models = source_db.execute(
        """SELECT id,kind,make_id,slug,name,body_types,regions
           FROM models
           WHERE lower(make_id) IN (?,?,?,?,?) AND kind IN ('car','van')
           ORDER BY kind,make_id,slug""",
        tuple(lock["scope"]["makes"]),
    ).fetchall()

    prepared_models: list[dict[str, Any]] = []
    used_source_ids: set[str] = set()
    skipped_models_no_approved_evidence = 0
    excluded_evidence_counts: Counter[str] = Counter()
    country_counts: Counter[str] = Counter()
    make_counts: Counter[str] = Counter()

    for model in source_models:
        make_name = make_rows.get((model["kind"], model["make_id"]))
        if not make_name:
            raise ValueError(f"Model references an unrecognized make: {model['make_id']}")
        evidence_rows = source_db.execute(
            """SELECT country,evidence,source FROM availability
               WHERE model_id=? AND kind=? ORDER BY country,source,evidence""",
            (model["id"], model["kind"]),
        ).fetchall()
        approved_evidence: list[dict[str, Any]] = []
        for evidence in evidence_rows:
            source_id = str(evidence["source"])
            if source_id in allowed_sources:
                source = allowed_sources[source_id]
                if str(evidence["country"]).lower() != str(source["country"]).lower():
                    raise ValueError(f"Country mismatch for source {source_id}")
                if evidence["evidence"] not in {"registration", "approval", "sales"}:
                    raise ValueError(f"Unknown evidence type for {source_id}: {evidence['evidence']}")
                if source.get("evidence") and evidence["evidence"] != source["evidence"]:
                    raise ValueError(f"Evidence type mismatch for source {source_id}")
                approved_evidence.append({
                    "country": str(evidence["country"]).lower(),
                    "evidence": evidence["evidence"],
                    "source_id": source_id,
                })
            elif source_id in excluded_sources:
                excluded_evidence_counts[source_id] += 1
            else:
                raise ValueError(f"Availability references an unreviewed source: {source_id}")
        if not approved_evidence:
            skipped_models_no_approved_evidence += 1
            continue
        countries = sorted({row["country"] for row in approved_evidence})
        fingerprint_payload = {
            "source_model_id": model["id"],
            "kind": model["kind"],
            "make_id": model["make_id"],
            "slug": model["slug"],
            "name": model["name"],
            "body_types": model["body_types"],
            "regions": model["regions"],
            "approved_evidence": approved_evidence,
        }
        prepared_models.append({
            "source_model_id": model["id"],
            "kind": model["kind"],
            "make_slug": model["make_id"],
            "make_name": make_name,
            "model_slug": model["slug"],
            "model_name": model["name"],
            "body_types_raw": model["body_types"],
            "regions_raw": model["regions"],
            "fingerprint": hashlib.sha256(canonical_json(fingerprint_payload).encode("utf-8")).hexdigest(),
            "countries": countries,
            "evidence": approved_evidence,
        })
        used_source_ids.update(row["source_id"] for row in approved_evidence)
        country_counts.update(row["country"] for row in approved_evidence)
        make_counts[model["make_id"]] += 1

    source_db.close()
    if not prepared_models:
        raise ValueError("No VAG model candidates with approved country evidence were found")

    output_dir = args.output_dir.resolve()
    if output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite existing output directory: {output_dir}")
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    temp_dir = Path(tempfile.mkdtemp(prefix="vag-identity-build-", dir=output_dir.parent))
    database_path = temp_dir / "vag-identity-vehiclesdb.sqlite"

    catalog_hash = sha256_file(args.source_db)
    upstream_manifest_hash = sha256_file(args.manifest)
    license_hash = sha256_file(args.license)
    attribution_hash = sha256_file(args.attribution)
    built_at = datetime.now(timezone.utc).isoformat()

    db = None
    try:
        db = sqlite3.connect(database_path)
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA journal_mode=DELETE")
        db.execute("PRAGMA synchronous=FULL")
        create_output_schema(db)
        db.execute("BEGIN IMMEDIATE")
        db.execute(
            """INSERT INTO dataset_provenance
               (provenance_id,dataset_id,publisher,repository_url,upstream_tag,dataset_version,
                dataset_license,license_url,attribution_required,attribution_text,attribution_url,
                catalog_sqlite_sha256,upstream_manifest_sha256,license_sha256,attribution_sha256,
                built_at_utc,ru_evidence_present,fitment_claim)
               VALUES(1,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0,0)""",
            (
                lock["dataset_id"], lock["publisher"], lock["repository"], lock["upstream_tag"],
                upstream_manifest["version"], EXPECTED_DATA_LICENSE, lock["license_url"],
                1, ATTRIBUTION_TEXT, "https://vehiclesdb.com", catalog_hash,
                upstream_manifest_hash, license_hash, attribution_hash, built_at,
            ),
        )
        attribution_required_licenses = {
            "CC-BY-4.0", "CC-BY-3.0-AU", "OGL-UK-3.0", "DL-DE-BY-2.0",
            "OGL-Canada-2.0", "Ley-37/2007",
        }
        for source_id in sorted(used_source_ids):
            row = allowed_sources[source_id]
            upstream_attribution_required = 1 if row["license"] in attribution_required_licenses else 0
            db.execute(
                """INSERT INTO source_registry
                   (source_id,country_code,source_name,source_url,upstream_license,
                    upstream_license_url,evidence_kind,rights_status,
                    upstream_attribution_required,source_notice_preserved)
                   VALUES(?,?,?,?,?,?,?,'approved_by_published_license',?,1)""",
                (
                    source_id, str(row["country"]).lower(), row["name"], row["url"],
                    row["license"], row["license_url"], row.get("evidence"),
                    upstream_attribution_required,
                ),
            )
        for filename, kind, path, url in (
            ("catalog.sqlite", "sqlite", args.source_db, f"https://cdn.jsdelivr.net/gh/vehiclesdb/vehiclesdb@{lock['upstream_tag']}/dist/catalog.sqlite"),
            ("manifest.json", "manifest", args.manifest, f"https://cdn.jsdelivr.net/gh/vehiclesdb/vehiclesdb@{lock['upstream_tag']}/manifest.json"),
            ("LICENSE", "license", args.license, f"https://cdn.jsdelivr.net/gh/vehiclesdb/vehiclesdb@{lock['upstream_tag']}/LICENSE"),
            ("ATTRIBUTION.md", "attribution", args.attribution, f"https://cdn.jsdelivr.net/gh/vehiclesdb/vehiclesdb@{lock['upstream_tag']}/ATTRIBUTION.md"),
        ):
            db.execute(
                """INSERT INTO source_file_artifacts
                   (relative_path,artifact_kind,byte_size,sha256,source_url)
                   VALUES(?,?,?,?,?)""",
                (filename, kind, path.stat().st_size, sha256_file(path), url),
            )

        for model in prepared_models:
            cur = db.execute(
                """INSERT INTO model_candidates
                   (source_model_id,kind,make_slug,make_name,model_slug,model_name,
                    body_types_raw,regions_raw,year_start,year_end,applicability_precision,
                    verification_status,fitment_status,record_fingerprint_sha256,market_scope_summary_json)
                   VALUES(?,?,?,?,?,?,?,?,NULL,NULL,'make_model_name_only','identity_candidate',
                          'not_established',?,?)""",
                (
                    model["source_model_id"], model["kind"], model["make_slug"], model["make_name"],
                    model["model_slug"], model["model_name"], model["body_types_raw"], model["regions_raw"],
                    model["fingerprint"], canonical_json(model["countries"]),
                ),
            )
            model_candidate_id = cur.lastrowid
            for evidence in model["evidence"]:
                db.execute(
                    """INSERT INTO model_market_evidence
                       (model_candidate_id,country_code,evidence_type,source_id,
                        applicability_precision,verification_status,model_year_start,model_year_end)
                       VALUES(?,?,?,?, 'market_presence_only','source_published_presence_evidence',NULL,NULL)""",
                    (model_candidate_id, evidence["country"], evidence["evidence"], evidence["source_id"]),
                )
        db.commit()
        integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
        fk_errors = db.execute("PRAGMA foreign_key_check").fetchall()
        if integrity != "ok" or fk_errors:
            raise RuntimeError(f"Output SQLite verification failed: integrity={integrity}, fk={fk_errors}")
        counts = {
            "sources": db.execute("SELECT count(*) FROM source_registry").fetchone()[0],
            "source_files": db.execute("SELECT count(*) FROM source_file_artifacts").fetchone()[0],
            "models": db.execute("SELECT count(*) FROM model_candidates").fetchone()[0],
            "market_evidence": db.execute("SELECT count(*) FROM model_market_evidence").fetchone()[0],
        }
        db.close()
        db = None

        shutil.copy2(args.manifest, temp_dir / "UPSTREAM-MANIFEST.json")
        shutil.copy2(args.license, temp_dir / "LICENSE.txt")
        shutil.copy2(args.attribution, temp_dir / "ATTRIBUTION.md")
        database_hash = sha256_file(database_path)
        source_countries = sorted(country_counts)
        pack_manifest = {
            "schema_version": 1,
            "dataset_id": lock["dataset_id"],
            "status": "identity_candidate_pack_verified",
            "publisher": lock["publisher"],
            "repository": lock["repository"],
            "upstream_tag": lock["upstream_tag"],
            "dataset_version": upstream_manifest["version"],
            "dataset_license": EXPECTED_DATA_LICENSE,
            "license_url": lock["license_url"],
            "attribution": lock["attribution"],
            "source_snapshot_sha256": {
                "catalog.sqlite": catalog_hash,
                "manifest.json": upstream_manifest_hash,
                "LICENSE": license_hash,
                "ATTRIBUTION.md": attribution_hash,
            },
            "source_snapshot_bytes": {
                "catalog.sqlite": args.source_db.stat().st_size,
                "manifest.json": args.manifest.stat().st_size,
                "LICENSE": args.license.stat().st_size,
                "ATTRIBUTION.md": args.attribution.stat().st_size,
            },
            "country_evidence_counts": dict(sorted(country_counts.items())),
            "database_file": "vag-identity-vehiclesdb.sqlite",
            "database_sha256": database_hash,
            "counts": counts,
            "make_counts": dict(sorted(make_counts.items())),
            "market_scope_countries": source_countries,
            "ru_evidence_present": False,
            "excluded_sources": lock["excluded_source_reasons"],
            "excluded_evidence_rows": dict(sorted(excluded_evidence_counts.items())),
            "models_without_approved_evidence_skipped": skipped_models_no_approved_evidence,
            "applicability_precision": "make_model_name_only",
            "verification_status": "identity_candidate",
            "fitment_status": "not_established",
            "generation_data_included": False,
            "model_year_data_included": False,
            "engine_codes_included": False,
            "gearbox_codes_included": False,
            "ecu_fitment_included": False,
            "fitment_claim": False,
            "built_at_utc": built_at,
            "integrity_check": integrity,
            "foreign_key_errors": len(fk_errors),
        }
        (temp_dir / "manifest.json").write_text(
            json.dumps(pack_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        if output_dir.exists():
            raise FileExistsError(f"Output directory appeared during build: {output_dir}")
        os.replace(temp_dir, output_dir)
        return pack_manifest
    except Exception:
        if db is not None:
            try:
                db.close()
            except sqlite3.Error:
                pass
        try:
            shutil.rmtree(temp_dir)
        except OSError:
            pass
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--source-db", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--attribution", type=Path, required=True)
    parser.add_argument("--license", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = build(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
