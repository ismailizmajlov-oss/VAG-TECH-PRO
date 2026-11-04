#!/usr/bin/env python3
"""Build a provenance-preserving CC0 Wikidata VAG model-identity candidate pack.

This commit re-runs the bounded live snapshot after the workflow was enabled on main.

Only structured Wikidata statements are queried. No article text, images, engine
codes, transmission codes, ECU data, DTC definitions, or repair procedures are
collected. All model rows remain candidate identity records with UNKNOWN market
scope and no exact vehicle-fitment claims.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Any

ENDPOINT = "https://query.wikidata.org/sparql"
SOURCE_ID = "wikidata-vag-model-taxonomy"
PUBLISHER = "Wikidata / Wikimedia Foundation"
SOURCE_URL = "https://www.wikidata.org/"
LICENSE_ID = "CC0-1.0"
LICENSE_URL = "https://creativecommons.org/publicdomain/zero/1.0/"
SOURCE_REVISION_PREFIX = "wikidata-snapshot-"
USER_AGENT = "VAG-TECH-PRO/0.1 (+https://github.com/ismailizmajlov-oss/VAG-TECH-PRO)"
MANUFACTURER_LABELS = [
    "Volkswagen", "Volkswagen AG", "Volkswagen Commercial Vehicles",
    "Audi AG", "Škoda Auto", "SEAT", "SEAT S.A.",
    "Porsche AG", "Bentley Motors Limited",
    "Automobili Lamborghini S.p.A.", "Bugatti Rimac",
]

SPARQL_QUERY = """PREFIX wd: <http://www.wikidata.org/entity/>
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX schema: <http://schema.org/>
SELECT DISTINCT ?model ?modelLabelEn ?modelLabelRu ?manufacturer ?manufacturerLabel ?inception ?dissolution ?modified
WHERE {
  ?model wdt:P176 ?manufacturer ;
         wdt:P31/wdt:P279* wd:Q3231690 .
  VALUES ?manufacturerLabel { "Volkswagen"@en "Volkswagen AG"@en "Volkswagen Commercial Vehicles"@en "Audi AG"@en "Škoda Auto"@en "SEAT"@en "SEAT S.A."@en "Porsche AG"@en "Bentley Motors Limited"@en "Automobili Lamborghini S.p.A."@en "Bugatti Rimac"@en }
  ?manufacturer rdfs:label ?manufacturerLabel .
  ?model rdfs:label ?modelLabelEn .
  FILTER(LANG(?modelLabelEn) = "en")
  OPTIONAL { ?model rdfs:label ?modelLabelRu . FILTER(LANG(?modelLabelRu) = "ru") }
  OPTIONAL { ?model wdt:P571 ?inception . }
  OPTIONAL { ?model wdt:P576 ?dissolution . }
  OPTIONAL { ?model schema:dateModified ?modified . }
}
ORDER BY ?manufacturerLabel ?modelLabelEn
LIMIT 3000
"""

LICENSE_NOTICE = """Wikidata structured data notice

The structured data queried for this research pack is made available under
Creative Commons CC0 1.0 Universal (CC0 1.0). Official legal code:
https://creativecommons.org/publicdomain/zero/1.0/legalcode

This notice applies only to the structured Wikidata statements represented in
the pinned query snapshot. It does not apply to Wikimedia article text, images,
logos, third-party linked resources, or any OEM material.
"""

ATTRIBUTION = """# Wikidata attribution and scope

Source: Wikidata structured data — https://www.wikidata.org/
Query endpoint: https://query.wikidata.org/sparql
License: CC0 1.0 Universal — https://creativecommons.org/publicdomain/zero/1.0/

This pack stores structured model/manufacturer identity statements only. It is
a candidate taxonomy, not an authoritative Volkswagen Group model register.
The manufacturer-label whitelist is a project-maintained acquisition filter,
not proof of corporate ownership or vehicle fitment.

No engine or gearbox codes, ECU identities, DTC definitions, diagnostic
procedures, repair instructions, wiring diagrams, pinouts, torque values,
adaptations, OEM part numbers, model-year applicability, market scope, VIN
fitment, or confirmed generation relationships are included.

All records are marked candidate; market scope is UNKNOWN; exact fitment and
technical applicability are false. The inception/dissolution fields preserve
Wikidata statements and are not converted into production-year ranges.
"""

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;
CREATE TABLE source_registry (
  source_id TEXT PRIMARY KEY,
  publisher TEXT NOT NULL,
  source_url TEXT NOT NULL,
  endpoint_url TEXT NOT NULL,
  license_id TEXT NOT NULL,
  license_url TEXT NOT NULL,
  rights_status TEXT NOT NULL,
  commercial_use_allowed INTEGER NOT NULL CHECK(commercial_use_allowed IN (0,1)),
  display_allowed INTEGER NOT NULL CHECK(display_allowed IN (0,1)),
  offline_cache_allowed INTEGER NOT NULL CHECK(offline_cache_allowed IN (0,1)),
  bulk_reuse_allowed INTEGER NOT NULL CHECK(bulk_reuse_allowed IN (0,1)),
  redistribution_allowed INTEGER NOT NULL CHECK(redistribution_allowed IN (0,1)),
  attribution_required INTEGER NOT NULL CHECK(attribution_required IN (0,1)),
  attribution_recommended INTEGER NOT NULL CHECK(attribution_recommended IN (0,1)),
  share_alike_required INTEGER NOT NULL CHECK(share_alike_required IN (0,1)),
  source_revision TEXT NOT NULL,
  source_snapshot_sha256 TEXT NOT NULL CHECK(length(source_snapshot_sha256)=64),
  source_query_sha256 TEXT NOT NULL CHECK(length(source_query_sha256)=64),
  market_scope TEXT NOT NULL CHECK(market_scope='UNKNOWN'),
  applicability_precision TEXT NOT NULL CHECK(applicability_precision='candidate_identity_only'),
  review_status TEXT NOT NULL CHECK(review_status='candidate')
);
CREATE TABLE vehicle_model_entities (
  model_qid TEXT NOT NULL,
  manufacturer_qid TEXT NOT NULL,
  model_uri TEXT NOT NULL,
  manufacturer_uri TEXT NOT NULL,
  model_label_en TEXT NOT NULL,
  model_label_ru TEXT,
  manufacturer_label_en TEXT NOT NULL,
  inception_dates_json TEXT NOT NULL,
  dissolution_dates_json TEXT NOT NULL,
  modified_dates_json TEXT NOT NULL,
  source_binding_indexes_json TEXT NOT NULL,
  source_binding_sha256s_json TEXT NOT NULL,
  source_record_sha256 TEXT NOT NULL CHECK(length(source_record_sha256)=64),
  source_revision TEXT NOT NULL,
  source_snapshot_sha256 TEXT NOT NULL CHECK(length(source_snapshot_sha256)=64),
  source_query_sha256 TEXT NOT NULL CHECK(length(source_query_sha256)=64),
  market_scope TEXT NOT NULL CHECK(market_scope='UNKNOWN'),
  applicability_precision TEXT NOT NULL CHECK(applicability_precision='candidate_identity_only'),
  review_status TEXT NOT NULL CHECK(review_status='candidate'),
  exact_vehicle_fitment INTEGER NOT NULL DEFAULT 0 CHECK(exact_vehicle_fitment=0),
  generation_verified INTEGER NOT NULL DEFAULT 0 CHECK(generation_verified=0),
  engine_code_fitment INTEGER NOT NULL DEFAULT 0 CHECK(engine_code_fitment=0),
  transmission_code_fitment INTEGER NOT NULL DEFAULT 0 CHECK(transmission_code_fitment=0),
  ecu_fitment INTEGER NOT NULL DEFAULT 0 CHECK(ecu_fitment=0),
  dtc_fitment INTEGER NOT NULL DEFAULT 0 CHECK(dtc_fitment=0),
  repair_procedure_fitment INTEGER NOT NULL DEFAULT 0 CHECK(repair_procedure_fitment=0),
  source_binding_count INTEGER NOT NULL CHECK(source_binding_count>0),
  PRIMARY KEY(model_qid, manufacturer_qid)
);
CREATE TABLE source_bindings (
  source_binding_index INTEGER PRIMARY KEY,
  model_qid TEXT NOT NULL,
  manufacturer_qid TEXT NOT NULL,
  source_binding_sha256 TEXT NOT NULL CHECK(length(source_binding_sha256)=64),
  source_revision TEXT NOT NULL,
  source_snapshot_sha256 TEXT NOT NULL CHECK(length(source_snapshot_sha256)=64),
  source_query_sha256 TEXT NOT NULL CHECK(length(source_query_sha256)=64),
  FOREIGN KEY(model_qid, manufacturer_qid)
    REFERENCES vehicle_model_entities(model_qid, manufacturer_qid)
);
CREATE TABLE model_date_statements (
  model_qid TEXT NOT NULL,
  manufacturer_qid TEXT NOT NULL,
  property_id TEXT NOT NULL CHECK(property_id IN ('P571','P576')),
  date_value TEXT NOT NULL,
  source_binding_index INTEGER NOT NULL,
  source_binding_sha256 TEXT NOT NULL CHECK(length(source_binding_sha256)=64),
  source_revision TEXT NOT NULL,
  PRIMARY KEY(model_qid, manufacturer_qid, property_id, date_value, source_binding_index),
  FOREIGN KEY(model_qid, manufacturer_qid)
    REFERENCES vehicle_model_entities(model_qid, manufacturer_qid),
  FOREIGN KEY(source_binding_index) REFERENCES source_bindings(source_binding_index)
);
CREATE INDEX idx_model_label_en ON vehicle_model_entities(model_label_en);
CREATE INDEX idx_manufacturer_label ON vehicle_model_entities(manufacturer_label_en);
CREATE INDEX idx_model_qid ON vehicle_model_entities(model_qid);
"""

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def binding_value(binding: dict[str, Any], key: str) -> str | None:
    value = binding.get(key)
    return value.get("value") if isinstance(value, dict) else None

def qid(uri: str | None) -> str:
    if not uri:
        raise ValueError("missing Wikidata entity URI")
    match = re.fullmatch(r"Q[0-9]+", uri.rsplit("/", 1)[-1])
    if not match:
        raise ValueError(f"invalid Wikidata QID URI: {uri}")
    return match.group(0)

def fetch_live_snapshot() -> bytes:
    body = urllib.parse.urlencode({"query": SPARQL_QUERY, "format": "json"}).encode("ascii")
    request = urllib.request.Request(
        ENDPOINT,
        data=body,
        method="POST",
        headers={
            "Accept": "application/sparql-results+json",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "User-Agent": USER_AGENT,
        },
    )
    last_error: Exception | None = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                if response.status != 200:
                    raise RuntimeError(f"Wikidata Query Service returned HTTP {response.status}")
                payload = response.read()
            parsed = json.loads(payload)
            if not isinstance(parsed.get("results", {}).get("bindings"), list):
                raise ValueError("SPARQL response has no results.bindings array")
            return payload
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError) as exc:
            last_error = exc
            if isinstance(exc, urllib.error.HTTPError) and exc.code not in (429, 500, 502, 503, 504):
                raise
            if attempt == 3:
                break
            retry_after = 0
            if isinstance(exc, urllib.error.HTTPError):
                try:
                    retry_after = int(exc.headers.get("Retry-After", "0"))
                except ValueError:
                    retry_after = 0
            time.sleep(max(retry_after, 2 ** attempt))
    raise RuntimeError(f"Wikidata snapshot acquisition failed: {last_error}")

def parse_snapshot(snapshot_bytes: bytes) -> list[dict[str, Any]]:
    payload = json.loads(snapshot_bytes)
    bindings = payload.get("results", {}).get("bindings")
    if not isinstance(bindings, list):
        raise ValueError("SPARQL snapshot has no bindings")
    parsed: list[dict[str, Any]] = []
    for index, binding in enumerate(bindings, start=1):
        model_uri = binding_value(binding, "model")
        manufacturer_uri = binding_value(binding, "manufacturer")
        manufacturer_label = binding_value(binding, "manufacturerLabel")
        model_label_en = binding_value(binding, "modelLabelEn")
        if not model_uri or not manufacturer_uri or not manufacturer_label or not model_label_en:
            raise ValueError(f"binding {index} lacks required model/manufacturer identity fields")
        if manufacturer_label not in MANUFACTURER_LABELS:
            raise ValueError(f"binding {index} manufacturer is outside the curated whitelist")
        row = {
            "binding_index": index,
            "binding_sha256": sha256(canonical_json(binding)),
            "model_qid": qid(model_uri),
            "model_uri": model_uri,
            "model_label_en": model_label_en.strip(),
            "model_label_ru": (binding_value(binding, "modelLabelRu") or "").strip() or None,
            "manufacturer_qid": qid(manufacturer_uri),
            "manufacturer_uri": manufacturer_uri,
            "manufacturer_label_en": manufacturer_label,
            "inception": binding_value(binding, "inception"),
            "dissolution": binding_value(binding, "dissolution"),
            "modified": binding_value(binding, "modified"),
        }
        if not row["model_label_en"]:
            raise ValueError(f"binding {index} has an empty English model label")
        parsed.append(row)
    if not parsed:
        raise ValueError("Wikidata query returned no VAG manufacturer model candidates")
    return parsed

def logical_content_hash(rows: list[dict[str, Any]]) -> str:
    material = [
        {
            "model_qid": row["model_qid"],
            "manufacturer_qid": row["manufacturer_qid"],
            "model_label_en": row["model_label_en"],
            "model_label_ru": row["model_label_ru"],
            "manufacturer_label_en": row["manufacturer_label_en"],
            "inception": row["inception"],
            "dissolution": row["dissolution"],
            "modified": row["modified"],
            "binding_index": row["binding_index"],
            "binding_sha256": row["binding_sha256"],
        }
        for row in rows
    ]
    return sha256(canonical_json(material))

def build_database(db_path: Path, rows: list[dict[str, Any]], source_revision: str, snapshot_sha: str, query_sha: str) -> dict[str, int]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(row["model_qid"], row["manufacturer_qid"])].append(row)
    db = sqlite3.connect(db_path)
    try:
        db.execute("PRAGMA journal_mode=DELETE")
        db.execute("PRAGMA synchronous=FULL")
        db.execute("PRAGMA foreign_keys=ON")
        db.executescript(SCHEMA_SQL)
        db.execute("PRAGMA user_version=1")
        db.execute(
            """INSERT INTO source_registry VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                SOURCE_ID, PUBLISHER, SOURCE_URL, ENDPOINT, LICENSE_ID, LICENSE_URL,
                "approved_by_published_license", 1, 1, 1, 1, 1, 0, 1, 0,
                source_revision, snapshot_sha, query_sha, "UNKNOWN", "candidate_identity_only", "candidate",
            ),
        )
        for (model_qid, manufacturer_qid), group in sorted(grouped.items()):
            group = sorted(group, key=lambda item: item["binding_index"])
            first = group[0]
            inception = sorted({r["inception"] for r in group if r["inception"]})
            dissolution = sorted({r["dissolution"] for r in group if r["dissolution"]})
            modified = sorted({r["modified"] for r in group if r["modified"]})
            indexes = [r["binding_index"] for r in group]
            binding_hashes = [r["binding_sha256"] for r in group]
            record = {
                "model_qid": model_qid, "manufacturer_qid": manufacturer_qid,
                "model_label_en": first["model_label_en"], "model_label_ru": first["model_label_ru"],
                "manufacturer_label_en": first["manufacturer_label_en"], "inception": inception,
                "dissolution": dissolution, "modified": modified, "binding_indexes": indexes,
                "binding_hashes": binding_hashes,
            }
            db.execute(
                """INSERT INTO vehicle_model_entities (
                  model_qid,manufacturer_qid,model_uri,manufacturer_uri,model_label_en,model_label_ru,
                  manufacturer_label_en,inception_dates_json,dissolution_dates_json,modified_dates_json,
                  source_binding_indexes_json,source_binding_sha256s_json,source_record_sha256,
                  source_revision,source_snapshot_sha256,source_query_sha256,market_scope,
                  applicability_precision,review_status,exact_vehicle_fitment,generation_verified,
                  engine_code_fitment,transmission_code_fitment,ecu_fitment,dtc_fitment,
                  repair_procedure_fitment,source_binding_count
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    model_qid, manufacturer_qid, first["model_uri"], first["manufacturer_uri"],
                    first["model_label_en"], first["model_label_ru"], first["manufacturer_label_en"],
                    json.dumps(inception, ensure_ascii=False), json.dumps(dissolution, ensure_ascii=False),
                    json.dumps(modified, ensure_ascii=False), json.dumps(indexes),
                    json.dumps(binding_hashes), sha256(canonical_json(record)), source_revision,
                    snapshot_sha, query_sha, "UNKNOWN", "candidate_identity_only", "candidate",
                    0, 0, 0, 0, 0, 0, 0, len(group),
                ),
            )
        for row in sorted(rows, key=lambda item: item["binding_index"]):
            db.execute(
                "INSERT INTO source_bindings VALUES (?,?,?,?,?,?,?)",
                (
                    row["binding_index"], row["model_qid"], row["manufacturer_qid"],
                    row["binding_sha256"], source_revision, snapshot_sha, query_sha,
                ),
            )
            for property_id, date_value in (("P571", row["inception"]), ("P576", row["dissolution"])):
                if date_value:
                    db.execute(
                        "INSERT OR IGNORE INTO model_date_statements VALUES (?,?,?,?,?,?,?)",
                        (
                            row["model_qid"], row["manufacturer_qid"], property_id, date_value,
                            row["binding_index"], row["binding_sha256"], source_revision,
                        ),
                    )
        db.commit()
        integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise RuntimeError(f"SQLite integrity_check failed: {integrity}")
        if db.execute("PRAGMA foreign_key_check").fetchall():
            raise RuntimeError("SQLite foreign-key check failed")
        return {
            "model_entities": len(grouped),
            "source_bindings": len(rows),
            "manufacturers": len({row["manufacturer_qid"] for row in rows}),
            "russian_labels": sum(1 for row in grouped.values() if row[0]["model_label_ru"]),
            "date_statements": db.execute("SELECT count(*) FROM model_date_statements").fetchone()[0],
        }
    finally:
        db.close()

def file_info(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {"sha256": sha256(data), "byte_size": len(data)}

def build_pack(snapshot_bytes: bytes, output_dir: Path, retrieved_at_utc: str | None = None) -> dict[str, Any]:
    rows = parse_snapshot(snapshot_bytes)
    query_bytes = SPARQL_QUERY.encode("utf-8")
    snapshot_sha = sha256(snapshot_bytes)
    query_sha = sha256(query_bytes)
    snapshot_id = snapshot_sha[:12]
    source_revision = SOURCE_REVISION_PREFIX + snapshot_id
    output_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path = output_dir / "snapshot.json"
    query_path = output_dir / "query.rq"
    license_path = output_dir / "LICENSE-NOTICE.txt"
    attribution_path = output_dir / "ATTRIBUTION.md"
    db_path = output_dir / "wikidata-vag-taxonomy.sqlite"
    snapshot_path.write_bytes(snapshot_bytes)
    query_path.write_bytes(query_bytes)
    license_path.write_text(LICENSE_NOTICE, encoding="utf-8", newline="\n")
    attribution_path.write_text(ATTRIBUTION, encoding="utf-8", newline="\n")
    counts = build_database(db_path, rows, source_revision, snapshot_sha, query_sha)
    logical_sha = logical_content_hash(rows)
    pack_files = {
        path.name: file_info(path)
        for path in (snapshot_path, query_path, license_path, attribution_path, db_path)
    }
    manifest = {
        "schema_version": 1,
        "pack_id": f"wikidata-vag-model-taxonomy-cc0-{snapshot_id}",
        "snapshot_id": snapshot_id,
        "built_at_utc": retrieved_at_utc or utc_now(),
        "publisher": PUBLISHER,
        "source_repository": SOURCE_URL,
        "source_endpoint": ENDPOINT,
        "source_id": SOURCE_ID,
        "data_license": LICENSE_ID,
        "license_url": LICENSE_URL,
        "rights_status": "approved_by_published_license",
        "commercial_use_allowed": True,
        "display_allowed": True,
        "offline_cache_allowed": True,
        "bulk_reuse_allowed": True,
        "redistribution_allowed": True,
        "attribution_required": False,
        "attribution_recommended": True,
        "share_alike_required": False,
        "attribution_text": "Wikidata structured data, CC0 1.0 Universal.",
        "source_revision": source_revision,
        "source_snapshot_sha256": snapshot_sha,
        "source_query_sha256": query_sha,
        "logical_content_sha256": logical_sha,
        "database_sha256": pack_files[db_path.name]["sha256"],
        "manufacturer_whitelist": MANUFACTURER_LABELS,
        "counts": counts,
        "query_limit": 3000,
        "limit_reached": len(rows) >= 3000,
        "completeness_status": "unknown",
        "scope": {
            "namespace": "vag_identity_candidate",
            "manufacturer_group_basis": "curated_manufacturer_label_whitelist; not an authoritative corporate ownership registry",
            "market_scope": "UNKNOWN",
            "completeness_status": "unknown",
            "applicability_precision": "candidate_identity_only",
            "review_status": "candidate",
            "generation_entities": 0,
            "generation_verified": False,
            "exact_vehicle_fitment": False,
            "engine_code_fitment": False,
            "transmission_code_fitment": False,
            "ecu_fitment": False,
            "dtc_fitment": False,
            "repair_procedure_fitment": False,
            "diagnostic_execution_allowed": False,
            "production_years_inferred": False,
        },
        "exclusions": [
            "No engine or gearbox codes", "No ECU identities", "No DTC definitions or descriptions",
            "No diagnostic test plans or execution commands", "No repair procedures",
            "No wiring diagrams or pinouts", "No torque values or adaptations",
            "No OEM part numbers", "No market scope", "No exact vehicle fitment",
            "No verified generation mapping", "No article text or images",
        ],
        "pack_files": pack_files,
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    verify_pack(output_dir)
    return manifest

def verify_pack(output_dir: Path) -> dict[str, Any]:
    manifest_path = output_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("data_license") != LICENSE_ID or manifest.get("rights_status") != "approved_by_published_license":
        raise ValueError("CC0 rights metadata is not approved")
    for flag in ("commercial_use_allowed", "display_allowed", "offline_cache_allowed", "bulk_reuse_allowed", "redistribution_allowed"):
        if manifest.get(flag) is not True:
            raise ValueError(f"required CC0 right is not true: {flag}")
    scope = manifest.get("scope", {})
    for field in ("exact_vehicle_fitment", "generation_verified", "engine_code_fitment", "transmission_code_fitment", "ecu_fitment", "dtc_fitment", "repair_procedure_fitment", "diagnostic_execution_allowed", "production_years_inferred"):
        if scope.get(field) is not False:
            raise ValueError(f"candidate-only scope boundary changed: {field}")
    if scope.get("market_scope") != "UNKNOWN" or scope.get("applicability_precision") != "candidate_identity_only" or scope.get("generation_entities") != 0 or scope.get("completeness_status") != "unknown" or manifest.get("completeness_status") != "unknown" or manifest.get("query_limit") != 3000:
        raise ValueError("candidate-only scope metadata changed")
    for name, info in manifest["pack_files"].items():
        path = output_dir / name
        if not path.is_file():
            raise ValueError(f"pack file missing: {name}")
        actual = file_info(path)
        if actual != info:
            raise ValueError(f"pack file SHA/size mismatch: {name}")
    db_path = output_dir / "wikidata-vag-taxonomy.sqlite"
    db = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    try:
        if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("SQLite integrity_check failed")
        if db.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("SQLite foreign-key check failed")
        if db.execute("PRAGMA user_version").fetchone()[0] != 1:
            raise ValueError("unexpected SQLite schema version")
        counts = {
            "model_entities": db.execute("SELECT count(*) FROM vehicle_model_entities").fetchone()[0],
            "source_bindings": db.execute("SELECT count(*) FROM source_bindings").fetchone()[0],
            "manufacturers": db.execute("SELECT count(DISTINCT manufacturer_qid) FROM vehicle_model_entities").fetchone()[0],
            "russian_labels": db.execute("SELECT count(*) FROM vehicle_model_entities WHERE model_label_ru IS NOT NULL AND model_label_ru!=''").fetchone()[0],
            "date_statements": db.execute("SELECT count(*) FROM model_date_statements").fetchone()[0],
        }
        if counts != manifest["counts"]:
            raise ValueError(f"SQLite counts do not match manifest: {counts}")
        unsafe = db.execute(
            """SELECT count(*) FROM vehicle_model_entities
               WHERE market_scope!='UNKNOWN' OR applicability_precision!='candidate_identity_only'
                  OR review_status!='candidate' OR exact_vehicle_fitment!=0 OR generation_verified!=0
                  OR engine_code_fitment!=0 OR transmission_code_fitment!=0 OR ecu_fitment!=0
                  OR dtc_fitment!=0 OR repair_procedure_fitment!=0"""
        ).fetchone()[0]
        if unsafe:
            raise ValueError(f"{unsafe} rows escaped candidate-only applicability")
        source = db.execute("SELECT * FROM source_registry").fetchone()
        if not source or source[0] != SOURCE_ID or source[5] != LICENSE_URL or source[6] != "approved_by_published_license":
            raise ValueError("SQLite source registry rights metadata mismatch")
        if any(source[i] != 1 for i in (7,8,9,10,11)) or source[12] != 0 or source[13] != 1 or source[14] != 0:
            raise ValueError("SQLite source registry reuse rights mismatch")
        if source[15] != manifest["source_revision"] or source[16] != manifest["source_snapshot_sha256"] or source[17] != manifest["source_query_sha256"]:
            raise ValueError("SQLite source registry revision/hash mismatch")
        if db.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name IN ('engines','transmissions','ecu','dtc','repair_procedures','wiring_diagrams','pinouts','torque_specs','adaptations')").fetchone()[0]:
            raise ValueError("technical data tables are forbidden in identity-only pack")
    finally:
        db.close()
    return manifest

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fetch", action="store_true")
    parser.add_argument("--snapshot-file", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--verify-dir", type=Path)
    args = parser.parse_args()
    if args.verify_dir:
        manifest = verify_pack(args.verify_dir)
    else:
        if args.fetch and args.snapshot_file:
            parser.error("use either --fetch or --snapshot-file")
        if args.fetch:
            snapshot = fetch_live_snapshot()
        elif args.snapshot_file:
            snapshot = args.snapshot_file.read_bytes()
        else:
            parser.error("one of --fetch or --snapshot-file is required")
        manifest = build_pack(snapshot, args.output_dir)
    print(json.dumps({
        "status": "verified",
        "pack_id": manifest["pack_id"],
        "snapshot_id": manifest["snapshot_id"],
        "source_revision": manifest["source_revision"],
        "source_snapshot_sha256": manifest["source_snapshot_sha256"],
        "source_query_sha256": manifest["source_query_sha256"],
        "database_sha256": manifest["database_sha256"],
        "counts": manifest["counts"],
        "scope": manifest["scope"],
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
