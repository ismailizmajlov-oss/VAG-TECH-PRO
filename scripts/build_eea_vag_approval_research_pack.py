#!/usr/bin/env python3
"""Build a rights-cleared, candidate-only EEA VAG type-approval variant SQLite pack."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import sqlite3
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SOURCE_ID = "eea-co2-passenger-cars-2019-2025"
PACK_ID = "eea-vag-type-approval-variants"
API_URL = "https://discodata.eea.europa.eu/sql"
LICENSE_ID = "CC-BY-4.0"
LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"
PUBLISHER = "European Environment Agency (EEA), Directorate-General for Climate Action (DG CLIMA)"
MARKET_SCOPE = "EU-27+IS+NO"
APPLICABILITY = "official_eea_type_approval_variant_aggregate_not_oem_powertrain_fitment"
PAGE_SIZE = 1000
MAX_ROWS_PER_TABLE = 250000
MAX_RESPONSE_BYTES = 25 * 1024 * 1024
MAX_PAGES = math.ceil(MAX_ROWS_PER_TABLE / PAGE_SIZE)
USER_AGENT = "VAG-TECH-PRO-EEA-Research-Pack/1.0 (rights-reviewed CC-BY-4.0 source; contact via repository)"

TABLES = [
    {
        "table_id": "2024F",
        "sql_name": "[CO2Emission].[latest].[co2cars_2024Fv30]",
        "year": 2024,
        "status": "F",
        "revision": "2024F_co2cars_2024Fv30_metadata_revised_2026-08-19",
        "metadata_url": "https://sdi.eea.europa.eu/catalogue/datahub/api/records/5018ec17-2348-4c92-8761-6f2377bbd1c0?language=eng",
    },
    {
        "table_id": "2025P",
        "sql_name": "[CO2Emission].[latest].[co2cars_2025Pv31]",
        "year": 2025,
        "status": "P",
        "revision": "2025P_co2cars_2025Pv31_metadata_revised_2026-08-19",
        "metadata_url": "https://sdi.eea.europa.eu/catalogue/datahub/api/records/b4044b06-2e6b-4f8e-a6e6-66e0e98bb0dd?language=eng",
    },
]

VAG_MAKES = {
    "VOLKSWAGEN": "VOLKSWAGEN",
    "AUDI": "AUDI",
    "SKODA": "SKODA",
    "SEAT": "SEAT",
    "CUPRA": "CUPRA",
}
REQUIRED_FIELDS = ("MS", "Year", "Status", "Mk", "Cn", "T", "Va", "Ve", "TAN")
FORBIDDEN_KEY_TOKENS = (
    "vin", "applicant", "owner", "holder", "address", "email", "phone",
    "contact", "licenseplate", "registrationplate", "personaldatum",
)

def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")

def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def normalize_key(value: Any) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFKD", str(value)).casefold() if ch.isalnum())

def normalize_make(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return " ".join("".join(ch if ch.isalnum() else " " for ch in text).upper().split())

def map_vag_make(value: Any) -> str | None:
    return VAG_MAKES.get(normalize_make(value))

def row_value(row: dict[str, Any], name: str) -> Any:
    wanted = normalize_key(name)
    for key, value in row.items():
        if normalize_key(key) == wanted:
            return value
    return None

def row_has_key(row: dict[str, Any], name: str) -> bool:
    wanted = normalize_key(name)
    return any(normalize_key(key) == wanted for key in row)

def reject_personal_fields(row: dict[str, Any]) -> None:
    for key in row:
        token = normalize_key(key)
        if any(forbidden in token for forbidden in FORBIDDEN_KEY_TOKENS):
            raise ValueError(f"EEA response contains an excluded personal/vehicle identifier field: {key}")

def validate_source_manifest(path: Path) -> tuple[dict[str, Any], bytes]:
    raw = path.read_bytes()
    manifest = json.loads(raw.decode("utf-8-sig"))
    source = next((item for item in manifest.get("sources", []) if item.get("source_id") == SOURCE_ID), None)
    if not source:
        raise ValueError("EEA source is absent from the authoritative VAG source register")
    rights = source.get("rights", {})
    if rights.get("data_license") != LICENSE_ID or rights.get("license_url") != LICENSE_URL:
        raise ValueError("EEA published licence identity mismatch")
    if rights.get("permission_status") != "approved_by_published_license_for_reuse_with_attribution":
        raise ValueError("EEA reuse rights are not approved by the published licence")
    for key in ("commercial_use_allowed", "third_party_display_allowed", "offline_cache_allowed", "bulk_reuse_allowed", "redistribution_allowed", "attribution_required"):
        if rights.get(key) is not True:
            raise ValueError(f"EEA rights gate is missing {key}=true")
    acquisition = source.get("acquisition", {})
    if acquisition.get("authentication_required") is not False or acquisition.get("paid_access_required") is not False:
        raise ValueError("EEA acquisition unexpectedly requires credentials or payment")
    if acquisition.get("research_pack_import_allowed") is not True or acquisition.get("product_import_allowed") is not False:
        raise ValueError("EEA source must remain research-only and excluded from product fitment import")
    if source.get("product_import_allowed") is not False or source.get("data_ingested") is not False:
        raise ValueError("EEA source register state changed; review before building")
    return source, raw

def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"

def make_filter_sql(raw_labels: list[str], table: dict[str, Any], query_kind: str) -> str:
    if not raw_labels:
        raise ValueError("No recognized VAG make labels were discovered")
    labels = ", ".join(sql_literal(label) for label in sorted(set(raw_labels)))
    base = f"FROM {table['sql_name']} WHERE [Year] = {int(table['year'])} AND [Status] = {sql_literal(table['status'])}"
    if query_kind == "count":
        return f"SELECT COUNT(*) AS [row_count] {base} AND [Mk] IN ({labels})"
    if query_kind == "rows":
        return f"SELECT * {base} AND [Mk] IN ({labels}) ORDER BY [MS], [Mk], [Cn], [T], [Va], [Ve], [TAN]"
    raise ValueError("Unknown query kind")

def api_request(sql: str, page: int = 1, page_size: int = PAGE_SIZE) -> tuple[bytes, dict[str, Any]]:
    query = urllib.parse.urlencode({"query": sql, "p": page, "nrOfHits": page_size})
    url = API_URL + "?" + query
    request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": USER_AGENT})
    last_error: Exception | None = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                final = urllib.parse.urlparse(response.geturl())
                if final.scheme != "https" or final.hostname != "discodata.eea.europa.eu":
                    raise ValueError("EEA API redirected outside the approved HTTPS host")
                raw = response.read(MAX_RESPONSE_BYTES + 1)
                if len(raw) > MAX_RESPONSE_BYTES:
                    raise ValueError("EEA API response exceeded the configured size limit")
                parsed = json.loads(raw.decode("utf-8-sig"))
                if isinstance(parsed, dict) and parsed.get("errors"):
                    raise ValueError("EEA SQL API error: " + json.dumps(parsed["errors"], ensure_ascii=False)[:1000])
                if not isinstance(parsed, dict) or not isinstance(parsed.get("results"), list):
                    raise ValueError("EEA SQL API response has no results array")
                return raw, parsed
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code not in (429, 500, 502, 503, 504) or attempt == 3:
                raise
        except (TimeoutError, urllib.error.URLError) as exc:
            last_error = exc
            if attempt == 3:
                raise
        time.sleep(2 ** attempt)
    raise RuntimeError(f"EEA API request failed: {last_error}")

def query_rows(sql: str) -> list[dict[str, Any]]:
    _, parsed = api_request(sql, page=1, page_size=1000)
    rows = parsed["results"]
    if not all(isinstance(row, dict) for row in rows):
        raise ValueError("EEA API returned a non-object row")
    return rows

def discover_make_labels(table: dict[str, Any]) -> tuple[list[str], list[str]]:
    sql = (
        f"SELECT DISTINCT [Mk] AS [make] FROM {table['sql_name']} "
        f"WHERE [Year] = {int(table['year'])} AND [Status] = {sql_literal(table['status'])} ORDER BY [Mk]"
    )
    rows = query_rows(sql)
    all_labels = sorted({str(row_value(row, "make")).strip() for row in rows if row_value(row, "make") is not None and str(row_value(row, "make")).strip()})
    recognized = [label for label in all_labels if map_vag_make(label)]
    return all_labels, recognized

def fetch_table_rows(table: dict[str, Any], raw_labels: list[str], out_dir: Path) -> dict[str, Any]:
    count_sql = make_filter_sql(raw_labels, table, "count")
    count_rows = query_rows(count_sql)
    if len(count_rows) != 1:
        raise ValueError("EEA count query did not return exactly one row")
    total = row_value(count_rows[0], "row_count")
    if total is None:
        total = next(iter(count_rows[0].values()), None)
    total_count = int(total)
    if total_count <= 0:
        return {"table": table, "rows": [], "pages": [], "query": count_sql, "total_rows": 0}
    if total_count > MAX_ROWS_PER_TABLE:
        raise ValueError(f"{table['table_id']} contains {total_count} VAG rows; exceeds safe cap {MAX_ROWS_PER_TABLE}")
    sql = make_filter_sql(raw_labels, table, "rows")
    query_hash = sha256_bytes(sql.encode("utf-8"))
    pages_dir = out_dir / "raw" / table["table_id"]
    pages_dir.mkdir(parents=True, exist_ok=False)
    expected_pages = math.ceil(total_count / PAGE_SIZE)
    if expected_pages > MAX_PAGES:
        raise ValueError("EEA page count exceeds safety cap")
    all_rows: list[dict[str, Any]] = []
    page_records: list[dict[str, Any]] = []
    for page in range(1, expected_pages + 1):
        raw, parsed = api_request(sql, page=page, page_size=PAGE_SIZE)
        rows = parsed["results"]
        if not all(isinstance(row, dict) for row in rows):
            raise ValueError("EEA API returned a non-object row")
        if not rows:
            raise ValueError(f"EEA page {page} is unexpectedly empty")
        for row in rows:
            reject_personal_fields(row)
            for field in REQUIRED_FIELDS:
                if not row_has_key(row, field):
                    raise ValueError(f"EEA row is missing required field {field}")
            if int(row_value(row, "Year")) != int(table["year"]) or str(row_value(row, "Status")).upper() != table["status"]:
                raise ValueError("EEA row year/status does not match the pinned table")
            if not map_vag_make(row_value(row, "Mk")):
                raise ValueError("EEA filtered query returned an unrecognized manufacturer label")
        filename = f"page-{page:04d}.json"
        path = pages_dir / filename
        path.write_bytes(raw)
        page_records.append({
            "table_id": table["table_id"],
            "page": page,
            "file": str(path.relative_to(out_dir)).replace("\\", "/"),
            "sha256": sha256_bytes(raw),
            "query_sha256": query_hash,
            "row_count": len(rows),
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        })
        all_rows.extend(rows)
    if len(all_rows) != total_count:
        raise ValueError(f"EEA row count mismatch: expected {total_count}, received {len(all_rows)}")
    return {"table": table, "rows": all_rows, "pages": page_records, "query": sql, "query_sha256": query_hash, "total_rows": total_count}

def build_database(
    db_path: Path,
    source: dict[str, Any],
    source_manifest_sha: str,
    table_results: list[dict[str, Any]],
    make_labels: dict[str, list[str]],
    snapshot_sha: str,
    retrieved_at: str,
) -> dict[str, Any]:
    db = sqlite3.connect(db_path)
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("PRAGMA journal_mode=DELETE")
    db.executescript("""
    CREATE TABLE source_registry(
      source_id TEXT PRIMARY KEY,
      publisher TEXT NOT NULL,
      source_url TEXT NOT NULL,
      license_id TEXT NOT NULL CHECK(license_id='CC-BY-4.0'),
      license_url TEXT NOT NULL,
      source_revision TEXT NOT NULL,
      market_scope TEXT NOT NULL CHECK(market_scope='EU-27+IS+NO'),
      attribution_text TEXT NOT NULL,
      permission_status TEXT NOT NULL CHECK(permission_status='approved_by_published_license_for_reuse_with_attribution'),
      commercial_use_allowed INTEGER NOT NULL CHECK(commercial_use_allowed=1),
      display_allowed INTEGER NOT NULL CHECK(display_allowed=1),
      offline_cache_allowed INTEGER NOT NULL CHECK(offline_cache_allowed=1),
      bulk_reuse_allowed INTEGER NOT NULL CHECK(bulk_reuse_allowed=1),
      redistribution_allowed INTEGER NOT NULL CHECK(redistribution_allowed=1),
      attribution_required INTEGER NOT NULL CHECK(attribution_required=1),
      source_manifest_sha256 TEXT NOT NULL CHECK(length(source_manifest_sha256)=64),
      filtered_snapshot_sha256 TEXT NOT NULL CHECK(length(filtered_snapshot_sha256)=64),
      product_import_allowed INTEGER NOT NULL CHECK(product_import_allowed=0),
      exact_vehicle_fitment INTEGER NOT NULL CHECK(exact_vehicle_fitment=0),
      exact_factory_engine_code INTEGER NOT NULL CHECK(exact_factory_engine_code=0),
      exact_factory_gearbox_code INTEGER NOT NULL CHECK(exact_factory_gearbox_code=0),
      engine_gearbox_pairing INTEGER NOT NULL CHECK(engine_gearbox_pairing=0),
      ecu_dtc_fitment INTEGER NOT NULL CHECK(ecu_dtc_fitment=0),
      repair_applicability INTEGER NOT NULL CHECK(repair_applicability=0),
      model_generation_verified INTEGER NOT NULL CHECK(model_generation_verified=0),
      applicability_precision TEXT NOT NULL CHECK(applicability_precision='official_eea_type_approval_variant_aggregate_not_oem_powertrain_fitment'),
      retrieved_at_utc TEXT NOT NULL
    ) STRICT;
    CREATE TABLE source_tables(
      table_id TEXT PRIMARY KEY,
      sql_table TEXT NOT NULL,
      source_revision TEXT NOT NULL,
      registration_year INTEGER NOT NULL,
      data_status TEXT NOT NULL CHECK(data_status IN ('F','P')),
      row_count INTEGER NOT NULL CHECK(row_count>=0),
      query_sha256 TEXT NOT NULL CHECK(length(query_sha256)=64)
    ) STRICT;
    CREATE TABLE source_pages(
      table_id TEXT NOT NULL REFERENCES source_tables(table_id),
      page_number INTEGER NOT NULL,
      relative_file TEXT NOT NULL,
      response_sha256 TEXT NOT NULL CHECK(length(response_sha256)=64),
      query_sha256 TEXT NOT NULL CHECK(length(query_sha256)=64),
      row_count INTEGER NOT NULL CHECK(row_count>0),
      retrieved_at_utc TEXT NOT NULL,
      PRIMARY KEY(table_id,page_number)
    ) STRICT;
    CREATE TABLE make_labels(
      raw_make_label TEXT PRIMARY KEY,
      normalized_make_label TEXT NOT NULL,
      brand_key TEXT,
      mapping_status TEXT NOT NULL CHECK(mapping_status IN ('exact_core_vag_make_label','not_in_core_vag_scope'))
    ) STRICT;
    CREATE TABLE approval_variants(
      id INTEGER PRIMARY KEY,
      table_id TEXT NOT NULL REFERENCES source_tables(table_id),
      source_revision TEXT NOT NULL,
      source_page INTEGER NOT NULL,
      source_row_in_page INTEGER NOT NULL,
      registration_year INTEGER NOT NULL,
      data_status TEXT NOT NULL CHECK(data_status IN ('F','P')),
      reporting_member_state_raw TEXT,
      make_raw TEXT NOT NULL,
      brand_key TEXT NOT NULL CHECK(brand_key IN ('VOLKSWAGEN','AUDI','SKODA','SEAT','CUPRA')),
      commercial_name_raw TEXT,
      type_raw TEXT,
      variant_raw TEXT,
      version_raw TEXT,
      type_approval_number_raw TEXT,
      fuel_type_raw TEXT,
      fuel_mode_raw TEXT,
      engine_capacity_cc_raw TEXT,
      engine_power_kw_raw TEXT,
      mass_kg_raw TEXT,
      wheelbase_mm_raw TEXT,
      track_width_mm_raw TEXT,
      co2_wltp_g_km_raw TEXT,
      raw_json TEXT NOT NULL,
      source_record_sha256 TEXT NOT NULL CHECK(length(source_record_sha256)=64),
      market_scope TEXT NOT NULL CHECK(market_scope='EU-27+IS+NO'),
      model_year INTEGER,
      engine_code TEXT,
      gearbox_code TEXT,
      exact_vehicle_fitment INTEGER NOT NULL CHECK(exact_vehicle_fitment=0),
      engine_gearbox_pairing INTEGER NOT NULL CHECK(engine_gearbox_pairing=0),
      ecu_dtc_fitment INTEGER NOT NULL CHECK(ecu_dtc_fitment=0),
      repair_applicability INTEGER NOT NULL CHECK(repair_applicability=0),
      review_status TEXT NOT NULL CHECK(review_status='candidate_only'),
      applicability_precision TEXT NOT NULL CHECK(applicability_precision='official_eea_type_approval_variant_aggregate_not_oem_powertrain_fitment'),
      UNIQUE(table_id,source_page,source_row_in_page)
    ) STRICT;
    CREATE INDEX idx_eea_brand_year ON approval_variants(brand_key,registration_year,data_status);
    CREATE INDEX idx_eea_approval_variant ON approval_variants(type_approval_number_raw,variant_raw,version_raw);
    """)
    attribution = (
        "European Environment Agency (EEA), Directorate-General for Climate Action (DG-CLIMA), "
        "Monitoring of CO2 emissions from passenger cars, 2024 Final and 2025 Provisional; "
        "CC BY 4.0. Retrieved 2026-11-10. Modified by filtering to exact core VAG make labels, "
        "normalizing selected fields, and adding provenance/applicability metadata. No EEA endorsement implied."
    )
    revision = ";".join(result["table"]["revision"] for result in table_results)
    rights = source["rights"]
    try:
        with db:
            db.execute(
                """INSERT INTO source_registry VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    SOURCE_ID, PUBLISHER, source["source_url"], LICENSE_ID, LICENSE_URL, revision, MARKET_SCOPE,
                    attribution, rights["permission_status"], 1, 1, 1, 1, 1, 1, source_manifest_sha, snapshot_sha,
                    0, 0, 0, 0, 0, 0, 0, 0, APPLICABILITY, retrieved_at,
                ),
            )
            for raw_label in sorted({label for labels in make_labels.values() for label in labels}):
                brand = map_vag_make(raw_label)
                db.execute(
                    "INSERT INTO make_labels VALUES(?,?,?,?)",
                    (raw_label, normalize_make(raw_label), brand, "exact_core_vag_make_label" if brand else "not_in_core_vag_scope"),
                )
            for result in table_results:
                table = result["table"]
                db.execute(
                    "INSERT INTO source_tables VALUES(?,?,?,?,?,?,?)",
                    (
                        table["table_id"], table["sql_name"], table["revision"], table["year"], table["status"],
                        result["total_rows"], result["query_sha256"],
                    ),
                )
                for page in result["pages"]:
                    db.execute(
                        "INSERT INTO source_pages VALUES(?,?,?,?,?,?,?)",
                        (
                            page["table_id"], page["page"], page["file"], page["sha256"],
                            page["query_sha256"], page["row_count"], page["retrieved_at_utc"],
                        ),
                    )
                page_number = 0
                row_in_page = 0
                for page in result["pages"]:
                    page_number = page["page"]
                    page_path = db_path.parent / page["file"]
                    page_json = json.loads(page_path.read_text(encoding="utf-8"))
                    page_rows = page_json["results"]
                    for row_in_page, raw_row in enumerate(page_rows, start=1):
                        make_raw = str(row_value(raw_row, "Mk")).strip()
                        brand = map_vag_make(make_raw)
                        if not brand:
                            raise ValueError("Unrecognized make reached database writer")
                        db.execute(
                            """INSERT INTO approval_variants(
                              table_id,source_revision,source_page,source_row_in_page,registration_year,data_status,
                              reporting_member_state_raw,make_raw,brand_key,commercial_name_raw,type_raw,variant_raw,
                              version_raw,type_approval_number_raw,fuel_type_raw,fuel_mode_raw,engine_capacity_cc_raw,
                              engine_power_kw_raw,mass_kg_raw,wheelbase_mm_raw,track_width_mm_raw,co2_wltp_g_km_raw,
                              raw_json,source_record_sha256,market_scope,model_year,engine_code,gearbox_code,
                              exact_vehicle_fitment,engine_gearbox_pairing,ecu_dtc_fitment,repair_applicability,
                              review_status,applicability_precision
                            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                            (
                                table["table_id"], table["revision"], page_number, row_in_page, table["year"], table["status"],
                                str(row_value(raw_row, "MS")) if row_value(raw_row, "MS") is not None else None,
                                make_raw, brand,
                                str(row_value(raw_row, "Cn")) if row_value(raw_row, "Cn") is not None else None,
                                str(row_value(raw_row, "T")) if row_value(raw_row, "T") is not None else None,
                                str(row_value(raw_row, "Va")) if row_value(raw_row, "Va") is not None else None,
                                str(row_value(raw_row, "Ve")) if row_value(raw_row, "Ve") is not None else None,
                                str(row_value(raw_row, "TAN")) if row_value(raw_row, "TAN") is not None else None,
                                str(row_value(raw_row, "Ft")) if row_value(raw_row, "Ft") is not None else None,
                                str(row_value(raw_row, "Fm")) if row_value(raw_row, "Fm") is not None else None,
                                str(row_value(raw_row, "Ec")) if row_value(raw_row, "Ec") is not None else None,
                                str(row_value(raw_row, "Ep")) if row_value(raw_row, "Ep") is not None else None,
                                str(row_value(raw_row, "M")) if row_value(raw_row, "M") is not None else None,
                                str(row_value(raw_row, "W")) if row_value(raw_row, "W") is not None else None,
                                str(row_value(raw_row, "At1")) if row_value(raw_row, "At1") is not None else None,
                                str(row_value(raw_row, "Ewltp")) if row_value(raw_row, "Ewltp") is not None else None,
                                canonical_json(raw_row).decode("utf-8"), sha256_bytes(canonical_json(raw_row)), MARKET_SCOPE,
                                None, None, None, 0, 0, 0, 0, "candidate_only", APPLICABILITY,
                            ),
                        )
        integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
        fk_errors = db.execute("PRAGMA foreign_key_check").fetchall()
        if integrity != "ok" or fk_errors:
            raise ValueError(f"SQLite validation failed: integrity={integrity}; foreign_key_errors={len(fk_errors)}")
        counts = {
            "total_rows": db.execute("SELECT COUNT(*) FROM approval_variants").fetchone()[0],
            "by_brand": dict(db.execute("SELECT brand_key,COUNT(*) FROM approval_variants GROUP BY brand_key ORDER BY brand_key").fetchall()),
            "by_year_status": [
                {"registration_year": row[0], "data_status": row[1], "count": row[2]}
                for row in db.execute("SELECT registration_year,data_status,COUNT(*) FROM approval_variants GROUP BY registration_year,data_status ORDER BY registration_year,data_status")
            ],
        }
        return counts
    finally:
        db.close()

def build_pack(source_manifest: Path, out_dir: Path) -> dict[str, Any]:
    if out_dir.exists():
        raise FileExistsError(f"Refusing to overwrite existing output directory: {out_dir}")
    out_dir.mkdir(parents=True)
    source, source_raw = validate_source_manifest(source_manifest)
    source_manifest_sha = sha256_bytes(source_raw)
    retrieved_at = datetime.now(timezone.utc).isoformat()
    table_results: list[dict[str, Any]] = []
    make_labels: dict[str, list[str]] = {}
    for table in TABLES:
        all_labels, recognized = discover_make_labels(table)
        make_labels[table["table_id"]] = all_labels
        if not recognized:
            table_results.append({
                "table": table, "rows": [], "pages": [], "query": "", "query_sha256": sha256_bytes(b""),
                "total_rows": 0, "recognized_labels": [],
            })
            continue
        result = fetch_table_rows(table, recognized, out_dir)
        result["recognized_labels"] = recognized
        table_results.append(result)
    if not any(result["total_rows"] for result in table_results):
        raise ValueError("No exact core VAG make labels were found in the EEA source tables")
    if not any(page for result in table_results for page in result["pages"]):
        raise ValueError("No source response pages were captured")
    page_hashes = [
        {"table_id": page["table_id"], "page": page["page"], "sha256": page["sha256"], "query_sha256": page["query_sha256"]}
        for result in table_results for page in result["pages"]
    ]
    snapshot_payload = {
        "source_id": SOURCE_ID,
        "tables": [{"table_id": r["table"]["table_id"], "revision": r["table"]["revision"], "query_sha256": r["query_sha256"], "rows": r["total_rows"]} for r in table_results],
        "pages": page_hashes,
    }
    snapshot_sha = sha256_bytes(canonical_json(snapshot_payload))
    db_path = out_dir / "eea-vag-type-approval-variants.sqlite"
    counts = build_database(db_path, source, source_manifest_sha, table_results, make_labels, snapshot_sha, retrieved_at)
    raw_files = []
    for result in table_results:
        for page in result["pages"]:
            path = out_dir / page["file"]
            raw_files.append({"file": page["file"], "sha256": sha256_file(path), "size_bytes": path.stat().st_size})
    manifest = {
        "schema_version": 1,
        "pack_id": PACK_ID,
        "source_id": SOURCE_ID,
        "publisher": PUBLISHER,
        "license": {"id": LICENSE_ID, "url": LICENSE_URL, "commercial_use_allowed": True, "offline_cache_allowed": True, "redistribution_allowed": True, "attribution_required": True},
        "attribution": "European Environment Agency (EEA), Directorate-General for Climate Action (DG-CLIMA), Monitoring of CO2 emissions from passenger cars, 2024 Final and 2025 Provisional, CC BY 4.0. Retrieved 2026-11-10. Modified: filtered to exact core VAG make labels and normalized into a separate research SQLite. No EEA endorsement implied.",
        "market_scope": ["EU-27", "IS", "NO"],
        "source_manifest_sha256": source_manifest_sha,
        "filtered_snapshot_sha256": snapshot_sha,
        "database_sha256": sha256_file(db_path),
        "database_file": db_path.name,
        "retrieved_at_utc": retrieved_at,
        "source_tables": [
            {
                "table_id": r["table"]["table_id"], "sql_name": r["table"]["sql_name"],
                "source_revision": r["table"]["revision"], "registration_year": r["table"]["year"],
                "data_status": r["table"]["status"], "rows": r["total_rows"],
                "recognized_raw_make_labels": r.get("recognized_labels", []),
                "all_raw_make_label_count": len(make_labels[r["table"]["table_id"]]),
                "query_sha256": r["query_sha256"],
            } for r in table_results
        ],
        "make_labels": {key: value for key, value in make_labels.items()},
        "counts": counts,
        "raw_response_files": raw_files,
        "applicability": {
            "precision": APPLICABILITY,
            "exact_vehicle_fitment": False,
            "exact_factory_engine_code": False,
            "exact_factory_gearbox_code": False,
            "engine_gearbox_pairing": False,
            "model_generation_verified": False,
            "ecu_dtc_fitment": False,
            "repair_applicability": False,
            "registration_year_is_model_year": False,
            "product_import_allowed": False,
            "research_pack_only": True,
        },
        "limitations": [
            "EEA records describe newly registered M1 passenger cars in EU-27, Iceland and Norway; they do not cover RU/EAEU market scope.",
            "Registration year is not model year or production boundary.",
            "Type approval number, type, variant and version are source identifiers, not exact individual-vehicle fitment.",
            "Engine capacity and power are technical attributes, not factory VAG engine codes.",
            "No factory gearbox code or engine/gearbox pairing is asserted.",
            "No ECU, DTC, wiring, pinout, torque, adaptation, service interval or repair procedure applicability is supplied.",
            "2024 rows are final (F); 2025 rows are provisional (P) and must remain visibly distinct.",
            "The dataset is a research reference only and must not be promoted into the production vehicle-fitment catalog."
        ],
    }
    (out_dir / "pack-manifest.json").write_bytes(canonical_json(manifest) + b"\n")
    (out_dir / "README.md").write_text(
        "# EEA VAG type-approval variant research pack\n\n"
        "This is a separate, read-only research dataset built from EEA passenger-car registration/type-approval variant records. "
        "It is not a VAG factory repair catalogue and is not a Russian/EAEU OTTS dataset.\n\n"
        f"**Licence:** [CC BY 4.0]({LICENSE_URL}). **Attribution:** {manifest['attribution']}\n\n"
        "Only exact core VAG make labels (Volkswagen, Audi, Škoda, SEAT, CUPRA) discovered in the source are included. "
        "Raw labels, source revisions, query hashes, raw response page hashes, row hashes and SQLite SHA-256 are retained.\n\n"
        "Registration year is not model year. EEA type/variant/version and engine capacity/power do not establish a factory engine code, "
        "gearbox code, exact engine/gearbox pairing, ECU, DTC or repair applicability. All rows remain candidate_only; product import is disabled.\n",
        encoding="utf-8",
    )
    (out_dir / "LICENSE-ATTRIBUTION.txt").write_text(
        "Dataset licence: Creative Commons Attribution 4.0 International (CC BY 4.0)\n"
        f"Licence URL: {LICENSE_URL}\n"
        f"Attribution: {manifest['attribution']}\n"
        "No endorsement by the European Environment Agency is implied.\n",
        encoding="utf-8",
    )
    sums = [f"{manifest['database_sha256']}  {db_path.name}"]
    sums.extend(f"{item['sha256']}  {item['file']}" for item in raw_files)
    (out_dir / "SHA256SUMS.txt").write_text("\n".join(sums) + "\n", encoding="utf-8")
    verify_pack(out_dir)
    return manifest

def verify_pack(out_dir: Path) -> dict[str, Any]:
    manifest_path = out_dir / "pack-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("pack_id") != PACK_ID or manifest.get("source_id") != SOURCE_ID:
        raise ValueError("EEA research pack identity mismatch")
    if manifest.get("license", {}).get("id") != LICENSE_ID or manifest.get("applicability", {}).get("product_import_allowed") is not False:
        raise ValueError("EEA research pack rights/applicability gate failed")
    db_path = out_dir / manifest["database_file"]
    if sha256_file(db_path) != manifest["database_sha256"]:
        raise ValueError("EEA SQLite SHA-256 mismatch")
    for item in manifest["raw_response_files"]:
        path = out_dir / item["file"]
        if not path.is_file() or sha256_file(path) != item["sha256"]:
            raise ValueError(f"EEA raw page SHA-256 mismatch: {item['file']}")
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    try:
        if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("EEA SQLite integrity_check failed")
        if db.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("EEA SQLite foreign_key_check failed")
        registry = db.execute("SELECT * FROM source_registry").fetchone()
        if not registry or registry["product_import_allowed"] != 0 or registry["exact_vehicle_fitment"] != 0:
            raise ValueError("EEA source registry was promoted beyond research-only")
        rows = db.execute("SELECT * FROM approval_variants ORDER BY id").fetchall()
        if len(rows) != manifest["counts"]["total_rows"]:
            raise ValueError("EEA SQLite row count does not match pack manifest")
        brand_counts: dict[str, int] = {}
        year_status: dict[tuple[int, str], int] = {}
        for row in rows:
            raw = json.loads(row["raw_json"])
            reject_personal_fields(raw)
            if sha256_bytes(canonical_json(raw)) != row["source_record_sha256"]:
                raise ValueError(f"EEA row hash mismatch at id={row['id']}")
            if row["model_year"] is not None or row["engine_code"] is not None or row["gearbox_code"] is not None:
                raise ValueError("EEA candidate contains inferred model year or factory powertrain code")
            for field in ("exact_vehicle_fitment", "engine_gearbox_pairing", "ecu_dtc_fitment", "repair_applicability"):
                if row[field] != 0:
                    raise ValueError(f"EEA candidate unexpectedly enables {field}")
            if row["review_status"] != "candidate_only" or row["applicability_precision"] != APPLICABILITY:
                raise ValueError("EEA candidate review/applicability precision mismatch")
            brand_counts[row["brand_key"]] = brand_counts.get(row["brand_key"], 0) + 1
            key = (row["registration_year"], row["data_status"])
            year_status[key] = year_status.get(key, 0) + 1
        if brand_counts != manifest["counts"]["by_brand"]:
            raise ValueError("EEA brand counts mismatch")
        expected_year_status = [
            {"registration_year": year, "data_status": status, "count": count}
            for (year, status), count in sorted(year_status.items())
        ]
        if expected_year_status != manifest["counts"]["by_year_status"]:
            raise ValueError("EEA year/status counts mismatch")
        return {"ok": True, "rows": len(rows), "database_sha256": manifest["database_sha256"], "filtered_snapshot_sha256": manifest["filtered_snapshot_sha256"]}
    finally:
        db.close()

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-manifest", type=Path, default=Path("data/source-manifests/vag-factory-source-register.json"))
    parser.add_argument("--out", type=Path, default=Path("eea-vag-approval-pack"))
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify:
        print(json.dumps(verify_pack(args.out), ensure_ascii=False, indent=2))
    else:
        manifest = build_pack(args.source_manifest, args.out)
        print(json.dumps({"ok": True, "pack_id": PACK_ID, "counts": manifest["counts"], "database_sha256": manifest["database_sha256"], "filtered_snapshot_sha256": manifest["filtered_snapshot_sha256"]}, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
