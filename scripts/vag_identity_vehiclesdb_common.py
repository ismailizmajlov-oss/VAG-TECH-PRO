#!/usr/bin/env python3
"""Rights-gated VehiclesDB VAG identity-candidate pack builder and verifier.

This package is a make/model identity aid only. It never establishes RU/EAEU
presence, generation, year, engine/gearbox code, ECU fitment, or repair fitment.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PACK_ID = "vehiclesdb-vag-identity"
DATASET_LICENSE = "CC-BY-4.0"
APPROVED_RIGHTS_STATUS = "approved_by_published_license"
EXCLUDED_COUNTRIES = {"ru", "th"}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def connect_readonly(path: Path) -> sqlite3.Connection:
    uri = f"file:{path.resolve().as_posix()}?mode=ro"
    db = sqlite3.connect(uri, uri=True)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA query_only=ON")
    if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        db.close()
        raise ValueError(f"Upstream SQLite integrity_check failed: {path}")
    if db.execute("PRAGMA foreign_key_check").fetchall():
        db.close()
        raise ValueError(f"Upstream SQLite foreign_key_check failed: {path}")
    return db


def table_names(db: sqlite3.Connection) -> set[str]:
    return {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def table_count(db: sqlite3.Connection, table: str) -> int:
    return int(db.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0])


def expected_counts(lock: dict[str, Any]) -> dict[str, int]:
    value = lock.get("expected_counts")
    if not isinstance(value, dict):
        raise ValueError("Lock file must pin expected_counts")
    required = {"sources", "source_files", "models", "market_evidence"}
    if set(value) != required or any(not isinstance(value[k], int) or value[k] < 0 for k in required):
        raise ValueError("Lock expected_counts schema is invalid")
    return {k: int(value[k]) for k in required}


def _source_snapshot(source_db: Path, source_manifest: Path, attribution: Path, license_file: Path) -> dict[str, dict[str, Any]]:
    files = {
        "catalog.sqlite": source_db,
        "manifest.json": source_manifest,
        "ATTRIBUTION.md": attribution,
        "LICENSE": license_file,
    }
    return {
        name: {"path": path, "byte_size": path.stat().st_size, "sha256": sha256_file(path)}
        for name, path in files.items()
    }


def _validate_inputs(lock: dict[str, Any], upstream: dict[str, Any], attribution_text: str, license_text: str) -> tuple[dict[str, str], dict[str, str], list[str], list[str]]:
    if lock.get("schema_version") != 1 or lock.get("dataset_id") != "vehiclesdb-vag-identity-cc-by-4.0":
        raise ValueError("VehiclesDB lock identity/schema mismatch")
    if upstream.get("version") != lock.get("expected_version") or upstream.get("version") != lock.get("upstream_tag", "").removeprefix("v"):
        raise ValueError("VehiclesDB pinned release version mismatch")
    if upstream.get("license") != DATASET_LICENSE or lock.get("data_license") != DATASET_LICENSE:
        raise ValueError("VehiclesDB data license mismatch")
    if lock.get("license_url") != "https://creativecommons.org/licenses/by/4.0/":
        raise ValueError("VehiclesDB license URL is not the pinned CC BY 4.0 license")
    if "creative commons attribution 4.0 international" not in " ".join(license_text.lower().split()):
        raise ValueError("VehiclesDB CC BY 4.0 license text is missing")
    if "even commercially" not in " ".join(license_text.lower().split()):
        raise ValueError("VehiclesDB commercial-use grant is missing")
    if "VehiclesDB" not in attribution_text or "https://vehiclesdb.com" not in attribution_text:
        raise ValueError("VehiclesDB attribution notice is incomplete")
    attribution = lock.get("attribution", {})
    if attribution.get("required") is not True or "Vehicle data by VehiclesDB" not in attribution.get("text", ""):
        raise ValueError("VehiclesDB attribution requirement is missing from the lock")

    approved = lock.get("approved_source_license_map")
    excluded = lock.get("excluded_source_reasons")
    not_in_release = lock.get("not_in_release_sources")
    scope = lock.get("scope")
    if (not isinstance(approved, dict) or not approved or not isinstance(excluded, dict)
            or not isinstance(not_in_release, dict) or not isinstance(scope, dict)):
        raise ValueError("VehiclesDB source-rights, absent-source or scope lock is invalid")
    if set(approved) & set(excluded) or set(approved) & set(not_in_release) or set(excluded) & set(not_in_release):
        raise ValueError("A VehiclesDB source cannot be approved, excluded and/or marked absent at the same time")
    makes = scope.get("makes")
    kinds = scope.get("kinds")
    if not isinstance(makes, list) or not makes or not isinstance(kinds, list) or not kinds:
        raise ValueError("VehiclesDB VAG make/kind scope is missing")
    if any(str(x).lower() in EXCLUDED_COUNTRIES for x in upstream.get("countries", [])):
        # Country presence in the upstream release is allowed; output evidence is filtered below.
        pass
    upstream_sources = {str(item.get("id")): item for item in upstream.get("sources", []) if isinstance(item, dict)}
    absent_but_present = set(upstream_sources) & set(not_in_release)
    if absent_but_present:
        raise ValueError("VehiclesDB source marked not in pinned release is present: " + ", ".join(sorted(absent_but_present)))
    if set(upstream_sources) != set(approved) | set(excluded):
        raise ValueError("VehiclesDB upstream source list differs from the pinned approved/excluded source map")
    for source_id, expected_license in approved.items():
        source = upstream_sources.get(source_id)
        if not source or source.get("license") != expected_license:
            raise ValueError(f"VehiclesDB source license drift: {source_id}")
        if source.get("country") in EXCLUDED_COUNTRIES:
            raise ValueError(f"VehiclesDB source from excluded market entered approved map: {source_id}")
    return (
        {str(k): str(v) for k, v in approved.items()},
        {str(k): str(v) for k, v in excluded.items()},
        [str(x).lower() for x in makes],
        [str(x).lower() for x in kinds],
    )


DDL = """
PRAGMA foreign_keys=ON;
CREATE TABLE dataset_provenance(
  dataset_id TEXT PRIMARY KEY,
  publisher TEXT NOT NULL,
  repository TEXT NOT NULL,
  upstream_tag TEXT NOT NULL,
  dataset_version TEXT NOT NULL,
  dataset_license TEXT NOT NULL,
  license_url TEXT NOT NULL,
  upstream_manifest_sha256 TEXT NOT NULL CHECK(length(upstream_manifest_sha256)=64),
  source_catalog_sha256 TEXT NOT NULL CHECK(length(source_catalog_sha256)=64),
  attribution_sha256 TEXT NOT NULL CHECK(length(attribution_sha256)=64),
  license_sha256 TEXT NOT NULL CHECK(length(license_sha256)=64),
  lock_sha256 TEXT NOT NULL CHECK(length(lock_sha256)=64),
  imported_at_utc TEXT NOT NULL
);
CREATE TABLE source_file_artifacts(
  source_path TEXT PRIMARY KEY,
  byte_size INTEGER NOT NULL CHECK(byte_size>=0),
  sha256 TEXT NOT NULL CHECK(length(sha256)=64),
  source_role TEXT NOT NULL
);
CREATE TABLE source_registry(
  source_id TEXT PRIMARY KEY,
  country_code TEXT NOT NULL,
  source_name TEXT NOT NULL,
  source_url TEXT,
  source_license TEXT NOT NULL,
  source_license_url TEXT,
  evidence_type TEXT,
  rights_status TEXT NOT NULL CHECK(rights_status='approved_by_published_license')
);
CREATE TABLE model_candidates(
  model_id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  make_id TEXT NOT NULL,
  make_slug TEXT NOT NULL,
  make_name TEXT NOT NULL,
  model_slug TEXT NOT NULL,
  model_name TEXT NOT NULL,
  body_types_json TEXT NOT NULL,
  regions_json TEXT NOT NULL,
  market_scope_json TEXT NOT NULL,
  source_ids_json TEXT NOT NULL,
  year_start INTEGER,
  year_end INTEGER,
  generation_data_included INTEGER NOT NULL CHECK(generation_data_included=0),
  model_year_data_included INTEGER NOT NULL CHECK(model_year_data_included=0),
  engine_codes_included INTEGER NOT NULL CHECK(engine_codes_included=0),
  gearbox_codes_included INTEGER NOT NULL CHECK(gearbox_codes_included=0),
  ecu_fitment_included INTEGER NOT NULL CHECK(ecu_fitment_included=0),
  fitment_status TEXT NOT NULL CHECK(fitment_status='not_established'),
  applicability_precision TEXT NOT NULL CHECK(applicability_precision='make_model_name_only'),
  verification_status TEXT NOT NULL CHECK(verification_status='identity_candidate')
);
CREATE TABLE model_market_evidence(
  model_id TEXT NOT NULL REFERENCES model_candidates(model_id),
  source_id TEXT NOT NULL REFERENCES source_registry(source_id),
  country_code TEXT NOT NULL,
  evidence_type TEXT NOT NULL,
  applicability_precision TEXT NOT NULL CHECK(applicability_precision='market_presence_only'),
  verification_status TEXT NOT NULL CHECK(verification_status='source_published_presence_evidence'),
  PRIMARY KEY(model_id, source_id, country_code)
);
CREATE INDEX idx_model_candidates_make ON model_candidates(make_slug, model_name);
CREATE INDEX idx_model_market_evidence_country ON model_market_evidence(country_code, model_id);
"""


def build_pack(lock_path: Path, source_db_path: Path, upstream_manifest_path: Path,
               attribution_path: Path, license_path: Path, output_dir: Path) -> dict[str, Any]:
    lock = read_json(lock_path)
    upstream = read_json(upstream_manifest_path)
    attribution_text = attribution_path.read_text(encoding="utf-8-sig")
    license_text = license_path.read_text(encoding="utf-8-sig")
    approved, excluded, scoped_makes, scoped_kinds = _validate_inputs(lock, upstream, attribution_text, license_text)
    not_in_release = lock["not_in_release_sources"]
    snapshot = _source_snapshot(source_db_path, upstream_manifest_path, attribution_path, license_path)
    pinned_counts = expected_counts(lock)

    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"Refusing to overwrite non-empty output directory: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    source_snapshot_dir = output_dir / "source-snapshot"
    source_snapshot_dir.mkdir()
    copied_paths = {
        "catalog.sqlite": source_snapshot_dir / "catalog.sqlite",
        "manifest.json": output_dir / "UPSTREAM-MANIFEST.json",
        "ATTRIBUTION.md": output_dir / "ATTRIBUTION.md",
        "LICENSE": output_dir / "LICENSE.txt",
    }
    shutil.copyfile(source_db_path, copied_paths["catalog.sqlite"])
    shutil.copyfile(upstream_manifest_path, copied_paths["manifest.json"])
    shutil.copyfile(attribution_path, copied_paths["ATTRIBUTION.md"])
    shutil.copyfile(license_path, copied_paths["LICENSE"])

    source_db = connect_readonly(source_db_path)
    try:
        required_tables = {"sources", "makes", "models", "availability"}
        missing = required_tables - table_names(source_db)
        if missing:
            raise ValueError(f"VehiclesDB source SQLite is missing tables: {sorted(missing)}")

        source_rows = {
            row["id"]: dict(row)
            for row in source_db.execute("SELECT id,country,name,url,license,license_url,evidence FROM sources")
        }
        if set(source_rows) != set(approved) | set(excluded):
            raise ValueError("VehiclesDB SQLite source registry differs from pinned manifest")
        upstream_source_rows = {str(item["id"]): item for item in upstream.get("sources", [])}
        for source_id, expected_license in approved.items():
            row = source_rows[source_id]
            manifest_source = upstream_source_rows[source_id]
            if row["license"] != expected_license or row["country"] != manifest_source.get("country"):
                raise ValueError(f"VehiclesDB SQLite source provenance mismatch: {source_id}")
            if row["country"] in EXCLUDED_COUNTRIES:
                raise ValueError(f"Excluded country entered approved source registry: {source_id}")

        allowed_placeholders = ",".join("?" for _ in approved)
        kind_placeholders = ",".join("?" for _ in scoped_kinds)
        make_placeholders = ",".join("?" for _ in scoped_makes)
        evidence_rows = list(source_db.execute(
            f"""SELECT a.kind,a.model_id,a.country,a.evidence,a.source
                FROM availability a
                WHERE a.source IN ({allowed_placeholders})
                  AND a.kind IN ({kind_placeholders})
                ORDER BY a.kind,a.model_id,a.country,a.source""",
            [*approved.keys(), *scoped_kinds],
        ))
        evidence_by_model: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for row in evidence_rows:
            item = dict(row)
            source = source_rows[item["source"]]
            if item["country"] != source["country"]:
                raise ValueError(f"VehiclesDB model evidence/source country mismatch: {item['source']}")
            if item["country"] in EXCLUDED_COUNTRIES:
                raise ValueError(f"Excluded market evidence entered output: {item['country']}")
            evidence_by_model.setdefault((item["kind"], item["model_id"]), []).append(item)

        model_query = f"""SELECT m.kind,m.id,m.make_id,m.slug,m.name,m.global_decile,m.mass_decile,
                                  mk.slug AS make_slug,mk.name AS make_name
                           FROM models m
                           JOIN makes mk ON mk.kind=m.kind AND mk.id=m.make_id
                           WHERE lower(m.make_id) IN ({make_placeholders})
                             AND lower(m.kind) IN ({kind_placeholders})
                           ORDER BY lower(m.make_id),lower(m.name),m.kind,m.id"""
        model_rows = list(source_db.execute(model_query, [*scoped_makes, *scoped_kinds]))
        selected_models: list[dict[str, Any]] = []
        for row in model_rows:
            key = (row["kind"], row["id"])
            evidence = evidence_by_model.get(key, [])
            if not evidence:
                continue
            body_types: list[str] = []
            regions: list[str] = []
            if "model_body_types" in table_names(source_db):
                body_types = [r[0] for r in source_db.execute(
                    "SELECT body_type FROM model_body_types WHERE kind=? AND model_id=? ORDER BY position,body_type",
                    key,
                )]
            if "model_regions" in table_names(source_db):
                regions = [r[0] for r in source_db.execute(
                    "SELECT region FROM model_regions WHERE kind=? AND model_id=? ORDER BY region", key
                )]
            countries = sorted({item["country"] for item in evidence})
            source_ids = sorted({item["source"] for item in evidence})
            selected_models.append({
                "model_id": f'{row["kind"]}/{row["id"]}',
                "kind": row["kind"],
                "make_id": row["make_id"],
                "make_slug": row["make_slug"],
                "make_name": row["make_name"],
                "model_slug": row["slug"],
                "model_name": row["name"],
                "body_types": body_types,
                "regions": regions,
                "countries": countries,
                "source_ids": source_ids,
                "evidence": evidence,
            })

        if not selected_models:
            raise ValueError("VehiclesDB VAG identity candidate selection produced no models")

        db_path = output_dir / "vag-identity-vehiclesdb.sqlite"
        output_db = sqlite3.connect(db_path)
        try:
            output_db.execute("PRAGMA foreign_keys=ON")
            output_db.execute("PRAGMA journal_mode=DELETE")
            output_db.execute("PRAGMA synchronous=FULL")
            output_db.executescript(DDL)
            with output_db:
                output_db.execute(
                    """INSERT INTO dataset_provenance VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        PACK_ID, "VehiclesDB", lock["repository"], lock["upstream_tag"], upstream["version"],
                        DATASET_LICENSE, lock["license_url"], snapshot["manifest.json"]["sha256"],
                        snapshot["catalog.sqlite"]["sha256"], snapshot["ATTRIBUTION.md"]["sha256"],
                        snapshot["LICENSE"]["sha256"], sha256_file(lock_path),
                        datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    ),
                )
                for source_id in sorted(approved):
                    row = source_rows[source_id]
                    output_db.execute(
                        """INSERT INTO source_registry VALUES(?,?,?,?,?,?,?,?)""",
                        (
                            source_id, row["country"], row["name"], row["url"], row["license"],
                            row["license_url"], row["evidence"], APPROVED_RIGHTS_STATUS,
                        ),
                    )
                for name, item in snapshot.items():
                    out_path = copied_paths[name]
                    output_db.execute(
                        "INSERT INTO source_file_artifacts VALUES(?,?,?,?)",
                        (
                            str(out_path.relative_to(output_dir)).replace("\\", "/"),
                            item["byte_size"], item["sha256"], name,
                        ),
                    )
                for item in selected_models:
                    output_db.execute(
                        """INSERT INTO model_candidates VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (
                            item["model_id"], item["kind"], item["make_id"], item["make_slug"], item["make_name"],
                            item["model_slug"], item["model_name"], json.dumps(item["body_types"], ensure_ascii=False),
                            json.dumps(item["regions"], ensure_ascii=False), json.dumps(item["countries"], ensure_ascii=False),
                            json.dumps(item["source_ids"], ensure_ascii=False), None, None, 0, 0, 0, 0, 0,
                            "not_established", "make_model_name_only", "identity_candidate",
                        ),
                    )
                    for evidence in item["evidence"]:
                        output_db.execute(
                            "INSERT INTO model_market_evidence VALUES(?,?,?,?,?,?)",
                            (
                                item["model_id"], evidence["source"], evidence["country"], evidence["evidence"],
                                "market_presence_only", "source_published_presence_evidence",
                            ),
                        )
            if output_db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("Output VehiclesDB SQLite integrity_check failed")
            if output_db.execute("PRAGMA foreign_key_check").fetchall():
                raise ValueError("Output VehiclesDB SQLite foreign_key_check failed")
            counts = {
                "sources": table_count(output_db, "source_registry"),
                "source_files": table_count(output_db, "source_file_artifacts"),
                "models": table_count(output_db, "model_candidates"),
                "market_evidence": table_count(output_db, "model_market_evidence"),
            }
            market_countries = sorted(row[0] for row in output_db.execute(
                "SELECT DISTINCT country_code FROM model_market_evidence"
            ))
            make_counts = {
                row[0]: row[1] for row in output_db.execute(
                    "SELECT make_slug,count(*) FROM model_candidates GROUP BY make_slug ORDER BY make_slug"
                )
            }
        finally:
            output_db.close()

    finally:
        source_db.close()

    if counts != pinned_counts:
        raise ValueError(f"VehiclesDB output counts differ from lock: {counts} != {pinned_counts}")
    if EXCLUDED_COUNTRIES.intersection(market_countries):
        raise ValueError("VehiclesDB output contains excluded RU/TH market evidence")

    source_snapshot_sha256 = {name: item["sha256"] for name, item in snapshot.items()}
    pack_manifest = {
        "schema_version": 1,
        "pack_id": PACK_ID,
        "publisher": "VehiclesDB",
        "source_repository": lock["repository"],
        "upstream_tag": lock["upstream_tag"],
        "dataset_version": upstream["version"],
        "source_revision": lock["upstream_tag"],
        "dataset_license": DATASET_LICENSE,
        "data_license": DATASET_LICENSE,
        "license_url": lock["license_url"],
        "rights_status": APPROVED_RIGHTS_STATUS,
        "attribution_required": True,
        "attribution": lock["attribution"],
        "share_alike_required": False,
        "status": "identity_candidate_pack_verified",
        "verification_status": "identity_candidate",
        "review_status": "identity_candidate",
        "product_eligibility": "make_model_identity_candidate_only_foreign_market_presence",
        "market_scope": "foreign_market_presence_only",
        "market_scope_countries": market_countries,
        "approved_source_license_map": approved,
        "excluded_source_reasons": excluded,
        "not_in_release_sources": not_in_release,
        "applicability_precision": "make_model_name_only",
        "fitment_status": "not_established",
        "fitment_claim": False,
        "exact_fitment": False,
        "ru_evidence_present": False,
        "generation_data_included": False,
        "model_year_data_included": False,
        "engine_codes_included": False,
        "gearbox_codes_included": False,
        "ecu_fitment_included": False,
        "pr_code_fitment_included": False,
        "counts": counts,
        "make_counts": make_counts,
        "database_file": db_path.name,
        "database_sha256": sha256_file(db_path),
        "source_manifest_sha256": snapshot["manifest.json"]["sha256"],
        "source_catalog_sha256": snapshot["catalog.sqlite"]["sha256"],
        "lock_sha256": sha256_file(lock_path),
        "source_snapshot_sha256": source_snapshot_sha256,
        "source_file_artifacts": [
            {"path": str(copied_paths[name].relative_to(output_dir)).replace("\\", "/"),
             "byte_size": item["byte_size"], "sha256": item["sha256"], "source_file": name}
            for name, item in snapshot.items()
        ],
        "warnings": [
            "Foreign-market model-presence evidence only; no Russian/EAEU market evidence is present.",
            "The open VehiclesDB release does not supply generations, model years, engine codes, gearbox codes, ECU fitment or PR-code fitment for this pack.",
            "A make/model candidate is not exact vehicle fitment, an OEM configuration, or a repair recommendation.",
            "Keep this CC-BY-4.0 dataset separate and preserve VehiclesDB plus all upstream register attribution notices.",
        ],
        "built_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    write_json(output_dir / "manifest.json", pack_manifest)
    return pack_manifest


def verify_pack(pack_dir: Path, lock_path: Path, *, strict_counts: bool = True) -> dict[str, Any]:
    pack_dir = pack_dir.resolve()
    lock = read_json(lock_path)
    manifest = read_json(pack_dir / "manifest.json")
    upstream_path = pack_dir / "UPSTREAM-MANIFEST.json"
    attribution_path = pack_dir / "ATTRIBUTION.md"
    license_path = pack_dir / "LICENSE.txt"
    db_path = pack_dir / str(manifest.get("database_file", "vag-identity-vehiclesdb.sqlite"))
    required_files = [upstream_path, attribution_path, license_path, db_path, pack_dir / "source-snapshot" / "catalog.sqlite"]
    if any(not path.is_file() for path in required_files):
        raise ValueError("VehiclesDB pack is missing a required source/provenance file")
    upstream = read_json(upstream_path)
    approved, excluded, _, _ = _validate_inputs(
        lock, upstream, attribution_path.read_text(encoding="utf-8-sig"),
        license_path.read_text(encoding="utf-8-sig"),
    )
    if manifest.get("status") != "identity_candidate_pack_verified" or manifest.get("dataset_license") != DATASET_LICENSE:
        raise ValueError("VehiclesDB pack status/license mismatch")
    if (manifest.get("approved_source_license_map") != approved
            or manifest.get("excluded_source_reasons") != excluded
            or manifest.get("not_in_release_sources") != lock.get("not_in_release_sources")):
        raise ValueError("VehiclesDB pack approved/excluded/absent source map mismatch")
    if manifest.get("ru_evidence_present") is not False or manifest.get("fitment_claim") is not False:
        raise ValueError("VehiclesDB RU-market or exact-fitment boundary failed")
    if any(manifest.get(key) is not False for key in (
        "generation_data_included", "model_year_data_included", "engine_codes_included",
        "gearbox_codes_included", "ecu_fitment_included", "pr_code_fitment_included",
    )):
        raise ValueError("VehiclesDB generation/year/engine/gearbox/ECU boundary failed")
    if upstream.get("version") != manifest.get("dataset_version") or upstream.get("license") != DATASET_LICENSE:
        raise ValueError("VehiclesDB upstream manifest version/license mismatch")
    if sha256_file(db_path) != manifest.get("database_sha256"):
        raise ValueError("VehiclesDB SQLite hash mismatch")
    source_snapshot = manifest.get("source_snapshot_sha256", {})
    path_map = {
        "catalog.sqlite": pack_dir / "source-snapshot" / "catalog.sqlite",
        "manifest.json": upstream_path,
        "ATTRIBUTION.md": attribution_path,
        "LICENSE": license_path,
    }
    for name, path in path_map.items():
        if not path.is_file() or sha256_file(path) != source_snapshot.get(name):
            raise ValueError(f"VehiclesDB source snapshot hash mismatch: {name}")

    db = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA query_only=ON")
    try:
        if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok" or db.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("VehiclesDB output SQLite integrity/foreign-key check failed")
        tables = table_names(db)
        required = {"dataset_provenance", "source_file_artifacts", "source_registry", "model_candidates", "model_market_evidence"}
        if not required.issubset(tables):
            raise ValueError("VehiclesDB output SQLite schema mismatch")
        counts = {
            "sources": table_count(db, "source_registry"),
            "source_files": table_count(db, "source_file_artifacts"),
            "models": table_count(db, "model_candidates"),
            "market_evidence": table_count(db, "model_market_evidence"),
        }
        if counts != manifest.get("counts"):
            raise ValueError(f"VehiclesDB manifest/SQLite counts mismatch: {counts}")
        if strict_counts and counts != expected_counts(lock):
            raise ValueError(f"VehiclesDB pinned output counts mismatch: {counts}")
        if set(row[0] for row in db.execute("SELECT source_id FROM source_registry")) != set(approved):
            raise ValueError("VehiclesDB output source registry differs from approved source map")
        if db.execute("SELECT count(*) FROM source_registry WHERE rights_status<>? ", (APPROVED_RIGHTS_STATUS,)).fetchone()[0]:
            raise ValueError("VehiclesDB source rights status mismatch")
        upstream_sources = {str(item["id"]): item for item in upstream.get("sources", [])}
        for source_id, expected_license in approved.items():
            row = db.execute("SELECT source_license,country_code FROM source_registry WHERE source_id=?", (source_id,)).fetchone()
            upstream_row = upstream_sources[source_id]
            if not row or row["source_license"] != expected_license:
                raise ValueError(f"VehiclesDB source license mismatch in output: {source_id}")
            if row["country_code"] != upstream_row.get("country"):
                raise ValueError(f"VehiclesDB source country mismatch in output: {source_id}")
        allowed_makes = {str(value).lower() for value in lock["scope"]["makes"]}
        allowed_kinds = {str(value).lower() for value in lock["scope"]["kinds"]}
        for model in db.execute("SELECT model_id,make_slug,kind,market_scope_json,source_ids_json FROM model_candidates"):
            if model["make_slug"].lower() not in allowed_makes or model["kind"].lower() not in allowed_kinds:
                raise ValueError(f"VehiclesDB out-of-scope model candidate: {model['model_id']}")
            expected_countries = sorted(row[0] for row in db.execute(
                "SELECT DISTINCT country_code FROM model_market_evidence WHERE model_id=?", (model["model_id"],)
            ))
            expected_sources = sorted(row[0] for row in db.execute(
                "SELECT DISTINCT source_id FROM model_market_evidence WHERE model_id=?", (model["model_id"],)
            ))
            if json.loads(model["market_scope_json"]) != expected_countries:
                raise ValueError(f"VehiclesDB model market scope/provenance mismatch: {model['model_id']}")
            if json.loads(model["source_ids_json"]) != expected_sources:
                raise ValueError(f"VehiclesDB model source provenance mismatch: {model['model_id']}")
        if db.execute("""SELECT count(*) FROM model_candidates
                         WHERE fitment_status<>'not_established' OR year_start IS NOT NULL OR year_end IS NOT NULL
                           OR applicability_precision<>'make_model_name_only'
                           OR verification_status<>'identity_candidate'
                           OR generation_data_included<>0 OR model_year_data_included<>0
                           OR engine_codes_included<>0 OR gearbox_codes_included<>0 OR ecu_fitment_included<>0""").fetchone()[0]:
            raise ValueError("VehiclesDB model candidate precision boundary failed")
        if db.execute("""SELECT count(*) FROM model_market_evidence
                         WHERE applicability_precision<>'market_presence_only'
                           OR verification_status<>'source_published_presence_evidence'
                           OR lower(country_code) IN ('ru','th')""").fetchone()[0]:
            raise ValueError("VehiclesDB market evidence precision/exclusion boundary failed")
        if db.execute("""SELECT count(*) FROM model_market_evidence e
                         JOIN source_registry s ON s.source_id=e.source_id
                         WHERE s.country_code<>e.country_code""").fetchone()[0]:
            raise ValueError("VehiclesDB evidence/source country mismatch")
        countries = sorted(row[0] for row in db.execute("SELECT DISTINCT country_code FROM model_market_evidence"))
        if countries != manifest.get("market_scope_countries") or EXCLUDED_COUNTRIES.intersection(countries):
            raise ValueError("VehiclesDB market scope summary mismatch")
        artifact_rows = list(db.execute("SELECT source_path,byte_size,sha256 FROM source_file_artifacts"))
        if len(artifact_rows) != 4:
            raise ValueError("VehiclesDB source artifact registry must contain exactly four upstream files")
        for row in artifact_rows:
            path = pack_dir / row["source_path"]
            if not path.is_file() or path.stat().st_size != row["byte_size"] or sha256_file(path) != row["sha256"]:
                raise ValueError(f"VehiclesDB source artifact hash mismatch: {row['source_path']}")
        expected_artifact_paths = {
            "source-snapshot/catalog.sqlite", "UPSTREAM-MANIFEST.json", "ATTRIBUTION.md", "LICENSE.txt"
        }
        if {row["source_path"] for row in artifact_rows} != expected_artifact_paths:
            raise ValueError("VehiclesDB source artifact path set mismatch")
        provenance = db.execute("SELECT * FROM dataset_provenance").fetchone()
        if provenance is None or table_count(db, "dataset_provenance") != 1:
            raise ValueError("VehiclesDB dataset provenance row count mismatch")
        if (
            provenance["dataset_id"] != PACK_ID
            or provenance["repository"] != lock["repository"]
            or provenance["upstream_tag"] != lock["upstream_tag"]
            or provenance["dataset_version"] != upstream["version"]
            or provenance["dataset_license"] != DATASET_LICENSE
            or provenance["upstream_manifest_sha256"] != source_snapshot["manifest.json"]
            or provenance["source_catalog_sha256"] != source_snapshot["catalog.sqlite"]
            or provenance["attribution_sha256"] != source_snapshot["ATTRIBUTION.md"]
            or provenance["license_sha256"] != source_snapshot["LICENSE"]
            or provenance["lock_sha256"] != sha256_file(lock_path)
        ):
            raise ValueError("VehiclesDB dataset provenance record mismatch")
        if manifest.get("source_manifest_sha256") != source_snapshot["manifest.json"] or manifest.get("source_catalog_sha256") != source_snapshot["catalog.sqlite"]:
            raise ValueError("VehiclesDB manifest/source snapshot provenance mismatch")
    finally:
        db.close()
    return {"status": "verified_identity_candidate_pack", "counts": counts, "market_scope_countries": countries,
            "database_sha256": manifest["database_sha256"], "source_snapshot_sha256": source_snapshot,
            "excluded_sources": sorted(excluded), "not_in_release_sources": sorted(lock["not_in_release_sources"])}


def main_build(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--source-db", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--attribution", type=Path, required=True)
    parser.add_argument("--license", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    result = build_pack(args.lock, args.source_db, args.manifest, args.attribution, args.license, args.output_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def main_verify(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--pack-dir", type=Path, required=True)
    parser.add_argument("--lock", type=Path, required=True)
    args = parser.parse_args(argv)
    result = verify_pack(args.pack_dir, args.lock)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0
