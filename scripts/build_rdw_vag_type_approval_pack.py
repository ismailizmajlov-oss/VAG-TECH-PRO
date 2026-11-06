#!/usr/bin/env python3
"""Build a rights-cleared RDW VAG type-approval projection as a separate SQLite research pack.

The pack is NL/EU approval-scope evidence only. It never contains registration plates,
VINs or holder data, never infers model year/generation, and never pairs engine and
gearbox rows. It is not eligible for production fitment or repair-data imports.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from probe_rdw_vag_type_approvals import (
    BASE,
    DATASETS,
    SOURCE_ID,
    build_soda_url,
    canonical_json,
    metadata_columns,
    soql_literal,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE_MANIFEST_PATH = ROOT / "data/source-manifests/rdw-eu-vag-type-approval-open-data.json"
SOURCE_REGISTER_PATH = ROOT / "data/source-manifests/vag-factory-source-register.json"
REGISTRATION_DATASET_ID = "m9d7-ebf2"
REGISTRATION_FIELDS = [
    "merk",
    "handelsbenaming",
    "typegoedkeuringsnummer",
    "variant",
    "uitvoering",
    "volgnummer_wijziging_eu_typegoedkeuring",
    "voertuigsoort",
    "cilinderinhoud",
    "aantal_cilinders",
]
REGISTRATION_REQUIRED = REGISTRATION_FIELDS[:7]
FORBIDDEN_FIELD_TOKENS = (
    "kenteken", "vin", "chassisnummer", "houder", "owner",
    "tenaamstelling", "address", "postcode", "persoon", "person",
)
PAGE_SIZE = 10000
APPROVAL_BATCH_SIZE = 25
PACK_ID = "rdw-vag-type-approval-nl-research"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_json(value: Any) -> str:
    return sha256_bytes(canonical_json(value))


def fetch_json(url: str, *, attempts: int = 4, timeout: int = 90) -> Any:
    last_error: Exception | None = None
    for attempt in range(attempts):
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "VAG-TECH-PRO-RDW-research-pack/1.0",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                if response.status != 200:
                    raise RuntimeError(f"RDW HTTP {response.status}: {url}")
                raw = response.read(32 * 1024 * 1024 + 1)
                if len(raw) > 32 * 1024 * 1024:
                    raise RuntimeError("RDW response exceeded the 32 MiB page limit")
                return json.loads(raw.decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, RuntimeError) as exc:
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(min(2 ** attempt, 8))
    raise RuntimeError(f"RDW request failed after {attempts} attempts: {last_error}") from last_error


def normalize_make(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_value = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return "".join(ch for ch in ascii_value.upper() if ch.isalnum())


def safe_projection(row: dict[str, Any], allowed_fields: list[str]) -> dict[str, Any]:
    for name in row:
        lowered = str(name).lower()
        if any(token in lowered for token in FORBIDDEN_FIELD_TOKENS):
            raise ValueError(f"RDW returned a forbidden identity/personal-data field: {name}")
    projected = {name: row[name] for name in allowed_fields if name in row}
    if not projected:
        raise ValueError("RDW returned an empty allowlisted projection")
    return projected


def fetch_metadata(dataset_id: str) -> dict[str, Any]:
    metadata = fetch_json(f"{BASE}/api/views/{dataset_id}.json")
    if not isinstance(metadata, dict):
        raise RuntimeError(f"Unexpected RDW metadata response for {dataset_id}")
    return metadata


def source_revision(metadata: dict[str, Any]) -> str:
    rows_updated = metadata.get("rowsUpdatedAt")
    view_modified = metadata.get("viewLastModified")
    revision = rows_updated or view_modified
    if revision is None:
        raise RuntimeError("RDW metadata has no rowsUpdatedAt or viewLastModified revision")
    return str(revision)


def query_all(
    dataset_id: str,
    *,
    select_fields: list[str],
    where: str,
    order: str,
    distinct: bool = False,
    page_size: int = PAGE_SIZE,
) -> list[dict[str, Any]]:
    if page_size < 1 or page_size > PAGE_SIZE:
        raise ValueError("RDW page size is outside the safe limit")
    select_clause = (["distinct"] if distinct else []) + select_fields
    rows: list[dict[str, Any]] = []
    offset = 0
    while True:
        params = {
            "$select": ",".join(select_clause),
            "$where": where,
            "$order": order,
            "$limit": str(page_size),
            "$offset": str(offset),
        }
        result = fetch_json(build_soda_url(dataset_id, params))
        if not isinstance(result, list):
            raise RuntimeError(f"Unexpected RDW row response for {dataset_id}")
        for row in result:
            if not isinstance(row, dict):
                raise RuntimeError(f"Non-object row in RDW dataset {dataset_id}")
            if any(
                any(token in str(key).lower() for token in FORBIDDEN_FIELD_TOKENS)
                for key in row
            ):
                raise RuntimeError(f"Forbidden field returned by RDW dataset {dataset_id}")
        rows.extend(result)
        if len(result) < page_size:
            break
        offset += page_size
        if offset > 2_000_000:
            raise RuntimeError(f"RDW query exceeded the 2,000,000-row safety cap: {dataset_id}")
        time.sleep(0.15)
    return rows


def registration_scope_key(row: dict[str, Any]) -> dict[str, str]:
    return {
        "typegoedkeuringsnummer": str(row.get("typegoedkeuringsnummer") or "").strip(),
        "variant": str(row.get("variant") or "").strip(),
        "version": str(row.get("uitvoering") or "").strip(),
        "revision": str(row.get("volgnummer_wijziging_eu_typegoedkeuring") or "").strip(),
    }


def tgk_scope_key(row: dict[str, Any], variant_field: str) -> dict[str, str]:
    if variant_field not in {"codevarianttgk", "codevariantgk"}:
        raise ValueError(f"Unapproved RDW variant field: {variant_field}")
    return {
        "typegoedkeuringsnummer": str(row.get("typegoedkeuringsnummer") or "").strip(),
        "variant": str(row.get(variant_field) or "").strip(),
        "version": str(row.get("codeuitvoeringtgk") or "").strip(),
        "revision": str(row.get("volgnummerrevisieuitvoering") or "").strip(),
    }


def scope_token(key: dict[str, str]) -> tuple[str, str, str, str]:
    return (
        key["typegoedkeuringsnummer"],
        key["variant"],
        key["version"],
        key["revision"],
    )


def scope_id_for(key: dict[str, str]) -> str:
    return sha256_json(key)


def chunks(values: list[str], size: int) -> list[list[str]]:
    return [values[index:index + size] for index in range(0, len(values), size)]


def load_rights_inputs() -> tuple[dict[str, Any], list[str]]:
    manifest = json.loads(SOURCE_MANIFEST_PATH.read_text(encoding="utf-8"))
    registry = json.loads(SOURCE_REGISTER_PATH.read_text(encoding="utf-8"))
    if manifest.get("source_id") != SOURCE_ID:
        raise RuntimeError("RDW source manifest identity mismatch")
    rights = manifest.get("rights", {})
    if (
        rights.get("rights_status") != "approved_by_published_CC0_license"
        or rights.get("offline_cache_allowed") is not True
        or rights.get("bulk_reuse_allowed") is not True
        or rights.get("redistribution_allowed") is not True
        or rights.get("commercial_use_allowed") is not True
        or rights.get("display_allowed") is not True
    ):
        raise RuntimeError("RDW CC0 rights gate is incomplete")
    source = next(
        (item for item in registry.get("sources", []) if item.get("source_id") == SOURCE_ID),
        None,
    )
    if source is None:
        raise RuntimeError("RDW source is missing from the central VAG source register")
    if source.get("product_import_allowed") is not False:
        raise RuntimeError("RDW must remain excluded from production fitment imports")
    if source.get("rights", {}).get("rights_status") != "approved_by_published_CC0_license":
        raise RuntimeError("Central RDW source rights status is not approved CC0")
    makes = source.get("vehicle_scope", {}).get("makes")
    if not isinstance(makes, list) or not makes:
        raise RuntimeError("Central RDW source register has no explicit VAG make allowlist")
    return manifest, [str(item) for item in makes]


def metadata_contracts(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    products = manifest.get("data_products", {})
    result: dict[str, dict[str, Any]] = {}
    registration = products.get("registered_vehicle_identity", {})
    if registration.get("dataset_id") != REGISTRATION_DATASET_ID or registration.get("catalog_license") != "CC0 1.0":
        raise RuntimeError("RDW registered-vehicle dataset identity/license mismatch")
    result["registered_vehicle_identity"] = {
        "dataset_id": REGISTRATION_DATASET_ID,
        "title": registration.get("title"),
        "catalog_url": registration.get("catalog_url"),
        "api_url": registration.get("api_url"),
        "license": registration.get("catalog_license"),
        "required": REGISTRATION_REQUIRED,
        "select": REGISTRATION_FIELDS,
        "variant_field": "variant",
    }
    for name, config in DATASETS.items():
        product = products.get(name, {})
        if product.get("dataset_id") != config["id"] or product.get("catalog_license") != "CC0 1.0":
            raise RuntimeError(f"RDW TGK dataset identity/license mismatch: {name}")
        result[name] = {
            "dataset_id": config["id"],
            "title": product.get("title"),
            "catalog_url": product.get("catalog_url"),
            "api_url": product.get("api_url"),
            "license": product.get("catalog_license"),
            "required": list(config["required"]),
            "select": list(config["select"]),
            "variant_field": config["variant_field"],
        }
    if len(result) != 6:
        raise RuntimeError("RDW pack must contain exactly six rights-cleared dataset projections")
    return result


def fetch_projection_data(
    manifest: dict[str, Any],
    make_allowlist: list[str],
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, dict[str, Any]], dict[str, Any]]:
    contracts = metadata_contracts(manifest)
    metadata_before: dict[str, dict[str, Any]] = {}
    for name, config in contracts.items():
        metadata = fetch_metadata(config["dataset_id"])
        columns = metadata_columns(metadata)
        missing = sorted(set(config["required"]) - columns)
        if missing:
            raise RuntimeError(f"RDW dataset {config['dataset_id']} is missing required fields: {missing}")
        metadata_before[name] = {
            "rows_updated_at": metadata.get("rowsUpdatedAt"),
            "view_last_modified": metadata.get("viewLastModified"),
            "source_revision": source_revision(metadata),
            "columns_sha256": sha256_json(sorted(columns)),
            "required_fields": sorted(config["required"]),
        }
        time.sleep(0.2)

    registered_config = contracts["registered_vehicle_identity"]
    dataset_id = registered_config["dataset_id"]
    make_rows = query_all(
        dataset_id,
        select_fields=["merk"],
        where="typegoedkeuringsnummer IS NOT NULL AND voertuigsoort='Personenauto'",
        order="merk",
        distinct=True,
        page_size=5000,
    )
    allowlisted = {normalize_make(value) for value in make_allowlist}
    observed_make_labels = sorted({
        str(row.get("merk") or "").strip()
        for row in make_rows
        if normalize_make(str(row.get("merk") or "")) in allowlisted
    })
    if not observed_make_labels:
        raise RuntimeError("RDW returned no exact VAG make labels from the configured allowlist")

    registration_rows: list[dict[str, Any]] = []
    for make in observed_make_labels:
        where = (
            f"merk={soql_literal(make)} AND typegoedkeuringsnummer IS NOT NULL "
            f"AND voertuigsoort='Personenauto'"
        )
        rows = query_all(
            dataset_id,
            select_fields=registered_config["select"],
            where=where,
            order="merk,handelsbenaming,typegoedkeuringsnummer,variant,uitvoering,volgnummer_wijziging_eu_typegoedkeuring",
            distinct=True,
        )
        registration_rows.extend(
            safe_projection(row, registered_config["select"])
            for row in rows
        )
        time.sleep(0.2)

    registration_unique = {
        sha256_json(row): row
        for row in registration_rows
    }
    registration_rows = [registration_unique[key] for key in sorted(registration_unique)]
    scope_keys: dict[tuple[str, str, str, str], dict[str, str]] = {}
    registration_records: list[dict[str, Any]] = []
    incomplete_scope_rows = 0
    for row in registration_rows:
        key = registration_scope_key(row)
        if any(not key[name] for name in ("typegoedkeuringsnummer", "variant", "version", "revision")):
            incomplete_scope_rows += 1
            continue
        token = scope_token(key)
        scope_keys[token] = key
        registration_records.append({
            "scope_id": scope_id_for(key),
            "record": row,
            "source_row_sha256": sha256_json(row),
        })
    if not scope_keys:
        raise RuntimeError("RDW returned no complete VAG approval/variant/version/revision scopes")

    approval_numbers = sorted({key["typegoedkeuringsnummer"] for key in scope_keys.values()})
    projections: dict[str, list[dict[str, Any]]] = {
        "registered_vehicle_identity": registration_records,
    }
    unmatched_tgk_rows: dict[str, int] = {}
    for name, config in contracts.items():
        if name == "registered_vehicle_identity":
            continue
        rows_by_hash: dict[str, dict[str, Any]] = {}
        unmatched = 0
        for approval_batch in chunks(approval_numbers, APPROVAL_BATCH_SIZE):
            quoted = ",".join(soql_literal(value) for value in approval_batch)
            where = f"typegoedkeuringsnummer IN ({quoted})"
            order_fields = [
                "typegoedkeuringsnummer",
                config["variant_field"],
                "codeuitvoeringtgk",
                "volgnummerrevisieuitvoering",
            ]
            if name == "tgk_drive":
                order_fields.append("motorcode")
            elif name == "tgk_gearbox":
                order_fields.append("codetypeversnellingsbak")
            rows = query_all(
                config["dataset_id"],
                select_fields=config["select"],
                where=where,
                order=",".join(order_fields),
            )
            for raw in rows:
                row = safe_projection(raw, config["select"])
                key = tgk_scope_key(row, config["variant_field"])
                token = scope_token(key)
                scope_id = scope_id_for(scope_keys[token]) if token in scope_keys else None
                if scope_id is None:
                    unmatched += 1
                    continue
                row_hash = sha256_json(row)
                rows_by_hash[row_hash] = {
                    "scope_id": scope_id,
                    "record": row,
                    "source_row_sha256": row_hash,
                }
            time.sleep(0.15)
        projections[name] = [rows_by_hash[key] for key in sorted(rows_by_hash)]
        unmatched_tgk_rows[name] = unmatched

    metadata_after: dict[str, dict[str, Any]] = {}
    for name, config in contracts.items():
        metadata = fetch_metadata(config["dataset_id"])
        revision = source_revision(metadata)
        metadata_after[name] = {"source_revision": revision}
        if revision != metadata_before[name]["source_revision"]:
            raise RuntimeError(
                f"RDW dataset changed during acquisition: {name} "
                f"{metadata_before[name]['source_revision']} -> {revision}"
            )

    context = {
        "contracts": contracts,
        "metadata": metadata_before,
        "observed_make_labels": observed_make_labels,
        "incomplete_scope_rows": incomplete_scope_rows,
        "unmatched_tgk_rows": unmatched_tgk_rows,
        "approval_scope_keys": [scope_keys[key] for key in sorted(scope_keys)],
    }
    return projections, metadata_before, context


def write_projection_files(
    output_dir: Path,
    projections: dict[str, list[dict[str, Any]]],
    context: dict[str, Any],
) -> tuple[list[dict[str, Any]], str]:
    snapshot_dir = output_dir / "source-projections"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    file_entries: list[dict[str, Any]] = []
    for name in sorted(projections):
        contract = context["contracts"][name]
        rows = projections[name]
        payload = {
            "schema_version": 1,
            "source_id": SOURCE_ID,
            "dataset_name": name,
            "dataset_id": contract["dataset_id"],
            "title": contract["title"],
            "catalog_url": contract["catalog_url"],
            "api_url": contract["api_url"],
            "license": "CC0-1.0",
            "source_revision": context["metadata"][name]["source_revision"],
            "market_scope": ["NL"],
            "projection_kind": "filtered_vag_make_and_exact_approval_scope_projection",
            "selected_fields": contract["select"],
            "row_count": len(rows),
            "rows": rows,
        }
        path = snapshot_dir / f"{name}.json"
        data = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n"
        path.write_bytes(data)
        query_spec = {
            "dataset_id": contract["dataset_id"],
            "selected_fields": contract["select"],
            "make_allowlist": context["observed_make_labels"],
            "exact_approval_scope_filter": True,
            "registration_identity_fields_excluded": True,
        }
        file_entries.append({
            "dataset_name": name,
            "dataset_id": contract["dataset_id"],
            "title": contract["title"],
            "catalog_url": contract["catalog_url"],
            "api_url": contract["api_url"],
            "license": "CC0-1.0",
            "source_revision": context["metadata"][name]["source_revision"],
            "query_sha256": sha256_json(query_spec),
            "projection_path": str(path.relative_to(output_dir)).replace("\\", "/"),
            "projection_sha256": sha256_bytes(data),
            "row_count": len(rows),
            "selected_fields": contract["select"],
        })
    bundle_hash_input = [
        {
            "dataset_id": item["dataset_id"],
            "source_revision": item["source_revision"],
            "query_sha256": item["query_sha256"],
            "projection_sha256": item["projection_sha256"],
        }
        for item in sorted(file_entries, key=lambda value: value["dataset_id"])
    ]
    return file_entries, sha256_json(bundle_hash_input)


def create_database(
    database_path: Path,
    projections: dict[str, list[dict[str, Any]]],
    file_entries: list[dict[str, Any]],
    context: dict[str, Any],
    projection_bundle_sha256: str,
) -> dict[str, int]:
    if database_path.exists():
        raise FileExistsError(f"Refusing to overwrite an existing RDW research database: {database_path}")
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA journal_mode=DELETE")
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute("PRAGMA application_id=1443431169")
        connection.execute("PRAGMA user_version=1")
        connection.executescript("""
            CREATE TABLE source_registry (
                dataset_id TEXT PRIMARY KEY,
                dataset_name TEXT NOT NULL,
                title TEXT NOT NULL,
                catalog_url TEXT NOT NULL,
                api_url TEXT NOT NULL,
                license_id TEXT NOT NULL CHECK (license_id='CC0-1.0'),
                rights_status TEXT NOT NULL CHECK (rights_status='approved_by_published_CC0_license'),
                source_revision TEXT NOT NULL,
                query_sha256 TEXT NOT NULL CHECK (length(query_sha256)=64),
                projection_sha256 TEXT NOT NULL CHECK (length(projection_sha256)=64),
                row_count INTEGER NOT NULL CHECK (row_count >= 0),
                market_scope TEXT NOT NULL CHECK (market_scope='NL'),
                production_import_allowed INTEGER NOT NULL CHECK (production_import_allowed=0)
            );
            CREATE TABLE approval_scope (
                scope_id TEXT PRIMARY KEY CHECK (length(scope_id)=64),
                type_approval_number TEXT NOT NULL,
                variant TEXT NOT NULL,
                version TEXT NOT NULL,
                revision TEXT NOT NULL,
                market_scope TEXT NOT NULL CHECK (market_scope='NL'),
                applicability_precision TEXT NOT NULL CHECK (applicability_precision='exact_RDW_approval_variant_version_revision_scope'),
                verification_status TEXT NOT NULL CHECK (verification_status='source_imported_unreviewed'),
                model_year INTEGER CHECK (model_year IS NULL),
                generation TEXT CHECK (generation IS NULL),
                individual_vehicle_fitment INTEGER NOT NULL CHECK (individual_vehicle_fitment=0),
                production_fitment INTEGER NOT NULL CHECK (production_fitment=0),
                ru_eaeu_applicability INTEGER NOT NULL CHECK (ru_eaeu_applicability=0),
                exact_vag_engine_code INTEGER NOT NULL CHECK (exact_vag_engine_code=0),
                exact_vag_gearbox_code INTEGER NOT NULL CHECK (exact_vag_gearbox_code=0),
                exact_engine_gearbox_pair INTEGER NOT NULL CHECK (exact_engine_gearbox_pair=0),
                ecu_dtc_repair_applicability INTEGER NOT NULL CHECK (ecu_dtc_repair_applicability=0),
                UNIQUE(type_approval_number, variant, version, revision)
            );
            CREATE TABLE registration_observation (
                source_row_sha256 TEXT PRIMARY KEY CHECK (length(source_row_sha256)=64),
                scope_id TEXT NOT NULL REFERENCES approval_scope(scope_id),
                source_dataset_id TEXT NOT NULL REFERENCES source_registry(dataset_id),
                source_revision TEXT NOT NULL,
                license_id TEXT NOT NULL CHECK (license_id='CC0-1.0'),
                make_label TEXT NOT NULL,
                trade_name_nl TEXT,
                vehicle_category TEXT,
                displacement_cc TEXT,
                cylinder_count TEXT,
                market_scope TEXT NOT NULL CHECK (market_scope='NL'),
                applicability_precision TEXT NOT NULL CHECK (applicability_precision='exact_RDW_approval_variant_version_revision_scope'),
                verification_status TEXT NOT NULL CHECK (verification_status='source_imported_unreviewed'),
                raw_record_json TEXT NOT NULL
            );
            CREATE TABLE tgk_drive (
                source_row_sha256 TEXT PRIMARY KEY CHECK (length(source_row_sha256)=64),
                scope_id TEXT NOT NULL REFERENCES approval_scope(scope_id),
                source_dataset_id TEXT NOT NULL REFERENCES source_registry(dataset_id),
                source_revision TEXT NOT NULL,
                license_id TEXT NOT NULL CHECK (license_id='CC0-1.0'),
                motorcode_candidate TEXT,
                engine_type_approval_number TEXT,
                cylinder_count TEXT,
                displacement_cc TEXT,
                market_scope TEXT NOT NULL CHECK (market_scope='NL'),
                applicability_precision TEXT NOT NULL CHECK (applicability_precision='exact_RDW_approval_variant_version_revision_scope'),
                verification_status TEXT NOT NULL CHECK (verification_status='source_imported_unreviewed'),
                raw_record_json TEXT NOT NULL
            );
            CREATE TABLE tgk_gearbox (
                source_row_sha256 TEXT PRIMARY KEY CHECK (length(source_row_sha256)=64),
                scope_id TEXT NOT NULL REFERENCES approval_scope(scope_id),
                source_dataset_id TEXT NOT NULL REFERENCES source_registry(dataset_id),
                source_revision TEXT NOT NULL,
                license_id TEXT NOT NULL CHECK (license_id='CC0-1.0'),
                gearbox_type_classification_candidate TEXT,
                market_scope TEXT NOT NULL CHECK (market_scope='NL'),
                applicability_precision TEXT NOT NULL CHECK (applicability_precision='exact_RDW_approval_variant_version_revision_scope'),
                verification_status TEXT NOT NULL CHECK (verification_status='source_imported_unreviewed'),
                raw_record_json TEXT NOT NULL
            );
            CREATE TABLE tgk_base (
                source_row_sha256 TEXT PRIMARY KEY CHECK (length(source_row_sha256)=64),
                scope_id TEXT NOT NULL REFERENCES approval_scope(scope_id),
                source_dataset_id TEXT NOT NULL REFERENCES source_registry(dataset_id),
                source_revision TEXT NOT NULL,
                license_id TEXT NOT NULL CHECK (license_id='CC0-1.0'),
                revision_start_date TEXT,
                vehicle_category TEXT,
                market_scope TEXT NOT NULL CHECK (market_scope='NL'),
                applicability_precision TEXT NOT NULL CHECK (applicability_precision='exact_RDW_approval_variant_version_revision_scope'),
                verification_status TEXT NOT NULL CHECK (verification_status='source_imported_unreviewed'),
                raw_record_json TEXT NOT NULL
            );
            CREATE TABLE tgk_make (
                source_row_sha256 TEXT PRIMARY KEY CHECK (length(source_row_sha256)=64),
                scope_id TEXT NOT NULL REFERENCES approval_scope(scope_id),
                source_dataset_id TEXT NOT NULL REFERENCES source_registry(dataset_id),
                source_revision TEXT NOT NULL,
                license_id TEXT NOT NULL CHECK (license_id='CC0-1.0'),
                rdw_make_code_candidate TEXT,
                market_scope TEXT NOT NULL CHECK (market_scope='NL'),
                applicability_precision TEXT NOT NULL CHECK (applicability_precision='exact_RDW_approval_variant_version_revision_scope'),
                verification_status TEXT NOT NULL CHECK (verification_status='source_imported_unreviewed'),
                raw_record_json TEXT NOT NULL
            );
            CREATE TABLE tgk_trade_name (
                source_row_sha256 TEXT PRIMARY KEY CHECK (length(source_row_sha256)=64),
                scope_id TEXT NOT NULL REFERENCES approval_scope(scope_id),
                source_dataset_id TEXT NOT NULL REFERENCES source_registry(dataset_id),
                source_revision TEXT NOT NULL,
                license_id TEXT NOT NULL CHECK (license_id='CC0-1.0'),
                manufacturer_trade_name_candidate TEXT,
                manufacturer_type_designation_candidate TEXT,
                market_scope TEXT NOT NULL CHECK (market_scope='NL'),
                applicability_precision TEXT NOT NULL CHECK (applicability_precision='exact_RDW_approval_variant_version_revision_scope'),
                verification_status TEXT NOT NULL CHECK (verification_status='source_imported_unreviewed'),
                raw_record_json TEXT NOT NULL
            );
            CREATE TABLE database_info (
                id INTEGER PRIMARY KEY CHECK (id=1),
                schema_version INTEGER NOT NULL CHECK (schema_version=1),
                source_id TEXT NOT NULL,
                source_projection_bundle_sha256 TEXT NOT NULL CHECK (length(source_projection_bundle_sha256)=64),
                created_at_utc TEXT NOT NULL,
                approval_scope_count INTEGER NOT NULL,
                registration_observation_count INTEGER NOT NULL,
                tgk_drive_count INTEGER NOT NULL,
                tgk_gearbox_count INTEGER NOT NULL,
                production_import_allowed INTEGER NOT NULL CHECK (production_import_allowed=0),
                engine_gearbox_pair_claims INTEGER NOT NULL CHECK (engine_gearbox_pair_claims=0),
                ru_eaeu_applicability INTEGER NOT NULL CHECK (ru_eaeu_applicability=0)
            );
            CREATE INDEX idx_approval_scope_number ON approval_scope(type_approval_number);
            CREATE INDEX idx_registration_make_trade ON registration_observation(make_label, trade_name_nl);
            CREATE INDEX idx_tgk_drive_scope ON tgk_drive(scope_id);
            CREATE INDEX idx_tgk_gearbox_scope ON tgk_gearbox(scope_id);
        """)
        registry_by_name = {item["dataset_name"]: item for item in file_entries}
        with connection:
            for name, item in registry_by_name.items():
                connection.execute(
                    """INSERT INTO source_registry
                    (dataset_id,dataset_name,title,catalog_url,api_url,license_id,rights_status,
                     source_revision,query_sha256,projection_sha256,row_count,market_scope,production_import_allowed)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,0)""",
                    (
                        item["dataset_id"], name, item["title"] or name, item["catalog_url"] or "",
                        item["api_url"] or "", "CC0-1.0", "approved_by_published_CC0_license",
                        item["source_revision"], item["query_sha256"], item["projection_sha256"],
                        item["row_count"], "NL",
                    ),
                )

            scope_keys = context["approval_scope_keys"]
            for key in scope_keys:
                connection.execute(
                    """INSERT INTO approval_scope
                    (scope_id,type_approval_number,variant,version,revision,market_scope,
                     applicability_precision,verification_status,model_year,generation,
                     individual_vehicle_fitment,production_fitment,ru_eaeu_applicability,
                     exact_vag_engine_code,exact_vag_gearbox_code,exact_engine_gearbox_pair,
                     ecu_dtc_repair_applicability)
                    VALUES (?,?,?,?,?,'NL','exact_RDW_approval_variant_version_revision_scope',
                            'source_imported_unreviewed',NULL,NULL,0,0,0,0,0,0,0)""",
                    (scope_id_for(key), key["typegoedkeuringsnummer"], key["variant"], key["version"], key["revision"]),
                )

            def insert_rows(dataset_name: str, table: str, sql: str, values_fn: Any) -> None:
                config = registry_by_name[dataset_name]
                for item in projections[dataset_name]:
                    record = item["record"]
                    assert_safe_record(record)
                    connection.execute(sql, values_fn(item, config))

            insert_rows(
                "registered_vehicle_identity",
                "registration_observation",
                """INSERT INTO registration_observation
                (source_row_sha256,scope_id,source_dataset_id,source_revision,license_id,make_label,
                 trade_name_nl,vehicle_category,displacement_cc,cylinder_count,market_scope,
                 applicability_precision,verification_status,raw_record_json)
                VALUES (?,?,?,?,?,?,?,?,?,?,'NL','exact_RDW_approval_variant_version_revision_scope',
                        'source_imported_unreviewed',?)""",
                lambda item, config: (
                    item["source_row_sha256"], item["scope_id"], config["dataset_id"],
                    config["source_revision"], "CC0-1.0",
                    str(item["record"].get("merk") or ""), item["record"].get("handelsbenaming"),
                    item["record"].get("voertuigsoort"), item["record"].get("cilinderinhoud"),
                    item["record"].get("aantal_cilinders"),
                    json.dumps(item["record"], ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                ),
            )
            insert_rows(
                "tgk_drive",
                "tgk_drive",
                """INSERT INTO tgk_drive
                (source_row_sha256,scope_id,source_dataset_id,source_revision,license_id,
                 motorcode_candidate,engine_type_approval_number,cylinder_count,displacement_cc,
                 market_scope,applicability_precision,verification_status,raw_record_json)
                VALUES (?,?,?,?,?,?,?,?,?,'NL','exact_RDW_approval_variant_version_revision_scope',
                        'source_imported_unreviewed',?)""",
                lambda item, config: (
                    item["source_row_sha256"], item["scope_id"], config["dataset_id"],
                    config["source_revision"], "CC0-1.0",
                    item["record"].get("motorcode"), item["record"].get("typegoedkeuringsnummermotor"),
                    item["record"].get("aantalcilinders"), item["record"].get("cilinderinhoud"),
                    json.dumps(item["record"], ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                ),
            )
            insert_rows(
                "tgk_gearbox",
                "tgk_gearbox",
                """INSERT INTO tgk_gearbox
                (source_row_sha256,scope_id,source_dataset_id,source_revision,license_id,
                 gearbox_type_classification_candidate,market_scope,applicability_precision,
                 verification_status,raw_record_json)
                VALUES (?,?,?,?,?,?,'NL','exact_RDW_approval_variant_version_revision_scope',
                        'source_imported_unreviewed',?)""",
                lambda item, config: (
                    item["source_row_sha256"], item["scope_id"], config["dataset_id"],
                    config["source_revision"], "CC0-1.0",
                    item["record"].get("codetypeversnellingsbak"),
                    json.dumps(item["record"], ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                ),
            )
            insert_rows(
                "tgk_base",
                "tgk_base",
                """INSERT INTO tgk_base
                (source_row_sha256,scope_id,source_dataset_id,source_revision,license_id,
                 revision_start_date,vehicle_category,market_scope,applicability_precision,
                 verification_status,raw_record_json)
                VALUES (?,?,?,?,?,?,?,'NL','exact_RDW_approval_variant_version_revision_scope',
                        'source_imported_unreviewed',?)""",
                lambda item, config: (
                    item["source_row_sha256"], item["scope_id"], config["dataset_id"],
                    config["source_revision"], "CC0-1.0",
                    item["record"].get("begindatumrevisieuitvoering"),
                    item["record"].get("voertuigcategorie"),
                    json.dumps(item["record"], ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                ),
            )
            insert_rows(
                "tgk_make",
                "tgk_make",
                """INSERT INTO tgk_make
                (source_row_sha256,scope_id,source_dataset_id,source_revision,license_id,
                 rdw_make_code_candidate,market_scope,applicability_precision,
                 verification_status,raw_record_json)
                VALUES (?,?,?,?,?,?,'NL','exact_RDW_approval_variant_version_revision_scope',
                        'source_imported_unreviewed',?)""",
                lambda item, config: (
                    item["source_row_sha256"], item["scope_id"], config["dataset_id"],
                    config["source_revision"], "CC0-1.0",
                    item["record"].get("merkcoderdw"),
                    json.dumps(item["record"], ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                ),
            )
            insert_rows(
                "tgk_trade_name",
                "tgk_trade_name",
                """INSERT INTO tgk_trade_name
                (source_row_sha256,scope_id,source_dataset_id,source_revision,license_id,
                 manufacturer_trade_name_candidate,manufacturer_type_designation_candidate,
                 market_scope,applicability_precision,verification_status,raw_record_json)
                VALUES (?,?,?,?,?,?,?,'NL','exact_RDW_approval_variant_version_revision_scope',
                        'source_imported_unreviewed',?)""",
                lambda item, config: (
                    item["source_row_sha256"], item["scope_id"], config["dataset_id"],
                    config["source_revision"], "CC0-1.0",
                    item["record"].get("handelsbenamingfabrikant"),
                    item["record"].get("typeaanduidingfabrikant"),
                    json.dumps(item["record"], ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                ),
            )

            counts = {
                "approval_scope": connection.execute("SELECT count(*) FROM approval_scope").fetchone()[0],
                "registration_observation": connection.execute("SELECT count(*) FROM registration_observation").fetchone()[0],
                "tgk_drive": connection.execute("SELECT count(*) FROM tgk_drive").fetchone()[0],
                "tgk_gearbox": connection.execute("SELECT count(*) FROM tgk_gearbox").fetchone()[0],
                "tgk_base": connection.execute("SELECT count(*) FROM tgk_base").fetchone()[0],
                "tgk_make": connection.execute("SELECT count(*) FROM tgk_make").fetchone()[0],
                "tgk_trade_name": connection.execute("SELECT count(*) FROM tgk_trade_name").fetchone()[0],
            }
            connection.execute(
                """INSERT INTO database_info
                (id,schema_version,source_id,source_projection_bundle_sha256,created_at_utc,
                 approval_scope_count,registration_observation_count,tgk_drive_count,tgk_gearbox_count,
                 production_import_allowed,engine_gearbox_pair_claims,ru_eaeu_applicability)
                VALUES (1,1,?,?,?,?,?,?,?,0,0,0)""",
                (
                    SOURCE_ID, projection_bundle_sha256, datetime.now(timezone.utc).isoformat(),
                    counts["approval_scope"], counts["registration_observation"],
                    counts["tgk_drive"], counts["tgk_gearbox"],
                ),
            )
        validate_database(connection)
        return counts
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def assert_safe_record(record: dict[str, Any]) -> None:
    for key in record:
        lowered = str(key).lower()
        if any(token in lowered for token in FORBIDDEN_FIELD_TOKENS):
            raise ValueError(f"Forbidden identity/personal-data field in stored projection: {key}")


def validate_database(connection: sqlite3.Connection) -> None:
    integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
    if integrity != "ok":
        raise RuntimeError(f"RDW SQLite integrity_check failed: {integrity}")
    foreign_keys = connection.execute("PRAGMA foreign_key_check").fetchall()
    if foreign_keys:
        raise RuntimeError(f"RDW SQLite foreign-key violations: {len(foreign_keys)}")
    table_names = {
        row[0] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('table','view')"
        )
    }
    if any("pair" in name.lower() for name in table_names):
        raise RuntimeError("RDW research database must not contain an engine/gearbox pair table or view")
    required_tables = {
        "source_registry", "approval_scope", "registration_observation",
        "tgk_drive", "tgk_gearbox", "tgk_base", "tgk_make", "tgk_trade_name",
        "database_info",
    }
    if not required_tables.issubset(table_names):
        raise RuntimeError("RDW SQLite schema is incomplete")
    bad_scopes = connection.execute("""
        SELECT count(*) FROM approval_scope
        WHERE model_year IS NOT NULL OR generation IS NOT NULL
           OR individual_vehicle_fitment<>0 OR production_fitment<>0
           OR ru_eaeu_applicability<>0 OR exact_vag_engine_code<>0
           OR exact_vag_gearbox_code<>0 OR exact_engine_gearbox_pair<>0
           OR ecu_dtc_repair_applicability<>0 OR market_scope<>'NL'
    """).fetchone()[0]
    if bad_scopes:
        raise RuntimeError(f"RDW approval scopes contain prohibited fitment claims: {bad_scopes}")
    for table in (
        "registration_observation", "tgk_drive", "tgk_gearbox", "tgk_base",
        "tgk_make", "tgk_trade_name",
    ):
        bad_rows = connection.execute(
            f"SELECT count(*) FROM {table} WHERE length(source_row_sha256)<>64 OR market_scope<>'NL' OR license_id<>'CC0-1.0'"
        ).fetchone()[0]
        if bad_rows:
            raise RuntimeError(f"RDW provenance/market/license validation failed for {table}: {bad_rows}")
        for (raw_json,) in connection.execute(f"SELECT raw_record_json FROM {table}"):
            record = json.loads(raw_json)
            assert_safe_record(record)
    info = connection.execute("SELECT * FROM database_info WHERE id=1").fetchone()
    if not info or info["production_import_allowed"] != 0 or info["engine_gearbox_pair_claims"] != 0:
        raise RuntimeError("RDW database production/pairing safety flags are invalid")


def build_pack(output_dir: Path) -> dict[str, Any]:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"Refusing to overwrite a non-empty output directory: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    source_manifest, make_allowlist = load_rights_inputs()
    projections, metadata, context = fetch_projection_data(source_manifest, make_allowlist)
    file_entries, projection_bundle_sha256 = write_projection_files(output_dir, projections, context)

    context["contracts"] = metadata_contracts(source_manifest)
    for item in file_entries:
        context["contracts"][item["dataset_name"]]["source_revision"] = item["source_revision"]
    database_path = output_dir / "rdw-vag-type-approval.sqlite"
    counts = create_database(
        database_path, projections, file_entries, context, projection_bundle_sha256
    )
    database_sha256 = sha256_bytes(database_path.read_bytes())

    manifest = {
        "schema_version": 1,
        "pack_id": PACK_ID,
        "source_id": SOURCE_ID,
        "publisher": "RDW (Dienst Wegverkeer), Netherlands",
        "license": "CC0-1.0",
        "rights_status": "approved_by_published_CC0_license",
        "rights_evidence_urls": source_manifest["rights"]["evidence_urls"],
        "market_scope": ["NL"],
        "approval_jurisdiction": "EU type-approval identifiers as recorded in RDW Netherlands datasets",
        "snapshot_kind": "filtered_source_projection_not_full_upstream_snapshot",
        "full_upstream_snapshot": False,
        "source_snapshot_sha256": None,
        "source_projection_bundle_sha256": projection_bundle_sha256,
        "source_projections": file_entries,
        "database": {
            "path": database_path.name,
            "sha256": database_sha256,
            "bytes": database_path.stat().st_size,
            "integrity_check": "ok",
            "foreign_key_violations": 0,
        },
        "counts": counts,
        "make_labels_observed": context["observed_make_labels"],
        "incomplete_registration_scope_rows_excluded": context["incomplete_scope_rows"],
        "unmatched_tgk_rows_excluded_by_exact_scope": context["unmatched_tgk_rows"],
        "applicability": {
            "precision": "exact_RDW_approval_variant_version_revision_scope",
            "model_year": None,
            "generation": None,
            "individual_vehicle_fitment": False,
            "production_fitment": False,
            "ru_eaeu_applicability": False,
            "exact_vag_engine_code": False,
            "exact_vag_gearbox_code": False,
            "exact_engine_gearbox_pair": False,
            "ecu_dtc_repair_applicability": False,
        },
        "field_semantics": {
            "motorcode": "RDW engine-designation candidate only; not independently confirmed as a VAG factory engine code.",
            "codetypeversnellingsbak": "RDW approval gearbox-type classification only; not a VAG gearbox code.",
            "engine_gearbox_pairing": "Engine and gearbox rows are stored in separate tables and are never cross-joined or represented as a pair.",
            "handelsbenaming": "Dutch registration trade-name observation; not a VAG generation identifier.",
            "handelsbenamingfabrikant": "Manufacturer trade-name candidate; not a generation identifier.",
            "datum_eerste_toelating": "Not selected; first registration date is not model year.",
        },
        "privacy": {
            "registration_plate_selected": False,
            "vin_selected": False,
            "holder_or_owner_fields_selected": False,
            "address_or_personal_data_selected": False,
            "excluded_field_tokens": list(FORBIDDEN_FIELD_TOKENS),
        },
        "import_policy": {
            "research_pack_only": True,
            "product_import_allowed": False,
            "production_import_allowed": False,
            "ru_eaeu_applicability": False,
            "engine_gearbox_pair_claims": False,
            "command_execution_allowed": False,
            "repair_guidance_allowed": False,
        },
        "verification_status": "verified_research_only",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    attribution = (
        "# RDW VAG type-approval research projection\n\n"
        "Source: RDW Open Data (Netherlands), CC0 1.0. Attribution is provided as a courtesy.\n\n"
        "This is a filtered projection of six public RDW datasets, not a full upstream snapshot. "
        "The data is limited to NL observations and EU type-approval scopes. RDW motorcode values "
        "and gearbox classifications remain candidates; no exact VAG engine/gearbox pairing, model "
        "year, generation, production fitment, RU/EAEU applicability, ECU, DTC or repair applicability "
        "is asserted. Registration plates, VIN and holder data were not selected or stored.\n"
    )
    (output_dir / "ATTRIBUTION.md").write_text(attribution, encoding="utf-8")
    return {
        "status": "verified_research_only",
        "pack_id": PACK_ID,
        "database_sha256": database_sha256,
        "source_projection_bundle_sha256": projection_bundle_sha256,
        "manifest_sha256": sha256_bytes(manifest_path.read_bytes()),
        "counts": counts,
        "make_labels_observed": context["observed_make_labels"],
        "market_scope": ["NL"],
        "production_import_allowed": False,
        "engine_gearbox_pair_claims": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/rdw-vag-research-pack"))
    args = parser.parse_args()
    report = build_pack(args.output_dir)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
