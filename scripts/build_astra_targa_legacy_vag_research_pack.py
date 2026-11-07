#!/usr/bin/env python3
"""Build a CH-only, rights-cleared ASTRA TARGA legacy VAG research pack.

This is deliberately not a production fitment importer. Raw engine markings
and gearbox classifications remain separate candidates; no pair table exists.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sqlite3
import time
import unicodedata
import urllib.request
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

SOURCE_ID = "astra-fedro-targa-legacy-type-approvals-ch"
PACK_ID = "astra-fedro-targa-legacy-vag-research"
SOURCE_URL = (
    "https://opendata.astra.admin.ch/ivzod/2000-Typengenehmigungen_TG_TARGA/"
    "2200-Basisdaten_TG_ab_1995/TG-Automobil.txt"
)
DATA_DESCRIPTION_URL = (
    "https://opendata.astra.admin.ch/ivzod/2000-Typengenehmigungen_TG_TARGA/"
    "2200-Basisdaten_TG_ab_1995/2220-Datenbeschreibung/Basisdaten_TG_ab_1995.pdf"
)
ASTRA_OPEN_DATA_URL = "https://www.astra.admin.ch/de/news-homologation"
OGD_TERMS_URL = "https://opendata.swiss/en/terms-of-use"
OGD_FAQ_URL = "https://opendata.swiss/en/faq"
OGD_POLICY_URL = "https://www.bk.admin.ch/en/open-government-data-ogd-2"
EMBAG_URL = "https://www.fedlex.admin.ch/eli/cc/2023/682/en"
EXPECTED_SIZE = 322_893_637
EXPECTED_LAST_MODIFIED = "Thu, 30 Jul 2026 09:22:48 GMT"
EXPECTED_ETAG = '"133ef745-657d09d960472"'
CHUNK_SIZE = 2 * 1024 * 1024

FIELDS = {
    "approval_number": 0,
    "approval_date": 1,
    "valid_import_until": 2,
    "extension_date": 3,
    "extension_positions": 4,
    "vehicle_group": 6,
    "vehicle_class": 9,
    "make": 10,
    "type": 11,
    "variant_version": 12,
    "eu_whole_vehicle_approval": 17,
    "gearbox_1": 26,
    "gearbox_1_ratio": 27,
    "gearbox_1_assignment": 28,
    "gearbox_2": 29,
    "gearbox_2_ratio": 30,
    "gearbox_2_assignment": 31,
    "gearbox_3": 32,
    "gearbox_3_ratio": 33,
    "gearbox_3_assignment": 34,
    "gearbox_4": 35,
    "gearbox_4_ratio": 36,
    "gearbox_4_assignment": 37,
    "engine_make": 59,
    "engine_type": 60,
    "engine_construction": 61,
    "fuel": 62,
    "displacement_cc": 63,
    "power_kw": 64,
    "power_rpm": 65,
    "max_torque_nm": 66,
    "max_torque_rpm": 67,
    "engine_marking": 75,
    "engine_marking_location": 76,
}
HEADER_CHECKS = {
    0: ("typengenehmigungsnummer",),
    1: ("typengenehmigung", "erteilt"),
    6: ("fahrzeugart",),
    9: ("fahrzeugklasse",),
    10: ("marke",),
    11: ("typ",),
    12: ("variante",),
    17: ("gesamtgenehmigung",),
    26: ("getriebe", "1"),
    59: ("motor", "marke"),
    60: ("motor", "typ"),
    75: ("motorkennzeichen",),
}
VAG_MAKES = {
    "VW", "VOLKSWAGEN", "AUDI", "SEAT", "SKODA", "ŠKODA",
    "CUPRA", "PORSCHE", "BENTLEY", "LAMBORGHINI", "BUGATTI",
}
ATTRIBUTION = (
    "Source: Federal Roads Office (FEDRO / ASTRA), Type approval data "
    "(TARGA), third-generation automobile records (TG-Automobil.txt), "
    "source revision 2026-07-30; "
    + SOURCE_URL
    + ". Swiss Open Government Data (OGD). VAG-only research extraction; "
      "source rows and field values are unchanged where retained."
)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_row_sha256(row: list[str]) -> str:
    raw = json.dumps(row, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return sha256_bytes(raw)


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value or "").casefold()
    return " ".join(value.replace("ä", "ae").replace("ö", "oe")
                    .replace("ü", "ue").replace("ß", "ss").split())


def normalize_make(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value or "").strip().upper().split())


def is_vag_make(value: str) -> bool:
    return normalize_make(value) in VAG_MAKES


def validate_header(header: list[str]) -> None:
    if len(header) != 223:
        raise ValueError(f"ASTRA TARGA schema column count changed: expected 223, got {len(header)}")
    for index, tokens in HEADER_CHECKS.items():
        observed = normalize_text(header[index])
        if not all(token in observed for token in tokens):
            raise ValueError(
                f"ASTRA TARGA header mismatch at zero-based column {index}: "
                f"expected tokens {tokens}, observed {header[index]!r}"
            )


def download_pinned_source(destination: Path) -> dict:
    """Stream the complete pinned public file once; never buffer it in memory."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        SOURCE_URL,
        headers={
            "Accept-Encoding": "identity",
            "User-Agent": "VAG-TECH-PRO-ASTRA-TARGA-research-pack/1.0",
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
            raise ValueError(f"ASTRA full-file GET returned HTTP {response.status}, expected 200")
        if metadata["last_modified"] != EXPECTED_LAST_MODIFIED or metadata["etag"] != EXPECTED_ETAG:
            raise ValueError("ASTRA source revision changed since the bounded schema probe; re-review before ingest")
        if metadata["content_length"] and int(metadata["content_length"]) != EXPECTED_SIZE:
            raise ValueError(f"ASTRA Content-Length changed: expected {EXPECTED_SIZE}, got {metadata['content_length']}")
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
        raise ValueError(f"ASTRA source size mismatch: expected {EXPECTED_SIZE}, got {total}")
    return {
        "source_url": SOURCE_URL,
        "source_revision": EXPECTED_LAST_MODIFIED,
        "etag": EXPECTED_ETAG,
        "file_size_bytes": total,
        "file_sha256": digest.hexdigest(),
        "download_mode": "single_streaming_http_get",
        "last_modified": EXPECTED_LAST_MODIFIED,
        "content_type": metadata["content_type"],
    }


def create_schema(db: sqlite3.Connection) -> None:
    db.executescript("""
      PRAGMA foreign_keys=ON;
      CREATE TABLE pack_metadata(
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
      ) WITHOUT ROWID;
      CREATE TABLE source_files(
        source_id TEXT PRIMARY KEY,
        source_url TEXT NOT NULL,
        source_revision TEXT NOT NULL,
        etag TEXT NOT NULL,
        file_size_bytes INTEGER NOT NULL CHECK(file_size_bytes>0),
        file_sha256 TEXT NOT NULL CHECK(length(file_sha256)=64),
        market_scope TEXT NOT NULL CHECK(market_scope='CH'),
        rights_status TEXT NOT NULL,
        attribution_required INTEGER NOT NULL CHECK(attribution_required=1)
      ) WITHOUT ROWID;
      CREATE TABLE type_approval_records(
        id INTEGER PRIMARY KEY,
        source_row_number INTEGER NOT NULL UNIQUE,
        source_row_sha256 TEXT NOT NULL CHECK(length(source_row_sha256)=64),
        source_record_locator TEXT NOT NULL,
        source_file_sha256 TEXT NOT NULL CHECK(length(source_file_sha256)=64),
        market_scope TEXT NOT NULL CHECK(market_scope='CH'),
        approval_number_raw TEXT NOT NULL,
        approval_date_raw TEXT,
        valid_import_until_raw TEXT,
        extension_date_raw TEXT,
        extension_positions_raw TEXT,
        vehicle_group_raw TEXT,
        vehicle_class_raw TEXT,
        make_raw TEXT NOT NULL,
        make_normalized TEXT NOT NULL,
        type_raw TEXT,
        variant_version_raw TEXT,
        eu_whole_vehicle_approval_raw TEXT,
        engine_make_raw TEXT,
        engine_type_raw TEXT,
        engine_construction_raw TEXT,
        fuel_raw TEXT,
        displacement_cc_raw TEXT,
        power_kw_raw TEXT,
        power_rpm_raw TEXT,
        max_torque_nm_raw TEXT,
        max_torque_rpm_raw TEXT,
        engine_marking_raw TEXT,
        engine_marking_location_raw TEXT,
        applicability_precision TEXT NOT NULL CHECK(applicability_precision='CH_type_approval_record'),
        technical_identity_status TEXT NOT NULL CHECK(technical_identity_status='candidate'),
        exact_vehicle_fitment_claim INTEGER NOT NULL DEFAULT 0 CHECK(exact_vehicle_fitment_claim=0),
        exact_engine_gearbox_pair_claim INTEGER NOT NULL DEFAULT 0 CHECK(exact_engine_gearbox_pair_claim=0),
        ru_eaeu_applicability_claim INTEGER NOT NULL DEFAULT 0 CHECK(ru_eaeu_applicability_claim=0)
      );
      CREATE TABLE engine_marking_candidates(
        id INTEGER PRIMARY KEY,
        approval_record_id INTEGER NOT NULL REFERENCES type_approval_records(id) ON DELETE CASCADE,
        source_row_sha256 TEXT NOT NULL CHECK(length(source_row_sha256)=64),
        engine_make_raw TEXT,
        engine_type_raw TEXT,
        engine_marking_raw TEXT,
        engine_marking_location_raw TEXT,
        candidate_status TEXT NOT NULL CHECK(candidate_status='unverified_source_engine_marking'),
        market_scope TEXT NOT NULL CHECK(market_scope='CH')
      );
      CREATE TABLE gearbox_classifications(
        id INTEGER PRIMARY KEY,
        approval_record_id INTEGER NOT NULL REFERENCES type_approval_records(id) ON DELETE CASCADE,
        source_row_sha256 TEXT NOT NULL CHECK(length(source_row_sha256)=64),
        slot_number INTEGER NOT NULL CHECK(slot_number BETWEEN 1 AND 4),
        gearbox_value_raw TEXT NOT NULL,
        final_drive_ratio_raw TEXT,
        assignment_raw TEXT,
        classification_status TEXT NOT NULL CHECK(classification_status='raw_approval_classification_not_vag_gearbox_code'),
        market_scope TEXT NOT NULL CHECK(market_scope='CH'),
        UNIQUE(approval_record_id,slot_number)
      );
      CREATE INDEX idx_targa_make_type ON type_approval_records(make_normalized,type_raw);
      CREATE INDEX idx_targa_approval_number ON type_approval_records(approval_number_raw);
      CREATE INDEX idx_targa_engine_marking ON engine_marking_candidates(engine_marking_raw);
      CREATE INDEX idx_targa_gearbox_value ON gearbox_classifications(gearbox_value_raw);
    """)


def _value(row: list[str], key: str) -> str:
    return row[FIELDS[key]] if FIELDS[key] < len(row) else ""


def build_database(source_path: Path, database_path: Path, source_meta: dict) -> dict:
    if database_path.exists():
        database_path.unlink()
    db = sqlite3.connect(database_path)
    db.execute("PRAGMA journal_mode=DELETE")
    db.execute("PRAGMA synchronous=FULL")
    db.execute("PRAGMA foreign_keys=ON")
    create_schema(db)
    counts_by_make: Counter[str] = Counter()
    engine_markings: Counter[str] = Counter()
    gearbox_values: Counter[str] = Counter()
    vehicle_classes: Counter[str] = Counter()
    malformed_rows = 0
    selected_rows = 0
    source_rows = 0
    engine_candidate_rows = 0
    gearbox_classification_rows = 0
    batch_records = []
    batch_engines = []
    batch_gearboxes = []

    db.execute("BEGIN IMMEDIATE")
    try:
        with source_path.open("r", encoding="cp1252", newline="") as handle:
            reader = csv.reader(handle, delimiter="\t", quotechar='"')
            header = next(reader, None)
            if header is None:
                raise ValueError("ASTRA TARGA source file is empty")
            validate_header(header)
            for source_row_number, row in enumerate(reader, start=2):
                if not row or not any(value.strip() for value in row):
                    continue
                source_rows += 1
                if len(row) != len(header):
                    malformed_rows += 1
                    continue
                make_raw = _value(row, "make")
                if not is_vag_make(make_raw):
                    continue
                approval_number = _value(row, "approval_number").strip()
                if not approval_number:
                    malformed_rows += 1
                    continue
                row_hash = canonical_row_sha256(row)
                make_norm = normalize_make(make_raw)
                selected_rows += 1
                counts_by_make[make_norm] += 1
                vehicle_classes[_value(row, "vehicle_class").strip()] += 1
                engine_marking = _value(row, "engine_marking")
                gearbox_fields = []
                for slot in range(1, 5):
                    raw = _value(row, f"gearbox_{slot}")
                    ratio = _value(row, f"gearbox_{slot}_ratio")
                    assignment = _value(row, f"gearbox_{slot}_assignment")
                    gearbox_fields.append((raw, ratio, assignment))
                    if raw.strip():
                        gearbox_values[raw.strip()] += 1
                if engine_marking.strip() or _value(row, "engine_type").strip():
                    engine_candidate_rows += 1
                    if engine_marking.strip():
                        engine_markings[engine_marking.strip()] += 1

                batch_records.append((
                    source_row_number, row_hash,
                    f"TG-Automobil.txt#row={source_row_number};approval={approval_number}",
                    source_meta["file_sha256"], "CH", approval_number,
                    _value(row, "approval_date"), _value(row, "valid_import_until"),
                    _value(row, "extension_date"), _value(row, "extension_positions"),
                    _value(row, "vehicle_group"), _value(row, "vehicle_class"),
                    make_raw, make_norm, _value(row, "type"), _value(row, "variant_version"),
                    _value(row, "eu_whole_vehicle_approval"), _value(row, "engine_make"),
                    _value(row, "engine_type"), _value(row, "engine_construction"),
                    _value(row, "fuel"), _value(row, "displacement_cc"), _value(row, "power_kw"),
                    _value(row, "power_rpm"), _value(row, "max_torque_nm"), _value(row, "max_torque_rpm"),
                    engine_marking, _value(row, "engine_marking_location"),
                    "CH_type_approval_record", "candidate", 0, 0, 0
                ))
                if len(batch_records) >= 500:
                    db.executemany("""
                      INSERT INTO type_approval_records(
                        source_row_number,source_row_sha256,source_record_locator,source_file_sha256,
                        market_scope,approval_number_raw,approval_date_raw,valid_import_until_raw,
                        extension_date_raw,extension_positions_raw,vehicle_group_raw,vehicle_class_raw,
                        make_raw,make_normalized,type_raw,variant_version_raw,eu_whole_vehicle_approval_raw,
                        engine_make_raw,engine_type_raw,engine_construction_raw,fuel_raw,displacement_cc_raw,
                        power_kw_raw,power_rpm_raw,max_torque_nm_raw,max_torque_rpm_raw,engine_marking_raw,
                        engine_marking_location_raw,applicability_precision,technical_identity_status,
                        exact_vehicle_fitment_claim,exact_engine_gearbox_pair_claim,ru_eaeu_applicability_claim
                      ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """, batch_records)
                    batch_records = []
        # Flush the final partial batch; otherwise trailing VAG rows under 500
        # would be silently omitted from the research database.
        if batch_records:
            db.executemany("""
              INSERT INTO type_approval_records(
                source_row_number,source_row_sha256,source_record_locator,source_file_sha256,
                market_scope,approval_number_raw,approval_date_raw,valid_import_until_raw,
                extension_date_raw,extension_positions_raw,vehicle_group_raw,vehicle_class_raw,
                make_raw,make_normalized,type_raw,variant_version_raw,eu_whole_vehicle_approval_raw,
                engine_make_raw,engine_type_raw,engine_construction_raw,fuel_raw,displacement_cc_raw,
                power_kw_raw,power_rpm_raw,max_torque_nm_raw,max_torque_rpm_raw,engine_marking_raw,
                engine_marking_location_raw,applicability_precision,technical_identity_status,
                exact_vehicle_fitment_claim,exact_engine_gearbox_pair_claim,ru_eaeu_applicability_claim
              ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, batch_records)
        db.commit()
    except Exception:
        db.rollback()
        db.close()
        raise
    db.close()
    if malformed_rows:
        raise ValueError(f"ASTRA TARGA source contains {malformed_rows} malformed VAG or non-VAG rows; refusing partial pack")

    # A second read-only pass inserts component candidates using stable source row hashes.
    db = sqlite3.connect(database_path)
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("BEGIN IMMEDIATE")
    try:
        row_index = {
            row[0]: row[1]
            for row in db.execute("SELECT source_row_number,id FROM type_approval_records")
        }
        with source_path.open("r", encoding="cp1252", newline="") as handle:
            reader = csv.reader(handle, delimiter="\t", quotechar='"')
            header = next(reader)
            validate_header(header)
            for source_row_number, row in enumerate(reader, start=2):
                if not row or not any(value.strip() for value in row) or len(row) != len(header):
                    continue
                if not is_vag_make(_value(row, "make")):
                    continue
                record_id = row_index.get(source_row_number)
                if record_id is None:
                    continue
                row_hash = canonical_row_sha256(row)
                engine_type = _value(row, "engine_type")
                engine_marking = _value(row, "engine_marking")
                if engine_type.strip() or engine_marking.strip():
                    db.execute("""
                      INSERT INTO engine_marking_candidates(
                        approval_record_id,source_row_sha256,engine_make_raw,engine_type_raw,
                        engine_marking_raw,engine_marking_location_raw,candidate_status,market_scope
                      ) VALUES(?,?,?,?,?,?,?,?)
                    """, (
                        record_id,row_hash,_value(row,"engine_make"),engine_type,engine_marking,
                        _value(row,"engine_marking_location"),"unverified_source_engine_marking","CH"
                    ))
                for slot in range(1,5):
                    raw = _value(row,f"gearbox_{slot}")
                    if raw.strip():
                        db.execute("""
                          INSERT INTO gearbox_classifications(
                            approval_record_id,source_row_sha256,slot_number,gearbox_value_raw,
                            final_drive_ratio_raw,assignment_raw,classification_status,market_scope
                          ) VALUES(?,?,?,?,?,?,?,?)
                        """, (
                            record_id,row_hash,slot,raw,_value(row,f"gearbox_{slot}_ratio"),
                            _value(row,f"gearbox_{slot}_assignment"),
                            "raw_approval_classification_not_vag_gearbox_code","CH"
                        ))
        metadata = {
            "pack_id": PACK_ID, "pack_status": "verified_research_only",
            "source_id": SOURCE_ID, "source_revision": source_meta["source_revision"],
            "source_file_sha256": source_meta["file_sha256"], "market_scope": "CH",
            "rights_status": "approved_by_official_astra_ogd_publication_and_swiss_ogd_reuse_terms",
            "attribution_required": "true", "production_import": "false",
            "research_pack_ingested": "true",
            "exact_vehicle_fitment": "false", "exact_engine_gearbox_pair": "false",
            "ru_eaeu_applicability": "false", "model_year_inferred": "false",
            "generation_inferred": "false", "engine_markings_are_candidates": "true",
            "gearbox_values_are_raw_classifications": "true",
            "no_pair_table": "true", "source_row_hash_method": "SHA-256 of canonical JSON array of all original parsed TSV field strings"
        }
        db.executemany("INSERT INTO pack_metadata(key,value) VALUES(?,?)", metadata.items())
        db.execute("""
          INSERT INTO source_files VALUES(?,?,?,?,?,?,?,?,?)
        """, (
            SOURCE_ID,SOURCE_URL,source_meta["source_revision"],source_meta["etag"],
            source_meta["file_size_bytes"],source_meta["file_sha256"],"CH",
            "approved_by_official_astra_ogd_publication_and_swiss_ogd_reuse_terms",1
        ))
        db.commit()
    except Exception:
        db.rollback()
        db.close()
        raise
    integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
    fk_violations = db.execute("PRAGMA foreign_key_check").fetchall()
    counts = {
        "approval_records": db.execute("SELECT count(*) FROM type_approval_records").fetchone()[0],
        "engine_marking_candidates": db.execute("SELECT count(*) FROM engine_marking_candidates").fetchone()[0],
        "gearbox_classifications": db.execute("SELECT count(*) FROM gearbox_classifications").fetchone()[0],
        "records_with_engine_marking": db.execute("SELECT count(*) FROM type_approval_records WHERE trim(coalesce(engine_marking_raw,''))<>''").fetchone()[0],
        "records_with_any_gearbox": db.execute("SELECT count(DISTINCT approval_record_id) FROM gearbox_classifications").fetchone()[0],
        "exact_engine_gearbox_pair_rows": 0,
    }
    table_names = {
        row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    db.close()
    if integrity != "ok" or fk_violations:
        raise ValueError("ASTRA TARGA SQLite integrity or foreign-key check failed")
    if any("pair" in name.casefold() for name in table_names):
        raise ValueError("ASTRA TARGA pack must not contain a pair table")
    if not counts["approval_records"] or not counts["engine_marking_candidates"] or not counts["gearbox_classifications"]:
        raise ValueError("ASTRA TARGA pack has no useful VAG technical approval rows")
    return {
        "counts": counts, "make_counts": dict(sorted(counts_by_make.items())),
        "vehicle_class_counts": dict(sorted(vehicle_classes.items())),
        "engine_marking_top_100": engine_markings.most_common(100),
        "gearbox_value_top_100": gearbox_values.most_common(100),
        "source_rows_scanned": source_rows, "malformed_rows": malformed_rows,
        "sqlite_integrity_check": integrity, "foreign_key_violations": len(fk_violations),
        "tables": sorted(table_names),
    }


def build_pack(output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    source_path = output_dir / "TG-Automobil.txt"
    database_path = output_dir / "astra-targa-legacy-vag.sqlite"
    source_meta = download_pinned_source(source_path)
    downloaded_at = datetime.now(timezone.utc).isoformat()
    data_report = build_database(source_path, database_path, source_meta)
    database_sha = sha256_bytes(database_path.read_bytes())
    source_manifest = {
        "schema_version": 1, "source_id": SOURCE_ID,
        "publisher": "Federal Roads Office (FEDRO / ASTRA), Swiss Confederation",
        "source_kind": "official_open_government_third_generation_type_approval_data",
        "market_scope": ["CH"], "source_url": SOURCE_URL,
        "data_description_url": DATA_DESCRIPTION_URL,
        "source_revision": source_meta["source_revision"], "etag": source_meta["etag"],
        "snapshot": {
            "downloaded_at_utc": downloaded_at, "downloaded": True,
            "file_size_bytes": source_meta["file_size_bytes"],
            "file_sha256": source_meta["file_sha256"],
            "source_generation": "third_generation_type_approvals_after_1995",
            "format": "tab-delimited TXT; cp1252; 223 columns",
        },
        "rights": {
            "data_license_status": "Swiss Open Government Data (OGD); no separate CC identifier assigned in the reviewed ASTRA publication",
            "rights_status": "approved_by_official_astra_ogd_publication_and_swiss_ogd_reuse_terms",
            "commercial_use_allowed": True, "display_allowed": True,
            "offline_cache_allowed": True, "bulk_reuse_allowed": True,
            "redistribution_allowed": True, "attribution_required": True,
            "attribution": ATTRIBUTION,
            "evidence_urls": [ASTRA_OPEN_DATA_URL, OGD_TERMS_URL, OGD_FAQ_URL, OGD_POLICY_URL, EMBAG_URL],
            "evidence": "ASTRA identifies the TARGA type-approval information products as open data and states that standardized technical type-approval data are freely available. Swiss OGD policy states that OGD may be reused freely subject to source disclosure; opendata.swiss terms explain commercial use and mandatory source attribution where indicated. No dataset-specific restriction was identified in the reviewed ASTRA publication.",
        },
        "coverage": {
            "source_generation": "third_generation_after_1995",
            "vehicle_group": "TG-Automobil.txt only; includes passenger and other automobile classes present in the source",
            "make_filter": "exact normalized source make values only; no fuzzy matching",
            "vag_make_counts": data_report["make_counts"],
        },
        "field_status": {
            "approval_number_and_date": "raw official CH type-approval record fields",
            "make_type_variant_version": "raw official source fields; not a model-generation or model-year assertion",
            "engine_make_type_and_marking": "raw approval fields; Motorkennzeichen is a source engine-marking candidate, not independently confirmed as a VAG factory engine code",
            "gearbox_1_to_4": "raw approval gearbox classifications; not VAG gearbox codes",
            "engine_gearbox_pair": "not established; no pair table and no pair claim",
            "model_year": "not inferred from approval date",
            "generation": "not inferred",
            "ecu_dtc_repair_content": "not provided by this source",
        },
        "applicability_policy": {
            "market_scope": "CH only", "approval_level": "type-approval record",
            "applicability_precision": "CH_type_approval_record",
            "variant_version": "preserve raw source string; do not expand embedded lists or wildcard-like values",
            "engine_marking": "store as unverified source candidate only",
            "gearbox_classification": "store separately as raw source classification only",
            "engine_gearbox_pair": "never infer or construct a pair from co-occurrence in one approval row",
            "model_year_generation": "not inferred",
            "individual_vehicle_fitment": False, "exact_engine_gearbox_pair": False,
            "production_fitment": False, "ru_eaeu_applicability": False,
            "repair_procedure_applicability": False, "diagnostic_execution_allowed": False,
        },
        "import_policy": {
            "research_pack_allowed": True, "data_ingested_to_research_pack": True,
            "product_import_allowed": False, "production_import": False,
            "ru_eaeu_applicability": False, "no_pair_table": True,
        },
    }
    source_manifest_path = output_dir / "source-manifest.json"
    source_manifest_path.write_text(json.dumps(source_manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    attribution_path = output_dir / "ATTRIBUTION.txt"
    attribution_path.write_text(ATTRIBUTION + "\n", encoding="utf-8")
    field_map_path = output_dir / "field-map.json"
    field_map_path.write_text(json.dumps({"zero_based_positions": FIELDS, "published_header_checks": HEADER_CHECKS}, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    pack_manifest = {
        "schema_version": 1, "pack_id": PACK_ID, "source_id": SOURCE_ID,
        "status": "verified_research_only", "market_scope": ["CH"],
        "rights_status": source_manifest["rights"]["rights_status"],
        "source_revision": source_meta["source_revision"],
        "source_file": {"name": "TG-Automobil.txt", **source_meta},
        "database": {"name": database_path.name, "sha256": database_sha, "size_bytes": database_path.stat().st_size},
        "source_manifest": {"name": source_manifest_path.name, "sha256": sha256_bytes(source_manifest_path.read_bytes())},
        "attribution": {"name": attribution_path.name, "sha256": sha256_bytes(attribution_path.read_bytes())},
        "field_map": {"name": field_map_path.name, "sha256": sha256_bytes(field_map_path.read_bytes())},
        "counts": data_report["counts"], "make_counts": data_report["make_counts"],
        "vehicle_class_counts": data_report["vehicle_class_counts"],
        "engine_marking_top_100": data_report["engine_marking_top_100"],
        "gearbox_value_top_100": data_report["gearbox_value_top_100"],
        "source_rows_scanned": data_report["source_rows_scanned"],
        "sqlite_integrity_check": data_report["sqlite_integrity_check"],
        "foreign_key_violations": data_report["foreign_key_violations"],
        "tables": data_report["tables"],
        "boundary": {
            "production_import": False, "exact_vehicle_fitment": False,
            "exact_engine_gearbox_pair": False, "ru_eaeu_applicability": False,
            "model_year_inferred": False, "generation_inferred": False,
            "dtc_content": False, "repair_content": False,
        },
    }
    pack_manifest_path = output_dir / "pack-manifest.json"
    pack_manifest_path.write_text(json.dumps(pack_manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    report_path = output_dir / "build-report.json"
    report_path.write_text(json.dumps(data_report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    archive_path = output_dir / "astra-targa-legacy-vag-research-pack.zip"
    # The archive digest is recorded in final-verification.json outside the ZIP
    # to avoid a self-referential manifest hash.
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for file_path in [database_path, source_manifest_path, attribution_path, field_map_path, pack_manifest_path, report_path]:
            archive.write(file_path, arcname=file_path.name)
    final = {
        "pack_id": PACK_ID, "source_id": SOURCE_ID,
        "source_file_sha256": source_meta["file_sha256"],
        "database_sha256": database_sha,
        "archive_sha256": sha256_bytes(archive_path.read_bytes()),
        "archive_size_bytes": archive_path.stat().st_size,
        "counts": data_report["counts"], "make_counts": data_report["make_counts"],
        "sqlite_integrity_check": data_report["sqlite_integrity_check"],
        "foreign_key_violations": data_report["foreign_key_violations"],
        "production_import": False, "ru_eaeu_applicability": False,
        "exact_engine_gearbox_pair": False,
    }
    (output_dir / "final-verification.json").write_text(json.dumps(final, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    source_path.unlink()
    return final


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="artifacts/astra-targa-legacy")
    args = parser.parse_args()
    result = build_pack(Path(args.output_dir))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
