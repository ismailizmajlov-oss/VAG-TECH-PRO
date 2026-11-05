#!/usr/bin/env python3
"""Build a separate, read-only Swiss ASTRA/FEDRO VAG type-approval research pack.

The pack is CH-only. It never creates Russian/EAEU fitment, VAG factory gearbox-code,
repair, ECU, DTC, or VIN-level claims. All source rows retain source-file and row hashes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import tempfile
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE = "https://opendata.astra.admin.ch/ivzod/4000-Typengenehmigungen_TAS"
VAG_MAKES = {
    "AUDI", "BENTLEY", "BUGATTI", "CUPRA", "LAMBORGHINI",
    "PORSCHE", "SEAT", "SKODA", "ŠKODA", "VOLKSWAGEN", "VW",
}
INDEX_KEYS = ("passenger_cars", "other_automobiles", "emissions")
REQUIRED_APPROVAL_FIELDS = {
    "chTypeApprovalNumber", "makeName", "commercialName", "type", "variant",
    "version", "versionNo", "vehicleCategoryCode", "VehicleType",
    "manufacturerOfTheEngine", "engineType", "chEngineCodeAsMarkedOnTheEngine",
    "chFuelType", "engineCapacity", "maximumNetPower", "maximumTorque",
    "numberOfCylinders", "driveType", "dateOfApproval", "dateOfLastChange",
    "cancelationDate", "dateOfApprovalExpiry",
}
REQUIRED_EMISSIONS_FIELDS = {
    "chTypeApprovalNumber", "makeName", "gearboxNumber", "chGearboxType",
    "chMapping", "versionDefined", "chFinalDriveRatio",
}
APPROVAL_COLUMNS = (
    "chTypeApprovalNumber", "makeName", "commercialName", "type", "variant",
    "version", "versionNo", "VehicleType", "vehicleCategoryCode", "chVehicleType",
    "chVehicleSubType", "manufacturerOfTheEngine", "engineType",
    "chEngineCodeAsMarkedOnTheEngine", "chFuelType", "engineCapacity",
    "maximumNetPower", "maximumTorque", "numberOfCylinders", "stroke",
    "driveType", "dateOfApproval", "dateOfLastChange", "cancelationDate",
    "dateOfApprovalExpiry",
)
EMISSIONS_COLUMNS = (
    "chTypeApprovalNumber", "makeName", "VehicleType", "commercialName",
    "totalnumberchGearboxType", "gearboxNumber", "chGearboxType", "chMapping",
    "versionDefined", "chFinalDriveRatio", "primaryFuelConsumption",
    "primaryEmissionCo2", "primaryFuelConsumptionWltp", "primaryEmissionCo2Wltp",
    "exhaustEmissionLevelCode", "exhaustEmissionLevelCodeShort",
)
ATTRIBUTION = "Source: Federal Roads Office (FEDRO/ASTRA), Type Approval System (TAS) open data."
SOURCE_ID = "astra-fedro-tas-type-approvals-open-data-ch"
PUBLISHER = "Federal Roads Office (FEDRO / ASTRA), Swiss Confederation"
RIGHTS_EVIDENCE_URL = "https://opendata.astra.admin.ch/ivzod/5000-Newsletter/2026_1/Newsletter_Fahrzeugdaten_1_2026_EN.pdf"
EXPECTED_DATA_PRODUCT_URLS = {
    "passenger_car_index": f"{BASE}/4300-Datensaetze/TAS_Personenwagen.xlsb",
    "other_automobile_index_xlsb": f"{BASE}/4300-Datensaetze/TAS_restliche_Automobilgruppen.xlsb",
    "emissions_and_gearbox_variants_xlsb": f"{BASE}/4300-Datensaetze/TAS_Emission.xlsb",
    "json_schema": f"{BASE}/4250-json-Schema/govServices_TypeApproval_Schema.json",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def canonical_row_sha256(row: dict[str, Any]) -> str:
    payload = json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def is_vag_make(value: Any, allowed: set[str] | None = None) -> bool:
    return normalize_text(value).upper() in (allowed or VAG_MAKES)


def resolve_scope_link(
    approval_index: dict[tuple[str, str], list[dict[str, Any]]],
    approval_number: Any,
    make_name: Any,
    version_defined: Any,
    ch_gearbox_type: Any,
) -> tuple[int | None, str]:
    """Link exact approval variant/version scope and a gearbox class listed by that approval.

    ASTRA's versionDefined is the composite raw scope variant/version. A '*' in
    either component is preserved as a wildcard and is never promoted to exact
    version fitment. This is an approval-scope association, not a factory VAG
    engine/gearbox code pair or production fitment claim.
    """
    approval = normalize_text(approval_number)
    make = normalize_text(make_name).upper()
    scope = normalize_text(version_defined)
    if not approval or not make:
        return None, "approval_key_missing"
    candidates = approval_index.get((approval, make), [])
    if not candidates:
        return None, "approval_record_missing"
    if not scope:
        return None, "version_scope_missing"

    scoped_candidates = [
        row for row in candidates
        if normalize_text(row.get("variant")) and normalize_text(row.get("version"))
    ]
    if not scoped_candidates:
        return None, "version_scope_missing"

    matches = [
        row for row in scoped_candidates
        if scope == f'{normalize_text(row["variant"])}/{normalize_text(row["version"])}'
    ]
    if len(matches) > 1:
        return None, "ambiguous_approval_version"
    if len(matches) != 1:
        return None, "no_exact_version_match"

    match = matches[0]
    gearbox_type = normalize_text(ch_gearbox_type)
    allowed_gearbox_classes = {
        normalize_text(value)
        for value in match.get("gearbox_classes", [])
        if normalize_text(value)
    }
    if not gearbox_type or gearbox_type not in allowed_gearbox_classes:
        return None, "gearbox_class_not_in_approval"

    if normalize_text(match["variant"]) == "*" or normalize_text(match["version"]) == "*":
        return int(match["approval_row_id"]), "linked_wildcard_approval_variant"
    return int(match["approval_row_id"]), "linked_exact_approval_version"


def _download_or_verify(url: str, destination: Path, expected: dict[str, Any]) -> dict[str, Any]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.is_file():
        request = urllib.request.Request(
            url, headers={"User-Agent": "VAG-TECH-PRO/0.1 (Swiss OGD attribution preserved)"}
        )
        with urllib.request.urlopen(request, timeout=300) as response, destination.open("wb") as output:
            if response.status != 200:
                raise ValueError(f"HTTP {response.status} while downloading {url}")
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                output.write(chunk)
    actual_size = destination.stat().st_size
    actual_hash = sha256_file(destination)
    if actual_size != int(expected["size_bytes"]):
        raise ValueError(f"Snapshot size mismatch for {destination.name}: {actual_size}")
    if actual_hash != expected["sha256"]:
        raise ValueError(f"Snapshot SHA-256 mismatch for {destination.name}: {actual_hash}")
    return {"url": url, "file_name": destination.name, "size_bytes": actual_size, "sha256": actual_hash}


def _workbook_rows(path: Path, expected_sheet: str, expected_rows: int):
    try:
        from pyxlsb import open_workbook
    except ImportError as exc:
        raise RuntimeError("pyxlsb==1.0.10 is required to read official ASTRA XLSB files") from exc
    with open_workbook(str(path)) as workbook:
        if list(workbook.sheets) != [expected_sheet]:
            raise ValueError(f"Unexpected sheets in {path.name}: {workbook.sheets}")
        with workbook.get_sheet(expected_sheet) as sheet:
            header: list[str] | None = None
            rows_seen = 0
            for row_number, cells in enumerate(sheet.rows(), start=1):
                rows_seen += 1
                values = [cell.v for cell in cells]
                if header is None:
                    if not any(value is not None for value in values):
                        continue
                    header = [normalize_text(value) for value in values]
                    continue
                yield row_number, header, {
                    header[index]: values[index] if index < len(values) else None
                    for index in range(len(header))
                    if header[index]
                }
            if header is None:
                raise ValueError(f"No header row found in {path.name}")
            if rows_seen != expected_rows:
                raise ValueError(f"Row-count drift in {path.name}: {rows_seen} != {expected_rows}")


def _read_rows(path: Path, expected_sheet: str, expected_rows: int):
    """Materialize the iterator while keeping workbook context open."""
    return list(_workbook_rows(path, expected_sheet, expected_rows))


def _check_rights(source_manifest: dict[str, Any]) -> None:
    if source_manifest.get("source_id") != SOURCE_ID:
        raise ValueError("ASTRA source identity mismatch")
    if source_manifest.get("publisher") != PUBLISHER:
        raise ValueError("ASTRA publisher identity mismatch")
    if source_manifest.get("source_kind") != "official_open_government_vehicle_type_approval_data":
        raise ValueError("ASTRA source kind mismatch")
    if source_manifest.get("market_scope") != ["CH"]:
        raise ValueError("ASTRA pack market scope must remain CH only")

    rights = source_manifest.get("rights", {})
    if rights.get("rights_status") != "approved_by_published_ogd_terms":
        raise ValueError("ASTRA OGD rights status is not approved")
    if "Swiss Open Government Data (OGD)" not in rights.get("data_license_status", ""):
        raise ValueError("ASTRA OGD licence basis is missing")
    if "EMBAG/EMOTA" not in rights.get("legal_basis", ""):
        raise ValueError("ASTRA OGD legal basis is missing")
    if rights.get("evidence_url") != RIGHTS_EVIDENCE_URL:
        raise ValueError("ASTRA OGD rights evidence URL is not the reviewed FEDRO notice")
    if "2026-02-23" not in rights.get("evidence", ""):
        raise ValueError("ASTRA OGD evidence date is missing")
    for key in ("commercial_use_allowed", "display_allowed", "offline_cache_allowed",
                "bulk_reuse_allowed", "redistribution_allowed", "attribution_required"):
        if rights.get(key) is not True:
            raise ValueError(f"ASTRA OGD rights gate failed: {key}")
    if rights.get("attribution") != ATTRIBUTION:
        raise ValueError("Required FEDRO/ASTRA attribution text changed or is missing")

    products = source_manifest.get("data_products", {})
    for key, expected_url in EXPECTED_DATA_PRODUCT_URLS.items():
        if products.get(key) != expected_url:
            raise ValueError(f"ASTRA source URL mismatch: {key}")
    if products.get("official_newsletter") != RIGHTS_EVIDENCE_URL:
        raise ValueError("ASTRA rights evidence and data-product manifest disagree")

    policy = source_manifest.get("import_policy", {})
    if policy.get("namespace") != "separate_read_only_research_pack":
        raise ValueError("ASTRA pack must remain a separate read-only research namespace")
    if policy.get("production_import") is not False or policy.get("ru_eaeu_applicability") is not False:
        raise ValueError("ASTRA source must never be imported as RU/EAEU production fitment")
    if policy.get("exact_brand_match_only") is not True:
        raise ValueError("ASTRA make filter must use exact source labels")


def _create_schema(db: sqlite3.Connection) -> None:
    db.executescript("""
    PRAGMA foreign_keys=ON;
    PRAGMA journal_mode=DELETE;
    PRAGMA synchronous=FULL;
    PRAGMA user_version=2;

    CREATE TABLE pack_metadata (
      key TEXT PRIMARY KEY,
      value TEXT NOT NULL
    ) WITHOUT ROWID;

    CREATE TABLE source_files (
      file_key TEXT PRIMARY KEY,
      source_url TEXT NOT NULL,
      file_name TEXT NOT NULL,
      size_bytes INTEGER NOT NULL CHECK(size_bytes>0),
      sha256 TEXT NOT NULL CHECK(length(sha256)=64 AND lower(sha256) NOT GLOB '*[^0-9a-f]*'),
      source_revision TEXT NOT NULL,
      rights_status TEXT NOT NULL CHECK(rights_status='approved_by_published_ogd_terms'),
      market_scope TEXT NOT NULL CHECK(market_scope='CH')
    ) WITHOUT ROWID;

    CREATE TABLE type_approval_records (
      approval_row_id INTEGER PRIMARY KEY,
      source_file_key TEXT NOT NULL REFERENCES source_files(file_key),
      source_row_number INTEGER NOT NULL CHECK(source_row_number>1),
      source_row_sha256 TEXT NOT NULL CHECK(length(source_row_sha256)=64 AND lower(source_row_sha256) NOT GLOB '*[^0-9a-f]*'),
      source_record_locator TEXT NOT NULL,
      market_scope TEXT NOT NULL DEFAULT 'CH' CHECK(market_scope='CH'),
      approval_number TEXT NOT NULL,
      make_name TEXT NOT NULL,
      commercial_name TEXT,
      type_designation TEXT,
      variant TEXT,
      version TEXT,
      version_no TEXT,
      vehicle_type TEXT,
      vehicle_category_code TEXT,
      ch_vehicle_type TEXT,
      ch_vehicle_subtype TEXT,
      manufacturer_of_engine TEXT,
      engine_type_designation TEXT,
      stamped_engine_marking TEXT,
      fuel_type TEXT,
      engine_capacity_cc REAL,
      maximum_net_power TEXT,
      maximum_torque TEXT,
      number_of_cylinders TEXT,
      stroke TEXT,
      drive_type TEXT,
      approval_gearbox_classes_json TEXT NOT NULL,
      date_of_approval TEXT,
      date_of_last_change TEXT,
      cancellation_date TEXT,
      approval_expiry_date TEXT,
      applicability_precision TEXT NOT NULL DEFAULT 'ch_type_approval_row'
        CHECK(applicability_precision='ch_type_approval_row'),
      technical_status TEXT NOT NULL DEFAULT 'research_only_not_repair_fitment'
        CHECK(technical_status='research_only_not_repair_fitment'),
      UNIQUE(source_file_key, source_row_number)
    );

    CREATE INDEX idx_astra_approval_search
      ON type_approval_records(make_name, commercial_name, approval_number);
    CREATE INDEX idx_astra_engine_descriptor
      ON type_approval_records(make_name, engine_type_designation, stamped_engine_marking);

    CREATE TABLE emissions_gearbox_rows (
      gearbox_row_id INTEGER PRIMARY KEY,
      source_file_key TEXT NOT NULL REFERENCES source_files(file_key),
      source_row_number INTEGER NOT NULL CHECK(source_row_number>1),
      source_row_sha256 TEXT NOT NULL CHECK(length(source_row_sha256)=64 AND lower(source_row_sha256) NOT GLOB '*[^0-9a-f]*'),
      source_record_locator TEXT NOT NULL,
      market_scope TEXT NOT NULL DEFAULT 'CH' CHECK(market_scope='CH'),
      approval_number TEXT NOT NULL,
      make_name TEXT NOT NULL,
      vehicle_type TEXT,
      commercial_name TEXT,
      total_gearbox_classes TEXT,
      gearbox_number TEXT,
      ch_gearbox_type TEXT,
      ch_mapping TEXT,
      version_defined TEXT,
      final_drive_ratio TEXT,
      fuel_consumption TEXT,
      co2_emission TEXT,
      fuel_consumption_wltp TEXT,
      co2_emission_wltp TEXT,
      emission_level TEXT,
      emission_level_short TEXT,
      linked_approval_row_id INTEGER REFERENCES type_approval_records(approval_row_id),
      scope_link_status TEXT NOT NULL CHECK(scope_link_status IN (
        'linked_exact_approval_version','linked_wildcard_approval_variant',
        'approval_key_missing','approval_record_missing','version_scope_missing',
        'ambiguous_approval_version','no_exact_version_match','gearbox_class_not_in_approval'
      )),
      classification_kind TEXT NOT NULL DEFAULT 'swiss_type_approval_gearbox_classification'
        CHECK(classification_kind='swiss_type_approval_gearbox_classification'),
      applicability_precision TEXT NOT NULL CHECK(applicability_precision IN (
        'approval_version_exact','approval_variant_wildcard','unlinked_scope'
      )),
      UNIQUE(source_file_key, source_row_number)
    );

    CREATE INDEX idx_astra_gearbox_search
      ON emissions_gearbox_rows(make_name, approval_number, ch_gearbox_type);

    CREATE TABLE engine_gearbox_scope_links (
      link_id INTEGER PRIMARY KEY,
      approval_row_id INTEGER NOT NULL REFERENCES type_approval_records(approval_row_id),
      gearbox_row_id INTEGER NOT NULL UNIQUE REFERENCES emissions_gearbox_rows(gearbox_row_id),
      market_scope TEXT NOT NULL DEFAULT 'CH' CHECK(market_scope='CH'),
      engine_type_designation TEXT,
      stamped_engine_marking TEXT,
      swiss_gearbox_type TEXT,
      version_scope TEXT NOT NULL,
      relation_precision TEXT NOT NULL CHECK(relation_precision IN (
        'approval_version_exact','approval_variant_wildcard'
      )),
      factory_vag_engine_code_claim INTEGER NOT NULL DEFAULT 0 CHECK(factory_vag_engine_code_claim=0),
      factory_vag_gearbox_code_claim INTEGER NOT NULL DEFAULT 0 CHECK(factory_vag_gearbox_code_claim=0),
      production_fitment_claim INTEGER NOT NULL DEFAULT 0 CHECK(production_fitment_claim=0)
    );

    CREATE TRIGGER prevent_non_ch_approval_insert
    BEFORE INSERT ON type_approval_records WHEN NEW.market_scope<>'CH'
    BEGIN SELECT RAISE(ABORT, 'ASTRA TAS records are CH-only'); END;
    CREATE TRIGGER prevent_non_ch_gearbox_insert
    BEFORE INSERT ON emissions_gearbox_rows WHEN NEW.market_scope<>'CH'
    BEGIN SELECT RAISE(ABORT, 'ASTRA TAS records are CH-only'); END;
    CREATE TRIGGER prevent_non_ch_link_insert
    BEFORE INSERT ON engine_gearbox_scope_links WHEN NEW.market_scope<>'CH'
    BEGIN SELECT RAISE(ABORT, 'ASTRA TAS links are CH-only'); END;
    """)


def _value(row: dict[str, Any], key: str) -> str | None:
    value = row.get(key)
    if value is None:
        return None
    return normalize_text(value) or None


def build_pack(input_dir: Path, output_dir: Path, source_manifest_path: Path) -> dict[str, Any]:
    source_manifest_bytes = source_manifest_path.read_bytes()
    source_manifest_sha256 = hashlib.sha256(source_manifest_bytes).hexdigest()
    source_manifest = json.loads(source_manifest_bytes.decode("utf-8-sig"))
    _check_rights(source_manifest)
    snapshot = source_manifest["snapshot"]
    source_revision = str(snapshot["source_data_date"])
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    definitions = {
        "passenger_cars": (snapshot["passenger_car_index"], source_manifest["data_products"]["passenger_car_index"], "TAS_Personenwagen.xlsb"),
        "other_automobiles": (snapshot["other_automobile_index"], source_manifest["data_products"]["other_automobile_index_xlsb"], "TAS_restliche_Automobilgruppen.xlsb"),
        "emissions": (snapshot["emissions_index"], source_manifest["data_products"]["emissions_and_gearbox_variants_xlsb"], "TAS_Emission.xlsb"),
        "json_schema": (snapshot["json_schema"], source_manifest["data_products"]["json_schema"], "govServices_TypeApproval_Schema.json"),
    }
    file_evidence: dict[str, dict[str, Any]] = {}
    for key, (expected, url, filename) in definitions.items():
        file_evidence[key] = _download_or_verify(url, input_dir / filename, expected)

    expected_indexes = snapshot["index_row_counts"]
    expected_make_counts = snapshot["vag_approval_counts"]
    expected_emissions_counts = snapshot.get("vag_emissions_gearbox_rows")
    if not isinstance(expected_emissions_counts, dict) or "total" not in expected_emissions_counts:
        raise ValueError("Pinned per-make VAG emissions/gearbox row counts are missing from source manifest")

    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    database_path = output_dir / "astra-ch-tas-vag-open-data.sqlite"
    fd, temp_name = tempfile.mkstemp(prefix="astra-ch-tas-", suffix=".sqlite", dir=output_dir)
    os.close(fd)
    temp_path = Path(temp_name)
    counts: dict[str, Any] = {
        "approval_rows": {},
        "emissions_gearbox_rows": {},
        "linked_scope_rows": 0,
        "unlinked_scope_rows": 0,
        "scope_link_counts": {},
        "scope_link_counts_by_make": {},
    }
    try:
        db = sqlite3.connect(temp_path)
        db.execute("PRAGMA foreign_keys=ON")
        _create_schema(db)
        db.execute("BEGIN IMMEDIATE")
        for key, evidence in file_evidence.items():
            db.execute(
                """INSERT INTO source_files(file_key,source_url,file_name,size_bytes,sha256,source_revision,rights_status,market_scope)
                   VALUES(?,?,?,?,?,?,?,?)""",
                (key, evidence["url"], evidence["file_name"], evidence["size_bytes"],
                 evidence["sha256"], source_revision, "approved_by_published_ogd_terms", "CH"),
            )
        metadata = {
            "schema_version": "2",
            "pack_id": "astra-ch-tas-vag-open-data",
            "pack_status": "verified_research_only",
            "publisher": source_manifest["publisher"],
            "market_scope": "CH",
            "source_revision": source_revision,
            "source_snapshot_date": source_revision,
            "source_manifest_sha256": source_manifest_sha256,
            "retrieved_at_utc": timestamp,
            "rights_status": "approved_by_published_ogd_terms",
            "license_name": "Swiss Open Government Data (OGD)",
            "spdx_license_id": "NONE_ASSIGNED_BY_SOURCE",
            "commercial_use_allowed": "true",
            "display_allowed": "true",
            "offline_cache_allowed": "true",
            "bulk_reuse_allowed": "true",
            "redistribution_allowed": "true",
            "attribution_required": "true",
            "attribution": ATTRIBUTION,
            "production_import": "false",
            "ru_eaeu_applicability": "false",
            "vin_fitment": "false",
            "repair_applicability": "false",
        }
        db.executemany("INSERT INTO pack_metadata(key,value) VALUES(?,?)", metadata.items())

        approval_index: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        approval_make_counts: dict[str, Counter[str]] = {}
        approval_expected = {
            "passenger_cars": ("Personenwagen", "passenger_cars"),
            "other_automobiles": ("restliche Automobilgruppen", "other_automobiles"),
        }
        for file_key, (sheet_name, count_key) in approval_expected.items():
            evidence = file_evidence[file_key]
            per_make: Counter[str] = Counter()
            expected_fields = REQUIRED_APPROVAL_FIELDS
            inserted = 0
            for row_number, header, row in _workbook_rows(
                input_dir / evidence["file_name"], sheet_name, int(expected_indexes[count_key])
            ):
                if not expected_fields.issubset(set(header)):
                    raise ValueError(f"Required approval columns missing from {file_key}")
                if not is_vag_make(row.get("makeName")):
                    continue
                approval = normalize_text(row.get("chTypeApprovalNumber"))
                make = normalize_text(row.get("makeName"))
                if not approval or not make:
                    raise ValueError(f"VAG approval row lacks approval number or make at {file_key}:{row_number}")
                selected = {column: row.get(column) for column in APPROVAL_COLUMNS}
                selected.update({
                    "gearboxEmissions1.chGearboxType": row.get("gearboxEmissions1.chGearboxType"),
                    "gearboxEmissions2.chGearboxType": row.get("gearboxEmissions2.chGearboxType"),
                    "gearboxEmissions3.chGearboxType": row.get("gearboxEmissions3.chGearboxType"),
                    "gearboxEmissions4.chGearboxType": row.get("gearboxEmissions4.chGearboxType"),
                })
                gearbox_classes = [
                    normalize_text(selected.get(f"gearboxEmissions{i}.chGearboxType"))
                    for i in range(1, 5)
                    if normalize_text(selected.get(f"gearboxEmissions{i}.chGearboxType"))
                ]
                row_hash = canonical_row_sha256(row)
                locator = f"{evidence['url']}#sheet={sheet_name}&row={row_number}"
                values = (
                    file_key, row_number, row_hash, locator, "CH", approval, make,
                    _value(row, "commercialName"), _value(row, "type"), _value(row, "variant"),
                    _value(row, "version"), _value(row, "versionNo"), _value(row, "VehicleType"),
                    _value(row, "vehicleCategoryCode"), _value(row, "chVehicleType"),
                    _value(row, "chVehicleSubType"), _value(row, "manufacturerOfTheEngine"),
                    _value(row, "engineType"), _value(row, "chEngineCodeAsMarkedOnTheEngine"),
                    _value(row, "chFuelType"), row.get("engineCapacity"),
                    _value(row, "maximumNetPower"), _value(row, "maximumTorque"),
                    _value(row, "numberOfCylinders"), _value(row, "stroke"),
                    _value(row, "driveType"),
                    json.dumps(gearbox_classes, ensure_ascii=False, separators=(",", ":")),
                    _value(row, "dateOfApproval"), _value(row, "dateOfLastChange"),
                    _value(row, "cancelationDate"), _value(row, "dateOfApprovalExpiry"),
                )
                cursor = db.execute(
                    """INSERT INTO type_approval_records(
                    source_file_key,source_row_number,source_row_sha256,source_record_locator,market_scope,
                    approval_number,make_name,commercial_name,type_designation,variant,version,version_no,
                    vehicle_type,vehicle_category_code,ch_vehicle_type,ch_vehicle_subtype,
                    manufacturer_of_engine,engine_type_designation,stamped_engine_marking,fuel_type,
                    engine_capacity_cc,maximum_net_power,maximum_torque,number_of_cylinders,stroke,drive_type,
                    approval_gearbox_classes_json,date_of_approval,date_of_last_change,cancellation_date,approval_expiry_date
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    values,
                )
                approval_row = {
                    "approval_row_id": int(cursor.lastrowid),
                    "variant": _value(row, "variant"),
                    "version": _value(row, "version"),
                    "gearbox_classes": gearbox_classes,
                    "engine_type_designation": _value(row, "engineType"),
                    "stamped_engine_marking": _value(row, "chEngineCodeAsMarkedOnTheEngine"),
                }
                approval_index[(approval, make.upper())].append(approval_row)
                per_make[make.upper()] += 1
                inserted += 1
            expected_counts = expected_make_counts[count_key]
            normalized_expected = {str(k).upper(): int(v) for k, v in expected_counts.items() if k != "total"}
            if dict(sorted(per_make.items())) != dict(sorted(normalized_expected.items())):
                raise ValueError(f"VAG approval counts changed for {file_key}: {dict(per_make)}")
            if inserted != int(expected_counts["total"]):
                raise ValueError(f"VAG approval total changed for {file_key}: {inserted}")
            counts["approval_rows"][file_key] = {"total": inserted, "by_make": dict(sorted(per_make.items()))}

        emission_evidence = file_evidence["emissions"]
        emission_counts: Counter[str] = Counter()
        scope_link_counts: Counter[str] = Counter()
        scope_link_counts_by_make: dict[str, Counter[str]] = defaultdict(Counter)
        emission_inserted = 0
        for row_number, header, row in _workbook_rows(
            input_dir / emission_evidence["file_name"], "Emissionsdaten", int(expected_indexes["emissions"])
        ):
            if not REQUIRED_EMISSIONS_FIELDS.issubset(set(header)):
                raise ValueError("Required ASTRA emissions/gearbox columns are missing")
            if not is_vag_make(row.get("makeName")):
                continue
            approval = normalize_text(row.get("chTypeApprovalNumber"))
            make = normalize_text(row.get("makeName"))
            if not approval or not make:
                raise ValueError(f"VAG emissions row lacks approval number or make at row {row_number}")
            linked_id, link_status = resolve_scope_link(
                approval_index, approval, make, row.get("versionDefined"),
                row.get("chGearboxType"),
            )
            if link_status == "linked_exact_approval_version":
                precision = "approval_version_exact"
                link_bucket = "exact"
            elif link_status == "linked_wildcard_approval_variant":
                precision = "approval_variant_wildcard"
                link_bucket = "wildcard"
            else:
                precision = "unlinked_scope"
                link_bucket = "unlinked"
            scope_link_counts[link_bucket] += 1
            scope_link_counts_by_make[make.upper()][link_bucket] += 1
            row_hash = canonical_row_sha256(row)
            locator = f"{emission_evidence['url']}#sheet=Emissionsdaten&row={row_number}"
            cursor = db.execute(
                """INSERT INTO emissions_gearbox_rows(
                source_file_key,source_row_number,source_row_sha256,source_record_locator,market_scope,
                approval_number,make_name,vehicle_type,commercial_name,total_gearbox_classes,gearbox_number,
                ch_gearbox_type,ch_mapping,version_defined,final_drive_ratio,fuel_consumption,co2_emission,
                fuel_consumption_wltp,co2_emission_wltp,emission_level,emission_level_short,
                linked_approval_row_id,scope_link_status,applicability_precision
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    "emissions", row_number, row_hash, locator, "CH", approval, make,
                    _value(row, "VehicleType"), _value(row, "commercialName"),
                    _value(row, "totalnumberchGearboxType"), _value(row, "gearboxNumber"),
                    _value(row, "chGearboxType"), _value(row, "chMapping"),
                    _value(row, "versionDefined"), _value(row, "chFinalDriveRatio"),
                    _value(row, "primaryFuelConsumption"), _value(row, "primaryEmissionCo2"),
                    _value(row, "primaryFuelConsumptionWltp"), _value(row, "primaryEmissionCo2Wltp"),
                    _value(row, "exhaustEmissionLevelCode"), _value(row, "exhaustEmissionLevelCodeShort"),
                    linked_id, link_status, precision,
                ),
            )
            if linked_id is not None:
                approval_row = next(
                    item for item in approval_index[(approval, make.upper())]
                    if int(item["approval_row_id"]) == linked_id
                )
                relation_precision = precision
                db.execute(
                    """INSERT INTO engine_gearbox_scope_links(
                    approval_row_id,gearbox_row_id,market_scope,engine_type_designation,
                    stamped_engine_marking,swiss_gearbox_type,version_scope,relation_precision
                    ) VALUES(?,?,?,?,?,?,?,?)""",
                    (
                        linked_id, int(cursor.lastrowid), "CH",
                        approval_row["engine_type_designation"], approval_row["stamped_engine_marking"],
                        _value(row, "chGearboxType"), normalize_text(row.get("versionDefined")),
                        relation_precision,
                    ),
                )
                counts["linked_scope_rows"] += 1
            else:
                counts["unlinked_scope_rows"] += 1
            emission_counts[make.upper()] += 1
            emission_inserted += 1

        expected_emissions = {str(k).upper(): int(v) for k, v in expected_emissions_counts.items() if k != "total"}
        if dict(sorted(emission_counts.items())) != dict(sorted(expected_emissions.items())):
            raise ValueError(f"VAG emissions/gearbox row counts changed: {dict(emission_counts)}")
        if emission_inserted != int(expected_emissions_counts["total"]):
            raise ValueError(f"VAG emissions/gearbox total changed: {emission_inserted}")
        counts["emissions_gearbox_rows"] = {"total": emission_inserted, "by_make": dict(sorted(emission_counts.items()))}

        expected_scope_links = snapshot.get("vag_emissions_scope_link_counts")
        if not isinstance(expected_scope_links, dict):
            raise ValueError("Pinned VAG emissions scope-link counts are missing from source manifest")
        actual_scope_links = {
            "exact": int(scope_link_counts.get("exact", 0)),
            "wildcard": int(scope_link_counts.get("wildcard", 0)),
            "unlinked": int(scope_link_counts.get("unlinked", 0)),
        }
        expected_scope_links_total = {
            key: int(expected_scope_links.get(key, -1))
            for key in ("exact", "wildcard", "unlinked")
        }
        if actual_scope_links != expected_scope_links_total:
            raise ValueError(
                f"VAG emissions scope-link counts changed: {actual_scope_links} != {expected_scope_links_total}"
            )
        actual_scope_links_by_make = {
            make_key: {
                key: int(scope_link_counts_by_make[make_key].get(key, 0))
                for key in ("exact", "wildcard", "unlinked")
            }
            for make_key in sorted(scope_link_counts_by_make)
        }
        expected_scope_links_by_make = expected_scope_links.get("by_make")
        if not isinstance(expected_scope_links_by_make, dict):
            raise ValueError("Pinned per-make VAG emissions scope-link counts are missing")
        normalized_expected_links_by_make = {
            str(make_key).upper(): {
                key: int(values.get(key, -1))
                for key in ("exact", "wildcard", "unlinked")
            }
            for make_key, values in expected_scope_links_by_make.items()
        }
        if actual_scope_links_by_make != normalized_expected_links_by_make:
            raise ValueError(
                f"Per-make VAG emissions scope-link counts changed: {actual_scope_links_by_make} != {normalized_expected_links_by_make}"
            )
        counts["scope_link_counts"] = actual_scope_links
        counts["scope_link_counts_by_make"] = actual_scope_links_by_make

        db.execute("COMMIT")
        integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
        foreign_key_errors = db.execute("PRAGMA foreign_key_check").fetchall()
        if integrity != "ok" or foreign_key_errors:
            raise ValueError(f"SQLite validation failed: integrity={integrity}, fk={foreign_key_errors[:5]}")
        forbidden = db.execute(
            """SELECT count(*) FROM engine_gearbox_scope_links
               WHERE market_scope<>'CH' OR factory_vag_engine_code_claim<>0
                 OR factory_vag_gearbox_code_claim<>0 OR production_fitment_claim<>0"""
        ).fetchone()[0]
        if forbidden:
            raise ValueError("ASTRA pack contains an invalid production/VAG factory-code claim")
        if db.execute("SELECT count(*) FROM type_approval_records WHERE market_scope<>'CH'").fetchone()[0]:
            raise ValueError("Non-CH type approval record found")
        if db.execute("SELECT count(*) FROM emissions_gearbox_rows WHERE market_scope<>'CH'").fetchone()[0]:
            raise ValueError("Non-CH gearbox/emissions record found")
        if db.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND lower(name) LIKE '%dtc%'").fetchone()[0]:
            raise ValueError("ASTRA homologation pack must not contain a DTC table")
        db.close()
        os.replace(temp_path, database_path)
    except Exception:
        try:
            db.close()
        except Exception:
            pass
        temp_path.unlink(missing_ok=True)
        raise

    database_hash = sha256_file(database_path)
    source_snapshot_payload = json.dumps(file_evidence, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    source_snapshot_sha256 = hashlib.sha256(source_snapshot_payload.encode("utf-8")).hexdigest()
    pack_manifest = {
        "schema_version": 2,
        "pack_id": "astra-ch-tas-vag-open-data",
        "status": "verified_research_only",
        "publisher": source_manifest["publisher"],
        "source_id": source_manifest["source_id"],
        "source_revision": source_revision,
        "source_snapshot_date": source_revision,
        "source_manifest_sha256": source_manifest_sha256,
        "source_snapshot_sha256": source_snapshot_sha256,
        "source_manifest_file": source_manifest_path.name,
        "market_scope": ["CH"],
        "rights": source_manifest["rights"],
        "attribution": ATTRIBUTION,
        "spdx_license_id": None,
        "source_files": file_evidence,
        "database": {
            "file_name": database_path.name,
            "size_bytes": database_path.stat().st_size,
            "sha256": database_hash,
            "integrity_check": "ok",
            "foreign_key_check": "ok",
        },
        "counts": counts,
        "applicability_boundaries": {
            "type_approval_only": True,
            "model_year_inferred": False,
            "generation_inferred": False,
            "vin_fitment": False,
            "individual_vehicle_fitment": False,
            "repair_procedure_applicability": False,
            "diagnostic_execution_allowed": False,
            "engine_type_is_factory_vag_engine_code": False,
            "stamped_engine_marking_is_factory_vag_engine_code": False,
            "ch_gearbox_type_is_vag_factory_gearbox_code": False,
            "engine_gearbox_links_are_ch_approval_scope_only": True,
            "wildcard_scope_is_exact_version_fitment": False,
            "ru_eaeu_applicability": False,
            "production_import": False,
        },
        "built_at_utc": timestamp,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(pack_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "ATTRIBUTION.md").write_text(
        "# Attribution\n\n" + ATTRIBUTION + "\n", encoding="utf-8"
    )
    (output_dir / "RIGHTS.md").write_text(
        "# Rights and use boundary\n\n"
        "This pack contains only the official FEDRO/ASTRA TAS Open Government Data products listed in the manifest. "
        "The reviewed FEDRO notice dated 2026-02-23 permits free OGD reuse, including commercial use, display, offline "
        "caching, bulk reuse and redistribution, with FEDRO attribution. No SPDX identifier is assigned by the source.\n\n"
        f"Required attribution: {ATTRIBUTION}\n\n"
        "Scope is Switzerland (CH) only. This pack is not Russian/EAEU OTTS data. It does not establish model year, "
        "generation, VIN-level fitment, VAG factory engine/gearbox codes, ECU, DTC, repair procedures, wiring diagrams, "
        "pinouts, torque values, adaptations or service intervals. Swiss gearbox classes remain Swiss approval "
        "classifications. Emissions rows are linked only when versionDefined exactly equals the approval's raw "
        "variant/version composite and the Swiss gearbox class is listed in that approval record. This remains an "
        "approval-scope association only, never a factory VAG engine/gearbox pair or production fitment. Wildcard "
        "'*' is not exact-version applicability.\n\n"
        "Excluded: paid datasets, holder/personal information, eDatenblatt portal output and PDF reproductions.\n",
        encoding="utf-8",
    )
    (output_dir / "README.md").write_text(
        "# ASTRA/FEDRO TAS — VAG Switzerland research pack\n\n"
        "Read-only CH homologation research data, separate from the production repair catalog. "
        "See manifest.json, RIGHTS.md and ATTRIBUTION.md. The database retains source-file SHA-256, "
        "source workbook row number and canonical row SHA-256.\n",
        encoding="utf-8",
    )
    report = {
        "status": "verified_research_only",
        "source_manifest_sha256": source_manifest_sha256,
        "source_snapshot_sha256": source_snapshot_sha256,
        "database_sha256": database_hash,
        "database_size_bytes": database_path.stat().st_size,
        "integrity_check": "ok",
        "foreign_key_check": "ok",
        "counts": counts,
        "source_files": file_evidence,
    }
    (output_dir / "build-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--source-manifest", type=Path,
        default=Path("data/source-manifests/astra-ch-tas-open-data.json"),
    )
    args = parser.parse_args()
    report = build_pack(args.input_dir, args.output_dir, args.source_manifest)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
