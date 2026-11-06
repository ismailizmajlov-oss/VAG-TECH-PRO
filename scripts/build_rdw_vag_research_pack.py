#!/usr/bin/env python3
"""Build an isolated CC0 RDW Netherlands/EU type-approval research SQLite pack.

The pack is not a Russian/EAEU fitment source. It preserves exact RDW approval
scope, keeps engine designations and gearbox classifications separate, and
never stores registration plates, VINs, holders, or owner data.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE = "https://opendata.rdw.nl"
SOURCE_ID = "rdw-eu-vag-type-approval-open-data-nl"
REGISTRATION_ID = "m9d7-ebf2"
MAKES = ["AUDI", "BENTLEY", "BUGATTI", "CUPRA", "LAMBORGHINI", "PORSCHE", "SEAT", "SKODA", "VOLKSWAGEN"]
FORBIDDEN_TOKENS = ("kenteken", "vin", "houder", "tenaamstelling", "owner", "address", "postcode")
PAGE_SIZE = 50000
MAX_TOTAL_ROWS_PER_DATASET = 500000
MAX_APPROVAL_NUMBERS = 50000
APPROVAL_BATCH_SIZE = 20

REGISTRATION_GROUP_FIELDS = [
    "merk", "handelsbenaming", "typegoedkeuringsnummer", "variant", "uitvoering",
    "volgnummer_wijziging_eu_typegoedkeuring", "voertuigsoort",
]
REGISTRATION_SELECT = REGISTRATION_GROUP_FIELDS + ["count(*) as registration_count"]
DATASETS: dict[str, dict[str, Any]] = {
    "registration": {
        "id": REGISTRATION_ID,
        "required": REGISTRATION_GROUP_FIELDS + ["datum_eerste_toelating", "cilinderinhoud", "aantal_cilinders"],
        "select": REGISTRATION_SELECT,
        "group": REGISTRATION_GROUP_FIELDS,
        "variant_field": "variant",
        "scope_fields": {
            "approval": "typegoedkeuringsnummer", "variant": "variant",
            "version": "uitvoering", "revision": "volgnummer_wijziging_eu_typegoedkeuring",
        },
    },
    "tgk_drive": {
        "id": "4by9-ammk",
        "required": ["typegoedkeuringsnummer", "codevarianttgk", "codeuitvoeringtgk",
                     "volgnummerrevisieuitvoering", "motorcode", "typegoedkeuringsnummermotor",
                     "aantalcilinders", "cilinderinhoud"],
        "select": ["typegoedkeuringsnummer", "codevarianttgk", "codeuitvoeringtgk",
                   "volgnummerrevisieuitvoering", "motorcode", "typegoedkeuringsnummermotor",
                   "aantalcilinders", "cilinderinhoud"],
        "variant_field": "codevarianttgk",
    },
    "tgk_gearbox": {
        "id": "7rjk-eycs",
        "required": ["typegoedkeuringsnummer", "codevarianttgk", "codeuitvoeringtgk",
                     "volgnummerrevisieuitvoering", "codetypeversnellingsbak"],
        "select": ["typegoedkeuringsnummer", "codevarianttgk", "codeuitvoeringtgk",
                   "volgnummerrevisieuitvoering", "codetypeversnellingsbak"],
        "variant_field": "codevarianttgk",
    },
    "tgk_base": {
        "id": "byxc-wwua",
        "required": ["typegoedkeuringsnummer", "codevarianttgk", "codeuitvoeringtgk",
                     "volgnummerrevisieuitvoering", "begindatumrevisieuitvoering", "voertuigcategorie"],
        "select": ["typegoedkeuringsnummer", "codevarianttgk", "codeuitvoeringtgk",
                   "volgnummerrevisieuitvoering", "begindatumrevisieuitvoering", "voertuigcategorie"],
        "variant_field": "codevarianttgk",
    },
    "tgk_make": {
        "id": "kyri-nuah",
        "required": ["typegoedkeuringsnummer", "codevarianttgk", "codeuitvoeringtgk",
                     "volgnummerrevisieuitvoering", "merkcoderdw"],
        "select": ["typegoedkeuringsnummer", "codevarianttgk", "codeuitvoeringtgk",
                   "volgnummerrevisieuitvoering", "merkcoderdw"],
        "variant_field": "codevarianttgk",
    },
    "tgk_trade_name": {
        "id": "x5v3-sewk",
        "required": ["typegoedkeuringsnummer", "codevariantgk", "codeuitvoeringtgk",
                     "volgnummerrevisieuitvoering", "handelsbenamingfabrikant", "typeaanduidingfabrikant"],
        "select": ["typegoedkeuringsnummer", "codevariantgk", "codeuitvoeringtgk",
                   "volgnummerrevisieuitvoering", "handelsbenamingfabrikant", "typeaanduidingfabrikant"],
        "variant_field": "codevariantgk",
    },
}


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def build_soda_url(dataset_id: str, params: dict[str, str]) -> str:
    if not dataset_id or any(ch not in "abcdefghijklmnopqrstuvwxyz0123456789-" for ch in dataset_id):
        raise ValueError("Invalid RDW dataset id")
    return f"{BASE}/resource/{dataset_id}.json?{urllib.parse.urlencode(params)}"


def soql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def chunks(values: list[str], size: int):
    for start in range(0, len(values), size):
        yield values[start:start + size]


def fetch_json(url: str, attempts: int = 5) -> Any:
    last_error: Exception | None = None
    for attempt in range(attempts):
        request = urllib.request.Request(
            url,
            headers={"Accept": "application/json", "User-Agent": "VAG-TECH-PRO-RDW-research-pack/1.0"},
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                if response.status != 200:
                    raise RuntimeError(f"RDW HTTP {response.status}")
                raw = response.read(64 * 1024 * 1024 + 1)
                if len(raw) > 64 * 1024 * 1024:
                    raise RuntimeError("RDW response exceeded 64 MiB safety limit")
                return json.loads(raw.decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, RuntimeError) as exc:
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(min(2 ** attempt, 20))
    raise RuntimeError(f"RDW request failed after {attempts} attempts: {last_error}") from last_error


def metadata_columns(metadata: dict[str, Any]) -> set[str]:
    return {
        str(item.get("fieldName") or item.get("name"))
        for item in metadata.get("columns", [])
        if item.get("fieldName") or item.get("name")
    }


def fetch_metadata(dataset_id: str) -> dict[str, Any]:
    return fetch_json(f"{BASE}/api/views/{dataset_id}.json")


def reject_forbidden_fields(value: Any, location: str = "row") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            lowered = str(key).lower()
            if any(token in lowered for token in FORBIDDEN_TOKENS):
                raise ValueError(f"Forbidden RDW field {key!r} at {location}")
            reject_forbidden_fields(child, f"{location}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            reject_forbidden_fields(child, f"{location}[{index}]")


def query_all(dataset_id: str, params: dict[str, str], page_size: int = PAGE_SIZE) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    offset = 0
    while True:
        query = dict(params)
        query["$limit"] = str(page_size)
        query["$offset"] = str(offset)
        page = fetch_json(build_soda_url(dataset_id, query))
        if not isinstance(page, list):
            raise ValueError(f"Unexpected RDW JSON shape for {dataset_id}")
        for row in page:
            if not isinstance(row, dict):
                raise ValueError(f"Non-object row in RDW dataset {dataset_id}")
            reject_forbidden_fields(row, dataset_id)
        result.extend(page)
        if len(result) > MAX_TOTAL_ROWS_PER_DATASET:
            raise ValueError(f"RDW {dataset_id} exceeded the {MAX_TOTAL_ROWS_PER_DATASET} row safety cap")
        if len(page) < page_size:
            break
        offset += len(page)
        time.sleep(0.15)
    return result


def scope_key(row: dict[str, Any], variant_field: str) -> tuple[str, str, str, str] | None:
    values = (
        str(row.get("typegoedkeuringsnummer") or ""),
        str(row.get(variant_field) or ""),
        str(row.get("codeuitvoeringtgk") or ""),
        str(row.get("volgnummerrevisieuitvoering") or ""),
    )
    return values if all(values) else None


def scope_id(key: tuple[str, str, str, str]) -> str:
    return sha256_bytes(canonical_bytes(list(key)))


def query_source_rows(manifest: dict[str, Any]) -> tuple[dict[str, list[dict[str, Any]]], dict[str, dict[str, Any]]]:
    metadata_report: dict[str, dict[str, Any]] = {}
    for name, config in DATASETS.items():
        dataset_id = str(config["id"])
        metadata = fetch_metadata(dataset_id)
        columns = metadata_columns(metadata)
        missing = sorted(set(config["required"]) - columns)
        if missing:
            raise ValueError(f"RDW {dataset_id} missing required fields: {missing}")
        revision = metadata.get("rowsUpdatedAt") or metadata.get("viewLastModified")
        if not revision:
            raise ValueError(f"RDW {dataset_id} has no source revision timestamp")
        required_columns = sorted(config["required"])
        metadata_report[name] = {
            "dataset_id": dataset_id,
            "rows_updated_at": metadata.get("rowsUpdatedAt"),
            "view_last_modified": metadata.get("viewLastModified"),
            "source_columns_sha256": sha256_bytes(canonical_bytes(sorted(columns))),
            "required_columns": required_columns,
            "required_columns_sha256": sha256_bytes(canonical_bytes(required_columns)),
        }
        time.sleep(0.15)

    make_literals = ",".join(soql_literal(make) for make in MAKES)
    registration_where = (
        f"merk in ({make_literals}) AND typegoedkeuringsnummer IS NOT NULL "
        f"AND voertuigsoort='Personenauto' AND cilinderinhoud > 0"
    )
    registration_params = {
        "$select": ",".join(REGISTRATION_SELECT),
        "$where": registration_where,
        "$group": ",".join(REGISTRATION_GROUP_FIELDS),
        "$order": ",".join(REGISTRATION_GROUP_FIELDS),
    }
    metadata_report["registration"]["query_spec"] = {
        "dataset_id": REGISTRATION_ID,
        "select": REGISTRATION_SELECT,
        "where": registration_where,
        "group": REGISTRATION_GROUP_FIELDS,
        "order": REGISTRATION_GROUP_FIELDS,
        "make_allowlist": MAKES,
        "market_scope": ["NL"],
        "privacy_filter": "No registration plate, VIN, holder, owner, address or personal fields requested.",
    }
    registration_rows = query_all(REGISTRATION_ID, registration_params)
    if not registration_rows:
        raise ValueError("RDW returned no VAG passenger-car approval observations")

    keys: set[tuple[str, str, str, str]] = set()
    for row in registration_rows:
        if str(row.get("merk") or "").upper() not in MAKES:
            raise ValueError("RDW registration aggregate escaped the VAG make allowlist")
        key = scope_key({
            "typegoedkeuringsnummer": row.get("typegoedkeuringsnummer"),
            "variant": row.get("variant"),
            "codeuitvoeringtgk": row.get("uitvoering"),
            "volgnummerrevisieuitvoering": row.get("volgnummer_wijziging_eu_typegoedkeuring"),
        }, "variant")
        if key:
            keys.add(key)

    approval_numbers = sorted({key[0] for key in keys})
    if not approval_numbers:
        raise ValueError("RDW VAG registration observations contained no complete approval scope keys")
    if len(approval_numbers) > MAX_APPROVAL_NUMBERS:
        raise ValueError(f"RDW VAG approval-number scope exceeded safety cap: {len(approval_numbers)}")

    output: dict[str, list[dict[str, Any]]] = {"registration": registration_rows}
    for name, config in DATASETS.items():
        if name == "registration":
            continue
        metadata_report[name]["query_spec"] = {
            "dataset_id": str(config["id"]),
            "select": config["select"],
            "where_template": "typegoedkeuringsnummer IN (approval-number batch)",
            "approval_numbers_count": len(approval_numbers),
            "approval_numbers_sha256": sha256_bytes(canonical_bytes(approval_numbers)),
            "approval_batch_size": APPROVAL_BATCH_SIZE,
            "exact_scope_filter": [
                "typegoedkeuringsnummer",
                str(config["variant_field"]),
                "codeuitvoeringtgk",
                "volgnummerrevisieuitvoering",
            ],
            "market_scope": ["NL"],
        }
        collected: list[dict[str, Any]] = []
        variant_field = str(config["variant_field"])
        for batch in chunks(approval_numbers, APPROVAL_BATCH_SIZE):
            where = "typegoedkeuringsnummer in (" + ",".join(soql_literal(value) for value in batch) + ")"
            params = {"$select": ",".join(config["select"]), "$where": where}
            rows = query_all(str(config["id"]), params)
            for row in rows:
                key = scope_key(row, variant_field)
                if key and key in keys:
                    collected.append(row)
            time.sleep(0.15)
        output[name] = collected

    for name, rows in output.items():
        unique: dict[str, dict[str, Any]] = {}
        for row in rows:
            reject_forbidden_fields(row, name)
            unique[sha256_bytes(canonical_bytes(row))] = row
        output[name] = [unique[key] for key in sorted(unique)]
    return output, metadata_report


def validate_source_manifest(source: dict[str, Any]) -> None:
    if source.get("source_id") != SOURCE_ID:
        raise ValueError("RDW source identity mismatch")
    rights = source.get("rights", {})
    if rights.get("rights_status") != "approved_by_published_CC0_license":
        raise ValueError("RDW CC0 rights gate is not approved")
    for field in ("commercial_use_allowed", "display_allowed", "offline_cache_allowed", "bulk_reuse_allowed", "redistribution_allowed"):
        if rights.get(field) is not True:
            raise ValueError(f"RDW reuse right is not explicitly true: {field}")
    policy = source.get("import_policy", {})
    if policy.get("production_import") is not False or policy.get("ru_eaeu_applicability") is not False:
        raise ValueError("RDW research-only market/production boundary is missing")
    if source.get("market_scope") != ["NL"]:
        raise ValueError("RDW pack must remain NL-scoped")
    products = source.get("data_products", {})
    product_keys = {
        "registration": "registered_vehicle_identity",
        "tgk_drive": "tgk_drive",
        "tgk_gearbox": "tgk_gearbox",
        "tgk_base": "tgk_base",
        "tgk_make": "tgk_make",
        "tgk_trade_name": "tgk_trade_name",
    }
    for name, config in DATASETS.items():
        product = products.get(product_keys[name], {})
        if product.get("dataset_id") != config["id"] or product.get("catalog_license") != "CC0 1.0":
            raise ValueError(f"RDW dataset identity/license mismatch: {name}")
    source_makes = source.get("vehicle_scope", {}).get("makes", [])
    if sorted(source_makes) != sorted(MAKES):
        raise ValueError("RDW VAG make allowlist differs from the reviewed source manifest")
    allowed_registration_fields = set(products["registered_vehicle_identity"].get("use_fields", []))
    if not set(REGISTRATION_GROUP_FIELDS).issubset(allowed_registration_fields):
        raise ValueError("RDW registration query exceeds the reviewed non-identifying field allowlist")
    if any(any(token in field.lower() for token in FORBIDDEN_TOKENS) for field in allowed_registration_fields):
        raise ValueError("RDW source manifest allowlist contains a forbidden registration/personal-data field")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> tuple[str, int]:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = b"".join(canonical_bytes(row) + b"\n" for row in rows)
    path.write_bytes(payload)
    return sha256_bytes(payload), len(payload)


def build_sqlite(database_path: Path, datasets: dict[str, list[dict[str, Any]]], metadata: dict[str, dict[str, Any]],
                 source_manifest_sha: str, source_files: list[dict[str, Any]]) -> dict[str, int]:
    if database_path.exists():
        raise FileExistsError(f"Refusing to overwrite SQLite database: {database_path}")
    db = sqlite3.connect(database_path)
    try:
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA journal_mode=DELETE")
        db.executescript("""
            CREATE TABLE source_registry (
              source_id TEXT PRIMARY KEY, publisher TEXT NOT NULL, license_id TEXT NOT NULL,
              rights_status TEXT NOT NULL, market_scope TEXT NOT NULL,
              production_import INTEGER NOT NULL CHECK(production_import=0),
              ru_eaeu_applicability INTEGER NOT NULL CHECK(ru_eaeu_applicability=0),
              source_manifest_sha256 TEXT NOT NULL, verification_status TEXT NOT NULL
            );
            CREATE TABLE source_file_artifacts (
              dataset_id TEXT PRIMARY KEY, dataset_name TEXT NOT NULL, source_revision TEXT NOT NULL,
              source_snapshot_sha256 TEXT NOT NULL, byte_size INTEGER NOT NULL, row_count INTEGER NOT NULL,
              query_scope TEXT NOT NULL, source_columns_sha256 TEXT NOT NULL,
              required_columns_sha256 TEXT NOT NULL, query_spec_sha256 TEXT NOT NULL,
              query_spec_json TEXT NOT NULL
            );
            CREATE TABLE approval_scope (
              scope_id TEXT PRIMARY KEY, type_approval_number TEXT NOT NULL, variant TEXT,
              version TEXT, revision TEXT, market_scope TEXT NOT NULL CHECK(market_scope='NL'),
              applicability_precision TEXT NOT NULL, verification_status TEXT NOT NULL,
              model_year TEXT CHECK(model_year IS NULL), generation TEXT CHECK(generation IS NULL),
              exact_vehicle_fitment INTEGER NOT NULL CHECK(exact_vehicle_fitment=0),
              ru_eaeu_applicability INTEGER NOT NULL CHECK(ru_eaeu_applicability=0)
            );
            CREATE TABLE registration_observations (
              observation_id TEXT PRIMARY KEY, scope_id TEXT, make TEXT NOT NULL, trade_name TEXT,
              vehicle_category TEXT, registration_count INTEGER NOT NULL,
              source_row_sha256 TEXT NOT NULL, market_scope TEXT NOT NULL CHECK(market_scope='NL'),
              applicability_precision TEXT NOT NULL, verification_status TEXT NOT NULL,
              FOREIGN KEY(scope_id) REFERENCES approval_scope(scope_id),
              FOREIGN KEY(source_row_sha256) REFERENCES source_rows(source_row_sha256)
            );
            CREATE TABLE source_rows (
              source_row_sha256 TEXT PRIMARY KEY, dataset_id TEXT NOT NULL,
              scope_id TEXT, raw_json TEXT NOT NULL, market_scope TEXT NOT NULL CHECK(market_scope='NL'),
              FOREIGN KEY(scope_id) REFERENCES approval_scope(scope_id)
            );
            CREATE TABLE engine_designation_candidates (
              source_row_sha256 TEXT PRIMARY KEY, scope_id TEXT NOT NULL,
              engine_designation TEXT, engine_type_approval_number TEXT,
              displacement_cc TEXT, cylinders TEXT, market_scope TEXT NOT NULL CHECK(market_scope='NL'),
              applicability_precision TEXT NOT NULL,
              verification_status TEXT NOT NULL CHECK(verification_status='rdw_engine_designation_candidate_not_oem_confirmed'),
              FOREIGN KEY(scope_id) REFERENCES approval_scope(scope_id),
              FOREIGN KEY(source_row_sha256) REFERENCES source_rows(source_row_sha256)
            );
            CREATE TABLE gearbox_classifications (
              source_row_sha256 TEXT PRIMARY KEY, scope_id TEXT NOT NULL,
              gearbox_type_classification TEXT, market_scope TEXT NOT NULL CHECK(market_scope='NL'),
              applicability_precision TEXT NOT NULL,
              verification_status TEXT NOT NULL CHECK(verification_status='rdw_approval_gearbox_classification_not_vag_code'),
              FOREIGN KEY(scope_id) REFERENCES approval_scope(scope_id),
              FOREIGN KEY(source_row_sha256) REFERENCES source_rows(source_row_sha256)
            );
            CREATE TABLE approval_auxiliary_rows (
              source_row_sha256 TEXT PRIMARY KEY, dataset_id TEXT NOT NULL, scope_id TEXT NOT NULL,
              FOREIGN KEY(scope_id) REFERENCES approval_scope(scope_id),
              FOREIGN KEY(source_row_sha256) REFERENCES source_rows(source_row_sha256)
            );
            CREATE INDEX idx_registration_make_trade ON registration_observations(make, trade_name);
            CREATE INDEX idx_approval_number ON approval_scope(type_approval_number);
            CREATE INDEX idx_engine_designation ON engine_designation_candidates(engine_designation);
            CREATE INDEX idx_gearbox_classification ON gearbox_classifications(gearbox_type_classification);
        """)
        db.execute("BEGIN IMMEDIATE")
        db.execute(
            "INSERT INTO source_registry VALUES (?,?,?,?,?,?,?,?,?)",
            (SOURCE_ID, "RDW (Dienst Wegverkeer), Netherlands", "CC0-1.0",
             "approved_by_published_CC0_license", "NL", 0, 0, source_manifest_sha,
             "rights_cleared_research_only_not_oem_fitment"),
        )

        exact_keys: dict[tuple[str, str, str, str], str] = {}
        counts = {"source_files": len(source_files), "approval_scopes": 0, "registration_observations": 0,
                  "engine_candidates": 0, "gearbox_classifications": 0, "auxiliary_rows": 0, "source_rows": 0}
        for item in source_files:
            db.execute(
                "INSERT INTO source_file_artifacts VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (item["dataset_id"], item["dataset_name"], item["source_revision"], item["sha256"],
                 item["byte_size"], item["row_count"], item["query_scope"], item["source_columns_sha256"],
                 item["required_columns_sha256"], item["query_spec_sha256"],
                 canonical_bytes(item["query_spec"]).decode("utf-8")),
            )
        for row in datasets["registration"]:
            raw_key = (
                str(row.get("typegoedkeuringsnummer") or ""),
                str(row.get("variant") or ""),
                str(row.get("uitvoering") or ""),
                str(row.get("volgnummer_wijziging_eu_typegoedkeuring") or ""),
            )
            exact = all(raw_key)
            sid = scope_id(raw_key) if exact else None
            row_hash = sha256_bytes(canonical_bytes(row))
            if sid:
                exact_keys[raw_key] = sid
                db.execute(
                    "INSERT OR IGNORE INTO approval_scope VALUES (?,?,?,?,?,'NL',?,'rdw_approval_scope_observed',NULL,NULL,0,0)",
                    (sid, *raw_key, "exact_RDW_approval_variant_version_revision_scope"),
                )
            observation_id = sha256_bytes(canonical_bytes([row_hash, row.get("merk"), row.get("handelsbenaming")]))
            db.execute(
                "INSERT OR IGNORE INTO source_rows VALUES (?,?,?,?,'NL')",
                (row_hash, REGISTRATION_ID, sid, canonical_bytes(row).decode("utf-8")),
            )
            db.execute(
                "INSERT OR IGNORE INTO registration_observations VALUES (?,?,?,?,?,?,?,?,?,?)",
                (observation_id, sid, str(row.get("merk") or ""), row.get("handelsbenaming"),
                 row.get("voertuigsoort"), int(row.get("registration_count") or 0), row_hash, "NL",
                 "exact_RDW_approval_variant_version_revision_scope" if sid else "approval_number_only",
                 "rdw_registration_observation_not_vehicle_fitment"),
            )
            counts["registration_observations"] += 1
            counts["source_rows"] += 1

        for name, rows in datasets.items():
            config = DATASETS[name]
            dataset_id = str(config["id"])
            for row in rows:
                row_hash = sha256_bytes(canonical_bytes(row))
                if name == "registration":
                    continue
                variant_field = str(config["variant_field"])
                key = scope_key(row, variant_field)
                sid = exact_keys.get(key) if key else None
                if not sid:
                    raise ValueError(f"RDW {name} row has no exact matching registration approval scope")
                db.execute(
                    "INSERT OR IGNORE INTO source_rows VALUES (?,?,?,?,'NL')",
                    (row_hash, dataset_id, sid, canonical_bytes(row).decode("utf-8")),
                )
                if name == "tgk_drive":
                    db.execute(
                        "INSERT OR IGNORE INTO engine_designation_candidates VALUES (?,?,?,?,?,?, 'NL', ?, 'rdw_engine_designation_candidate_not_oem_confirmed')",
                        (row_hash, sid, row.get("motorcode"), row.get("typegoedkeuringsnummermotor"),
                         row.get("cilinderinhoud"), row.get("aantalcilinders"),
                         "exact_RDW_approval_variant_version_revision_scope"),
                    )
                    counts["engine_candidates"] += 1
                elif name == "tgk_gearbox":
                    db.execute(
                        "INSERT OR IGNORE INTO gearbox_classifications VALUES (?,?,?,'NL',?,'rdw_approval_gearbox_classification_not_vag_code')",
                        (row_hash, sid, row.get("codetypeversnellingsbak"),
                         "exact_RDW_approval_variant_version_revision_scope"),
                    )
                    counts["gearbox_classifications"] += 1
                else:
                    db.execute(
                        "INSERT OR IGNORE INTO approval_auxiliary_rows VALUES (?,?,?)",
                        (row_hash, dataset_id, sid),
                    )
                    counts["auxiliary_rows"] += 1
                counts["source_rows"] += 1

        db.commit()
        db.execute("PRAGMA optimize")
        counts = {
            "source_files": int(db.execute("SELECT count(*) FROM source_file_artifacts").fetchone()[0]),
            "approval_scopes": int(db.execute("SELECT count(*) FROM approval_scope").fetchone()[0]),
            "registration_observations": int(db.execute("SELECT count(*) FROM registration_observations").fetchone()[0]),
            "engine_candidates": int(db.execute("SELECT count(*) FROM engine_designation_candidates").fetchone()[0]),
            "gearbox_classifications": int(db.execute("SELECT count(*) FROM gearbox_classifications").fetchone()[0]),
            "auxiliary_rows": int(db.execute("SELECT count(*) FROM approval_auxiliary_rows").fetchone()[0]),
            "source_rows": int(db.execute("SELECT count(*) FROM source_rows").fetchone()[0]),
        }
        integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok" or db.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("RDW SQLite integrity or foreign-key check failed")
        return counts
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def build_pack(output_dir: Path, source_manifest: dict[str, Any], source_manifest_bytes: bytes,
               datasets: dict[str, list[dict[str, Any]]], metadata: dict[str, dict[str, Any]]) -> dict[str, Any]:
    validate_source_manifest(source_manifest)
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"Refusing to overwrite non-empty pack directory: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    source_manifest_sha = sha256_bytes(source_manifest_bytes)
    copied_manifest = output_dir / "rdw-eu-vag-type-approval-open-data.json"
    copied_manifest.write_bytes(source_manifest_bytes)

    source_files = []
    for name, rows in sorted(datasets.items()):
        dataset_id = str(DATASETS[name]["id"])
        file_name = f"{dataset_id}.jsonl"
        digest, byte_size = write_jsonl(output_dir / "source-snapshot" / file_name, rows)
        source_files.append({
            "dataset_name": name, "dataset_id": dataset_id, "path": f"source-snapshot/{file_name}",
            "sha256": digest, "byte_size": byte_size, "row_count": len(rows),
            "source_revision": metadata[name]["rows_updated_at"] or metadata[name]["view_last_modified"],
            "source_columns_sha256": metadata[name]["source_columns_sha256"],
            "required_columns": metadata[name]["required_columns"],
            "required_columns_sha256": metadata[name]["required_columns_sha256"],
            "query_spec": metadata[name]["query_spec"],
            "query_spec_sha256": sha256_bytes(canonical_bytes(metadata[name]["query_spec"])),
            "query_scope": "Per-dataset query specification is retained and hashed in query_spec/query_spec_sha256.",
        })

    database = output_dir / "rdw-vag-research.sqlite"
    counts = build_sqlite(database, datasets, metadata, source_manifest_sha, source_files)
    db_sha = sha256_file(database)
    manifest = {
        "schema_version": 1,
        "pack_id": "rdw-vag-nl-eu-type-approval-research",
        "status": "verified_research_only",
        "source_id": SOURCE_ID,
        "publisher": "RDW (Dienst Wegverkeer), Netherlands",
        "license": "CC0-1.0",
        "rights_status": "approved_by_published_CC0_license",
        "commercial_use_allowed": True,
        "display_allowed": True,
        "offline_cache_allowed": True,
        "bulk_reuse_allowed": True,
        "redistribution_allowed": True,
        "attribution_required": False,
        "attribution": "Source: RDW Open Data (Netherlands), CC0 1.0. Attribution is provided as a courtesy.",
        "source_manifest_file": copied_manifest.name,
        "source_manifest_sha256": source_manifest_sha,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_revisions": {item["dataset_name"]: item["source_revision"] for item in source_files},
        "source_files": source_files,
        "database": {"path": database.name, "sha256": db_sha, "byte_size": database.stat().st_size},
        "counts": counts,
        "market_scope": ["NL"],
        "approval_jurisdiction": "EU type-approval identifiers observed in Netherlands RDW datasets",
        "applicability_precision": "exact_RDW_approval_variant_version_revision_scope_or_approval_number_only",
        "production_import": False,
        "product_import_allowed": False,
        "ru_eaeu_applicability": False,
        "exact_vehicle_fitment": False,
        "individual_vehicle_fitment": False,
        "model_year_inferred": False,
        "generation_inferred": False,
        "exact_vag_engine_code": False,
        "exact_vag_gearbox_code": False,
        "exact_engine_gearbox_pair": False,
        "ecu_dtc_repair_applicability": False,
        "diagnostic_execution_allowed": False,
        "pair_table_created": False,
        "policies": [
            "RDW motorcode is a source designation candidate, not an OEM-confirmed VAG engine code.",
            "RDW codetypeversnellingsbak is an approval classification, not a VAG gearbox code.",
            "Engine designations and gearbox classifications are stored in separate tables; no pair table or cross-join is created.",
            "First registration is not model year; no generation or production date is inferred.",
            "No VIN, registration plate, holder, ownership, address or personal data is requested or stored.",
            "This NL/EU research pack is never RU/EAEU production fitment or repair authorization.",
        ],
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output_dir / "LICENSE.txt").write_text(
        "RDW datasets listed in manifest.json are published by the Dutch national data catalogue as CC0 1.0. "
        "See https://creativecommons.org/publicdomain/zero/1.0/ and the dataset-specific evidence URLs in the source manifest.\n",
        encoding="utf-8",
    )
    (output_dir / "ATTRIBUTION.md").write_text(
        "# Attribution\n\nSource: RDW Open Data (Netherlands). The six listed datasets are marked CC0 1.0 by data.overheid.nl. "
        "Attribution is not required by CC0; this notice is provided as a courtesy.\n",
        encoding="utf-8",
    )
    report = {
        "schema_version": 1, "status": "verified_research_only", "source_id": SOURCE_ID,
        "database_sha256": db_sha, "database_integrity_check": "ok",
        "source_manifest_sha256": source_manifest_sha, "counts": counts,
        "market_scope": ["NL"], "ru_eaeu_applicability": False,
        "exact_engine_gearbox_pair_claim": False, "production_import": False,
    }
    (output_dir / "build-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    validate_pack(output_dir)
    return report


def validate_pack(pack_dir: Path) -> dict[str, Any]:
    manifest = read_json(pack_dir / "manifest.json")
    if manifest.get("status") != "verified_research_only" or manifest.get("source_id") != SOURCE_ID:
        raise ValueError("RDW pack identity/status mismatch")
    for field in ("commercial_use_allowed", "display_allowed", "offline_cache_allowed", "bulk_reuse_allowed", "redistribution_allowed"):
        if manifest.get(field) is not True:
            raise ValueError(f"RDW pack rights missing: {field}")
    for field in ("production_import", "product_import_allowed", "ru_eaeu_applicability", "exact_vehicle_fitment",
                  "individual_vehicle_fitment", "model_year_inferred", "generation_inferred", "exact_vag_engine_code",
                  "exact_vag_gearbox_code", "exact_engine_gearbox_pair", "ecu_dtc_repair_applicability",
                  "diagnostic_execution_allowed", "pair_table_created"):
        if manifest.get(field) is not False:
            raise ValueError(f"RDW pack boundary failed: {field}")
    if manifest.get("market_scope") != ["NL"]:
        raise ValueError("RDW pack market scope mismatch")
    database = pack_dir / manifest["database"]["path"]
    if sha256_file(database) != manifest["database"]["sha256"]:
        raise ValueError("RDW SQLite database hash mismatch")
    for item in manifest["source_files"]:
        path = pack_dir / item["path"]
        if not path.is_file() or path.stat().st_size != item["byte_size"] or sha256_file(path) != item["sha256"]:
            raise ValueError(f"RDW source snapshot hash mismatch: {item['dataset_id']}")
        required_columns = item.get("required_columns")
        if not isinstance(required_columns, list) or sha256_bytes(canonical_bytes(required_columns)) != item.get("required_columns_sha256"):
            raise ValueError(f"RDW required-column provenance hash mismatch: {item['dataset_id']}")
        query_spec = item.get("query_spec")
        if not isinstance(query_spec, dict) or sha256_bytes(canonical_bytes(query_spec)) != item.get("query_spec_sha256"):
            raise ValueError(f"RDW query-spec provenance hash mismatch: {item['dataset_id']}")
        for hash_field in ("source_columns_sha256", "required_columns_sha256", "query_spec_sha256"):
            value = item.get(hash_field)
            if not isinstance(value, str) or len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
                raise ValueError(f"RDW provenance digest is malformed: {item['dataset_id']} / {hash_field}")
    if sha256_file(pack_dir / manifest["source_manifest_file"]) != manifest["source_manifest_sha256"]:
        raise ValueError("RDW source manifest hash mismatch")
    db = sqlite3.connect(f"file:{database.resolve().as_posix()}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    try:
        if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok" or db.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("RDW SQLite integrity/foreign-key check failed")
        tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "engine_gearbox_pairs" in tables or any("pair" in table.lower() for table in tables):
            raise ValueError("RDW pack must not contain an engine/gearbox pair table")
        expected = {
            "source_files": db.execute("SELECT count(*) FROM source_file_artifacts").fetchone()[0],
            "approval_scopes": db.execute("SELECT count(*) FROM approval_scope").fetchone()[0],
            "registration_observations": db.execute("SELECT count(*) FROM registration_observations").fetchone()[0],
            "engine_candidates": db.execute("SELECT count(*) FROM engine_designation_candidates").fetchone()[0],
            "gearbox_classifications": db.execute("SELECT count(*) FROM gearbox_classifications").fetchone()[0],
            "auxiliary_rows": db.execute("SELECT count(*) FROM approval_auxiliary_rows").fetchone()[0],
            "source_rows": db.execute("SELECT count(*) FROM source_rows").fetchone()[0],
        }
        if expected != manifest["counts"]:
            raise ValueError(f"RDW SQLite row counts differ from manifest: {expected}")
        if db.execute("SELECT count(*) FROM source_registry WHERE rights_status<>'approved_by_published_CC0_license' OR market_scope<>'NL' OR production_import<>0 OR ru_eaeu_applicability<>0").fetchone()[0] != 0:
            raise ValueError("RDW source registry rights/market boundary failed")
        for item in manifest["source_files"]:
            stored = db.execute(
                "SELECT source_columns_sha256, required_columns_sha256, query_spec_sha256, query_spec_json "
                "FROM source_file_artifacts WHERE dataset_id=?",
                (item["dataset_id"],),
            ).fetchone()
            if stored is None:
                raise ValueError(f"RDW source-file provenance row missing: {item['dataset_id']}")
            if tuple(stored[:3]) != (
                item["source_columns_sha256"], item["required_columns_sha256"], item["query_spec_sha256"]
            ):
                raise ValueError(f"RDW SQLite source-file provenance differs from manifest: {item['dataset_id']}")
            if json.loads(stored["query_spec_json"]) != item["query_spec"]:
                raise ValueError(f"RDW SQLite query specification differs from manifest: {item['dataset_id']}")
        if db.execute("SELECT count(*) FROM engine_designation_candidates WHERE verification_status<>'rdw_engine_designation_candidate_not_oem_confirmed' OR market_scope<>'NL'").fetchone()[0]:
            raise ValueError("RDW engine candidate promotion detected")
        if db.execute("SELECT count(*) FROM gearbox_classifications WHERE verification_status<>'rdw_approval_gearbox_classification_not_vag_code' OR market_scope<>'NL'").fetchone()[0]:
            raise ValueError("RDW gearbox classification promotion detected")
        if db.execute("SELECT count(*) FROM approval_scope WHERE model_year IS NOT NULL OR generation IS NOT NULL OR exact_vehicle_fitment<>0 OR ru_eaeu_applicability<>0").fetchone()[0]:
            raise ValueError("RDW approval scope was promoted to vehicle fitment")
        for row in db.execute("SELECT raw_json FROM source_rows"):
            reject_forbidden_fields(json.loads(row["raw_json"]), "sqlite.source_rows")
    finally:
        db.close()
    return {"status": "verified_research_only", "database_sha256": manifest["database"]["sha256"], "counts": expected}


def acquire(output_dir: Path, manifest_path: Path) -> dict[str, Any]:
    source_bytes = manifest_path.read_bytes()
    source = json.loads(source_bytes.decode("utf-8-sig"))
    validate_source_manifest(source)
    datasets, metadata = query_source_rows(source)
    return build_pack(output_dir, source, source_bytes, datasets, metadata)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=Path("data/source-manifests/rdw-eu-vag-type-approval-open-data.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/rdw-vag-research-pack"))
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    result = validate_pack(args.output_dir) if args.verify_only else acquire(args.output_dir, args.manifest)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
