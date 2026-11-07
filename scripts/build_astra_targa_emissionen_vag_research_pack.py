#!/usr/bin/env python3
"""Build a separate CH-only ASTRA TARGA per-gearbox approval-variant research pack."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sqlite3
import unicodedata
import urllib.request
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

SOURCE_ID = "astra-fedro-targa-emissionen-approval-variants-ch"
PACK_ID = "astra-fedro-targa-emissionen-vag-research"
SOURCE_URL = (
    "https://opendata.astra.admin.ch/ivzod/2000-Typengenehmigungen_TG_TARGA/"
    "2200-Basisdaten_TG_ab_1995/emissionen.txt"
)
DATA_DESCRIPTION_URL = (
    "https://www.astra.admin.ch/dam/de/sd-web/7fPLSFMqD6JR/informationsprodukte_typengenehmigungsdaten.pdf"
)
ASTRA_OPEN_DATA_URL = "https://www.astra.admin.ch/de/news-homologation"
ASTRA_VEHICLE_DATA_URL = "https://www.astra.admin.ch/de/fahrzeugdaten"
OGD_POLICY_URL = "https://www.bk.admin.ch/en/open-government-data-ogd-2"
OGD_TERMS_URL = "https://opendata.swiss/en/terms-of-use"
EMBAG_URL = "https://www.fedlex.admin.ch/eli/cc/2023/682/en"
EXPECTED_SIZE = 70_829_020
EXPECTED_LAST_MODIFIED = "Thu, 30 Jul 2026 09:22:59 GMT"
EXPECTED_ETAG = '"438c3dc-657d09e3d7852"'
EXPECTED_COLUMNS = 65
VAG_MAKES = {
    "VW", "VOLKSWAGEN", "AUDI", "SEAT", "SKODA", "ŠKODA",
    "CUPRA", "PORSCHE", "BENTLEY", "LAMBORGHINI", "BUGATTI",
}
REQUIRED_HEADERS = {
    "approval_number": ("tgcode", "typengenehmigungsnummer"),
    "make": ("marke",),
    "type": ("typ",),
    "gearbox": ("getriebe",),
    "final_drive_ratio": ("iachse",),
    "engine_make": ("motormarke",),
    "engine_type": ("motortyp",),
    "engine_construction": ("bauart",),
    "fuel": ("treibstoff",),
    "displacement_cc": ("hubraum",),
    "power_kw": ("leistung",),
    "power_rpm": ("leistungbeinmin",),
    "torque_nm": ("drehmoment",),
    "torque_rpm": ("drehmomentbeinmin",),
    "emission_control": ("abgasreinigung",),
    "drive": ("antrieb",),
    "emissions_code": ("emissionscode",),
    "homologation_date": ("homologationsdatum",),
}
ATTRIBUTION = (
    "Source: Federal Roads Office (FEDRO / ASTRA), TARGA emissions data "
    "(emissionen.txt), third-generation type-approval data, source revision "
    "2026-07-30; " + SOURCE_URL + ". Swiss Open Government Data (OGD). "
    "VAG-only research extraction; source field values are retained as raw "
    "approval classifications and are not promoted to OEM VAG codes."
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_row_sha256(row: list[str]) -> str:
    raw = json.dumps(row, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return sha256_bytes(raw)


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value or "").casefold()
    value = value.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    return "".join(char for char in value if char.isalnum())


def normalize_make(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value or "").strip().upper().split())


def is_vag_make(value: str) -> bool:
    return normalize_make(value) in VAG_MAKES


def resolve_header_positions(header: list[str]) -> dict[str, int]:
    if len(header) != EXPECTED_COLUMNS:
        raise ValueError(f"ASTRA emissionen schema changed: expected {EXPECTED_COLUMNS} columns, got {len(header)}")
    normalized = [normalize_text(value) for value in header]
    positions = {}
    for key, aliases in REQUIRED_HEADERS.items():
        matches = [index for index, value in enumerate(normalized) if value in aliases]
        if not matches:
            raise ValueError(f"Required ASTRA emissionen field {key!r} not found in header")
        positions[key] = matches[0]
    return positions


def download_source(destination: Path) -> dict:
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        SOURCE_URL,
        headers={
            "Accept-Encoding": "identity",
            "User-Agent": "VAG-TECH-PRO-ASTRA-TARGA-emissionen-research-pack/1.0",
        },
        method="GET",
    )
    digest = hashlib.sha256()
    total = 0
    with urllib.request.urlopen(request, timeout=180) as response:
        metadata = {
            "status": response.status,
            "content_length": response.headers.get("Content-Length"),
            "last_modified": response.headers.get("Last-Modified"),
            "etag": response.headers.get("ETag"),
            "content_type": response.headers.get("Content-Type"),
        }
        if response.status != 200:
            raise ValueError(f"ASTRA emissionen GET returned HTTP {response.status}, expected 200")
        if metadata["last_modified"] != EXPECTED_LAST_MODIFIED or metadata["etag"] != EXPECTED_ETAG:
            raise ValueError("ASTRA emissionen source revision changed since bounded probe; re-review before ingest")
        if metadata["content_length"] and int(metadata["content_length"]) != EXPECTED_SIZE:
            raise ValueError(f"ASTRA emissionen Content-Length changed: expected {EXPECTED_SIZE}, got {metadata['content_length']}")
        with destination.open("wb") as output:
            while True:
                chunk = response.read(8 * 1024 * 1024)
                if not chunk:
                    break
                output.write(chunk)
                digest.update(chunk)
                total += len(chunk)
            output.flush()
            os.fsync(output.fileno())
    if total != EXPECTED_SIZE or destination.stat().st_size != EXPECTED_SIZE:
        raise ValueError(f"ASTRA emissionen size mismatch: expected {EXPECTED_SIZE}, got {total}")
    return {
        "source_url": SOURCE_URL,
        "source_revision": EXPECTED_LAST_MODIFIED,
        "etag": EXPECTED_ETAG,
        "file_size_bytes": total,
        "file_sha256": digest.hexdigest(),
        "download_mode": "single_streaming_http_get",
        "content_type": metadata["content_type"],
    }


def create_schema(db: sqlite3.Connection) -> None:
    db.executescript("""
      PRAGMA foreign_keys=ON;
      CREATE TABLE pack_metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL) WITHOUT ROWID;
      CREATE TABLE source_files(
        source_id TEXT PRIMARY KEY,source_url TEXT NOT NULL,source_revision TEXT NOT NULL,
        etag TEXT NOT NULL,file_size_bytes INTEGER NOT NULL CHECK(file_size_bytes>0),
        file_sha256 TEXT NOT NULL CHECK(length(file_sha256)=64),
        market_scope TEXT NOT NULL CHECK(market_scope='CH'),rights_status TEXT NOT NULL,
        attribution_required INTEGER NOT NULL CHECK(attribution_required=1)
      ) WITHOUT ROWID;
      CREATE TABLE approval_powertrain_variant_rows(
        id INTEGER PRIMARY KEY,
        source_row_number INTEGER NOT NULL UNIQUE,
        source_row_sha256 TEXT NOT NULL CHECK(length(source_row_sha256)=64),
        source_record_locator TEXT NOT NULL,
        source_file_sha256 TEXT NOT NULL CHECK(length(source_file_sha256)=64),
        market_scope TEXT NOT NULL CHECK(market_scope='CH'),
        approval_number_raw TEXT NOT NULL,
        make_raw TEXT NOT NULL,
        make_normalized TEXT NOT NULL,
        type_raw TEXT,
        gearbox_classification_raw TEXT,
        final_drive_ratio_raw TEXT,
        engine_make_raw TEXT,
        engine_type_raw TEXT,
        engine_construction_raw TEXT,
        fuel_raw TEXT,
        displacement_cc_raw TEXT,
        power_kw_raw TEXT,
        power_rpm_raw TEXT,
        torque_nm_raw TEXT,
        torque_rpm_raw TEXT,
        emission_control_raw TEXT,
        drive_raw TEXT,
        emissions_code_raw TEXT,
        homologation_date_raw TEXT,
        applicability_precision TEXT NOT NULL CHECK(applicability_precision='CH_type_approval_gearbox_variant_row'),
        source_defined_variant_link INTEGER NOT NULL CHECK(source_defined_variant_link=1),
        exact_vag_factory_code_pair INTEGER NOT NULL CHECK(exact_vag_factory_code_pair=0),
        exact_vehicle_fitment INTEGER NOT NULL CHECK(exact_vehicle_fitment=0),
        ru_eaeu_applicability INTEGER NOT NULL CHECK(ru_eaeu_applicability=0),
        model_year_inferred INTEGER NOT NULL CHECK(model_year_inferred=0),
        generation_inferred INTEGER NOT NULL CHECK(generation_inferred=0),
        engine_type_status TEXT NOT NULL CHECK(engine_type_status='raw_approval_engine_type_candidate'),
        gearbox_status TEXT NOT NULL CHECK(gearbox_status='raw_approval_classification_not_vag_gearbox_code')
      );
      CREATE INDEX idx_targa_emissionen_make_type ON approval_powertrain_variant_rows(make_normalized,type_raw);
      CREATE INDEX idx_targa_emissionen_approval ON approval_powertrain_variant_rows(approval_number_raw);
      CREATE INDEX idx_targa_emissionen_engine ON approval_powertrain_variant_rows(engine_type_raw);
      CREATE INDEX idx_targa_emissionen_gearbox ON approval_powertrain_variant_rows(gearbox_classification_raw);
    """)


def build_database(source_path: Path, database_path: Path, source_meta: dict) -> dict:
    if database_path.exists():
        database_path.unlink()
    db = sqlite3.connect(database_path)
    db.execute("PRAGMA journal_mode=DELETE")
    db.execute("PRAGMA synchronous=FULL")
    db.execute("PRAGMA foreign_keys=ON")
    create_schema(db)
    positions = None
    header = None
    source_rows = 0
    malformed_rows = 0
    selected_rows = 0
    make_counts = Counter()
    engine_type_counts = Counter()
    gearbox_counts = Counter()
    batch = []
    db.execute("BEGIN IMMEDIATE")
    try:
        with source_path.open("r", encoding="cp1252", newline="") as handle:
            reader = csv.reader(handle, delimiter="\t", quotechar='"')
            header = next(reader, None)
            if header is None:
                raise ValueError("ASTRA emissionen source is empty")
            positions = resolve_header_positions(header)
            for source_row_number, row in enumerate(reader, start=2):
                if not row or not any(value.strip() for value in row):
                    continue
                source_rows += 1
                if len(row) != len(header):
                    malformed_rows += 1
                    continue
                make_raw = row[positions["make"]]
                if not is_vag_make(make_raw):
                    continue
                approval = row[positions["approval_number"]].strip()
                if not approval:
                    malformed_rows += 1
                    continue
                make_normalized = normalize_make(make_raw)
                row_hash = canonical_row_sha256(row)
                selected_rows += 1
                make_counts[make_normalized] += 1
                engine_type = row[positions["engine_type"]]
                gearbox = row[positions["gearbox"]]
                if engine_type.strip():
                    engine_type_counts[engine_type.strip()] += 1
                if gearbox.strip():
                    gearbox_counts[gearbox.strip()] += 1
                batch.append((
                    source_row_number,row_hash,
                    f"emissionen.txt#row={source_row_number};TG-Code={approval}",
                    source_meta["file_sha256"],"CH",approval,make_raw,make_normalized,
                    row[positions["type"]],gearbox,row[positions["final_drive_ratio"]],
                    row[positions["engine_make"]],engine_type,row[positions["engine_construction"]],
                    row[positions["fuel"]],row[positions["displacement_cc"]],row[positions["power_kw"]],
                    row[positions.get("power_rpm", positions["power_kw"])],
                    row[positions["torque_nm"]],row[positions.get("torque_rpm", positions["torque_nm"])],
                    row[positions["emission_control"]],row[positions["drive"]],
                    row[positions["emissions_code"]],row[positions["homologation_date"]],
                    "CH_type_approval_gearbox_variant_row",1,0,0,0,0,0,
                    "raw_approval_engine_type_candidate",
                    "raw_approval_classification_not_vag_gearbox_code"
                ))
                if len(batch) >= 500:
                    db.executemany("""
                      INSERT INTO approval_powertrain_variant_rows(
                        source_row_number,source_row_sha256,source_record_locator,source_file_sha256,
                        market_scope,approval_number_raw,make_raw,make_normalized,type_raw,
                        gearbox_classification_raw,final_drive_ratio_raw,engine_make_raw,engine_type_raw,
                        engine_construction_raw,fuel_raw,displacement_cc_raw,power_kw_raw,power_rpm_raw,
                        torque_nm_raw,torque_rpm_raw,emission_control_raw,drive_raw,emissions_code_raw,
                        homologation_date_raw,applicability_precision,source_defined_variant_link,
                        exact_vag_factory_code_pair,exact_vehicle_fitment,ru_eaeu_applicability,
                        model_year_inferred,generation_inferred,engine_type_status,gearbox_status
                      ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,batch)
                    batch=[]
        if batch:
            db.executemany("""
              INSERT INTO approval_powertrain_variant_rows(
                source_row_number,source_row_sha256,source_record_locator,source_file_sha256,
                market_scope,approval_number_raw,make_raw,make_normalized,type_raw,
                gearbox_classification_raw,final_drive_ratio_raw,engine_make_raw,engine_type_raw,
                engine_construction_raw,fuel_raw,displacement_cc_raw,power_kw_raw,power_rpm_raw,
                torque_nm_raw,torque_rpm_raw,emission_control_raw,drive_raw,emissions_code_raw,
                homologation_date_raw,applicability_precision,source_defined_variant_link,
                exact_vag_factory_code_pair,exact_vehicle_fitment,ru_eaeu_applicability,
                model_year_inferred,generation_inferred,engine_type_status,gearbox_status
              ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,batch)
        db.commit()
        rights_status = "approved_by_published_ogd_terms"
        metadata = {
            "pack_id": PACK_ID,
            "source_id": SOURCE_ID,
            "source_revision": source_meta["source_revision"],
            "source_file_sha256": source_meta["file_sha256"],
            "market_scope": "CH",
            "rights_status": rights_status,
            "attribution_required": "true",
            "source_defined_variant_link": "true",
            "exact_vag_factory_code_pair": "false",
            "exact_vehicle_fitment": "false",
            "ru_eaeu_applicability": "false",
            "model_year_inferred": "false",
            "generation_inferred": "false",
            "source_row_hash_method": "SHA-256 of canonical JSON array of all original parsed TSV field strings",
        }
        db.executemany("INSERT INTO pack_metadata(key,value) VALUES(?,?)", metadata.items())
        db.execute("INSERT INTO source_files VALUES(?,?,?,?,?,?,?,?,?)", (
            SOURCE_ID, SOURCE_URL, source_meta["source_revision"], source_meta["etag"],
            source_meta["file_size_bytes"], source_meta["file_sha256"], "CH",
            rights_status, 1
        ))
        db.commit()
    except Exception:
        db.rollback()
        db.close()
        raise
    integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
    fk = db.execute("PRAGMA foreign_key_check").fetchall()
    table_names = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    count = db.execute("SELECT count(*) FROM approval_powertrain_variant_rows").fetchone()[0]
    false_claims = db.execute("""
      SELECT count(*) FROM approval_powertrain_variant_rows
      WHERE exact_vag_factory_code_pair<>0 OR exact_vehicle_fitment<>0
         OR ru_eaeu_applicability<>0 OR model_year_inferred<>0 OR generation_inferred<>0
    """).fetchone()[0]
    db.close()
    if malformed_rows:
        raise ValueError(f"ASTRA emissionen contains {malformed_rows} malformed rows; refusing partial pack")
    if integrity != "ok" or fk:
        raise ValueError("ASTRA emissionen SQLite integrity or foreign-key check failed")
    if any("pair" in name.casefold() for name in table_names):
        raise ValueError("ASTRA emissionen pack must not create a factory pair table")
    if false_claims or not count:
        raise ValueError("ASTRA emissionen applicability/code boundary check failed or no VAG rows found")
    return {
        "counts": {
            "approval_powertrain_variant_rows": count,
            "source_defined_variant_link_rows": count,
            "exact_vag_factory_code_pair_rows": 0,
            "exact_vehicle_fitment_rows": 0,
            "ru_eaeu_applicability_rows": 0,
        },
        "make_counts": dict(sorted(make_counts.items())),
        "engine_type_top_100": engine_type_counts.most_common(100),
        "gearbox_classification_top_100": gearbox_counts.most_common(100),
        "source_rows_scanned": source_rows,
        "selected_vag_rows": selected_rows,
        "malformed_rows": malformed_rows,
        "header_column_count": len(header or []),
        "field_positions_zero_based": positions,
        "sqlite_integrity_check": integrity,
        "foreign_key_violations": len(fk),
        "tables": sorted(table_names),
    }


def build_pack(output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    source_path = output_dir / "emissionen.txt"
    database_path = output_dir / "astra-targa-emissionen-vag.sqlite"
    source_meta = download_source(source_path)
    built_at = datetime.now(timezone.utc).isoformat()
    report = build_database(source_path,database_path,source_meta)
    database_sha = sha256_bytes(database_path.read_bytes())
    source_manifest = {
        "schema_version":1,"source_id":SOURCE_ID,
        "publisher":"Federal Roads Office (FEDRO / ASTRA), Swiss Confederation",
        "source_kind":"official_open_government_per_gearbox_type_approval_data",
        "market_scope":["CH"],"source_url":SOURCE_URL,
        "data_description_url":DATA_DESCRIPTION_URL,
        "source_revision":source_meta["source_revision"],"etag":source_meta["etag"],
        "snapshot":{
            "downloaded_at_utc":built_at,"downloaded":True,
            "file_size_bytes":source_meta["file_size_bytes"],
            "file_sha256":source_meta["file_sha256"],
            "format":"tab-delimited TXT; cp1252; 65 columns",
            "source_generation":"third_generation_type_approvals_after_1995",
        },
        "rights":{
            "data_license_status":"Swiss Open Government Data (OGD); no separate CC identifier assigned in the reviewed ASTRA publication",
            "rights_status":"approved_by_published_ogd_terms",
            "commercial_use_allowed":True,"display_allowed":True,
            "offline_cache_allowed":True,"bulk_reuse_allowed":True,
            "redistribution_allowed":True,"attribution_required":True,
            "attribution":ATTRIBUTION,
            "evidence_urls":[ASTRA_OPEN_DATA_URL,ASTRA_VEHICLE_DATA_URL,OGD_POLICY_URL,OGD_TERMS_URL,EMBAG_URL],
            "evidence":"ASTRA identifies the TARGA type-approval information products as freely available OGD. The official ASTRA vehicle-data page distinguishes the free factual type-approval data from paid holder/location and registration-plate mapping products. Swiss OGD policy permits reuse subject to source disclosure. Only the free factual emissions/type-approval file is included.",
            "excluded_products":["paid holder/location data","registration-plate mappings","eDatenblatt portal output","non-public type-approval documents"],
        },
        "coverage":{
            "source_generation":"third_generation_after_1995",
            "vehicle_group":"motor vehicles; source documentation says one row is emitted for each gearbox variant",
            "make_filter":"exact normalized make values only; no fuzzy matching",
            "vag_make_counts":report["make_counts"],
        },
        "field_status":{
            "approval_number_make_type":"raw official CH type-approval fields",
            "gearbox":"raw ASTRA approval gearbox classification, not a confirmed VAG gearbox code",
            "engine_make_type":"raw ASTRA approval engine fields, not independently confirmed VAG factory engine codes",
            "source_defined_variant_link":"one source row per gearbox variant; preserves the source-defined approval type/gearbox row",
            "exact_vag_factory_code_pair":"not established",
            "model_year_generation":"not inferred",
            "ecu_dtc_repair_content":"not provided",
        },
        "applicability_policy":{
            "market_scope":"CH only",
            "applicability_precision":"CH_type_approval_gearbox_variant_row",
            "source_defined_variant_link":True,
            "exact_vag_factory_code_pair":False,
            "individual_vehicle_fitment":False,
            "production_fitment":False,
            "ru_eaeu_applicability":False,
            "model_year_inferred":False,
            "generation_inferred":False,
            "repair_procedure_applicability":False,
            "diagnostic_execution_allowed":False,
        },
        "import_policy":{
            "research_pack_allowed":True,
            "data_ingested_to_research_pack":True,
            "product_import_allowed":False,
            "production_import":False,
            "ru_eaeu_applicability":False,
            "exact_vag_factory_code_pair":False,
        },
    }
    source_manifest_path=output_dir/"source-manifest.json"
    source_manifest_path.write_text(json.dumps(source_manifest,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    attribution_path=output_dir/"ATTRIBUTION.txt"
    attribution_path.write_text(ATTRIBUTION+"\n",encoding="utf-8")
    field_map_path=output_dir/"field-map.json"
    field_map_path.write_text(json.dumps({"required_headers":REQUIRED_HEADERS,"resolved_positions":report["field_positions_zero_based"]},ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    pack_manifest={
        "schema_version":1,"pack_id":PACK_ID,"source_id":SOURCE_ID,
        "status":"verified_research_only","market_scope":["CH"],
        "rights_status":"approved_by_published_ogd_terms",
        "source_revision":source_meta["source_revision"],
        "source_file":{"name":"emissionen.txt",**source_meta},
        "database":{"name":database_path.name,"sha256":database_sha,"size_bytes":database_path.stat().st_size},
        "source_manifest":{"name":source_manifest_path.name,"sha256":sha256_bytes(source_manifest_path.read_bytes())},
        "attribution":{"name":attribution_path.name,"sha256":sha256_bytes(attribution_path.read_bytes())},
        "field_map":{"name":field_map_path.name,"sha256":sha256_bytes(field_map_path.read_bytes())},
        "counts":report["counts"],"make_counts":report["make_counts"],
        "engine_type_top_100":report["engine_type_top_100"],
        "gearbox_classification_top_100":report["gearbox_classification_top_100"],
        "source_rows_scanned":report["source_rows_scanned"],
        "selected_vag_rows":report["selected_vag_rows"],
        "header_column_count":report["header_column_count"],
        "field_positions_zero_based":report["field_positions_zero_based"],
        "sqlite_integrity_check":report["sqlite_integrity_check"],
        "foreign_key_violations":report["foreign_key_violations"],
        "tables":report["tables"],
        "boundary":{
            "source_defined_variant_link":True,
            "exact_vag_factory_code_pair":False,
            "exact_vehicle_fitment":False,
            "production_fitment":False,
            "ru_eaeu_applicability":False,
            "model_year_inferred":False,
            "generation_inferred":False,
            "dtc_content":False,
            "repair_content":False,
        },
    }
    pack_manifest_path=output_dir/"pack-manifest.json"
    pack_manifest_path.write_text(json.dumps(pack_manifest,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    build_report_path=output_dir/"build-report.json"
    build_report_path.write_text(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    archive_path=output_dir/"astra-targa-emissionen-vag-research-pack.zip"
    with zipfile.ZipFile(archive_path,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for file_path in [database_path,source_manifest_path,attribution_path,field_map_path,pack_manifest_path,build_report_path]:
            archive.write(file_path,arcname=file_path.name)
    final={
        "pack_id":PACK_ID,"source_id":SOURCE_ID,
        "source_file_sha256":source_meta["file_sha256"],
        "database_sha256":database_sha,
        "archive_sha256":sha256_bytes(archive_path.read_bytes()),
        "archive_size_bytes":archive_path.stat().st_size,
        "counts":report["counts"],"make_counts":report["make_counts"],
        "sqlite_integrity_check":report["sqlite_integrity_check"],
        "foreign_key_violations":report["foreign_key_violations"],
        "source_defined_variant_link":True,"exact_vag_factory_code_pair":False,
        "ru_eaeu_applicability":False,
    }
    (output_dir/"final-verification.json").write_text(json.dumps(final,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    source_path.unlink()
    return final


def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--output-dir",default="artifacts/astra-targa-emissionen")
    args=parser.parse_args()
    result=build_pack(Path(args.output_dir))
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
