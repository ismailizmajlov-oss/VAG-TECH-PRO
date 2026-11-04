#!/usr/bin/env python3
"""Build a CC0, candidate-only Wikidata model-series member pack.

P179/P527 links are preserved as candidate relationships. They are not treated
as verified generations, production-year ranges, or vehicle fitment.
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
SOURCE_ID = "wikidata-vag-generation-candidates"
PUBLISHER = "Wikidata / Wikimedia Foundation"
SOURCE_URL = "https://www.wikidata.org/"
LICENSE_ID = "CC0-1.0"
LICENSE_URL = "https://creativecommons.org/publicdomain/zero/1.0/"
SOURCE_REVISION_PREFIX = "wikidata-generation-candidates-"
USER_AGENT = "VAG-TECH-PRO/0.1 (+https://github.com/ismailizmajlov-oss/VAG-TECH-PRO)"
MODEL_PACK_ROOT = Path("data/research/wikidata-vag-taxonomy")
QUERY_LIMIT = 5000

LICENSE_NOTICE = """Wikidata structured data notice

The structured Wikidata statements represented in this pinned research pack are
made available under Creative Commons CC0 1.0 Universal:
https://creativecommons.org/publicdomain/zero/1.0/legalcode

This notice applies only to structured statements in the pinned query snapshot.
It does not apply to article text, images, logos, third-party resources, or OEM
materials.
"""

ATTRIBUTION = """# Wikidata model-series member candidate pack

Source: Wikidata structured data — https://www.wikidata.org/
Query endpoint: https://query.wikidata.org/sparql
License: CC0 1.0 Universal — https://creativecommons.org/publicdomain/zero/1.0/

This pack stores only P179 (part of the series) and P527 (has part(s))
relationships from Wikidata, linked to the parent VAG model-identity candidate
snapshot recorded in manifest.json.

These are model-series member candidates, not verified vehicle generations.
Dates retain their original Wikidata property identifiers and are not converted
into production-year ranges. Market scope is UNKNOWN. Exact vehicle fitment,
engine/gearbox, ECU, DTC, repair, wiring, and diagnostic applicability are false.
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
  parent_model_source_revision TEXT NOT NULL,
  parent_model_source_snapshot_sha256 TEXT NOT NULL CHECK(length(parent_model_source_snapshot_sha256)=64),
  parent_model_database_sha256 TEXT NOT NULL CHECK(length(parent_model_database_sha256)=64),
  market_scope TEXT NOT NULL CHECK(market_scope='UNKNOWN'),
  applicability_precision TEXT NOT NULL CHECK(applicability_precision='series_member_candidate'),
  review_status TEXT NOT NULL CHECK(review_status='candidate'),
  generation_verified INTEGER NOT NULL CHECK(generation_verified=0),
  exact_vehicle_fitment INTEGER NOT NULL CHECK(exact_vehicle_fitment=0),
  engine_code_fitment INTEGER NOT NULL CHECK(engine_code_fitment=0),
  transmission_code_fitment INTEGER NOT NULL CHECK(transmission_code_fitment=0),
  ecu_fitment INTEGER NOT NULL CHECK(ecu_fitment=0),
  dtc_fitment INTEGER NOT NULL CHECK(dtc_fitment=0),
  repair_procedure_fitment INTEGER NOT NULL CHECK(repair_procedure_fitment=0),
  diagnostic_execution_allowed INTEGER NOT NULL CHECK(diagnostic_execution_allowed=0),
  production_years_inferred INTEGER NOT NULL CHECK(production_years_inferred=0)
);
CREATE TABLE model_series_member_candidates (
  member_qid TEXT NOT NULL,
  model_qid TEXT NOT NULL,
  manufacturer_qid TEXT NOT NULL,
  member_uri TEXT NOT NULL,
  model_label_en TEXT NOT NULL,
  member_label_en TEXT NOT NULL,
  member_label_ru TEXT,
  member_type_qids_json TEXT NOT NULL,
  member_manufacturer_qids_json TEXT NOT NULL,
  start_dates_json TEXT NOT NULL,
  end_dates_json TEXT NOT NULL,
  inception_dates_json TEXT NOT NULL,
  dissolution_dates_json TEXT NOT NULL,
  series_ordinals_json TEXT NOT NULL,
  relation_properties_json TEXT NOT NULL,
  source_binding_indexes_json TEXT NOT NULL,
  source_binding_sha256s_json TEXT NOT NULL,
  source_record_sha256 TEXT NOT NULL CHECK(length(source_record_sha256)=64),
  source_revision TEXT NOT NULL,
  source_snapshot_sha256 TEXT NOT NULL CHECK(length(source_snapshot_sha256)=64),
  source_query_sha256 TEXT NOT NULL CHECK(length(source_query_sha256)=64),
  market_scope TEXT NOT NULL CHECK(market_scope='UNKNOWN'),
  applicability_precision TEXT NOT NULL CHECK(applicability_precision='series_member_candidate'),
  review_status TEXT NOT NULL CHECK(review_status='candidate'),
  manufacturer_relation_status TEXT NOT NULL CHECK(manufacturer_relation_status IN ('match','mismatch','unknown')),
  generation_verified INTEGER NOT NULL DEFAULT 0 CHECK(generation_verified=0),
  exact_vehicle_fitment INTEGER NOT NULL DEFAULT 0 CHECK(exact_vehicle_fitment=0),
  engine_code_fitment INTEGER NOT NULL DEFAULT 0 CHECK(engine_code_fitment=0),
  transmission_code_fitment INTEGER NOT NULL DEFAULT 0 CHECK(transmission_code_fitment=0),
  ecu_fitment INTEGER NOT NULL DEFAULT 0 CHECK(ecu_fitment=0),
  dtc_fitment INTEGER NOT NULL DEFAULT 0 CHECK(dtc_fitment=0),
  repair_procedure_fitment INTEGER NOT NULL DEFAULT 0 CHECK(repair_procedure_fitment=0),
  diagnostic_execution_allowed INTEGER NOT NULL DEFAULT 0 CHECK(diagnostic_execution_allowed=0),
  production_years_inferred INTEGER NOT NULL DEFAULT 0 CHECK(production_years_inferred=0),
  PRIMARY KEY(member_qid, model_qid)
);
CREATE TABLE series_member_source_bindings (
  source_binding_index INTEGER PRIMARY KEY,
  member_qid TEXT NOT NULL,
  model_qid TEXT NOT NULL,
  relation_property TEXT NOT NULL CHECK(relation_property IN ('P179','P527')),
  source_binding_sha256 TEXT NOT NULL CHECK(length(source_binding_sha256)=64),
  source_revision TEXT NOT NULL,
  source_snapshot_sha256 TEXT NOT NULL CHECK(length(source_snapshot_sha256)=64),
  source_query_sha256 TEXT NOT NULL CHECK(length(source_query_sha256)=64),
  FOREIGN KEY(member_qid, model_qid)
    REFERENCES model_series_member_candidates(member_qid, model_qid)
);
CREATE TABLE series_member_date_statements (
  member_qid TEXT NOT NULL,
  model_qid TEXT NOT NULL,
  property_id TEXT NOT NULL CHECK(property_id IN ('P571','P576','P580','P582')),
  date_value TEXT NOT NULL,
  source_binding_index INTEGER NOT NULL,
  source_binding_sha256 TEXT NOT NULL CHECK(length(source_binding_sha256)=64),
  source_revision TEXT NOT NULL,
  PRIMARY KEY(member_qid, model_qid, property_id, date_value, source_binding_index),
  FOREIGN KEY(member_qid, model_qid)
    REFERENCES model_series_member_candidates(member_qid, model_qid),
  FOREIGN KEY(source_binding_index)
    REFERENCES series_member_source_bindings(source_binding_index)
);
CREATE INDEX idx_series_member_label_en ON model_series_member_candidates(member_label_en);
CREATE INDEX idx_series_member_model_qid ON model_series_member_candidates(model_qid);
CREATE INDEX idx_series_member_member_qid ON model_series_member_candidates(member_qid);
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

def fetch_sparql(query: str) -> bytes:
    body = urllib.parse.urlencode({"query": query, "format": "json"}).encode("ascii")
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
            with urllib.request.urlopen(request, timeout=120) as response:
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
    raise RuntimeError(f"Wikidata generation candidate query failed: {last_error}")

def latest_model_pack(repo_root: Path) -> tuple[dict[str, Any], Path, list[dict[str, str]]]:
    manifests = list((repo_root / MODEL_PACK_ROOT).glob("*/manifest.json"))
    candidates = []
    for manifest_path in manifests:
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if manifest.get("source_id") == "wikidata-vag-model-taxonomy" and manifest.get("data_license") == LICENSE_ID:
            candidates.append((manifest.get("built_at_utc", ""), manifest, manifest_path.parent))
    if not candidates:
        raise FileNotFoundError("No verified CC0 Wikidata VAG model-identity parent pack is available")
    _, manifest, pack_dir = max(candidates, key=lambda item: item[0])
    verify_parent = json.loads((pack_dir / "manifest.json").read_text(encoding="utf-8"))
    db_path = pack_dir / "wikidata-vag-taxonomy.sqlite"
    if sha256(db_path.read_bytes()) != verify_parent.get("database_sha256"):
        raise ValueError("Parent Wikidata model database SHA-256 does not match its manifest")
    db = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    try:
        if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("Parent Wikidata model database integrity check failed")
        rows = db.execute(
            """SELECT model_qid, manufacturer_qid, model_label_en, model_label_ru,
                      manufacturer_label_en
               FROM vehicle_model_entities ORDER BY model_qid"""
        ).fetchall()
    finally:
        db.close()
    models = [
        {
            "model_qid": row[0],
            "manufacturer_qid": row[1],
            "model_label_en": row[2],
            "model_label_ru": row[3] or "",
            "manufacturer_label_en": row[4],
        }
        for row in rows
    ]
    if not models:
        raise ValueError("Parent Wikidata model pack contains no model entities")
    return manifest, db_path, models

def build_generation_query(model_qids: list[str]) -> str:
    values = " ".join(f"wd:{value}" for value in sorted(set(model_qids)))
    if not values:
        raise ValueError("No parent model QIDs supplied to generation candidate query")
    return f"""PREFIX wd: <http://www.wikidata.org/entity/>
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema/>
SELECT DISTINCT ?model ?member ?relation ?memberLabelEn ?memberLabelRu ?memberType
                ?start ?end ?inception ?dissolution ?ordinal ?memberManufacturer
WHERE {{
  VALUES ?model {{ {values} }}
  {{
    ?member wdt:P179 ?model .
    BIND("P179" AS ?relation)
  }}
  UNION
  {{
    ?model wdt:P527 ?member .
    BIND("P527" AS ?relation)
  }}
  FILTER(?member != ?model)
  ?member wdt:P31/wdt:P279* wd:Q3231690 .
  ?member rdfs:label ?memberLabelEn .
  FILTER(LANG(?memberLabelEn) = "en")
  OPTIONAL {{ ?member rdfs:label ?memberLabelRu . FILTER(LANG(?memberLabelRu) = "ru") }}
  OPTIONAL {{ ?member wdt:P31 ?memberType . }}
  OPTIONAL {{ ?member wdt:P580 ?start . }}
  OPTIONAL {{ ?member wdt:P582 ?end . }}
  OPTIONAL {{ ?member wdt:P571 ?inception . }}
  OPTIONAL {{ ?member wdt:P576 ?dissolution . }}
  OPTIONAL {{ ?member wdt:P1545 ?ordinal . }}
  OPTIONAL {{ ?member wdt:P176 ?memberManufacturer . }}
}}
ORDER BY ?model ?member ?relation
LIMIT {QUERY_LIMIT}
"""

def fetch_live_snapshot(repo_root: Path) -> bytes:
    parent_manifest, parent_db_path, parent_models = latest_model_pack(repo_root)
    query = build_generation_query([row["model_qid"] for row in parent_models])
    raw_results = fetch_sparql(query)
    payload = {
        "schema_version": 1,
        "retrieved_at_utc": utc_now(),
        "parent_model_pack": {
            "pack_id": parent_manifest["pack_id"],
            "snapshot_id": parent_manifest["snapshot_id"],
            "source_revision": parent_manifest["source_revision"],
            "source_snapshot_sha256": parent_manifest["source_snapshot_sha256"],
            "database_sha256": parent_manifest["database_sha256"],
            "model_entities": parent_manifest["counts"]["model_entities"],
        },
        "parent_models": parent_models,
        "query": query,
        "results": json.loads(raw_results),
    }
    return canonical_json(payload)

def parse_snapshot(snapshot_bytes: bytes) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    payload = json.loads(snapshot_bytes)
    parent_models = payload.get("parent_models")
    bindings = payload.get("results", {}).get("bindings")
    if not isinstance(parent_models, list) or not isinstance(bindings, list):
        raise ValueError("Generation snapshot must include parent_models and results.bindings")
    parent_by_qid = {item["model_qid"]: item for item in parent_models}
    parsed: list[dict[str, Any]] = []
    for index, binding in enumerate(bindings, start=1):
        model_uri = binding_value(binding, "model")
        member_uri = binding_value(binding, "member")
        relation = binding_value(binding, "relation")
        label_en = binding_value(binding, "memberLabelEn")
        if not model_uri or not member_uri or not relation or not label_en:
            raise ValueError(f"generation binding {index} lacks required relationship or label fields")
        model_qid = qid(model_uri)
        member_qid = qid(member_uri)
        if model_qid not in parent_by_qid:
            raise ValueError(f"generation binding {index} references a model outside the pinned parent pack")
        if member_qid == model_qid or relation not in ("P179", "P527"):
            raise ValueError(f"generation binding {index} has an invalid series relationship")
        parent = parent_by_qid[model_qid]
        member_manufacturer_uri = binding_value(binding, "memberManufacturer")
        member_manufacturer_qid = qid(member_manufacturer_uri) if member_manufacturer_uri else None
        parsed.append({
            "binding_index": index,
            "binding_sha256": sha256(canonical_json(binding)),
            "model_qid": model_qid,
            "manufacturer_qid": parent["manufacturer_qid"],
            "model_label_en": parent["model_label_en"],
            "member_qid": member_qid,
            "member_uri": member_uri,
            "member_label_en": label_en.strip(),
            "member_label_ru": (binding_value(binding, "memberLabelRu") or "").strip() or None,
            "relation_property": relation,
            "member_type_qid": qid(binding_value(binding, "memberType")) if binding_value(binding, "memberType") else None,
            "member_manufacturer_qid": member_manufacturer_qid,
            "start": binding_value(binding, "start"),
            "end": binding_value(binding, "end"),
            "inception": binding_value(binding, "inception"),
            "dissolution": binding_value(binding, "dissolution"),
            "ordinal": binding_value(binding, "ordinal"),
        })
    if not parsed:
        raise ValueError("Wikidata returned no model-series member candidates for the pinned parent models")
    return payload, parsed

def logical_content_hash(rows: list[dict[str, Any]]) -> str:
    material = [
        {key: row[key] for key in (
            "model_qid", "manufacturer_qid", "model_label_en", "member_qid",
            "member_label_en", "member_label_ru", "relation_property",
            "member_type_qid", "member_manufacturer_qid", "start", "end",
            "inception", "dissolution", "ordinal", "binding_index", "binding_sha256"
        )}
        for row in rows
    ]
    return sha256(canonical_json(material))

def build_database(
    db_path: Path,
    rows: list[dict[str, Any]],
    parent: dict[str, Any],
    source_revision: str,
    snapshot_sha: str,
    query_sha: str,
) -> dict[str, int]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(row["member_qid"], row["model_qid"])].append(row)
    db = sqlite3.connect(db_path)
    try:
        db.execute("PRAGMA journal_mode=DELETE")
        db.execute("PRAGMA synchronous=FULL")
        db.execute("PRAGMA foreign_keys=ON")
        db.executescript(SCHEMA_SQL)
        db.execute("PRAGMA user_version=1")
        db.execute(
            """INSERT INTO source_registry VALUES (
              :source_id,:publisher,:source_url,:endpoint_url,:license_id,:license_url,
              :rights_status,:commercial_use_allowed,:display_allowed,:offline_cache_allowed,
              :bulk_reuse_allowed,:redistribution_allowed,:attribution_required,:attribution_recommended,
              :share_alike_required,:source_revision,:source_snapshot_sha256,:source_query_sha256,
              :parent_model_source_revision,:parent_model_source_snapshot_sha256,:parent_model_database_sha256,
              :market_scope,:applicability_precision,:review_status,:generation_verified,:exact_vehicle_fitment,
              :engine_code_fitment,:transmission_code_fitment,:ecu_fitment,:dtc_fitment,
              :repair_procedure_fitment,:diagnostic_execution_allowed,:production_years_inferred
            )""",
            {
                "source_id": SOURCE_ID, "publisher": PUBLISHER, "source_url": SOURCE_URL,
                "endpoint_url": ENDPOINT, "license_id": LICENSE_ID, "license_url": LICENSE_URL,
                "rights_status": "approved_by_published_license", "commercial_use_allowed": 1,
                "display_allowed": 1, "offline_cache_allowed": 1, "bulk_reuse_allowed": 1,
                "redistribution_allowed": 1, "attribution_required": 0, "attribution_recommended": 1,
                "share_alike_required": 0, "source_revision": source_revision,
                "source_snapshot_sha256": snapshot_sha, "source_query_sha256": query_sha,
                "parent_model_source_revision": parent["source_revision"],
                "parent_model_source_snapshot_sha256": parent["source_snapshot_sha256"],
                "parent_model_database_sha256": parent["database_sha256"],
                "market_scope": "UNKNOWN", "applicability_precision": "series_member_candidate",
                "review_status": "candidate", "generation_verified": 0, "exact_vehicle_fitment": 0,
                "engine_code_fitment": 0, "transmission_code_fitment": 0, "ecu_fitment": 0,
                "dtc_fitment": 0, "repair_procedure_fitment": 0,
                "diagnostic_execution_allowed": 0, "production_years_inferred": 0,
            },
        )
        for (member_qid, model_qid), group in sorted(grouped.items()):
            group = sorted(group, key=lambda item: item["binding_index"])
            first = group[0]
            def values(key: str) -> list[str]:
                return sorted({item[key] for item in group if item.get(key)})
            types = values("member_type_qid")
            member_manufacturers = values("member_manufacturer_qid")
            relations = values("relation_property")
            indexes = [item["binding_index"] for item in group]
            hashes = [item["binding_sha256"] for item in group]
            parent_manufacturer = first["manufacturer_qid"]
            relation_status = (
                "unknown" if not member_manufacturers
                else "match" if parent_manufacturer in member_manufacturers
                else "mismatch"
            )
            record = {
                "member_qid": member_qid, "model_qid": model_qid,
                "manufacturer_qid": parent_manufacturer,
                "member_label_en": first["member_label_en"],
                "member_label_ru": next((item["member_label_ru"] for item in group if item["member_label_ru"]), None),
                "member_type_qids": types, "member_manufacturer_qids": member_manufacturers,
                "start_dates": values("start"), "end_dates": values("end"),
                "inception_dates": values("inception"), "dissolution_dates": values("dissolution"),
                "series_ordinals": values("ordinal"), "relation_properties": relations,
                "binding_indexes": indexes, "binding_hashes": hashes,
                "manufacturer_relation_status": relation_status,
            }
            db.execute(
                """INSERT INTO model_series_member_candidates (
                  member_qid,model_qid,manufacturer_qid,member_uri,model_label_en,member_label_en,
                  member_label_ru,member_type_qids_json,member_manufacturer_qids_json,start_dates_json,
                  end_dates_json,inception_dates_json,dissolution_dates_json,series_ordinals_json,
                  relation_properties_json,source_binding_indexes_json,source_binding_sha256s_json,
                  source_record_sha256,source_revision,source_snapshot_sha256,source_query_sha256,
                  market_scope,applicability_precision,review_status,manufacturer_relation_status
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    member_qid, model_qid, parent_manufacturer, first["member_uri"], first["model_label_en"],
                    first["member_label_en"], record["member_label_ru"], json.dumps(types),
                    json.dumps(member_manufacturers), json.dumps(record["start_dates"]),
                    json.dumps(record["end_dates"]), json.dumps(record["inception_dates"]),
                    json.dumps(record["dissolution_dates"]), json.dumps(record["series_ordinals"]),
                    json.dumps(relations), json.dumps(indexes), json.dumps(hashes),
                    sha256(canonical_json(record)), source_revision, snapshot_sha, query_sha,
                    "UNKNOWN", "series_member_candidate", "candidate", relation_status,
                ),
            )
        for row in sorted(rows, key=lambda item: item["binding_index"]):
            db.execute(
                "INSERT INTO series_member_source_bindings VALUES (?,?,?,?,?,?,?,?)",
                (
                    row["binding_index"], row["member_qid"], row["model_qid"],
                    row["relation_property"], row["binding_sha256"], source_revision,
                    snapshot_sha, query_sha,
                ),
            )
            for property_id, date_value in (
                ("P571", row["inception"]), ("P576", row["dissolution"]),
                ("P580", row["start"]), ("P582", row["end"]),
            ):
                if date_value:
                    db.execute(
                        "INSERT OR IGNORE INTO series_member_date_statements VALUES (?,?,?,?,?,?,?)",
                        (
                            row["member_qid"], row["model_qid"], property_id, date_value,
                            row["binding_index"], row["binding_sha256"], source_revision,
                        ),
                    )
        db.commit()
        if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("SQLite integrity_check failed")
        if db.execute("PRAGMA foreign_key_check").fetchall():
            raise RuntimeError("SQLite foreign-key check failed")
        return {
            "member_entities": db.execute("SELECT count(DISTINCT member_qid) FROM model_series_member_candidates").fetchone()[0],
            "model_member_links": len(grouped),
            "source_bindings": len(rows),
            "models_with_members": db.execute("SELECT count(DISTINCT model_qid) FROM model_series_member_candidates").fetchone()[0],
            "manufacturers": db.execute("SELECT count(DISTINCT manufacturer_qid) FROM model_series_member_candidates").fetchone()[0],
            "russian_labels": db.execute("SELECT count(*) FROM model_series_member_candidates WHERE member_label_ru IS NOT NULL AND member_label_ru!=''").fetchone()[0],
            "date_statements": db.execute("SELECT count(*) FROM series_member_date_statements").fetchone()[0],
        }
    finally:
        db.close()

def file_info(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {"sha256": sha256(data), "byte_size": len(data)}

def build_pack(snapshot_bytes: bytes, output_dir: Path) -> dict[str, Any]:
    payload, rows = parse_snapshot(snapshot_bytes)
    query_bytes = payload["query"].encode("utf-8")
    snapshot_sha = sha256(snapshot_bytes)
    query_sha = sha256(query_bytes)
    snapshot_id = snapshot_sha[:12]
    source_revision = SOURCE_REVISION_PREFIX + snapshot_id
    parent = payload["parent_model_pack"]
    output_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path = output_dir / "generation-snapshot.json"
    query_path = output_dir / "generation-query.rq"
    license_path = output_dir / "LICENSE-NOTICE.txt"
    attribution_path = output_dir / "ATTRIBUTION.md"
    db_path = output_dir / "wikidata-vag-generations.sqlite"
    snapshot_path.write_bytes(snapshot_bytes)
    query_path.write_bytes(query_bytes)
    license_path.write_text(LICENSE_NOTICE, encoding="utf-8", newline="\n")
    attribution_path.write_text(ATTRIBUTION, encoding="utf-8", newline="\n")
    counts = build_database(db_path, rows, parent, source_revision, snapshot_sha, query_sha)
    logical_sha = logical_content_hash(rows)
    pack_files = {
        path.name: file_info(path)
        for path in (snapshot_path, query_path, license_path, attribution_path, db_path)
    }
    manifest = {
        "schema_version": 1,
        "pack_id": f"wikidata-vag-generation-candidates-cc0-{snapshot_id}",
        "snapshot_id": snapshot_id,
        "built_at_utc": payload.get("retrieved_at_utc") or utc_now(),
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
        "parent_model_pack": parent,
        "counts": counts,
        "query_limit": QUERY_LIMIT,
        "limit_reached": len(rows) >= QUERY_LIMIT,
        "completeness_status": "unknown",
        "scope": {
            "namespace": "vag_model_series_member_candidate",
            "market_scope": "UNKNOWN",
            "completeness_status": "unknown",
            "applicability_precision": "series_member_candidate",
            "review_status": "candidate",
            "generation_entities": counts["member_entities"],
            "generation_verified": False,
            "exact_vehicle_fitment": False,
            "engine_code_fitment": False,
            "transmission_code_fitment": False,
            "ecu_fitment": False,
            "dtc_fitment": False,
            "repair_procedure_fitment": False,
            "diagnostic_execution_allowed": False,
            "production_years_inferred": False,
            "relationship_properties": ["P179", "P527"],
        },
        "exclusions": [
            "Series-member links are candidates, not verified vehicle generations.",
            "No production-year ranges are inferred from Wikidata date properties.",
            "No Russian/EAEU market scope or exact vehicle fitment.",
            "No engine or gearbox codes, ECU identities, DTC definitions, or diagnostic test plans.",
            "No repair procedures, wiring diagrams, pinouts, torque values, adaptations, or OEM parts.",
            "No article text, images, logos, or third-party linked resources.",
        ],
        "pack_files": pack_files,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8", newline="\n"
    )
    verify_pack(output_dir)
    return manifest

def verify_pack(output_dir: Path) -> dict[str, Any]:
    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("data_license") != LICENSE_ID or manifest.get("rights_status") != "approved_by_published_license":
        raise ValueError("CC0 rights metadata is not approved")
    for flag in ("commercial_use_allowed", "display_allowed", "offline_cache_allowed", "bulk_reuse_allowed", "redistribution_allowed"):
        if manifest.get(flag) is not True:
            raise ValueError(f"required CC0 right is not true: {flag}")
    scope = manifest.get("scope", {})
    for field in ("generation_verified", "exact_vehicle_fitment", "engine_code_fitment", "transmission_code_fitment", "ecu_fitment", "dtc_fitment", "repair_procedure_fitment", "diagnostic_execution_allowed", "production_years_inferred"):
        if scope.get(field) is not False:
            raise ValueError(f"candidate-only scope boundary changed: {field}")
    if scope.get("market_scope") != "UNKNOWN" or scope.get("applicability_precision") != "series_member_candidate" or scope.get("completeness_status") != "unknown" or manifest.get("completeness_status") != "unknown" or manifest.get("query_limit") != QUERY_LIMIT:
        raise ValueError("candidate-only scope metadata changed")
    for name, info in manifest["pack_files"].items():
        path = output_dir / name
        if not path.is_file() or file_info(path) != info:
            raise ValueError(f"pack file SHA/size mismatch: {name}")
    db_path = output_dir / "wikidata-vag-generations.sqlite"
    db = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    try:
        if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("SQLite integrity_check failed")
        if db.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("SQLite foreign-key check failed")
        if db.execute("PRAGMA user_version").fetchone()[0] != 1:
            raise ValueError("unexpected SQLite schema version")
        counts = {
            "member_entities": db.execute("SELECT count(DISTINCT member_qid) FROM model_series_member_candidates").fetchone()[0],
            "model_member_links": db.execute("SELECT count(*) FROM model_series_member_candidates").fetchone()[0],
            "source_bindings": db.execute("SELECT count(*) FROM series_member_source_bindings").fetchone()[0],
            "models_with_members": db.execute("SELECT count(DISTINCT model_qid) FROM model_series_member_candidates").fetchone()[0],
            "manufacturers": db.execute("SELECT count(DISTINCT manufacturer_qid) FROM model_series_member_candidates").fetchone()[0],
            "russian_labels": db.execute("SELECT count(*) FROM model_series_member_candidates WHERE member_label_ru IS NOT NULL AND member_label_ru!=''").fetchone()[0],
            "date_statements": db.execute("SELECT count(*) FROM series_member_date_statements").fetchone()[0],
        }
        if counts != manifest["counts"]:
            raise ValueError(f"SQLite counts do not match manifest: {counts}")
        unsafe = db.execute(
            """SELECT count(*) FROM model_series_member_candidates
               WHERE market_scope!='UNKNOWN' OR applicability_precision!='series_member_candidate'
                  OR review_status!='candidate' OR manufacturer_relation_status NOT IN ('match','mismatch','unknown')
                  OR generation_verified!=0 OR exact_vehicle_fitment!=0 OR engine_code_fitment!=0
                  OR transmission_code_fitment!=0 OR ecu_fitment!=0 OR dtc_fitment!=0
                  OR repair_procedure_fitment!=0 OR diagnostic_execution_allowed!=0
                  OR production_years_inferred!=0"""
        ).fetchone()[0]
        if unsafe:
            raise ValueError(f"{unsafe} rows escaped candidate-only generation scope")
        source = db.execute("SELECT * FROM source_registry").fetchone()
        if not source or source["source_id"] != SOURCE_ID or source["license_id"] != LICENSE_ID or source["rights_status"] != "approved_by_published_license":
            raise ValueError("SQLite source registry rights metadata mismatch")
        for field in ("commercial_use_allowed","display_allowed","offline_cache_allowed","bulk_reuse_allowed","redistribution_allowed"):
            if source[field] != 1:
                raise ValueError(f"SQLite source registry reuse right is not approved: {field}")
        if source["market_scope"] != "UNKNOWN" or source["applicability_precision"] != "series_member_candidate" or source["review_status"] != "candidate":
            raise ValueError("SQLite source registry applicability metadata mismatch")
        if source["source_revision"] != manifest["source_revision"] or source["source_snapshot_sha256"] != manifest["source_snapshot_sha256"] or source["source_query_sha256"] != manifest["source_query_sha256"]:
            raise ValueError("SQLite source registry revision/hash mismatch")
        if source["parent_model_source_snapshot_sha256"] != manifest["parent_model_pack"]["source_snapshot_sha256"] or source["parent_model_database_sha256"] != manifest["parent_model_pack"]["database_sha256"]:
            raise ValueError("Parent model-pack provenance mismatch")
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
            snapshot = fetch_live_snapshot(Path.cwd())
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
