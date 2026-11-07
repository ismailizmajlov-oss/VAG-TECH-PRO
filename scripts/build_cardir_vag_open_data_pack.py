#!/usr/bin/env python3
"""Acquire and build a fail-closed CarDir CC BY 4.0 VAG owner-manual facts pack."""
from __future__ import annotations
import argparse, csv, hashlib, json, os, re, shutil, sqlite3, tempfile, urllib.request
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

SOURCE_ID = "cardir-vag-owner-manual-facts-cc-by-4.0"
PACK_ID = "cardir-vag-owner-manual-facts-research"
DATA_URL = "https://cardir.ru/dannye/cardir-zapravochnye-obemy.csv"
DATA_PAGE_URL = "https://cardir.ru/dannye/"
LICENSE_ID = "CC-BY-4.0"
LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"
COLUMNS = ["brand","model","key","key_label_ru","qualifier","value","unit","source_title","source_page","source_url","page_url","verified_at"]
ALLOWED_BRANDS = {"audi","volkswagen","volkswagen commercial vehicles","volkswagen nutzfahrzeuge","skoda","škoda","seat","cupra","porsche","bentley","lamborghini","vw"}
MAX_DOWNLOAD_BYTES = 32 * 1024 * 1024
MAX_ROWS = 100_000
VIN_RE = re.compile(r"(?<![A-HJ-NPR-Z0-9])[A-HJ-NPR-Z0-9]{17}(?![A-HJ-NPR-Z0-9])", re.I)
KEY_RE = re.compile(r"^[a-z0-9_]+$")
ALLOWED_HOSTS = {"cardir.ru","www.cardir.ru"}
TABLES = {"pack_metadata","source_registry","source_files","brands","models","facts"}


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",",":"), allow_nan=False).encode("utf-8")


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    info = path.lstat()
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Expected a regular non-symlink JSON file: {path}")
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def validate_cardir_url(value: str) -> None:
    try:
        parts = urlsplit(value)
        port = parts.port
    except ValueError as exc:
        raise ValueError(f"Malformed source URL: {value!r}") from exc
    if parts.scheme != "https" or parts.hostname not in ALLOWED_HOSTS or parts.username is not None or parts.password is not None or port not in (None,443) or not parts.path.startswith("/"):
        raise ValueError(f"URL must remain on the official CarDir HTTPS host: {value!r}")


def normalize_brand(value: str) -> str:
    return " ".join(value.strip().split()).casefold()


def is_vag_brand(value: str) -> bool:
    return normalize_brand(value) in ALLOWED_BRANDS


def validate_rights(source: dict[str, Any]) -> None:
    if source.get("source_id") != SOURCE_ID or source.get("publisher") != "CarDir":
        raise ValueError("CarDir source identity mismatch")
    urls = source.get("source_urls") or {}
    if urls.get("csv") != DATA_URL or urls.get("dataset_page") != DATA_PAGE_URL:
        raise ValueError("CarDir source URL mismatch")
    rights = source.get("rights") or {}
    if rights.get("rights_status") != "approved_by_published_CC_BY_4_0" or rights.get("permission_status") != "not_required_under_published_CC_BY_4_0":
        raise ValueError("CarDir data rights are not cleared by the reviewed published licence")
    if rights.get("license_id") != LICENSE_ID or rights.get("license_url") != LICENSE_URL:
        raise ValueError("CarDir data licence identifier/URL mismatch")
    for field in ("commercial_use_allowed","display_allowed","offline_cache_allowed","bulk_reuse_allowed","redistribution_allowed","attribution_required"):
        if rights.get(field) is not True:
            raise ValueError(f"CarDir permission/attribution field missing: {field}")
    if not isinstance(rights.get("attribution_text"),str) or "cardir.ru/dannye" not in rights["attribution_text"]:
        raise ValueError("CarDir attribution text is missing")
    policy = source.get("applicability_policy") or {}
    for field in ("exact_engine_code_mapping","exact_gearbox_code_mapping","exact_engine_gearbox_pair","model_generation_inferred","model_year_inferred","exact_vehicle_fitment","ru_eaeu_applicability","ecu_fitment","dtc_fitment","wiring_or_pinout_content","repair_procedure_content","production_fitment"):
        if policy.get(field) is not False:
            raise ValueError(f"CarDir applicability boundary must be false: {field}")
    if policy.get("market_scope") != "UNKNOWN":
        raise ValueError("CarDir market scope must remain UNKNOWN")
    data_scope=source.get("data_scope") or {}
    manifest_allowlist={normalize_brand(value) for value in data_scope.get("vag_brand_allowlist",[])}
    if manifest_allowlist != ALLOWED_BRANDS:
        raise ValueError("CarDir exact VAG brand allowlist differs between source manifest and builder")
    import_policy = source.get("import_policy") or {}
    if import_policy.get("research_pack_allowed") is not True or import_policy.get("production_import") is not False or import_policy.get("product_database_ingested") is not False or import_policy.get("product_import_allowed") is not False:
        raise ValueError("CarDir import policy must remain research-only")


def validate_row(row: dict[str,str], row_number: int, retrieved_date: date | None = None) -> None:
    for field in ("brand","model","key","key_label_ru","value","source_title","source_page","source_url","page_url","verified_at"):
        if not row[field].strip():
            raise ValueError(f"Required CarDir field {field!r} is empty at source line {row_number}")
    if not KEY_RE.fullmatch(row["key"].strip()):
        raise ValueError(f"Invalid CarDir parameter key at source line {row_number}")
    validate_cardir_url(row["source_url"])
    validate_cardir_url(row["page_url"])
    try:
        verified = date.fromisoformat(row["verified_at"].strip())
    except ValueError as exc:
        raise ValueError(f"Invalid verified_at date at source line {row_number}") from exc
    if retrieved_date and verified > retrieved_date:
        raise ValueError(f"CarDir verified_at date is in the future at source line {row_number}")
    if VIN_RE.search(" ".join(row.values())):
        raise ValueError(f"VIN-like identifier found in CarDir row {row_number}; refusing to ingest")


def read_csv_rows(path: Path, retrieved_date: date | None = None) -> tuple[list[dict[str,str]],dict[str,Any]]:
    info = path.lstat()
    if path.is_symlink() or not path.is_file() or info.st_size <= 0 or info.st_size > MAX_DOWNLOAD_BYTES:
        raise ValueError("CSV input is not a regular file or exceeds the size limit")
    rows=[]; all_models=set(); vag_rows=[]; vag_models=set(); brands=set(); verified=[]
    with path.open("r",encoding="utf-8-sig",newline="") as stream:
        reader=csv.DictReader(stream,delimiter=",",strict=True)
        if reader.fieldnames != COLUMNS:
            raise ValueError(f"CarDir CSV columns differ from reviewed schema: {reader.fieldnames!r}")
        for row_number,incoming in enumerate(reader,start=2):
            if row_number > MAX_ROWS+1 or None in incoming or any(not isinstance(incoming.get(k),str) for k in COLUMNS):
                raise ValueError(f"Malformed or oversized CarDir CSV row at line {row_number}")
            raw={key:incoming[key] for key in COLUMNS}
            validate_row(raw,row_number,retrieved_date)
            rows.append(raw); brands.add(raw["brand"]); all_models.add((raw["brand"],raw["model"])); verified.append(raw["verified_at"])
            if is_vag_brand(raw["brand"]):
                vag_rows.append((row_number,raw)); vag_models.add((raw["brand"],raw["model"]))
    if not rows or not vag_rows:
        raise ValueError("CarDir CSV has no rows or no exact VAG-brand rows")
    summary={
        "source_row_count":len(rows),
        "model_count":len(all_models),
        "vag_row_count":len(vag_rows),
        "vag_model_count":len(vag_models),
        "vag_brand_values":sorted({r["brand"] for _,r in vag_rows},key=str.casefold),
        "all_brand_values":sorted(brands,key=str.casefold),
        "verified_at_min":min(verified),
        "verified_at_max":max(verified),
        "columns":COLUMNS,
        "columns_sha256":sha256_bytes(canonical_bytes(COLUMNS)),
    }
    return rows,summary


def inspect_csv(path: Path, source: dict[str,Any], retrieved_date: date | None = None):
    rows,summary=read_csv_rows(path,retrieved_date)
    expected=source.get("snapshot") or {}
    if summary["source_row_count"] != expected.get("expected_source_row_count") or summary["model_count"] != expected.get("expected_model_count"):
        raise ValueError(
            "CarDir live CSV differs from the reviewed publisher snapshot: "
            f"observed rows={summary['source_row_count']} (expected {expected.get('expected_source_row_count')}), "
            f"observed brand/model pairs={summary['model_count']} (expected {expected.get('expected_model_count')}), "
            f"VAG rows={summary['vag_row_count']}, VAG models={summary['vag_model_count']}"
        )
    return rows,summary


class CardirRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        validate_cardir_url(newurl)
        return super().redirect_request(req,fp,code,msg,headers,newurl)


def acquire(source_manifest_path: Path,output_dir: Path) -> dict[str,Any]:
    source=read_json(source_manifest_path); validate_rights(source)
    source_raw=source_manifest_path.read_bytes()
    if output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite acquisition directory: {output_dir}")
    output_dir.parent.mkdir(parents=True,exist_ok=True); output_dir.mkdir()
    temp_path=output_dir/".source.csv.download"; final_path=output_dir/"source.csv"
    try:
        request=urllib.request.Request(DATA_URL,headers={"User-Agent":"VAG-TECH-PRO-licensed-research-pack/1.0","Accept":"text/csv,application/octet-stream;q=0.9,*/*;q=0.1"})
        opener=urllib.request.build_opener(CardirRedirectHandler())
        with opener.open(request,timeout=60) as response:
            if getattr(response,"status",200)!=200:
                raise ValueError("CarDir CSV did not return HTTP 200")
            validate_cardir_url(response.geturl())
            content_type=(response.headers.get("Content-Type") or "").lower()
            if "text/html" in content_type or "application/json" in content_type:
                raise ValueError(f"Unexpected CarDir CSV content type: {content_type}")
            length=response.headers.get("Content-Length")
            if length and int(length)>MAX_DOWNLOAD_BYTES:
                raise ValueError("CarDir CSV Content-Length exceeds safety limit")
            total=0
            with temp_path.open("xb") as output:
                while True:
                    chunk=response.read(1024*1024)
                    if not chunk: break
                    total+=len(chunk)
                    if total>MAX_DOWNLOAD_BYTES: raise ValueError("CarDir CSV exceeded streaming size limit")
                    output.write(chunk)
                output.flush(); os.fsync(output.fileno())
        if total<=0: raise ValueError("CarDir CSV download is empty")
        os.replace(temp_path,final_path)
        retrieved=datetime.now(timezone.utc)
        rows,summary=read_csv_rows(final_path,retrieved.date())
        snapshot={
            "schema_version":1,"source_id":SOURCE_ID,"source_file":"source.csv",
            "source_url":DATA_URL,"data_page_url":DATA_PAGE_URL,"source_revision":source["data_revision"],
            "data_updated_at":source["snapshot"]["expected_data_updated_at"],
            "retrieved_at_utc":retrieved.isoformat(),"source_manifest_sha256":sha256_bytes(source_raw),
            "source_snapshot_sha256":sha256_file(final_path),"source_file_bytes":final_path.stat().st_size,
            **summary
        }
        # Persist the observed snapshot before enforcing the reviewed counts. If the
        # publisher changes the file, CI can retain this probe evidence without building a pack.
        write_json(output_dir/"snapshot.json",snapshot)
        expected=source["snapshot"]
        if summary["source_row_count"]!=expected.get("expected_source_row_count") or summary["model_count"]!=expected.get("expected_model_count"):
            raise ValueError(
                "CarDir live CSV differs from the reviewed publisher snapshot: "
                f"observed rows={summary['source_row_count']} (expected {expected.get('expected_source_row_count')}), "
                f"observed brand/model pairs={summary['model_count']} (expected {expected.get('expected_model_count')}), "
                f"VAG rows={summary['vag_row_count']}, VAG models={summary['vag_model_count']}"
            )
        pinned_hash=expected.get("source_snapshot_sha256")
        pinned_bytes=expected.get("source_file_bytes")
        if pinned_hash and snapshot["source_snapshot_sha256"]!=pinned_hash:
            raise ValueError("CarDir live CSV differs from the pinned source snapshot SHA-256")
        if pinned_bytes and snapshot["source_file_bytes"]!=pinned_bytes:
            raise ValueError("CarDir live CSV differs from the pinned source snapshot byte size")
        return {"status":"acquired_schema_verified",**snapshot}
    except Exception:
        if temp_path.exists(): temp_path.unlink()
        # Keep a complete CSV + snapshot as auditable evidence when the only failure
        # is a changed publisher snapshot; remove incomplete/network-error staging.
        if not (final_path.exists() and (output_dir/"snapshot.json").is_file()):
            shutil.rmtree(output_dir,ignore_errors=True)
        raise


def verify_snapshot(csv_path: Path,snapshot_path: Path,source_manifest_path: Path):
    source_raw=source_manifest_path.read_bytes()
    source=read_json(source_manifest_path); validate_rights(source)
    snapshot=read_json(snapshot_path)
    if snapshot.get("source_id")!=SOURCE_ID or snapshot.get("source_url")!=DATA_URL:
        raise ValueError("CarDir snapshot source identity mismatch")
    if snapshot.get("source_manifest_sha256")!=sha256_bytes(source_raw):
        raise ValueError("CarDir source-manifest SHA-256 mismatch")
    pinned_hash=(source.get("snapshot") or {}).get("source_snapshot_sha256")
    pinned_bytes=(source.get("snapshot") or {}).get("source_file_bytes")
    if pinned_hash and snapshot.get("source_snapshot_sha256")!=pinned_hash:
        raise ValueError("CarDir snapshot differs from pinned source SHA-256")
    if pinned_bytes and snapshot.get("source_file_bytes")!=pinned_bytes:
        raise ValueError("CarDir snapshot differs from pinned source byte size")
    if snapshot.get("source_snapshot_sha256")!=sha256_file(csv_path):
        raise ValueError("CarDir source CSV SHA-256 mismatch")
    if snapshot.get("source_file_bytes")!=csv_path.stat().st_size:
        raise ValueError("CarDir source CSV byte-size mismatch")
    retrieved=date.fromisoformat(snapshot["retrieved_at_utc"][:10])
    rows,summary=inspect_csv(csv_path,source,retrieved)
    for key in ("source_row_count","model_count","vag_row_count","vag_model_count","vag_brand_values","columns","columns_sha256","verified_at_min","verified_at_max"):
        if snapshot.get(key)!=summary.get(key):
            raise ValueError(f"CarDir snapshot summary mismatch: {key}")
    return source,snapshot,rows


def create_database(db_path: Path,source: dict[str,Any],snapshot: dict[str,Any],source_manifest_sha256: str,rows: list[dict[str,str]]):
    db=sqlite3.connect(db_path); db.execute("PRAGMA foreign_keys=ON"); db.execute("PRAGMA journal_mode=DELETE"); db.execute("PRAGMA synchronous=FULL")
    try:
        db.executescript("""
        CREATE TABLE pack_metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE source_registry(
          source_id TEXT PRIMARY KEY,publisher TEXT NOT NULL,dataset_url TEXT NOT NULL,data_revision TEXT NOT NULL,
          license_id TEXT NOT NULL,license_url TEXT NOT NULL,rights_status TEXT NOT NULL,
          commercial_use_allowed INTEGER NOT NULL CHECK(commercial_use_allowed=1),
          display_allowed INTEGER NOT NULL CHECK(display_allowed=1),
          offline_cache_allowed INTEGER NOT NULL CHECK(offline_cache_allowed=1),
          bulk_reuse_allowed INTEGER NOT NULL CHECK(bulk_reuse_allowed=1),
          redistribution_allowed INTEGER NOT NULL CHECK(redistribution_allowed=1),
          attribution_required INTEGER NOT NULL CHECK(attribution_required=1),
          attribution_text TEXT NOT NULL,market_scope TEXT NOT NULL CHECK(market_scope='UNKNOWN'),
          applicability_precision TEXT NOT NULL CHECK(applicability_precision='model_and_raw_qualifier_text'),
          research_pack_only INTEGER NOT NULL CHECK(research_pack_only=1),
          production_import INTEGER NOT NULL CHECK(production_import=0),
          exact_vehicle_fitment INTEGER NOT NULL CHECK(exact_vehicle_fitment=0),
          exact_engine_code INTEGER NOT NULL CHECK(exact_engine_code=0),
          exact_gearbox_code INTEGER NOT NULL CHECK(exact_gearbox_code=0),
          exact_engine_gearbox_pair INTEGER NOT NULL CHECK(exact_engine_gearbox_pair=0),
          model_generation INTEGER NOT NULL CHECK(model_generation=0),
          model_year INTEGER NOT NULL CHECK(model_year=0),
          ru_eaeu_applicability INTEGER NOT NULL CHECK(ru_eaeu_applicability=0),
          ecu_fitment INTEGER NOT NULL CHECK(ecu_fitment=0),
          dtc_fitment INTEGER NOT NULL CHECK(dtc_fitment=0),
          repair_procedure INTEGER NOT NULL CHECK(repair_procedure=0)
        );
        CREATE TABLE source_files(
          source_file_id TEXT PRIMARY KEY,source_id TEXT NOT NULL REFERENCES source_registry(source_id),
          file_name TEXT NOT NULL,source_revision TEXT NOT NULL,sha256 TEXT NOT NULL CHECK(length(sha256)=64),
          byte_size INTEGER NOT NULL CHECK(byte_size>0),source_row_count INTEGER NOT NULL CHECK(source_row_count>0),
          filtered_vag_row_count INTEGER NOT NULL CHECK(filtered_vag_row_count>0),
          columns_json TEXT NOT NULL,columns_sha256 TEXT NOT NULL CHECK(length(columns_sha256)=64),
          retrieved_at_utc TEXT NOT NULL
        );
        CREATE TABLE brands(brand_id INTEGER PRIMARY KEY,source_value TEXT NOT NULL UNIQUE);
        CREATE TABLE models(model_id INTEGER PRIMARY KEY,brand_id INTEGER NOT NULL REFERENCES brands(brand_id),source_value TEXT NOT NULL,UNIQUE(brand_id,source_value));
        CREATE TABLE facts(
          source_row_number INTEGER PRIMARY KEY,source_id TEXT NOT NULL REFERENCES source_registry(source_id),
          brand_id INTEGER NOT NULL REFERENCES brands(brand_id),model_id INTEGER NOT NULL REFERENCES models(model_id),
          parameter_key TEXT NOT NULL,parameter_label_ru TEXT NOT NULL,qualifier_raw TEXT NOT NULL,value_raw TEXT NOT NULL,unit_raw TEXT NOT NULL,
          source_title TEXT NOT NULL,source_page TEXT NOT NULL,source_url TEXT NOT NULL,page_url TEXT NOT NULL,verified_at TEXT NOT NULL,
          raw_fields_json TEXT NOT NULL,source_row_sha256 TEXT NOT NULL CHECK(length(source_row_sha256)=64),
          publisher_verification_status TEXT NOT NULL CHECK(publisher_verification_status='publisher_verified'),
          technical_review_status TEXT NOT NULL CHECK(technical_review_status='not_independently_reviewed'),
          market_scope TEXT NOT NULL CHECK(market_scope='UNKNOWN'),
          applicability_precision TEXT NOT NULL CHECK(applicability_precision IN ('model_level_only','model_and_raw_qualifier_text')),
          model_generation TEXT,model_year_from INTEGER,model_year_to INTEGER,engine_code TEXT,transmission_code TEXT,
          exact_engine_gearbox_pair INTEGER NOT NULL CHECK(exact_engine_gearbox_pair=0),
          production_fitment INTEGER NOT NULL CHECK(production_fitment=0),ecu_fitment INTEGER NOT NULL CHECK(ecu_fitment=0),
          dtc_fitment INTEGER NOT NULL CHECK(dtc_fitment=0),repair_procedure INTEGER NOT NULL CHECK(repair_procedure=0)
        );
        CREATE INDEX idx_cardir_facts_brand_model ON facts(brand_id,model_id);
        CREATE INDEX idx_cardir_facts_parameter ON facts(parameter_key);
        CREATE INDEX idx_cardir_facts_qualifier ON facts(qualifier_raw);
        """)
        rights=source["rights"]
        with db:
            db.execute("INSERT INTO source_registry VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(
                SOURCE_ID,"CarDir",DATA_PAGE_URL,source["data_revision"],LICENSE_ID,LICENSE_URL,rights["rights_status"],
                1,1,1,1,1,1,rights["attribution_text"],"UNKNOWN","model_and_raw_qualifier_text",1,0,0,0,0,0,0,0,0,0,0,0
            ))
            db.execute("INSERT INTO source_files VALUES (?,?,?,?,?,?,?,?,?,?,?)",(
                "cardir-owner-manual-facts-csv",SOURCE_ID,"source.csv",source["data_revision"],
                snapshot["source_snapshot_sha256"],snapshot["source_file_bytes"],snapshot["source_row_count"],
                snapshot["vag_row_count"],json.dumps(COLUMNS,ensure_ascii=False,separators=(",",":")),
                snapshot["columns_sha256"],snapshot["retrieved_at_utc"]
            ))
            brand_ids={}; model_ids={}
            for source_row_number,row in enumerate(rows,start=2):
                if not is_vag_brand(row["brand"]): continue
                raw_json=canonical_bytes(row).decode("utf-8"); row_hash=sha256_bytes(raw_json.encode("utf-8"))
                brand=row["brand"]
                if brand not in brand_ids:
                    brand_ids[brand]=int(db.execute("INSERT INTO brands(source_value) VALUES (?)",(brand,)).lastrowid)
                model_key=(brand,row["model"])
                if model_key not in model_ids:
                    model_ids[model_key]=int(db.execute("INSERT INTO models(brand_id,source_value) VALUES (?,?)",(brand_ids[brand],row["model"])).lastrowid)
                precision="model_and_raw_qualifier_text" if row["qualifier"].strip() else "model_level_only"
                db.execute("""INSERT INTO facts(
                  source_row_number,source_id,brand_id,model_id,parameter_key,parameter_label_ru,qualifier_raw,value_raw,unit_raw,
                  source_title,source_page,source_url,page_url,verified_at,raw_fields_json,source_row_sha256,
                  publisher_verification_status,technical_review_status,market_scope,applicability_precision,
                  model_generation,model_year_from,model_year_to,engine_code,transmission_code,
                  exact_engine_gearbox_pair,production_fitment,ecu_fitment,dtc_fitment,repair_procedure
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,NULL,NULL,NULL,NULL,NULL,0,0,0,0,0)""",(
                    source_row_number,SOURCE_ID,brand_ids[brand],model_ids[model_key],row["key"],row["key_label_ru"],
                    row["qualifier"],row["value"],row["unit"],row["source_title"],row["source_page"],row["source_url"],
                    row["page_url"],row["verified_at"],raw_json,row_hash,"publisher_verified","not_independently_reviewed",
                    "UNKNOWN",precision
                ))
            for key,value in {
                "pack_id":PACK_ID,"source_id":SOURCE_ID,"license_id":LICENSE_ID,"market_scope":"UNKNOWN",
                "research_pack_only":"true","production_import":"false","source_snapshot_sha256":snapshot["source_snapshot_sha256"],
                "source_manifest_sha256":source_manifest_sha256
            }.items():
                db.execute("INSERT INTO pack_metadata(key,value) VALUES (?,?)",(key,str(value)))
        if db.execute("PRAGMA integrity_check").fetchone()[0]!="ok" or db.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("CarDir SQLite integrity/foreign-key check failed")
        counts={
            "facts":db.execute("SELECT count(*) FROM facts").fetchone()[0],
            "brands":db.execute("SELECT count(*) FROM brands").fetchone()[0],
            "models":db.execute("SELECT count(*) FROM models").fetchone()[0],
            "parameter_keys":db.execute("SELECT count(DISTINCT parameter_key) FROM facts").fetchone()[0],
            "exact_engine_gearbox_pairs":db.execute("SELECT count(*) FROM facts WHERE exact_engine_gearbox_pair<>0").fetchone()[0],
            "production_fitment_rows":db.execute("SELECT count(*) FROM facts WHERE production_fitment<>0").fetchone()[0]
        }
        if counts["facts"]!=snapshot["vag_row_count"] or counts["exact_engine_gearbox_pairs"] or counts["production_fitment_rows"]:
            raise ValueError("CarDir SQLite row counts or research-only boundary mismatch")
        return counts
    finally:
        db.close()


def build(csv_path: Path,snapshot_path: Path,source_manifest_path: Path,output_dir: Path):
    if output_dir.exists(): raise FileExistsError(f"Refusing to overwrite pack directory: {output_dir}")
    source,snapshot,rows=verify_snapshot(csv_path,snapshot_path,source_manifest_path)
    output_dir.parent.mkdir(parents=True,exist_ok=True)
    staging=Path(tempfile.mkdtemp(prefix=".cardir-vag-pack-",dir=str(output_dir.parent)))
    try:
        shutil.copy2(csv_path,staging/"source.csv")
        shutil.copy2(snapshot_path,staging/"source-snapshot.json")
        shutil.copy2(source_manifest_path,staging/"source-manifest.json")
        counts=create_database(staging/"cardir-vag-owner-manual-facts.sqlite",source,snapshot,sha256_file(source_manifest_path),rows)
        (staging/"LICENSE.txt").write_text("Data licence: CC BY 4.0\nLicence URL: https://creativecommons.org/licenses/by/4.0/\nDataset URL: https://cardir.ru/dannye/\nAttribution: CarDir (https://cardir.ru/dannye/), CC BY 4.0.\n",encoding="utf-8")
        (staging/"ATTRIBUTION.md").write_text("# Attribution\n\nSource: CarDir open data, https://cardir.ru/dannye/\n\nLicence: CC BY 4.0, https://creativecommons.org/licenses/by/4.0/\n\nChanges: filtered to the exact VAG-brand allowlist. Original source field strings, qualifiers, source titles, page locators, CarDir source URLs and verification dates are retained. No model year, generation, exact engine/gearbox code or fitment is inferred.\n",encoding="utf-8")
        key_counts={}
        for row in rows:
            if is_vag_brand(row["brand"]): key_counts[row["key"]]=key_counts.get(row["key"],0)+1
        manifest={
            "schema_version":1,"pack_id":PACK_ID,"source_id":SOURCE_ID,"publisher":"CarDir",
            "source_revision":source["data_revision"],"license":{"id":LICENSE_ID,"url":LICENSE_URL,"attribution_required":True},
            "attribution_file":"ATTRIBUTION.md","license_file":"LICENSE.txt","source_manifest_file":"source-manifest.json",
            "source_snapshot_file":"source-snapshot.json","source_snapshot_sha256":snapshot["source_snapshot_sha256"],
            "source_manifest_sha256":sha256_file(source_manifest_path),"source_file":"source.csv","source_file_bytes":snapshot["source_file_bytes"],
            "database":{"file":"cardir-vag-owner-manual-facts.sqlite","sha256":sha256_file(staging/"cardir-vag-owner-manual-facts.sqlite"),"integrity_check":"ok","foreign_key_violations":0},
            "counts":{"source_rows":snapshot["source_row_count"],"source_models":snapshot["model_count"],"vag_facts":counts["facts"],"vag_brands":counts["brands"],"vag_models":counts["models"],"parameter_keys":counts["parameter_keys"],"parameter_counts":dict(sorted(key_counts.items()))},
            "market_scope":["UNKNOWN"],"applicability_precision":"model_and_raw_qualifier_text",
            "publisher_verification_status":"publisher_verified","technical_review_status":"not_independently_reviewed",
            "research_pack_ingested":True,"product_database_ingested":False,"data_ingested":False,"product_import_allowed":False,
            "production_import":False,"exact_vehicle_fitment":False,"exact_engine_code_mapping":False,"exact_gearbox_code_mapping":False,
            "exact_engine_gearbox_pair":False,"model_generation_inferred":False,"model_year_inferred":False,
            "ru_eaeu_applicability":False,"ecu_fitment":False,"dtc_fitment":False,"repair_procedure":False,"wiring_or_pinout":False,
            "created_at_utc":datetime.now(timezone.utc).isoformat()
        }
        write_json(staging/"manifest.json",manifest)
        verify_pack(staging)
        os.replace(staging,output_dir)
        return verify_pack(output_dir)
    finally:
        if staging.exists(): shutil.rmtree(staging,ignore_errors=True)


def verify_pack(pack_dir: Path):
    if not pack_dir.is_dir() or pack_dir.is_symlink(): raise ValueError("Cardir pack path must be a regular directory")
    manifest=read_json(pack_dir/"manifest.json")
    source_manifest=read_json(pack_dir/"source-manifest.json")
    snapshot=read_json(pack_dir/"source-snapshot.json")
    validate_rights(source_manifest)
    if manifest.get("pack_id")!=PACK_ID or manifest.get("source_id")!=SOURCE_ID: raise ValueError("Cardir pack identity mismatch")
    if manifest.get("market_scope")!=["UNKNOWN"] or manifest.get("product_import_allowed") is not False or manifest.get("production_import") is not False:
        raise ValueError("Cardir pack escaped UNKNOWN-market research-only boundary")
    for key in ("exact_vehicle_fitment","exact_engine_code_mapping","exact_gearbox_code_mapping","exact_engine_gearbox_pair","model_generation_inferred","model_year_inferred","ru_eaeu_applicability","ecu_fitment","dtc_fitment","repair_procedure","wiring_or_pinout"):
        if manifest.get(key) is not False: raise ValueError(f"Cardir pack applicability boundary failed: {key}")
    csv_path=pack_dir/"source.csv"; source_path=pack_dir/"source-manifest.json"; snapshot_path=pack_dir/"source-snapshot.json"
    if sha256_file(csv_path)!=manifest.get("source_snapshot_sha256") or sha256_file(csv_path)!=snapshot.get("source_snapshot_sha256"):
        raise ValueError("Cardir source CSV SHA-256 mismatch")
    if sha256_file(source_path)!=manifest.get("source_manifest_sha256") or snapshot.get("source_manifest_sha256")!=sha256_file(source_path):
        raise ValueError("Cardir source-manifest SHA-256 mismatch")
    _,snapshot,rows=verify_snapshot(csv_path,snapshot_path,source_path)
    db_path=pack_dir/manifest["database"]["file"]
    if sha256_file(db_path)!=manifest["database"]["sha256"]: raise ValueError("Cardir SQLite SHA-256 mismatch")
    db=sqlite3.connect(f"file:{db_path.resolve().as_posix()}?mode=ro",uri=True); db.row_factory=sqlite3.Row
    try:
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA integrity_check").fetchone()[0]!="ok" or db.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("Cardir SQLite integrity/foreign-key check failed")
        tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if tables!=TABLES: raise ValueError("Cardir SQLite table set mismatch")
        facts=db.execute("SELECT source_row_number,raw_fields_json,source_row_sha256 FROM facts ORDER BY source_row_number").fetchall()
        expected=[(n,row) for n,row in enumerate(rows,start=2) if is_vag_brand(row["brand"])]
        if len(facts)!=len(expected) or len(facts)!=manifest["counts"]["vag_facts"]: raise ValueError("Cardir SQLite retained-row parity mismatch")
        for stored,(line,row) in zip(facts,expected):
            raw=canonical_bytes(row).decode("utf-8")
            if stored["source_row_number"]!=line or stored["raw_fields_json"]!=raw or stored["source_row_sha256"]!=sha256_bytes(raw.encode("utf-8")):
                raise ValueError(f"Cardir source-row provenance mismatch at line {line}")
            if VIN_RE.search(stored["raw_fields_json"]): raise ValueError(f"VIN-like data found in retained row {line}")
        bad=db.execute("SELECT count(*) FROM facts WHERE market_scope<>'UNKNOWN' OR technical_review_status<>'not_independently_reviewed' OR publisher_verification_status<>'publisher_verified' OR exact_engine_gearbox_pair<>0 OR production_fitment<>0 OR ecu_fitment<>0 OR dtc_fitment<>0 OR repair_procedure<>0 OR model_generation IS NOT NULL OR model_year_from IS NOT NULL OR model_year_to IS NOT NULL OR engine_code IS NOT NULL OR transmission_code IS NOT NULL").fetchone()[0]
        if bad: raise ValueError("Cardir SQLite applicability boundary failed")
        if db.execute("SELECT count(*) FROM source_registry WHERE source_id=? AND license_id=? AND market_scope='UNKNOWN' AND production_import=0 AND exact_engine_gearbox_pair=0 AND ru_eaeu_applicability=0",(SOURCE_ID,LICENSE_ID)).fetchone()[0]!=1:
            raise ValueError("Cardir SQLite source registry mismatch")
        counts={"vag_facts":len(facts),"vag_brands":db.execute("SELECT count(*) FROM brands").fetchone()[0],"vag_models":db.execute("SELECT count(*) FROM models").fetchone()[0]}
    finally: db.close()
    return {"status":"verified_research_only","pack_id":PACK_ID,"source_snapshot_sha256":manifest["source_snapshot_sha256"],
            "source_manifest_sha256":manifest["source_manifest_sha256"],"database_sha256":manifest["database"]["sha256"],
            "counts":manifest["counts"],"market_scope":["UNKNOWN"],"product_import_allowed":False,
            "production_import":False,"exact_engine_gearbox_pair":False,"ru_eaeu_applicability":False}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--acquire",action="store_true"); mode.add_argument("--build",action="store_true"); mode.add_argument("--verify-only",action="store_true")
    parser.add_argument("--source-manifest",type=Path); parser.add_argument("--csv",type=Path); parser.add_argument("--snapshot-manifest",type=Path); parser.add_argument("--output-dir",type=Path,required=True)
    args=parser.parse_args()
    if args.acquire:
        if not args.source_manifest: parser.error("--acquire requires --source-manifest")
        result=acquire(args.source_manifest,args.output_dir)
    elif args.build:
        if not args.source_manifest or not args.csv or not args.snapshot_manifest: parser.error("--build requires --source-manifest, --csv and --snapshot-manifest")
        result=build(args.csv,args.snapshot_manifest,args.source_manifest,args.output_dir)
    else: result=verify_pack(args.output_dir)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
