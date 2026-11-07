#!/usr/bin/env python3
"""Build an isolated KBA Germany VAG stock-reference SQLite research pack.

The KBA source contains aggregate stock observations, not individual vehicles.
No engine/gearbox pairing, model-year/generation inference, OEM fitment or RU/EAEU
applicability is created by this builder.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, os, shutil, sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PACK_ID = "kba-de-vag-stock-research"
SOURCE_ID = "kba-de-fz-hersteller-handelsnamen-pkw"
SOURCE_URL = "https://www.govdata.de/suche/daten/fz-hersteller-handelsnamen-pkw?ids=638594fd-195a-4e03-b91c-f5ea2eacfa39"
RESOURCE_URL = "https://hub.arcgis.com/api/download/v1/items/d277ec18ff1e442597c9411d7c1aaeaa/csv?layers=0"
LICENSE_ID = "DL-DE-BY-2.0"
LICENSE_URL = "https://www.govdata.de/dl-de/by-2-0"
EXACT_LABELS = {"volkswagen (d)", "audi (d)", "audi (h)", "skoda (cz)", "seat (e)", "porsche", "bentley (uk)", "lamborghini (i)"}
COLUMNS = ["Berichtszeitpunkt", "Hersteller", "Handelsname", "Typschlüssel", "Bundesland", "Anzahl", "ZS Anzahl", "ObjectId"]
TABLES = ["federal_states", "manufacturers", "pack_metadata", "reference_dates", "source_files", "source_registry", "stock_observations", "trade_names", "type_keys"]
INDEXES = ["idx_kba_stock_manufacturer", "idx_kba_stock_trade_name", "idx_kba_stock_type_key", "idx_kba_stock_report_date", "idx_kba_stock_make_trade_date", "idx_kba_stock_federal_state"]
HASH_METHOD = "SHA-256 of canonical JSON over the original parsed CSV field strings without trimming; source column names retained; JSON keys sorted."

def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

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

def normalize_label(value: str) -> str:
    return " ".join(value.strip().split()).casefold()

def parse_date(raw: str) -> str:
    return datetime.strptime(raw.strip(), "%d.%m.%Y").date().isoformat()

def parse_int(raw: str, field: str, row_number: int) -> int | None:
    value = (raw or "").strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"Invalid integer in {field} at source row {row_number}: {value!r}") from exc

def verify_source(source_csv: Path, source_manifest_path: Path):
    manifest_bytes = source_manifest_path.read_bytes()
    source = json.loads(manifest_bytes.decode("utf-8-sig"))
    if source.get("source_id") != SOURCE_ID:
        raise ValueError("KBA source_id mismatch")
    rights = source.get("rights") or {}
    if rights.get("rights_status") != "approved_by_published_DL_DE_BY_2_0":
        raise ValueError("KBA rights status is not cleared by the published licence")
    for key in ("commercial_use_allowed", "display_allowed", "offline_cache_allowed", "bulk_reuse_allowed", "redistribution_allowed", "attribution_required"):
        if rights.get(key) is not True:
            raise ValueError(f"KBA licence permission/condition missing: {key}")
    snapshot = source.get("snapshot") or {}
    if snapshot.get("status") != "source_snapshot_acquired_schema_verified" or snapshot.get("downloaded") is not True:
        raise ValueError("KBA source snapshot is not acquired and schema-verified")
    expected_hash = snapshot.get("source_snapshot_sha256") or snapshot.get("file_sha256")
    actual_hash = sha256_file(source_csv)
    if not expected_hash or actual_hash != expected_hash:
        raise ValueError("KBA source CSV SHA-256 differs from the reviewed source manifest")
    if source_csv.stat().st_size != snapshot.get("file_bytes"):
        raise ValueError("KBA source CSV byte size differs from the reviewed source manifest")
    labels = [str(x) for x in snapshot.get("vag_manufacturer_labels", [])]
    if {normalize_label(x) for x in labels} != EXACT_LABELS or len(labels) != len(EXACT_LABELS):
        raise ValueError("KBA exact VAG manufacturer allowlist differs from the reviewed source manifest")
    if snapshot.get("observed_columns") != COLUMNS:
        raise ValueError("KBA observed CSV columns differ from the reviewed source manifest")
    return source, actual_hash, sha256_bytes(manifest_bytes)

def create_schema(db: sqlite3.Connection):
    db.executescript("""
    PRAGMA foreign_keys=ON;
    CREATE TABLE pack_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
    CREATE TABLE source_registry (
      source_id TEXT PRIMARY KEY, publisher TEXT NOT NULL, dataset_title TEXT NOT NULL,
      dataset_uri TEXT NOT NULL, resource_uri TEXT NOT NULL, license_id TEXT NOT NULL,
      license_uri TEXT NOT NULL, rights_status TEXT NOT NULL,
      commercial_use_allowed INTEGER NOT NULL CHECK(commercial_use_allowed=1),
      display_allowed INTEGER NOT NULL CHECK(display_allowed=1),
      offline_cache_allowed INTEGER NOT NULL CHECK(offline_cache_allowed=1),
      bulk_reuse_allowed INTEGER NOT NULL CHECK(bulk_reuse_allowed=1),
      redistribution_allowed INTEGER NOT NULL CHECK(redistribution_allowed=1),
      attribution_required INTEGER NOT NULL CHECK(attribution_required=1),
      attribution_text TEXT NOT NULL, market_scope TEXT NOT NULL CHECK(market_scope='DE'),
      applicability_precision TEXT NOT NULL CHECK(applicability_precision='aggregate_stock_observation'),
      review_status TEXT NOT NULL CHECK(review_status='research_only'),
      source_revision TEXT NOT NULL, source_manifest_sha256 TEXT NOT NULL, source_snapshot_sha256 TEXT NOT NULL,
      product_import_allowed INTEGER NOT NULL CHECK(product_import_allowed=0),
      production_fitment INTEGER NOT NULL CHECK(production_fitment=0),
      individual_vehicle_fitment INTEGER NOT NULL CHECK(individual_vehicle_fitment=0),
      exact_vehicle_fitment INTEGER NOT NULL CHECK(exact_vehicle_fitment=0),
      model_year_inferred INTEGER NOT NULL CHECK(model_year_inferred=0),
      generation_inferred INTEGER NOT NULL CHECK(generation_inferred=0),
      engine_codes_included INTEGER NOT NULL CHECK(engine_codes_included=0),
      gearbox_codes_included INTEGER NOT NULL CHECK(gearbox_codes_included=0),
      exact_engine_gearbox_pair INTEGER NOT NULL CHECK(exact_engine_gearbox_pair=0),
      ecu_fitment INTEGER NOT NULL CHECK(ecu_fitment=0),
      dtc_fitment INTEGER NOT NULL CHECK(dtc_fitment=0),
      repair_applicability INTEGER NOT NULL CHECK(repair_applicability=0),
      ru_eaeu_applicability INTEGER NOT NULL CHECK(ru_eaeu_applicability=0)
    );
    CREATE TABLE source_files (
      source_file_id TEXT PRIMARY KEY, source_id TEXT NOT NULL REFERENCES source_registry(source_id),
      file_name TEXT NOT NULL, source_revision TEXT NOT NULL, sha256 TEXT NOT NULL,
      byte_size INTEGER NOT NULL, source_row_count INTEGER NOT NULL, filtered_row_count INTEGER NOT NULL,
      columns_json TEXT NOT NULL, columns_sha256 TEXT NOT NULL, downloaded_at_utc TEXT NOT NULL
    );
    CREATE TABLE manufacturers (id INTEGER PRIMARY KEY, source_value TEXT NOT NULL UNIQUE);
    CREATE TABLE trade_names (id INTEGER PRIMARY KEY, source_value TEXT NOT NULL UNIQUE);
    CREATE TABLE type_keys (id INTEGER PRIMARY KEY, source_value TEXT NOT NULL UNIQUE);
    CREATE TABLE federal_states (id INTEGER PRIMARY KEY, source_value TEXT NOT NULL UNIQUE);
    CREATE TABLE reference_dates (id INTEGER PRIMARY KEY, source_value TEXT NOT NULL UNIQUE, iso_date TEXT NOT NULL UNIQUE);
    CREATE TABLE stock_observations (
      source_row_number INTEGER PRIMARY KEY, source_object_id TEXT NOT NULL UNIQUE,
      report_date_id INTEGER NOT NULL REFERENCES reference_dates(id),
      manufacturer_id INTEGER NOT NULL REFERENCES manufacturers(id),
      trade_name_id INTEGER NOT NULL REFERENCES trade_names(id),
      type_key_id INTEGER NOT NULL REFERENCES type_keys(id),
      federal_state_id INTEGER NOT NULL REFERENCES federal_states(id),
      vehicle_count INTEGER NOT NULL CHECK(vehicle_count>=0), zs_count_raw TEXT NOT NULL,
      source_record_sha256 TEXT NOT NULL CHECK(length(source_record_sha256)=64)
    );
    CREATE INDEX idx_kba_stock_manufacturer ON stock_observations(manufacturer_id);
    CREATE INDEX idx_kba_stock_trade_name ON stock_observations(trade_name_id);
    CREATE INDEX idx_kba_stock_type_key ON stock_observations(type_key_id);
    CREATE INDEX idx_kba_stock_report_date ON stock_observations(report_date_id);
    CREATE INDEX idx_kba_stock_make_trade_date ON stock_observations(manufacturer_id,trade_name_id,report_date_id);
    CREATE INDEX idx_kba_stock_federal_state ON stock_observations(federal_state_id);
    CREATE VIEW v_stock_observations AS
      SELECT o.source_row_number, o.source_object_id, d.source_value AS report_date_raw, d.iso_date AS report_date_iso,
        m.source_value AS manufacturer_raw, t.source_value AS trade_name_raw, k.source_value AS type_key_raw,
        s.source_value AS federal_state_raw, o.vehicle_count, o.zs_count_raw, o.source_record_sha256,
        r.source_id, r.source_revision, r.source_manifest_sha256, r.source_snapshot_sha256,
        r.market_scope, r.applicability_precision, r.review_status, r.product_import_allowed,
        r.individual_vehicle_fitment, r.exact_vehicle_fitment, r.model_year_inferred, r.generation_inferred,
        r.engine_codes_included, r.gearbox_codes_included, r.exact_engine_gearbox_pair,
        r.ecu_fitment, r.dtc_fitment, r.repair_applicability, r.ru_eaeu_applicability
      FROM stock_observations o
      JOIN reference_dates d ON d.id=o.report_date_id
      JOIN manufacturers m ON m.id=o.manufacturer_id
      JOIN trade_names t ON t.id=o.trade_name_id
      JOIN type_keys k ON k.id=o.type_key_id
      JOIN federal_states s ON s.id=o.federal_state_id
      JOIN source_registry r ON r.source_id=(SELECT source_id FROM source_files LIMIT 1);
    """)

def build(source_csv: Path, source_manifest_path: Path, output_dir: Path, builder_path: Path):
    source, source_hash, source_manifest_hash = verify_source(source_csv, source_manifest_path)
    snapshot = source["snapshot"]
    output_dir.mkdir(parents=True, exist_ok=True)
    db_final = output_dir / "kba-de-vag-stock-research.sqlite"
    db_tmp = output_dir / (db_final.name + ".tmp")
    if db_tmp.exists():
        db_tmp.unlink()
    source_revision = str(snapshot["source_revision"])
    source_rows = filtered_rows = 0
    labels_seen, trade_pairs, type_pairs, dated_tuples, states_seen, dates_seen = set(), set(), set(), set(), set(), set()
    caches = {name: {} for name in ("manufacturers", "trade_names", "type_keys", "federal_states", "reference_dates")}
    batch = []
    columns_hash = sha256_bytes(canonical_bytes(COLUMNS))
    attribution = (
      "Source: Kraftfahrt-Bundesamt (KBA), FZ Hersteller Handelsnamen Pkw, published via GovData/Mobilithek; "
      "Datenlizenz Deutschland – Namensnennung – Version 2.0 (DL-DE BY 2.0); "
      f"{SOURCE_URL}. Modified data: filtered to eight exact KBA manufacturer labels, report dates normalized "
      "to ISO 8601, source-row SHA-256 values added. Aggregate German stock data only; not individual-vehicle fitment."
    )
    def dimension_id(db, table, value, cache):
        if value in cache:
            return cache[value]
        if table == "reference_dates":
            db.execute("INSERT OR IGNORE INTO reference_dates(source_value,iso_date) VALUES (?,?)", (value, parse_date(value)))
        else:
            db.execute(f'INSERT OR IGNORE INTO "{table}"(source_value) VALUES (?)', (value,))
        found = db.execute(f'SELECT id FROM "{table}" WHERE source_value=?', (value,)).fetchone()
        if not found:
            raise RuntimeError(f"Failed to create {table} dimension value")
        cache[value] = int(found[0])
        return cache[value]
    with sqlite3.connect(db_tmp) as db:
        db.execute("PRAGMA page_size=4096")
        db.execute("PRAGMA journal_mode=DELETE")
        db.execute("PRAGMA synchronous=FULL")
        db.execute("PRAGMA foreign_keys=ON")
        create_schema(db)
        db.execute("BEGIN IMMEDIATE")
        db.execute("INSERT INTO source_registry VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
          SOURCE_ID, "Kraftfahrt-Bundesamt (KBA), published via GovData/Mobilithek",
          "FZ Hersteller Handelsnamen Pkw", SOURCE_URL, RESOURCE_URL, LICENSE_ID, LICENSE_URL,
          source["rights"]["rights_status"], 1,1,1,1,1,1,attribution,"DE",
          "aggregate_stock_observation","research_only",source_revision,source_manifest_hash,source_hash,
          0,0,0,0,0,0,0,0,0,0,0,0,0
        ))
        with source_csv.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames != COLUMNS:
                raise ValueError(f"Unexpected KBA columns: {reader.fieldnames!r}")
            for source_rows, row in enumerate(reader, start=1):
                if None in row:
                    raise ValueError(f"Malformed KBA CSV row {source_rows}: extra columns")
                raw = {column: (row.get(column) if row.get(column) is not None else "") for column in COLUMNS}
                manufacturer = raw["Hersteller"]
                if normalize_label(manufacturer) not in EXACT_LABELS:
                    continue
                if not raw["ObjectId"].strip() or not raw["Bundesland"].strip():
                    raise ValueError(f"Missing required KBA source key/state at row {source_rows}")
                report_iso = parse_date(raw["Berichtszeitpunkt"])
                count_value = parse_int(raw["Anzahl"], "Anzahl", source_rows)
                if count_value is None:
                    raise ValueError(f"Missing KBA Anzahl at source row {source_rows}")
                row_hash = sha256_bytes(canonical_bytes(raw))
                ids = [
                  dimension_id(db,"reference_dates",raw["Berichtszeitpunkt"],caches["reference_dates"]),
                  dimension_id(db,"manufacturers",manufacturer,caches["manufacturers"]),
                  dimension_id(db,"trade_names",raw["Handelsname"],caches["trade_names"]),
                  dimension_id(db,"type_keys",raw["Typschlüssel"],caches["type_keys"]),
                  dimension_id(db,"federal_states",raw["Bundesland"],caches["federal_states"])
                ]
                batch.append((source_rows,raw["ObjectId"],*ids,count_value,raw["ZS Anzahl"],row_hash))
                filtered_rows += 1
                labels_seen.add(manufacturer)
                trade_pairs.add((manufacturer,raw["Handelsname"]))
                type_pairs.add((manufacturer,raw["Typschlüssel"]))
                dated_tuples.add((report_iso,manufacturer,raw["Handelsname"],raw["Typschlüssel"]))
                states_seen.add(raw["Bundesland"])
                dates_seen.add(report_iso)
                if len(batch)>=10000:
                    db.executemany("INSERT INTO stock_observations VALUES (?,?,?,?,?,?,?,?,?,?)",batch)
                    batch.clear()
            if batch:
                db.executemany("INSERT INTO stock_observations VALUES (?,?,?,?,?,?,?,?,?,?)",batch)
        db.execute("INSERT INTO source_files VALUES (?,?,?,?,?,?,?,?,?,?,?)", (
          "kba-fz-hersteller-handelsnamen-pkw-csv",SOURCE_ID,source_csv.name,source_revision,source_hash,
          source_csv.stat().st_size,source_rows,filtered_rows,json.dumps(COLUMNS,ensure_ascii=False),
          columns_hash,snapshot.get("downloaded_at_utc","")
        ))
        counts = {
          "source_rows":source_rows,"vag_stock_observations":filtered_rows,
          "manufacturer_labels":len(labels_seen),"unique_make_trade_name_pairs":len(trade_pairs),
          "unique_make_type_key_pairs":len(type_pairs),
          "unique_make_trade_type_reference_date_tuples":len(dated_tuples),
          "federal_states":len(states_seen),"reference_dates":sorted(dates_seen),
          "dimension_counts":{name:len(cache) for name,cache in caches.items()}
        }
        expected = {
          "source_rows":snapshot.get("source_row_count"),
          "vag_stock_observations":snapshot.get("filtered_vag_row_count"),
          "manufacturer_labels":snapshot.get("manufacturer_label_count"),
          "unique_make_trade_name_pairs":snapshot.get("unique_make_trade_name_pairs"),
          "unique_make_type_key_pairs":snapshot.get("unique_make_type_key_pairs"),
          "unique_make_trade_type_reference_date_tuples":snapshot.get("unique_make_trade_type_reference_date_tuples"),
          "federal_states":snapshot.get("unique_federal_states")
        }
        for key, value in expected.items():
            if value is not None and counts[key] != value:
                raise ValueError(f"KBA source count mismatch for {key}: {counts[key]} != {value}")
        coverage = snapshot.get("temporal_coverage_observed")
        if coverage is not None and coverage != [counts["reference_dates"][0], counts["reference_dates"][-1]]:
            raise ValueError("KBA observed temporal coverage differs from the acquired source")
        metadata = {
          "schema_version":1,"pack_id":PACK_ID,"source_id":SOURCE_ID,"market_scope":"DE",
          "license_id":LICENSE_ID,"source_snapshot_sha256":source_hash,
          "source_manifest_sha256":source_manifest_hash,"source_revision":source_revision,
          "counts":counts,"production_import":False,"ru_eaeu_applicability":False,
          "exact_vehicle_fitment":False,"exact_engine_gearbox_pair":False
        }
        for key,value in metadata.items():
            db.execute("INSERT INTO pack_metadata(key,value) VALUES (?,?)",(key,json.dumps(value,ensure_ascii=False,sort_keys=True)))
        db.commit()
        if db.execute("PRAGMA integrity_check").fetchone()[0]!="ok":
            raise RuntimeError("SQLite integrity_check failed")
        if db.execute("PRAGMA foreign_key_check").fetchall():
            raise RuntimeError("SQLite foreign_key_check failed")
        if db.execute("SELECT count(*) FROM v_stock_observations WHERE market_scope!='DE' OR review_status!='research_only' OR exact_engine_gearbox_pair!=0 OR ru_eaeu_applicability!=0").fetchone()[0]:
            raise RuntimeError("KBA view crossed its research-only applicability boundary")
    db.close()
    with sqlite3.connect(db_tmp) as db:
        db.execute("VACUUM")
    db.close()
    os.replace(db_tmp,db_final)
    database_hash=sha256_file(db_final)
    source_snapshot_copy=output_dir/"source-snapshot.csv"
    if source_csv.resolve()!=source_snapshot_copy.resolve():
        shutil.copyfile(source_csv,source_snapshot_copy)
    manifest = {
      "schema_version":1,"pack_id":PACK_ID,"source_id":SOURCE_ID,"status":"verified_research_only",
      "publisher":"Kraftfahrt-Bundesamt (KBA), published via GovData/Mobilithek",
      "dataset_title":"FZ Hersteller Handelsnamen Pkw","source_url":SOURCE_URL,"resource_url":RESOURCE_URL,
      "license":LICENSE_ID,"license_url":LICENSE_URL,"rights_status":source["rights"]["rights_status"],
      "commercial_use_allowed":True,"display_allowed":True,"offline_cache_allowed":True,
      "bulk_reuse_allowed":True,"redistribution_allowed":True,"attribution_required":True,
      "attribution":attribution,"market_scope":["DE"],"applicability_precision":"aggregate_stock_observation",
      "review_status":"research_only","source_revision":source_revision,
      "source_snapshot_sha256":source_hash,"source_manifest_sha256":source_manifest_hash,
      "source_file":{"name":source_snapshot_copy.name,"sha256":source_hash,"byte_size":source_snapshot_copy.stat().st_size,
        "row_count":source_rows,"filtered_vag_row_count":filtered_rows,"columns":COLUMNS,"columns_sha256":columns_hash},
      "database":{"path":db_final.name,"sha256":database_hash,"byte_size":db_final.stat().st_size},
      "counts":counts,"exact_vag_manufacturer_labels":sorted(labels_seen),
      "production_import":False,"product_import_allowed":False,"data_ingested":False,
      "ru_eaeu_applicability":False,"individual_vehicle_fitment":False,"exact_vehicle_fitment":False,
      "model_year_inferred":False,"generation_inferred":False,"engine_codes_included":False,
      "gearbox_codes_included":False,"exact_engine_gearbox_pair":False,"ecu_fitment":False,
      "dtc_fitment":False,"repair_applicability":False,"diagnostic_execution_allowed":False,
      "search_indexes":INDEXES,"build_script_sha256":sha256_file(builder_path),
      "source_record_hash_method":HASH_METHOD,"generated_at_utc":datetime.now(timezone.utc).isoformat(),
      "limitations":[
        "Aggregate German passenger-car stock observations only; not individual vehicles or vehicle build sheets.",
        "Typschlüssel is preserved verbatim as a raw KBA type-key field; it is not promoted to HSN or confirmed TSN.",
        "Berichtszeitpunkt is the annual stock reference date, not model year or generation.",
        "Anzahl is an aggregate stock count; ZS Anzahl is preserved raw and was blank in the acquired snapshot.",
        "No engine code, gearbox code, engine/gearbox pair, ECU, DTC, repair procedure or exact vehicle fitment is supplied.",
        "No Russian/EAEU applicability is inferred."
      ]
    }
    (output_dir/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (output_dir/"source-manifest.json").write_bytes(source_manifest_path.read_bytes())
    (output_dir/"ATTRIBUTION.md").write_text("# KBA data attribution\n\n"+attribution+"\n",encoding="utf-8")
    (output_dir/"LICENSE.txt").write_text(
      "Data licence Germany – attribution – Version 2.0 (DL-DE BY 2.0)\nOfficial licence: "+LICENSE_URL+"\n"
      "Commercial and non-commercial copying, processing, redistribution and product integration are permitted subject to provider attribution, dataset URI and a notice for modifications. See the official licence text.\n",
      encoding="utf-8"
    )
    report={"status":"verified_research_only","pack_id":PACK_ID,"source_snapshot_sha256":source_hash,
      "source_manifest_sha256":source_manifest_hash,"database_sha256":database_hash,"counts":counts,
      "integrity_check":"ok","product_import_allowed":False,"exact_engine_gearbox_pair_claim":False,
      "ru_eaeu_applicability":False}
    (output_dir/"build-report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return manifest

def verify(output_dir: Path):
    manifest=read_json(output_dir/"manifest.json")
    db_path=output_dir/manifest["database"]["path"]
    source_manifest_path=output_dir/"source-manifest.json"
    source_csv=output_dir/manifest["source_file"]["name"]
    source,source_hash,source_manifest_hash=verify_source(source_csv,source_manifest_path)
    if sha256_file(db_path)!=manifest["database"]["sha256"]:
        raise ValueError("KBA SQLite SHA-256 mismatch")
    if source_hash!=manifest["source_snapshot_sha256"] or source_manifest_hash!=manifest["source_manifest_sha256"]:
        raise ValueError("KBA source snapshot/source manifest provenance mismatch")
    if source_csv.stat().st_size!=manifest["source_file"]["byte_size"]:
        raise ValueError("KBA source snapshot byte-size mismatch")
    if manifest.get("source_record_hash_method")!=HASH_METHOD:
        raise ValueError("KBA source-record hash method is not documented")
    if manifest.get("status")!="verified_research_only" or manifest.get("market_scope")!=["DE"]:
        raise ValueError("KBA pack status/market scope mismatch")
    for key in ("production_import","product_import_allowed","data_ingested","ru_eaeu_applicability",
      "individual_vehicle_fitment","exact_vehicle_fitment","model_year_inferred","generation_inferred",
      "engine_codes_included","gearbox_codes_included","exact_engine_gearbox_pair","ecu_fitment",
      "dtc_fitment","repair_applicability","diagnostic_execution_allowed"):
        if manifest.get(key) is not False:
            raise ValueError(f"KBA pack boundary failed: {key}")
    with sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro",uri=True) as db:
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA integrity_check").fetchone()[0]!="ok":
            raise ValueError("KBA SQLite integrity_check failed")
        tables=sorted(r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"))
        if tables!=sorted(TABLES):
            raise ValueError(f"KBA table set mismatch: {tables}")
        indexes={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='index'")}
        if not set(INDEXES).issubset(indexes):
            raise ValueError("KBA indexes missing")
        views={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='view'")}
        if "v_stock_observations" not in views:
            raise ValueError("KBA provenance view missing")
        counts={
          "source_rows":db.execute("SELECT source_row_count FROM source_files").fetchone()[0],
          "vag_stock_observations":db.execute("SELECT count(*) FROM stock_observations").fetchone()[0],
          "manufacturer_labels":db.execute("SELECT count(*) FROM manufacturers").fetchone()[0],
          "unique_make_trade_name_pairs":db.execute("SELECT count(*) FROM (SELECT 1 FROM stock_observations GROUP BY manufacturer_id,trade_name_id)").fetchone()[0],
          "unique_make_type_key_pairs":db.execute("SELECT count(*) FROM (SELECT 1 FROM stock_observations GROUP BY manufacturer_id,type_key_id)").fetchone()[0],
          "unique_make_trade_type_reference_date_tuples":db.execute("SELECT count(*) FROM (SELECT 1 FROM stock_observations GROUP BY report_date_id,manufacturer_id,trade_name_id,type_key_id)").fetchone()[0],
          "federal_states":db.execute("SELECT count(*) FROM federal_states").fetchone()[0],
          "reference_dates":[r[0] for r in db.execute("SELECT iso_date FROM reference_dates ORDER BY iso_date")],
          "dimension_counts":{
            "manufacturers":db.execute("SELECT count(*) FROM manufacturers").fetchone()[0],
            "trade_names":db.execute("SELECT count(*) FROM trade_names").fetchone()[0],
            "type_keys":db.execute("SELECT count(*) FROM type_keys").fetchone()[0],
            "federal_states":db.execute("SELECT count(*) FROM federal_states").fetchone()[0],
            "reference_dates":db.execute("SELECT count(*) FROM reference_dates").fetchone()[0]
          }
        }
        if counts!=manifest["counts"]:
            raise ValueError(f"KBA SQLite counts mismatch: {counts}")
        registry=db.execute("SELECT source_id,license_id,rights_status,market_scope,applicability_precision,review_status,source_revision,source_manifest_sha256,source_snapshot_sha256,product_import_allowed,exact_engine_gearbox_pair,ru_eaeu_applicability FROM source_registry").fetchone()
        expected_registry=(SOURCE_ID,LICENSE_ID,source["rights"]["rights_status"],"DE","aggregate_stock_observation","research_only",
          str(source["snapshot"]["source_revision"]),source_manifest_hash,source_hash,0,0,0)
        if not registry or tuple(registry)!=expected_registry:
            raise ValueError("KBA SQLite source registry provenance/scope mismatch")
        file_row=db.execute("SELECT source_id,sha256,byte_size,source_row_count,filtered_row_count,columns_sha256 FROM source_files").fetchone()
        expected_file=(SOURCE_ID,source_hash,source_csv.stat().st_size,counts["source_rows"],counts["vag_stock_observations"],sha256_bytes(canonical_bytes(COLUMNS)))
        if not file_row or tuple(file_row)!=expected_file:
            raise ValueError("KBA SQLite source file registry mismatch")
        invalid=db.execute("""
          SELECT count(*) FROM v_stock_observations
          WHERE market_scope!='DE' OR applicability_precision!='aggregate_stock_observation'
          OR review_status!='research_only' OR individual_vehicle_fitment!=0 OR exact_vehicle_fitment!=0
          OR model_year_inferred!=0 OR generation_inferred!=0 OR engine_codes_included!=0
          OR gearbox_codes_included!=0 OR exact_engine_gearbox_pair!=0 OR ecu_fitment!=0
          OR dtc_fitment!=0 OR repair_applicability!=0 OR ru_eaeu_applicability!=0
        """).fetchone()[0]
        if invalid:
            raise ValueError("KBA rows contain an invalid fitment/applicability claim")
        observation_cursor=db.execute("SELECT source_row_number,source_object_id,source_record_sha256 FROM stock_observations ORDER BY source_row_number")
        with source_csv.open("r",encoding="utf-8-sig",newline="") as stream:
            reader=csv.DictReader(stream)
            for row_number,source_row in enumerate(reader,start=1):
                raw={column:(source_row.get(column) if source_row.get(column) is not None else "") for column in COLUMNS}
                if normalize_label(raw["Hersteller"]) not in EXACT_LABELS:
                    continue
                observed=observation_cursor.fetchone()
                expected_hash=sha256_bytes(canonical_bytes(raw))
                if observed is None or observed[0]!=row_number or observed[1]!=raw["ObjectId"] or observed[2]!=expected_hash:
                    raise ValueError(f"KBA row provenance mismatch at source row {row_number}")
        if observation_cursor.fetchone() is not None:
            raise ValueError("KBA SQLite contains extra stock rows")
        if db.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND lower(name) LIKE '%pair%'").fetchone()[0]:
            raise ValueError("KBA pack must not contain an engine/gearbox pair table")
    return {"status":"verified_research_only","counts":counts,"database_sha256":manifest["database"]["sha256"]}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--csv",type=Path)
    parser.add_argument("--source-manifest",type=Path)
    parser.add_argument("--output-dir",type=Path,required=True)
    parser.add_argument("--builder",type=Path,default=Path(__file__))
    parser.add_argument("--verify-only",action="store_true")
    args=parser.parse_args()
    if args.verify_only:
        print(json.dumps(verify(args.output_dir),ensure_ascii=False,indent=2))
        return 0
    if not args.csv or not args.source_manifest:
        parser.error("--csv and --source-manifest are required unless --verify-only is used")
    result=build(args.csv,args.source_manifest,args.output_dir,args.builder)
    print(json.dumps({"status":result["status"],"counts":result["counts"],"database":result["database"]},ensure_ascii=False,indent=2))
    print(json.dumps(verify(args.output_dir),ensure_ascii=False,indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
