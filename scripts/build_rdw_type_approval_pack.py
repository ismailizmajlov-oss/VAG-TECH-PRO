#!/usr/bin/env python3
"""Build an isolated RDW CC0 type-approval candidate pack for Windows offline use.

The source is the Netherlands RDW register. It is not Russian/EAEU OTTS and does not
establish exact vehicle fitment or VAG factory engine/gearbox-code semantics.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import shutil
import sqlite3
import tempfile
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_MANIFEST = Path("data/source-manifests/rdw-eu-type-approval-cc0.json")
ALLOWED_HOSTS = {"opendata.rdw.nl", "data.overheid.nl", "www.data.overheid.nl", "creativecommons.org"}
MARKET_SCOPE = "NL_EU_TYPE_APPROVAL_REGISTER"
PRECISION = "type_approval_variant"
VERIFICATION = "source_published_candidate"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def normalize_field(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).casefold())


def normalize_make_code(value: Any) -> str:
    text = str(value or "").upper().translate(str.maketrans({"Š": "S", "Ž": "Z", "Ä": "A", "Ö": "O", "Ü": "U"}))
    return re.sub(r"[^A-Z0-9]", "", text)


def make_name_for_code(value: Any, aliases: dict[str, str]) -> str | None:
    return aliases.get(normalize_make_code(value))


def field(row: dict[str, Any], *names: str) -> str | None:
    normalized = {normalize_field(k): v for k, v in row.items()}
    for name in names:
        value = normalized.get(normalize_field(name))
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def variant_key(row: dict[str, Any]) -> tuple[str, str, str, str] | None:
    approval = field(row, "typegoedkeuringsnummer")
    variant = field(row, "codevarianttgk", "codevariantgk")
    version = field(row, "codeuitvoeringtgk")
    revision = field(row, "volgnummerrevisieuitvoering")
    if not all((approval, variant, version, revision)):
        return None
    return (approval.casefold(), variant.casefold(), version.casefold(), revision.casefold())


def safe_fetch(url: str, max_bytes: int, timeout: int, accept: str) -> bytes:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
        raise ValueError(f"Blocked non-allowlisted source URL: {url}")
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "VAG-TECH-PRO-RDW-CC0-builder/1.0",
            "Accept": accept,
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        final = urllib.parse.urlparse(response.geturl())
        if final.scheme != "https" or final.hostname not in ALLOWED_HOSTS:
            raise ValueError(f"Unexpected source redirect: {response.geturl()}")
        if response.status != 200:
            raise ValueError(f"Unexpected HTTP status {response.status}: {url}")
        content_type = response.headers.get("Content-Type", "").casefold()
        data = response.read(max_bytes + 1)
    if not data or len(data) > max_bytes:
        raise ValueError(f"Empty or oversized source response: {url}")
    if "text/html" in content_type and "csv" in accept:
        raise ValueError(f"CSV endpoint returned HTML: {url}")
    return data


def read_csv_rows(raw: bytes, dataset_id: str, max_rows: int) -> tuple[list[dict[str, Any]], list[str]]:
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{dataset_id}: CSV is not UTF-8") from exc
    reader = csv.DictReader(io.StringIO(text, newline=""))
    if not reader.fieldnames:
        raise ValueError(f"{dataset_id}: CSV has no header")
    rows: list[dict[str, Any]] = []
    for row in reader:
        if len(rows) >= max_rows:
            raise ValueError(f"{dataset_id}: row limit {max_rows} exceeded")
        cleaned = {str(k).strip(): (str(v).strip() if v is not None else "") for k, v in row.items() if k is not None}
        if any(value for value in cleaned.values()):
            rows.append(cleaned)
    return rows, [str(x) for x in reader.fieldnames]


def validate_view_metadata(raw: bytes, dataset: dict[str, Any]) -> tuple[dict[str, Any], str]:
    try:
        metadata = json.loads(raw.decode("utf-8-sig"))
    except Exception as exc:
        raise ValueError(f"{dataset['dataset_id']}: invalid Socrata view metadata JSON") from exc
    view_id = str(metadata.get("id") or metadata.get("resource", {}).get("id") or "")
    if view_id.casefold() != str(dataset["view_id"]).casefold():
        raise ValueError(f"{dataset['dataset_id']}: view ID mismatch {view_id!r}")
    columns = metadata.get("columns") or []
    names = {normalize_field(c.get("fieldName") or c.get("name") or "") for c in columns if isinstance(c, dict)}
    required = {normalize_field(x) for x in dataset.get("required_fields", [])}
    # The manufacturer trade-name table uses codevariantgk in some published snapshots.
    if dataset["view_id"] == "x5v3-sewk":
        required.discard(normalize_field("codevarianttgk"))
    if normalize_field("codevarianttgk") in required:
        if normalize_field("codevariantgk") in names:
            required.discard(normalize_field("codevarianttgk"))
    if not required.issubset(names):
        missing = sorted(required - names)
        raise ValueError(f"{dataset['dataset_id']}: required metadata columns missing: {missing}")
    revision = (
        metadata.get("rowsUpdatedAt")
        or metadata.get("viewLastModified")
        or metadata.get("metadataUpdatedAt")
        or metadata.get("createdAt")
        or "revision_not_exposed_snapshot_hash_is_authoritative"
    )
    return metadata, str(revision)


def build_database(
    path: Path,
    manifest: dict[str, Any],
    snapshots: dict[str, dict[str, Any]],
    rows_by_dataset: dict[str, list[dict[str, Any]]],
    aliases: dict[str, str],
    brand_inventory: dict[str, int],
) -> dict[str, int]:
    by_id = {item["dataset_id"]: item for item in manifest["datasets"]}
    make_dataset = "rdw-tgk-merk-uitvoering"
    make_rows = rows_by_dataset[make_dataset]
    selected: dict[tuple[str, str, str, str, str], dict[str, Any]] = {}
    unmapped = {code: count for code, count in brand_inventory.items() if make_name_for_code(code, aliases) is None}

    for row in make_rows:
        key = variant_key(row)
        code = field(row, "merkcoderdw", "merkcodeRdw")
        make_name = make_name_for_code(code, aliases)
        if key is None or not code:
            continue
        if make_name is None:
            continue
        composite = (*key, normalize_make_code(code))
        selected.setdefault(composite, {
            "key": key,
            "make_code": str(code),
            "make_name": make_name,
            "make_row": row,
        })

    datasets = {item["purpose"]: item["dataset_id"] for item in manifest["datasets"]}
    base_by_key: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    engine_by_key: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    names_by_key: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    gearbox_by_key: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)

    for purpose, target in (
        ("approval_variant_base", base_by_key),
        ("engine_type_approval_candidates", engine_by_key),
        ("manufacturer_trade_name_candidates", names_by_key),
        ("gearbox_type_approval_candidates", gearbox_by_key),
    ):
        dataset_id = datasets[purpose]
        for row in rows_by_dataset[dataset_id]:
            key = variant_key(row)
            if key is not None:
                target[key].append(row)

    db = sqlite3.connect(path)
    try:
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA journal_mode=DELETE")
        db.execute("PRAGMA synchronous=FULL")
        db.execute("PRAGMA user_version=1")
        db.executescript("""
        CREATE TABLE source_registry(
          source_id TEXT PRIMARY KEY,
          publisher TEXT NOT NULL,
          dataset_id TEXT NOT NULL UNIQUE,
          title TEXT NOT NULL,
          dataset_page TEXT NOT NULL,
          view_id TEXT NOT NULL,
          license_id TEXT NOT NULL CHECK(license_id='CC0-1.0'),
          license_url TEXT NOT NULL,
          rights_status TEXT NOT NULL CHECK(rights_status='approved_by_dataset_specific_CC0'),
          commercial_use_allowed INTEGER NOT NULL CHECK(commercial_use_allowed=1),
          display_allowed INTEGER NOT NULL CHECK(display_allowed=1),
          offline_cache_allowed INTEGER NOT NULL CHECK(offline_cache_allowed=1),
          redistribution_allowed INTEGER NOT NULL CHECK(redistribution_allowed=1),
          market_scope TEXT NOT NULL CHECK(market_scope='NL_EU_TYPE_APPROVAL_REGISTER'),
          source_revision TEXT NOT NULL,
          metadata_sha256 TEXT NOT NULL CHECK(length(metadata_sha256)=64)
        );
        CREATE TABLE source_files(
          file_id INTEGER PRIMARY KEY,
          dataset_id TEXT NOT NULL REFERENCES source_registry(dataset_id),
          file_kind TEXT NOT NULL CHECK(file_kind IN ('csv_snapshot','view_metadata','license_evidence_page','license_text','discovery_query')),
          chunk_no INTEGER NOT NULL DEFAULT 0 CHECK(chunk_no>=0),
          query_text TEXT NOT NULL DEFAULT '',
          relative_path TEXT NOT NULL,
          source_url TEXT NOT NULL,
          retrieved_at_utc TEXT NOT NULL,
          byte_size INTEGER NOT NULL CHECK(byte_size>0),
          sha256 TEXT NOT NULL CHECK(length(sha256)=64),
          UNIQUE(dataset_id,file_kind,chunk_no)
        );
        CREATE TABLE vag_type_approval_variants(
          variant_id INTEGER PRIMARY KEY,
          type_approval_number TEXT NOT NULL,
          variant_code TEXT NOT NULL,
          version_code TEXT NOT NULL,
          revision_sequence TEXT NOT NULL,
          rdw_make_code TEXT NOT NULL,
          make_name TEXT NOT NULL,
          market_scope TEXT NOT NULL CHECK(market_scope='NL_EU_TYPE_APPROVAL_REGISTER'),
          applicability_precision TEXT NOT NULL CHECK(applicability_precision='type_approval_variant'),
          verification_status TEXT NOT NULL CHECK(verification_status='source_published_candidate'),
          exact_vehicle_fitment INTEGER NOT NULL DEFAULT 0 CHECK(exact_vehicle_fitment=0),
          russian_eaeu_fitment INTEGER NOT NULL DEFAULT 0 CHECK(russian_eaeu_fitment=0),
          factory_engine_code_confirmed INTEGER NOT NULL DEFAULT 0 CHECK(factory_engine_code_confirmed=0),
          factory_gearbox_code_confirmed INTEGER NOT NULL DEFAULT 0 CHECK(factory_gearbox_code_confirmed=0),
          model_generation_year_confirmed INTEGER NOT NULL DEFAULT 0 CHECK(model_generation_year_confirmed=0),
          make_source_row_sha256 TEXT NOT NULL CHECK(length(make_source_row_sha256)=64),
          make_source_row_json TEXT NOT NULL,
          UNIQUE(type_approval_number,variant_code,version_code,revision_sequence,rdw_make_code)
        );
        CREATE TABLE base_variant_evidence(
          evidence_id INTEGER PRIMARY KEY,
          variant_id INTEGER NOT NULL REFERENCES vag_type_approval_variants(variant_id),
          source_dataset_id TEXT NOT NULL REFERENCES source_registry(dataset_id),
          source_record_sha256 TEXT NOT NULL CHECK(length(source_record_sha256)=64),
          source_record_json TEXT NOT NULL,
          UNIQUE(variant_id,source_record_sha256)
        );
        CREATE TABLE engine_candidates(
          engine_candidate_id INTEGER PRIMARY KEY,
          variant_id INTEGER NOT NULL REFERENCES vag_type_approval_variants(variant_id),
          rdw_motorcode_candidate TEXT,
          displacement_cc_candidate TEXT,
          cylinder_count_candidate TEXT,
          fuel_type_code_candidate TEXT,
          cylinder_layout_code_candidate TEXT,
          engine_operation_code_candidate TEXT,
          semantics TEXT NOT NULL CHECK(semantics='rdw_motorcode_field_not_confirmed_as_vag_factory_engine_code'),
          source_dataset_id TEXT NOT NULL REFERENCES source_registry(dataset_id),
          source_record_sha256 TEXT NOT NULL CHECK(length(source_record_sha256)=64),
          source_record_json TEXT NOT NULL,
          UNIQUE(variant_id,source_record_sha256)
        );
        CREATE TABLE gearbox_type_candidates(
          gearbox_candidate_id INTEGER PRIMARY KEY,
          variant_id INTEGER NOT NULL REFERENCES vag_type_approval_variants(variant_id),
          rdw_gearbox_type_code_candidate TEXT,
          gear_count_min_candidate TEXT,
          gear_count_max_candidate TEXT,
          semantics TEXT NOT NULL CHECK(semantics='rdw_type_approval_gearbox_type_not_vag_factory_gearbox_code'),
          source_dataset_id TEXT NOT NULL REFERENCES source_registry(dataset_id),
          source_record_sha256 TEXT NOT NULL CHECK(length(source_record_sha256)=64),
          source_record_json TEXT NOT NULL,
          UNIQUE(variant_id,source_record_sha256)
        );
        CREATE TABLE manufacturer_trade_names(
          trade_name_id INTEGER PRIMARY KEY,
          variant_id INTEGER NOT NULL REFERENCES vag_type_approval_variants(variant_id),
          trade_name_candidate TEXT,
          manufacturer_type_candidate TEXT,
          source_dataset_id TEXT NOT NULL REFERENCES source_registry(dataset_id),
          source_record_sha256 TEXT NOT NULL CHECK(length(source_record_sha256)=64),
          source_record_json TEXT NOT NULL,
          UNIQUE(variant_id,source_record_sha256)
        );
        CREATE TABLE brand_code_inventory(
          normalized_make_code TEXT PRIMARY KEY,
          source_make_code TEXT NOT NULL,
          source_row_count INTEGER NOT NULL CHECK(source_row_count>=0),
          mapped_vag_make TEXT
        );
        CREATE TABLE database_info(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE INDEX idx_rdw_approval_number ON vag_type_approval_variants(type_approval_number);
        CREATE INDEX idx_rdw_make_name ON vag_type_approval_variants(make_name);
        CREATE INDEX idx_rdw_motorcode_candidate ON engine_candidates(rdw_motorcode_candidate);
        CREATE INDEX idx_rdw_gearbox_type_candidate ON gearbox_type_candidates(rdw_gearbox_type_code_candidate);
        """)

        now = datetime.now(timezone.utc).isoformat()
        for dataset in manifest["datasets"]:
            snap = snapshots[dataset["dataset_id"]]
            db.execute(
                """INSERT INTO source_registry VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    manifest["source_id"] + ":" + dataset["dataset_id"], manifest["publisher"], dataset["dataset_id"], dataset["title"],
                    dataset["dataset_page"], dataset["view_id"], manifest["dataset_license"], manifest["license_url"],
                    "approved_by_dataset_specific_CC0", 1, 1, 1, 1, MARKET_SCOPE,
                    snap["source_revision"], snap["metadata_sha256"],
                ),
            )
            for kind in ("view_metadata", "license_evidence_page"):
                item = snap[kind]
                db.execute(
                    """INSERT INTO source_files(
                         dataset_id,file_kind,chunk_no,query_text,relative_path,source_url,retrieved_at_utc,byte_size,sha256
                       ) VALUES(?,?,?,?,?,?,?,?,?)""",
                    (dataset["dataset_id"], kind, 0, "", item["relative_path"], item["source_url"], now,
                     item["byte_size"], item["sha256"]),
                )
            for item in snap.get("csv_snapshots", []):
                db.execute(
                    """INSERT INTO source_files(
                         dataset_id,file_kind,chunk_no,query_text,relative_path,source_url,retrieved_at_utc,byte_size,sha256
                       ) VALUES(?,?,?,?,?,?,?,?,?)""",
                    (dataset["dataset_id"], "csv_snapshot", item["chunk_no"], item["query_text"],
                     item["relative_path"], item["source_url"], now, item["byte_size"], item["sha256"]),
                )
            discovery = snap.get("discovery_query")
            if discovery:
                db.execute(
                    """INSERT INTO source_files(
                         dataset_id,file_kind,chunk_no,query_text,relative_path,source_url,retrieved_at_utc,byte_size,sha256
                       ) VALUES(?,?,?,?,?,?,?,?,?)""",
                    (dataset["dataset_id"], "discovery_query", 0, discovery["query_text"],
                     discovery["relative_path"], discovery["source_url"], now,
                     discovery["byte_size"], discovery["sha256"]),
                )
        license_snapshot = snapshots["__license__"]["license_text"]
        db.execute(
            """INSERT INTO source_files(
                 dataset_id,file_kind,chunk_no,query_text,relative_path,source_url,retrieved_at_utc,byte_size,sha256
               ) VALUES(?,?,?,?,?,?,?,?,?)""",
            ("rdw-tgk-basis-uitvoering", "license_text", 0, "", license_snapshot["relative_path"],
             license_snapshot["source_url"], now, license_snapshot["byte_size"], license_snapshot["sha256"]),
        )

        for code, count_value in sorted(brand_inventory.items()):
            db.execute(
                "INSERT INTO brand_code_inventory VALUES(?,?,?,?)",
                (normalize_make_code(code), code, count_value, make_name_for_code(code, aliases)),
            )

        variant_ids: dict[tuple[str, str, str, str, str], int] = {}
        for composite, item in sorted(selected.items()):
            key = item["key"]
            row_json = canonical_json(item["make_row"])
            row_hash = sha256_bytes(row_json.encode("utf-8"))
            source_row = item["make_row"]
            display_key = (
                field(source_row, "typegoedkeuringsnummer"),
                field(source_row, "codevarianttgk", "codevariantgk"),
                field(source_row, "codeuitvoeringtgk"),
                field(source_row, "volgnummerrevisieuitvoering"),
            )
            if not all(display_key):
                raise ValueError("Selected RDW make row lost one of its published display-key fields")
            cursor = db.execute(
                """INSERT INTO vag_type_approval_variants(
                     type_approval_number,variant_code,version_code,revision_sequence,rdw_make_code,make_name,
                     market_scope,applicability_precision,verification_status,make_source_row_sha256,make_source_row_json
                   ) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (*display_key, item["make_code"], item["make_name"], MARKET_SCOPE, PRECISION, VERIFICATION, row_hash, row_json),
            )
            variant_ids[composite] = int(cursor.lastrowid)

        key_to_ids: dict[tuple[str, str, str, str], list[int]] = defaultdict(list)
        for composite, variant_id in variant_ids.items():
            key_to_ids[composite[:4]].append(variant_id)

        def add_evidence(table: str, purpose: str, target: dict[tuple[str, str, str, str], list[dict[str, Any]]],
                         columns: tuple[str, ...]) -> int:
            dataset_id = datasets[purpose]
            inserted = 0
            for key, rows in target.items():
                for variant_id in key_to_ids.get(key, []):
                    for row in rows:
                        row_json = canonical_json(row)
                        row_hash = sha256_bytes(row_json.encode("utf-8"))
                        values = [variant_id, dataset_id, row_hash, row_json]
                        if table == "engine_candidates":
                            cursor = db.execute(
                                """INSERT OR IGNORE INTO engine_candidates(
                                   variant_id,rdw_motorcode_candidate,displacement_cc_candidate,cylinder_count_candidate,
                                   fuel_type_code_candidate,cylinder_layout_code_candidate,engine_operation_code_candidate,
                                   semantics,source_dataset_id,source_record_sha256,source_record_json
                                   ) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                                [
                                variant_id,
                                field(row, "motorcode"),
                                field(row, "cilinderinhoud"),
                                field(row, "aantalcilinders"),
                                field(row, "codebrandstoftypemotor"),
                                field(row, "codecilinderopstelling"),
                                field(row, "codewerkingmotor"),
                                "rdw_motorcode_field_not_confirmed_as_vag_factory_engine_code",
                                dataset_id, row_hash, row_json,
                                ])
                        elif table == "gearbox_type_candidates":
                            values = [
                                variant_id,
                                field(row, "codetypeversnellingsbak"),
                                field(row, "aantalversnellingenondergrens"),
                                field(row, "aantalversnellingenbovengrens"),
                                "rdw_type_approval_gearbox_type_not_vag_factory_gearbox_code",
                                dataset_id, row_hash, row_json,
                            ]
                            cursor = db.execute(
                                """INSERT OR IGNORE INTO gearbox_type_candidates(
                                   variant_id,rdw_gearbox_type_code_candidate,gear_count_min_candidate,
                                   gear_count_max_candidate,semantics,source_dataset_id,source_record_sha256,source_record_json
                                   ) VALUES(?,?,?,?,?,?,?,?)""", values)
                        elif table == "manufacturer_trade_names":
                            values = [
                                variant_id, field(row, "handelsbenamingfabrikant"),
                                field(row, "typeaanduidingfabrikant"), dataset_id, row_hash, row_json,
                            ]
                            cursor = db.execute(
                                """INSERT OR IGNORE INTO manufacturer_trade_names(
                                   variant_id,trade_name_candidate,manufacturer_type_candidate,
                                   source_dataset_id,source_record_sha256,source_record_json
                                   ) VALUES(?,?,?,?,?,?)""", values)
                        else:
                            cursor = db.execute(
                                """INSERT OR IGNORE INTO base_variant_evidence(
                                   variant_id,source_dataset_id,source_record_sha256,source_record_json
                                   ) VALUES(?,?,?,?)""", values)
                        inserted += max(cursor.rowcount, 0)
            return inserted

        counts = {
            "vag_type_approval_variants": len(variant_ids),
            "base_variant_evidence": add_evidence("base_variant_evidence", "approval_variant_base", base_by_key, ()),
            "engine_candidates": add_evidence("engine_candidates", "engine_type_approval_candidates", engine_by_key, ()),
            "gearbox_type_candidates": add_evidence("gearbox_type_candidates", "gearbox_type_approval_candidates", gearbox_by_key, ()),
            "manufacturer_trade_names": add_evidence("manufacturer_trade_names", "manufacturer_trade_name_candidates", names_by_key, ()),
        }
        info = {
            "schema_version": "1",
            "source_id": manifest["source_id"],
            "dataset_license": manifest["dataset_license"],
            "market_scope": MARKET_SCOPE,
            "applicability_precision": PRECISION,
            "verification_status": VERIFICATION,
            "exact_vehicle_fitment_rows": "0",
            "russian_eaeu_fitment_rows": "0",
            "factory_engine_code_confirmed_rows": "0",
            "factory_gearbox_code_confirmed_rows": "0",
            "model_generation_year_confirmed_rows": "0",
            "brand_code_inventory_json": canonical_json(brand_inventory),
            "unmapped_brand_codes_json": canonical_json(unmapped),
            "built_at_utc": now,
        }
        db.executemany("INSERT INTO database_info(key,value) VALUES(?,?)", sorted(info.items()))
        if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("RDW SQLite integrity_check failed")
        if db.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("RDW SQLite foreign_key_check failed")
        return counts
    finally:
        db.close()


def verify_pack(pack_dir: Path) -> dict[str, Any]:
    manifest_path = pack_dir / "manifest.json"
    db_path = pack_dir / "rdw-eu-type-approval-candidates.sqlite"
    report_path = pack_dir / "report.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    report = json.loads(report_path.read_text(encoding="utf-8-sig"))
    if manifest.get("dataset_license") != "CC0-1.0" or manifest.get("rights_confirmed") is not True:
        raise ValueError("RDW CC0 rights status mismatch")
    if manifest.get("market_scope") != MARKET_SCOPE or manifest.get("exact_vehicle_fitment") is not False:
        raise ValueError("RDW market/applicability boundary mismatch")
    if manifest.get("russian_eaeu_fitment") is not False:
        raise ValueError("RDW pack must not claim Russian/EAEU fitment")
    for item in manifest.get("files", []):
        path = pack_dir / item["relative_path"]
        if not path.is_file() or path.stat().st_size != item["byte_size"] or sha256_file(path) != item["sha256"]:
            raise ValueError(f"RDW snapshot hash/size mismatch: {item['relative_path']}")
    source_manifest_path = pack_dir / "source-manifest.json"
    if not source_manifest_path.is_file() or sha256_file(source_manifest_path) != manifest.get("source_manifest_sha256"):
        raise ValueError("RDW source manifest hash mismatch")
    if sha256_file(db_path) != manifest.get("database_sha256"):
        raise ValueError("RDW SQLite database hash mismatch")
    db = sqlite3.connect(f"file:{db_path.resolve().as_posix()}?mode=ro", uri=True)
    try:
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("RDW SQLite integrity_check failed during verification")
        if db.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("RDW SQLite foreign_key_check failed during verification")
        counts = {
            "vag_type_approval_variants": db.execute("SELECT count(*) FROM vag_type_approval_variants").fetchone()[0],
            "base_variant_evidence": db.execute("SELECT count(*) FROM base_variant_evidence").fetchone()[0],
            "engine_candidates": db.execute("SELECT count(*) FROM engine_candidates").fetchone()[0],
            "gearbox_type_candidates": db.execute("SELECT count(*) FROM gearbox_type_candidates").fetchone()[0],
            "manufacturer_trade_names": db.execute("SELECT count(*) FROM manufacturer_trade_names").fetchone()[0],
        }
        if counts != manifest.get("counts"):
            raise ValueError(f"RDW SQLite row counts mismatch: {counts} != {manifest.get('counts')}")
        if db.execute("SELECT count(*) FROM source_registry").fetchone()[0] != 5:
            raise ValueError("RDW source registry must contain exactly five licensed datasets")
        if db.execute("SELECT count(*) FROM source_files").fetchone()[0] != int(manifest.get("source_file_count", -1)):
            raise ValueError("RDW source file registry count does not match the pack manifest")
        if db.execute("SELECT count(*) FROM source_registry WHERE license_id<>'CC0-1.0' OR rights_status<>'approved_by_dataset_specific_CC0' OR commercial_use_allowed<>1 OR display_allowed<>1 OR offline_cache_allowed<>1 OR redistribution_allowed<>1").fetchone()[0] != 0:
            raise ValueError("RDW source rights flags mismatch")
        if db.execute("SELECT count(*) FROM vag_type_approval_variants WHERE market_scope<>? OR applicability_precision<>? OR verification_status<>? OR exact_vehicle_fitment<>0 OR russian_eaeu_fitment<>0 OR factory_engine_code_confirmed<>0 OR factory_gearbox_code_confirmed<>0 OR model_generation_year_confirmed<>0",
                      (MARKET_SCOPE, PRECISION, VERIFICATION)).fetchone()[0] != 0:
            raise ValueError("RDW applicability boundary failed")
        if db.execute("SELECT count(*) FROM engine_candidates WHERE semantics<>'rdw_motorcode_field_not_confirmed_as_vag_factory_engine_code'").fetchone()[0] != 0:
            raise ValueError("RDW motorcode semantics boundary failed")
        if db.execute("SELECT count(*) FROM gearbox_type_candidates WHERE semantics<>'rdw_type_approval_gearbox_type_not_vag_factory_gearbox_code'").fetchone()[0] != 0:
            raise ValueError("RDW gearbox semantics boundary failed")
    finally:
        db.close()
    if report.get("counts") != counts:
        raise ValueError("RDW report/database counts mismatch")
    return {"status": "verified", "database": db_path.name, "counts": counts, "market_scope": MARKET_SCOPE,
            "exact_vehicle_fitment": False, "database_sha256": manifest["database_sha256"]}


def build(manifest_path: Path, output_dir: Path) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    if manifest.get("schema_version") != 1 or manifest.get("source_id") != "rdw-eu-type-approval-register":
        raise ValueError("Unexpected RDW source manifest")
    if manifest.get("dataset_license") != "CC0-1.0" or len(manifest.get("datasets", [])) != 5:
        raise ValueError("RDW dataset license or source list changed; manual review required")
    if manifest.get("market_scope") != MARKET_SCOPE:
        raise ValueError("RDW market scope changed")
    if output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite existing pack directory: {output_dir}")
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    temp_dir = Path(tempfile.mkdtemp(prefix="rdw-type-approval-", dir=output_dir.parent))
    try:
        timeout = int(manifest["limits"]["timeout_seconds"])
        max_meta = int(manifest["limits"]["max_metadata_bytes"])
        max_csv = int(manifest["limits"]["max_csv_bytes_per_dataset"])
        max_rows = int(manifest["limits"]["max_rows_per_dataset"])
        snapshots: dict[str, dict[str, Any]] = {}
        rows_by_dataset: dict[str, list[dict[str, Any]]] = {}
        file_records: list[dict[str, Any]] = []
        now = datetime.now(timezone.utc).isoformat()

        license_raw = safe_fetch(manifest["license_text_url"], max_meta, timeout, "text/plain, text/html;q=0.9")
        license_text = license_raw.decode("utf-8", errors="replace")
        if "CC0 1.0 Universal" not in license_text and "CC0 1.0" not in license_text:
            raise ValueError("Fetched CC0 legal text did not match CC0-1.0")
        license_path = temp_dir / "LICENSES" / "CC0-1.0-legalcode.txt"
        license_path.parent.mkdir(parents=True, exist_ok=True)
        license_path.write_bytes(license_raw)
        license_record = {
            "relative_path": license_path.relative_to(temp_dir).as_posix(),
            "source_url": manifest["license_text_url"], "byte_size": len(license_raw),
            "sha256": sha256_bytes(license_raw),
        }
        file_records.append({"relative_path": license_record["relative_path"], "byte_size": len(license_raw), "sha256": license_record["sha256"]})

        aliases = {normalize_make_code(k): v for k, v in manifest["brand_code_aliases"].items()}
        for dataset in manifest["datasets"]:
            metadata_raw = safe_fetch(dataset["metadata_url"], max_meta, timeout, "application/json")
            metadata, revision = validate_view_metadata(metadata_raw, dataset)
            csv_raw = safe_fetch(dataset["download_url"], max_csv, timeout, "text/csv, application/csv;q=0.9")
            rows, headers = read_csv_rows(csv_raw, dataset["dataset_id"], max_rows)
            required = dataset.get("required_fields", [])
            header_norm = {normalize_field(x) for x in headers}
            for required_field in required:
                if normalize_field(required_field) not in header_norm:
                    # Manufacturer trade names use the published codevariantgk alias.
                    if not (required_field == "codevarianttgk" and "codevariantgk" in header_norm):
                        raise ValueError(f"{dataset['dataset_id']}: required CSV column missing: {required_field}")
            page_raw = safe_fetch(dataset["dataset_page"], max_meta, timeout, "text/html,application/xhtml+xml")
            page_text = page_raw.decode("utf-8", errors="replace").casefold()
            if "cc-0" not in page_text and "cc0" not in page_text:
                raise ValueError(f"{dataset['dataset_id']}: dataset page no longer declares CC0")
            base = temp_dir / "upstream"
            base.mkdir(exist_ok=True)
            csv_path = base / f"{dataset['view_id']}.csv"
            metadata_path = base / f"{dataset['view_id']}.metadata.json"
            page_path = base / f"{dataset['view_id']}.license-evidence.html"
            csv_path.write_bytes(csv_raw)
            metadata_path.write_bytes(metadata_raw)
            page_path.write_bytes(page_raw)
            snapshots[dataset["dataset_id"]] = {
                "source_revision": revision,
                "metadata_sha256": sha256_bytes(metadata_raw),
                "csv_snapshot": {"relative_path": csv_path.relative_to(temp_dir).as_posix(), "source_url": dataset["download_url"], "byte_size": len(csv_raw), "sha256": sha256_bytes(csv_raw)},
                "view_metadata": {"relative_path": metadata_path.relative_to(temp_dir).as_posix(), "source_url": dataset["metadata_url"], "byte_size": len(metadata_raw), "sha256": sha256_bytes(metadata_raw)},
                "license_evidence_page": {"relative_path": page_path.relative_to(temp_dir).as_posix(), "source_url": dataset["dataset_page"], "byte_size": len(page_raw), "sha256": sha256_bytes(page_raw)},
            }
            rows_by_dataset[dataset["dataset_id"]] = rows
            for kind in ("csv_snapshot", "view_metadata", "license_evidence_page"):
                item = snapshots[dataset["dataset_id"]][kind]
                file_records.append({"relative_path": item["relative_path"], "byte_size": item["byte_size"], "sha256": item["sha256"]})

        snapshots["__license__"] = {"license_text": license_record}
        make_dataset = "rdw-tgk-merk-uitvoering"
        inventory: Counter[str] = Counter()
        for row in rows_by_dataset[make_dataset]:
            code = field(row, "merkcoderdw", "merkcodeRdw")
            if code:
                inventory[code] += 1

        db_path = temp_dir / "rdw-eu-type-approval-candidates.sqlite"
        counts = build_database(db_path, manifest, snapshots, rows_by_dataset, aliases, dict(inventory))
        database_hash = sha256_file(db_path)
        report = {
            "status": "candidate_pack_built",
            "source_id": manifest["source_id"],
            "publisher": manifest["publisher"],
            "dataset_license": manifest["dataset_license"],
            "market_scope": MARKET_SCOPE,
            "retrieved_at_utc": now,
            "source_row_counts": {key: len(value) for key, value in rows_by_dataset.items()},
            "brand_code_inventory": dict(sorted(inventory.items())),
            "matched_vag_brand_codes": {code: name for code, name in sorted(aliases.items()) if code in {normalize_make_code(x) for x in inventory}},
            "unmapped_brand_codes": {code: count for code, count in sorted(inventory.items()) if normalize_make_code(code) not in aliases},
            "counts": counts,
            "database_sha256": database_hash,
        }
        report_path = temp_dir / "report.json"
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        pack_manifest = {
            "schema_version": 1,
            "pack_id": "rdw-eu-type-approval-cc0",
            "status": "verified_candidate_pack" if counts["vag_type_approval_variants"] else "discovery_only_no_vag_make_codes_matched",
            "publisher": manifest["publisher"],
            "publisher_url": manifest["publisher_url"],
            "source_manifest": "source-manifest.json",
            "source_manifest_sha256": sha256_file(manifest_path),
            "dataset_license": "CC0-1.0",
            "license_url": manifest["license_url"],
            "license_text_sha256": license_record["sha256"],
            "rights_confirmed": True,
            "commercial_use_allowed": True,
            "display_allowed": True,
            "offline_cache_allowed": True,
            "redistribution_allowed": True,
            "market_scope": MARKET_SCOPE,
            "market_scope_note": manifest["market_scope_note"],
            "applicability_precision": PRECISION,
            "verification_status": VERIFICATION,
            "exact_vehicle_fitment": False,
            "russian_eaeu_fitment": False,
            "factory_engine_code_confirmed": False,
            "factory_gearbox_code_confirmed": False,
            "model_generation_year_confirmed": False,
            "datasets": [
                {"dataset_id": item["dataset_id"], "title": item["title"], "view_id": item["view_id"],
                 "dataset_page": item["dataset_page"], "download_url": item["download_url"],
                 "source_revision": snapshots[item["dataset_id"]]["source_revision"],
                 "metadata_sha256": snapshots[item["dataset_id"]]["metadata_sha256"]}
                for item in manifest["datasets"]
            ],
            "counts": counts,
            "brand_code_inventory": dict(sorted(inventory.items())),
            "matched_vag_brand_codes": report["matched_vag_brand_codes"],
            "unmapped_brand_codes": report["unmapped_brand_codes"],
            "database_file": db_path.name,
            "database_sha256": database_hash,
            "files": file_records,
            "built_at_utc": now,
        }
        (temp_dir / "source-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (temp_dir / "manifest.json").write_text(json.dumps(pack_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        verification = verify_pack(temp_dir)
        if verification["status"] != "verified":
            raise RuntimeError("RDW pack verification failed")
        os.replace(temp_dir, output_dir)
        return {**verification, "brand_code_inventory": report["brand_code_inventory"],
                "matched_vag_brand_codes": report["matched_vag_brand_codes"],
                "unmapped_brand_codes": report["unmapped_brand_codes"],
                "source_row_counts": report["source_row_counts"]}
    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    if args.verify_only:
        result = verify_pack(args.output.resolve())
    else:
        result = build(args.manifest.resolve(), args.output.resolve())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
