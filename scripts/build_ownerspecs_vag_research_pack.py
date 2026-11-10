#!/usr/bin/env python3
"""Build a separate, fail-closed OwnerSpecs CC BY-SA 4.0 VAG research pack."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import tempfile
from datetime import datetime, timezone
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

SOURCE_ID = "ownerspecs-verified-vehicle-specs-cc-by-sa-4.0"
PACK_ID = "ownerspecs-vag-vehicle-specs-research"
ALLOWED_HOSTS = {"ownerspecs.com", "www.ownerspecs.com"}
VAG_BRANDS = {
    "audi", "bentley", "cupra", "lamborghini", "porsche", "seat",
    "skoda", "škoda", "volkswagen", "volkswagen commercial vehicles",
    "volkswagen nutzfahrzeuge", "vw",
}
MAX_DOWNLOAD_BYTES = 16 * 1024 * 1024
VIN_RE = re.compile(r"(?<![A-HJ-NPR-Z0-9])[A-HJ-NPR-Z0-9]{17}(?![A-HJ-NPR-Z0-9])", re.I)
EXPECTED_TABLES = {
    "pack_metadata", "source_registry", "source_files", "generations", "facts"
}


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def read_json(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Expected a regular non-symlink JSON file: {path}")
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def validate_url(url: str) -> None:
    parts = urlsplit(url)
    if (
        parts.scheme != "https"
        or parts.hostname not in ALLOWED_HOSTS
        or parts.username is not None
        or parts.password is not None
        or parts.port not in (None, 443)
        or parts.query
        or parts.fragment
    ):
        raise ValueError("OwnerSpecs URL must be HTTPS on the reviewed publisher host.")


class SameHostRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def acquire_json(url: str, destination: Path) -> dict[str, Any]:
    validate_url(url)
    opener = urllib.request.build_opener(SameHostRedirect())
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "VAG-TECH-PRO-research-pack/1.0",
            "Accept": "application/json",
        },
    )
    with opener.open(request, timeout=30) as response:
        validate_url(response.geturl())
        content_type = response.headers.get_content_type()
        if content_type not in {"application/json", "text/json"}:
            raise ValueError(f"Unexpected OwnerSpecs content type: {content_type}")
        raw = response.read(MAX_DOWNLOAD_BYTES + 1)
    if not raw or len(raw) > MAX_DOWNLOAD_BYTES:
        raise ValueError("OwnerSpecs JSON is empty or exceeds the download limit.")
    parsed = json.loads(raw.decode("utf-8-sig"))
    if not isinstance(parsed, dict):
        raise ValueError("OwnerSpecs dataset root must be a JSON object.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(raw)
    return parsed


def validate_source_manifest(source: dict[str, Any]) -> None:
    if source.get("source_id") != SOURCE_ID:
        raise ValueError("OwnerSpecs source_id mismatch.")
    rights = source.get("rights") or {}
    required_true = (
        "commercial_use_allowed", "display_allowed", "offline_cache_allowed",
        "bulk_reuse_allowed", "redistribution_allowed", "attribution_required",
        "share_alike_required", "separate_pack_required",
    )
    if rights.get("license_id") != "CC-BY-SA-4.0":
        raise ValueError("OwnerSpecs CC BY-SA 4.0 license identifier missing.")
    if rights.get("rights_status") != "approved_by_published_CC_BY_SA_4_0_for_separate_research_pack":
        raise ValueError("OwnerSpecs rights review is not approved for a separate research pack.")
    if any(rights.get(key) is not True for key in required_true):
        raise ValueError("OwnerSpecs rights/Share-Alike/attribution gate failed.")
    policy = source.get("import_policy") or {}
    if (
        policy.get("research_pack_import_allowed") is not True
        or policy.get("require_sharealike_isolated_database") is not True
        or policy.get("require_attribution_in_ui_and_pack") is not True
        or policy.get("production_import") is not False
        or policy.get("product_import_allowed") is not False
    ):
        raise ValueError("OwnerSpecs import policy does not allow this isolated research pack.")
    if source.get("applicability_policy", {}).get("market_scope") != "UNKNOWN":
        raise ValueError("OwnerSpecs market scope must remain UNKNOWN.")


def validate_dataset(dataset: dict[str, Any], source: dict[str, Any]) -> list[dict[str, Any]]:
    if dataset.get("dataset") != "ownerspecs.com — verified vehicle specifications":
        raise ValueError("Unexpected OwnerSpecs dataset identity.")
    if dataset.get("license") != "CC BY-SA 4.0":
        raise ValueError("OwnerSpecs dataset license changed.")
    if dataset.get("license_url") != "https://creativecommons.org/licenses/by-sa/4.0/":
        raise ValueError("OwnerSpecs license URL changed.")
    if dataset.get("attribution_required") is not True:
        raise ValueError("OwnerSpecs attribution requirement missing.")
    attribution = str(dataset.get("attribution") or "")
    if "ownerspecs.com" not in attribution:
        raise ValueError("OwnerSpecs attribution text missing.")
    generations = dataset.get("generations")
    if not isinstance(generations, list):
        raise ValueError("OwnerSpecs generations must be an array.")
    expected_count = source["snapshot"]["json_descriptor_generation_count"]
    expected_points = source["snapshot"]["html_page_verified_datapoint_count"]
    if dataset.get("generation_count") != expected_count or len(generations) != expected_count:
        raise ValueError("OwnerSpecs generation count does not match the reviewed publisher count.")
    if not all(isinstance(item, dict) for item in generations):
        raise ValueError("OwnerSpecs generation array contains a non-object.")
    datapoints = 0
    for generation in generations:
        specs = generation.get("specifications") or []
        masses = generation.get("masses") or []
        tyres = generation.get("tyres") or []
        if not all(isinstance(rows, list) for rows in (specs, masses, tyres)):
            raise ValueError("OwnerSpecs nested fact collection is not an array.")
        nested_count = len(specs) + len(masses) + len(tyres)
        if generation.get("verified_datapoints") != nested_count:
            raise ValueError("OwnerSpecs per-generation verified_datapoints mismatch.")
        datapoints += nested_count
        for fact in [*specs, *masses, *tyres]:
            if not isinstance(fact, dict):
                raise ValueError("OwnerSpecs fact collection contains a non-object.")
            if not isinstance(fact.get("sources", 0), int) or fact.get("sources", 0) < 0:
                raise ValueError("OwnerSpecs source count must be a non-negative integer.")
            provenance = fact.get("provenance", [])
            if not isinstance(provenance, list) or any(not isinstance(x, str) for x in provenance):
                raise ValueError("OwnerSpecs provenance must be an array of strings.")
    if datapoints != expected_points:
        raise ValueError(
            f"OwnerSpecs datapoint count mismatch: expected {expected_points}, got {datapoints}."
        )
    if dataset.get("provenance_kinds") != source["data_scope"]["provenance_kinds"]:
        raise ValueError("OwnerSpecs provenance-kind definitions changed.")
    return generations


def flatten_generation(generation: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    rows: list[tuple[str, dict[str, Any]]] = []
    for fact in generation.get("specifications") or []:
        field = str(fact.get("field") or "")
        category = "dimension" if field.startswith("dim_") else "specification"
        rows.append((category, fact))
    for fact in generation.get("masses") or []:
        rows.append(("mass", fact))
    for fact in generation.get("tyres") or []:
        rows.append(("tyre_pressure", fact))
    return rows


def fact_identity(generation: dict[str, Any], category: str, fact: dict[str, Any]) -> dict[str, Any]:
    return {
        "generation": {
            "brand": generation.get("brand"),
            "model": generation.get("model"),
            "generation": generation.get("generation"),
            "generation_slug": generation.get("generation_slug"),
            "url": generation.get("url"),
            "year_start": generation.get("year_start"),
            "year_end": generation.get("year_end"),
        },
        "category": category,
        "fact": fact,
    }


def build_pack(source_json: Path, source_manifest_path: Path, output_dir: Path) -> dict[str, Any]:
    source = read_json(source_manifest_path)
    validate_source_manifest(source)
    dataset = read_json(source_json)
    generations = validate_dataset(dataset, source)
    snapshot_hash = sha256_file(source_json)
    snapshot_size = source_json.stat().st_size
    pinned_hash = source["snapshot"].get("source_snapshot_sha256")
    if pinned_hash and pinned_hash != snapshot_hash:
        raise ValueError("OwnerSpecs source JSON SHA-256 differs from the pinned manifest.")
    source_manifest_hash = sha256_file(source_manifest_path)
    acquisition_snapshot_path = source_json.parent / "acquisition-snapshot.json"
    if acquisition_snapshot_path.is_file() and not acquisition_snapshot_path.is_symlink():
        acquisition_snapshot = read_json(acquisition_snapshot_path)
        if acquisition_snapshot.get("source_snapshot_sha256") != snapshot_hash:
            raise ValueError("OwnerSpecs acquisition snapshot does not match the source JSON.")
        retrieved_at_utc = acquisition_snapshot.get("retrieved_at_utc")
        if not isinstance(retrieved_at_utc, str) or not retrieved_at_utc.endswith("+00:00"):
            raise ValueError("OwnerSpecs acquisition timestamp must be UTC.")
    else:
        retrieved_at_utc = datetime.now(timezone.utc).isoformat()

    output_dir.mkdir(parents=True, exist_ok=True)
    database_path = output_dir / "ownerspecs-vag-research.sqlite"
    if database_path.exists() or database_path.is_symlink():
        raise FileExistsError(f"Refusing to overwrite an existing research database: {database_path}")
    db = sqlite3.connect(database_path)
    try:
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA journal_mode=DELETE")
        db.execute("PRAGMA synchronous=FULL")
        db.executescript("""
          CREATE TABLE pack_metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
          CREATE TABLE source_registry(
            source_id TEXT PRIMARY KEY,publisher TEXT NOT NULL,dataset_url TEXT NOT NULL,
            data_revision TEXT NOT NULL,license_id TEXT NOT NULL,license_url TEXT NOT NULL,
            rights_status TEXT NOT NULL,commercial_use_allowed INTEGER NOT NULL,
            display_allowed INTEGER NOT NULL,offline_cache_allowed INTEGER NOT NULL,
            bulk_reuse_allowed INTEGER NOT NULL,redistribution_allowed INTEGER NOT NULL,
            attribution_required INTEGER NOT NULL,share_alike_required INTEGER NOT NULL,
            separate_pack_required INTEGER NOT NULL,attribution_text TEXT NOT NULL,
            market_scope TEXT NOT NULL,research_pack_only INTEGER NOT NULL,
            production_import INTEGER NOT NULL,product_import_allowed INTEGER NOT NULL,
            exact_vehicle_fitment INTEGER NOT NULL,exact_engine_code_mapping INTEGER NOT NULL,
            exact_gearbox_code_mapping INTEGER NOT NULL,exact_engine_gearbox_pair INTEGER NOT NULL,
            ru_eaeu_applicability INTEGER NOT NULL,ecu_fitment INTEGER NOT NULL,
            dtc_fitment INTEGER NOT NULL,repair_procedure_applicability INTEGER NOT NULL,
            critical_technical_values_publishable INTEGER NOT NULL
          );
          CREATE TABLE source_files(
            source_file_id TEXT PRIMARY KEY,source_id TEXT NOT NULL REFERENCES source_registry(source_id),
            file_name TEXT NOT NULL,source_revision TEXT NOT NULL,sha256 TEXT NOT NULL,
            byte_size INTEGER NOT NULL,generation_count INTEGER NOT NULL,fact_count INTEGER NOT NULL,
            retrieved_at_utc TEXT NOT NULL
          );
          CREATE TABLE generations(
            generation_id INTEGER PRIMARY KEY,source_id TEXT NOT NULL REFERENCES source_registry(source_id),
            source_ordinal INTEGER NOT NULL,brand TEXT NOT NULL,model TEXT NOT NULL,
            generation_label TEXT NOT NULL,generation_slug TEXT NOT NULL,generation_url TEXT NOT NULL,
            year_start INTEGER,year_end INTEGER,body_type TEXT,dimensions_json TEXT NOT NULL,
            fuel_tank_l_json TEXT,verified_datapoints INTEGER NOT NULL,
            raw_generation_json TEXT NOT NULL,generation_sha256 TEXT NOT NULL,
            publisher_verification_status TEXT NOT NULL,
            technical_review_status TEXT NOT NULL,market_scope TEXT NOT NULL,
            applicability_precision TEXT NOT NULL,model_generation_candidate INTEGER NOT NULL,
            model_year_candidate INTEGER NOT NULL,exact_vehicle_fitment INTEGER NOT NULL,
            exact_engine_code_mapping INTEGER NOT NULL,exact_gearbox_code_mapping INTEGER NOT NULL,
            exact_engine_gearbox_pair INTEGER NOT NULL,ru_eaeu_applicability INTEGER NOT NULL,
            ecu_fitment INTEGER NOT NULL,dtc_fitment INTEGER NOT NULL,repair_procedure_applicability INTEGER NOT NULL,
            UNIQUE(source_id,source_ordinal),UNIQUE(source_id,generation_slug)
          );
          CREATE TABLE facts(
            fact_id INTEGER PRIMARY KEY,generation_id INTEGER NOT NULL REFERENCES generations(generation_id),
            source_ordinal INTEGER NOT NULL,category TEXT NOT NULL,field_key TEXT NOT NULL,label TEXT NOT NULL,
            value_json TEXT,value_max_json TEXT,unit TEXT,is_range INTEGER NOT NULL,
            source_count INTEGER NOT NULL,provenance_json TEXT NOT NULL,raw_fact_json TEXT NOT NULL,
            source_row_sha256 TEXT NOT NULL,primary_document_url TEXT,primary_document_revision TEXT,
            publisher_verification_status TEXT NOT NULL,technical_review_status TEXT NOT NULL,
            market_scope TEXT NOT NULL,applicability_precision TEXT NOT NULL,
            critical_value_publishable INTEGER NOT NULL,exact_engine_code_mapping INTEGER NOT NULL,
            exact_gearbox_code_mapping INTEGER NOT NULL,exact_engine_gearbox_pair INTEGER NOT NULL,
            ru_eaeu_applicability INTEGER NOT NULL,repair_procedure_applicability INTEGER NOT NULL,
            UNIQUE(generation_id,source_ordinal)
          );
          CREATE INDEX idx_ownerspecs_generation_brand_model ON generations(brand,model);
          CREATE INDEX idx_ownerspecs_fact_field ON facts(field_key);
          CREATE INDEX idx_ownerspecs_fact_category ON facts(category);
        """)
        db.execute("BEGIN IMMEDIATE")
        rights = source["rights"]
        policy = source["applicability_policy"]
        attribution = rights["attribution_text"]
        db.execute("""
          INSERT INTO source_registry VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            SOURCE_ID, "ownerspecs.com", source["source_urls"]["dataset_page"],
            source["data_revision"], "CC-BY-SA-4.0", rights["license_url"],
            rights["rights_status"], 1, 1, 1, 1, 1, 1, 1, 1, attribution,
            "UNKNOWN", 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        ))
        flat_vag_generations = []
        for ordinal, generation in enumerate(generations, start=1):
            brand = str(generation.get("brand") or "").strip()
            if brand.casefold() not in VAG_BRANDS:
                continue
            required = ("model", "generation", "generation_slug", "url")
            if any(not str(generation.get(key) or "").strip() for key in required):
                raise ValueError("OwnerSpecs VAG generation lacks a stable identity field.")
            validate_url(str(generation["url"]))
            if generation.get("year_start") is not None and not isinstance(generation["year_start"], int):
                raise ValueError("OwnerSpecs year_start must be an integer or null.")
            if generation.get("year_end") is not None and not isinstance(generation["year_end"], int):
                raise ValueError("OwnerSpecs year_end must be an integer or null.")
            raw_generation = canonical_bytes(generation).decode("utf-8")
            generation_hash = sha256_bytes(raw_generation.encode("utf-8"))
            cur = db.execute("""
              INSERT INTO generations(
                source_id,source_ordinal,brand,model,generation_label,generation_slug,generation_url,
                year_start,year_end,body_type,dimensions_json,fuel_tank_l_json,verified_datapoints,
                raw_generation_json,generation_sha256,publisher_verification_status,technical_review_status,
                market_scope,applicability_precision,model_generation_candidate,model_year_candidate,
                exact_vehicle_fitment,exact_engine_code_mapping,exact_gearbox_code_mapping,
                exact_engine_gearbox_pair,ru_eaeu_applicability,ecu_fitment,dtc_fitment,repair_procedure_applicability
              ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                SOURCE_ID, ordinal, brand, generation["model"], generation["generation"],
                generation["generation_slug"], generation["url"], generation.get("year_start"),
                generation.get("year_end"), generation.get("body_type"),
                json.dumps(generation.get("dimensions_mm") or {}, ensure_ascii=False, sort_keys=True),
                json.dumps(generation.get("fuel_tank_l"), ensure_ascii=False),
                int(generation.get("verified_datapoints") or 0), raw_generation, generation_hash,
                "publisher_verified", "not_independently_reviewed", "UNKNOWN",
                "publisher_generation_candidate_only", 1, 1, 0, 0, 0, 0, 0, 0, 0, 0,
            ))
            generation_id = int(cur.lastrowid)
            flat = flatten_generation(generation)
            if len(flat) != int(generation.get("verified_datapoints") or 0):
                raise ValueError("OwnerSpecs VAG generation fact count mismatch after flattening.")
            for fact_ordinal, (category, fact) in enumerate(flat, start=1):
                field_key = str(fact.get("field") or fact.get("kind") or fact.get("label") or "unclassified").strip()
                label = str(fact.get("label") or fact.get("field") or fact.get("kind") or field_key)
                raw_fact = canonical_bytes(fact_identity(generation, category, fact)).decode("utf-8")
                row_hash = sha256_bytes(raw_fact.encode("utf-8"))
                provenance = fact.get("provenance") or []
                if not isinstance(provenance, list):
                    raise ValueError("OwnerSpecs fact provenance must remain an array.")
                value = fact.get("value", fact.get("value_kg", fact.get("pressure", fact.get("size"))))
                value_max = fact.get("value_max", fact.get("value_max_kg"))
                db.execute("""
                  INSERT INTO facts(
                    generation_id,source_ordinal,category,field_key,label,value_json,value_max_json,unit,
                    is_range,source_count,provenance_json,raw_fact_json,source_row_sha256,
                    primary_document_url,primary_document_revision,publisher_verification_status,
                    technical_review_status,market_scope,applicability_precision,critical_value_publishable,
                    exact_engine_code_mapping,exact_gearbox_code_mapping,exact_engine_gearbox_pair,
                    ru_eaeu_applicability,repair_procedure_applicability
                  ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,NULL,NULL,?,?,?,?,0,0,0,0,0,0)
                """, (
                    generation_id, fact_ordinal, category, field_key, label,
                    None if value is None else json.dumps(value, ensure_ascii=False, sort_keys=True),
                    None if value_max is None else json.dumps(value_max, ensure_ascii=False, sort_keys=True),
                    fact.get("unit"), int(bool(fact.get("is_range"))), int(fact.get("sources") or 0),
                    json.dumps(provenance, ensure_ascii=False, sort_keys=True),
                    raw_fact, row_hash, "publisher_verified", "not_independently_reviewed",
                    "UNKNOWN", "publisher_generation_candidate_only",
                ))
            flat_vag_generations.append(generation)
        if not flat_vag_generations:
            raise ValueError("OwnerSpecs source contains no exact-allowlist VAG generations.")
        vag_fact_count = db.execute("SELECT count(*) FROM facts").fetchone()[0]
        if vag_fact_count != sum(int(g.get("verified_datapoints") or 0) for g in flat_vag_generations):
            raise ValueError("OwnerSpecs VAG fact-count reconciliation failed.")
        db.execute("""
          INSERT INTO source_files VALUES (?,?,?,?,?,?,?,?,?)
        """, (
            "ownerspecs-dataset-json", SOURCE_ID, "dataset.json", source["data_revision"],
            snapshot_hash, snapshot_size, len(generations),
            sum(int(g.get("verified_datapoints") or 0) for g in generations),
            retrieved_at_utc,
        ))
        metadata = {
            "pack_id": PACK_ID,
            "source_id": SOURCE_ID,
            "license_id": "CC-BY-SA-4.0",
            "source_snapshot_sha256": snapshot_hash,
            "source_manifest_sha256": source_manifest_hash,
            "market_scope": "UNKNOWN",
            "status": "verified_research_only",
            "research_pack_only": "true",
            "production_import": "false",
            "product_import_allowed": "false",
            "critical_technical_values_publishable": "false",
        }
        db.executemany("INSERT INTO pack_metadata(key,value) VALUES (?,?)", sorted(metadata.items()))
        db.commit()
    except Exception:
        db.rollback()
        db.close()
        database_path.unlink(missing_ok=True)
        raise
    else:
        db.close()

    attribution_path = output_dir / "ATTRIBUTION.md"
    attribution_path.write_text(
        "# OwnerSpecs attribution\n\n"
        + attribution + "\n\n"
        + "Modified: filtered to the exact reviewed VAG-brand allowlist and stored in a separate "
          "CC BY-SA 4.0 SQLite research pack. Source values and provenance labels are preserved. "
          "Market scope remains UNKNOWN; no primary-document URL/revision is supplied per value; "
          "no critical repair value or exact vehicle fitment is approved.\n",
        encoding="utf-8",
    )
    (output_dir / "LICENSE-REFERENCE.txt").write_text(
        "CC BY-SA 4.0 International\n"
        "https://creativecommons.org/licenses/by-sa/4.0/\n"
        "This database is a separate adapted research pack and must remain under CC BY-SA 4.0.\n",
        encoding="utf-8",
    )
    snapshot = {
        "source_id": SOURCE_ID,
        "source_url": source["source_urls"]["json"],
        "source_revision": source["data_revision"],
        "retrieved_at_utc": retrieved_at_utc,
        "source_file": "source.json",
        "source_file_bytes": snapshot_size,
        "source_snapshot_sha256": snapshot_hash,
        "source_manifest_sha256": source_manifest_hash,
        "generation_count": len(generations),
        "verified_datapoints": sum(int(g.get("verified_datapoints") or 0) for g in generations),
        "vag_generation_count": len(flat_vag_generations),
        "vag_fact_count": vag_fact_count,
    }
    write_json(output_dir / "source-snapshot.json", snapshot)
    pack_manifest = {
        "schema_version": 1,
        "pack_id": PACK_ID,
        "source_id": SOURCE_ID,
        "publisher": "ownerspecs.com",
        "status": "verified_research_only",
        "license": {
            "id": "CC-BY-SA-4.0",
            "url": "https://creativecommons.org/licenses/by-sa/4.0/",
            "share_alike_required": True,
            "separate_database_required": True,
            "attribution_required": True,
            "attribution": attribution,
        },
        "source_revision": source["data_revision"],
        "source_snapshot_sha256": snapshot_hash,
        "source_manifest_sha256": source_manifest_hash,
        "database": {
            "file": database_path.name,
            "sha256": sha256_file(database_path),
            "byte_size": database_path.stat().st_size,
            "integrity_check": "ok",
            "foreign_key_violations": 0,
        },
        "counts": {
            "all_source_generations": len(generations),
            "all_source_verified_datapoints": snapshot["verified_datapoints"],
            "vag_generations": len(flat_vag_generations),
            "vag_facts": vag_fact_count,
        },
        "market_scope": ["UNKNOWN"],
        "publisher_verification_status": "publisher_verified",
        "technical_review_status": "not_independently_reviewed",
        "applicability_precision": "publisher_generation_candidate_only",
        "model_generation_candidate_only": True,
        "model_year_candidate_only": True,
        "exact_factory_engine_code_mapping": False,
        "exact_factory_gearbox_code_mapping": False,
        "exact_engine_gearbox_pair": False,
        "exact_vehicle_fitment": False,
        "ru_eaeu_applicability": False,
        "ecu_fitment": False,
        "dtc_fitment": False,
        "repair_procedure_applicability": False,
        "critical_technical_values_publishable": False,
        "primary_document_locator_per_value": False,
        "primary_document_revision_per_value": False,
        "product_database_ingested": False,
        "production_import": False,
        "product_import_allowed": False,
        "attribution_file": attribution_path.name,
        "license_reference_file": "LICENSE-REFERENCE.txt",
        "source_file": "source.json",
        "source_snapshot_file": "source-snapshot.json",
        "database_file": database_path.name,
        "fact_hash_method": "SHA-256 of compact canonical UTF-8 JSON over generation identity, category and original nested fact object",
    }
    write_json(output_dir / "manifest.json", pack_manifest)
    verify_pack(output_dir, source_manifest_path)
    return pack_manifest


def verify_pack(output_dir: Path, source_manifest_path: Path) -> dict[str, Any]:
    source = read_json(source_manifest_path)
    validate_source_manifest(source)
    manifest = read_json(output_dir / "manifest.json")
    snapshot = read_json(output_dir / "source-snapshot.json")
    dataset = read_json(output_dir / "source.json")
    if manifest.get("pack_id") != PACK_ID or manifest.get("source_id") != SOURCE_ID:
        raise ValueError("OwnerSpecs pack identity mismatch.")
    if manifest.get("license", {}).get("id") != "CC-BY-SA-4.0":
        raise ValueError("OwnerSpecs pack license mismatch.")
    if manifest.get("source_snapshot_sha256") != sha256_file(output_dir / "source.json"):
        raise ValueError("OwnerSpecs source snapshot hash mismatch.")
    if manifest.get("source_manifest_sha256") != sha256_file(source_manifest_path):
        raise ValueError("OwnerSpecs source manifest hash mismatch.")
    generations = validate_dataset(dataset, source)
    db_path = output_dir / "ownerspecs-vag-research.sqlite"
    if sha256_file(db_path) != manifest["database"]["sha256"]:
        raise ValueError("OwnerSpecs SQLite hash mismatch.")
    db = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        integrity = db.execute("PRAGMA integrity_check").fetchall()
        if integrity != [("ok",)]:
            raise ValueError("OwnerSpecs SQLite integrity_check failed.")
        if db.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("OwnerSpecs SQLite foreign_key_check failed.")
        tables = {
            row[0] for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
        }
        if tables != EXPECTED_TABLES:
            raise ValueError("OwnerSpecs SQLite table set mismatch.")
        generation_rows = db.execute("""
          SELECT generation_id,brand,model,generation_label,generation_slug,generation_url,
                 year_start,year_end,raw_generation_json,generation_sha256,market_scope,
                 technical_review_status,applicability_precision,exact_vehicle_fitment,
                 exact_engine_code_mapping,exact_gearbox_code_mapping,exact_engine_gearbox_pair,
                 ru_eaeu_applicability,ecu_fitment,dtc_fitment,repair_procedure_applicability
          FROM generations ORDER BY generation_id
        """).fetchall()
        fact_rows = db.execute("""
          SELECT generation_id,source_ordinal,raw_fact_json,source_row_sha256,market_scope,
                 technical_review_status,critical_value_publishable,exact_engine_code_mapping,
                 exact_gearbox_code_mapping,exact_engine_gearbox_pair,ru_eaeu_applicability,
                 repair_procedure_applicability,primary_document_url,primary_document_revision
          FROM facts ORDER BY generation_id,source_ordinal
        """).fetchall()
        if len(generation_rows) != manifest["counts"]["vag_generations"]:
            raise ValueError("OwnerSpecs generation count mismatch.")
        if len(fact_rows) != manifest["counts"]["vag_facts"]:
            raise ValueError("OwnerSpecs fact count mismatch.")
        for row in generation_rows:
            raw = row[8]
            if sha256_bytes(raw.encode("utf-8")) != row[9]:
                raise ValueError("OwnerSpecs generation row hash mismatch.")
            if row[10] != "UNKNOWN" or row[11] != "not_independently_reviewed" or row[12] != "publisher_generation_candidate_only":
                raise ValueError("OwnerSpecs generation review/applicability boundary failed.")
            if any(row[index] != 0 for index in range(13, 21)):
                raise ValueError("OwnerSpecs generation crossed a production applicability boundary.")
            if row[1].casefold() not in VAG_BRANDS:
                raise ValueError("Non-VAG generation entered the OwnerSpecs VAG pack.")
            if VIN_RE.search(raw):
                raise ValueError("VIN-like content found in OwnerSpecs generation.")
        for row in fact_rows:
            raw = row[2]
            if sha256_bytes(raw.encode("utf-8")) != row[3]:
                raise ValueError("OwnerSpecs fact row hash mismatch.")
            if row[4] != "UNKNOWN" or row[5] != "not_independently_reviewed":
                raise ValueError("OwnerSpecs fact review/applicability boundary failed.")
            if any(row[index] != 0 for index in range(6, 12)):
                raise ValueError("OwnerSpecs fact crossed a critical/production applicability boundary.")
            if row[12] is not None or row[13] is not None:
                raise ValueError("OwnerSpecs fact unexpectedly claims a primary document locator/revision.")
            if VIN_RE.search(raw):
                raise ValueError("VIN-like content found in OwnerSpecs fact.")
        registry = db.execute("SELECT * FROM source_registry").fetchall()
        if len(registry) != 1 or registry[0][0] != SOURCE_ID:
            raise ValueError("OwnerSpecs SQLite source registry mismatch.")
        if (
            registry[0][4] != "CC-BY-SA-4.0"
            or registry[0][5] != "https://creativecommons.org/licenses/by-sa/4.0/"
            or registry[0][6] != source["rights"]["rights_status"]
            or any(registry[0][index] != 1 for index in range(7, 15))
            or "ownerspecs.com" not in registry[0][15]
            or registry[0][16] != "UNKNOWN"
            or registry[0][17] != 1
            or any(registry[0][index] != 0 for index in range(18, 29))
        ):
            raise ValueError("OwnerSpecs SQLite source rights/applicability boundary failed.")
        source_file = db.execute("SELECT sha256,byte_size,generation_count,fact_count FROM source_files").fetchone()
        if (
            source_file is None
            or source_file[0] != manifest["source_snapshot_sha256"]
            or source_file[1] != (output_dir / "source.json").stat().st_size
            or source_file[2] != manifest["counts"]["all_source_generations"]
            or source_file[3] != manifest["counts"]["all_source_verified_datapoints"]
        ):
            raise ValueError("OwnerSpecs SQLite source-file registry mismatch.")
        metadata = dict(db.execute("SELECT key,value FROM pack_metadata"))
        if (
            metadata.get("source_snapshot_sha256") != manifest["source_snapshot_sha256"]
            or metadata.get("source_manifest_sha256") != manifest["source_manifest_sha256"]
            or metadata.get("product_import_allowed") != "false"
            or metadata.get("critical_technical_values_publishable") != "false"
        ):
            raise ValueError("OwnerSpecs SQLite pack metadata boundary failed.")
    finally:
        db.close()
    attribution = (output_dir / "ATTRIBUTION.md").read_text(encoding="utf-8")
    if "ownerspecs.com" not in attribution or "CC BY-SA 4.0" not in attribution:
        raise ValueError("OwnerSpecs attribution file is incomplete.")
    if snapshot.get("source_snapshot_sha256") != manifest["source_snapshot_sha256"]:
        raise ValueError("OwnerSpecs source-snapshot manifest mismatch.")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--acquire", action="store_true")
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--input-json", type=Path)
    args = parser.parse_args()
    if args.verify_only:
        if args.acquire or args.input_json:
            parser.error("--verify-only cannot be combined with --acquire or --input-json")
        manifest = verify_pack(args.output_dir, args.source_manifest)
        print(json.dumps({"status": "verified_research_only", "counts": manifest["counts"], "database_sha256": manifest["database"]["sha256"]}, ensure_ascii=False))
        return 0
    if args.acquire == bool(args.input_json):
        parser.error("Specify exactly one of --acquire or --input-json")
    if args.acquire:
        source = read_json(args.source_manifest)
        validate_source_manifest(source)
        source_json_path = args.output_dir / "source.json"
        if source_json_path.exists() or source_json_path.is_symlink():
            raise FileExistsError(f"Refusing to overwrite an existing OwnerSpecs source snapshot: {source_json_path}")
        raw = acquire_json(source["source_urls"]["json"], source_json_path)
        generations = validate_dataset(raw, source)
        vag_generations = [g for g in generations if str(g.get("brand") or "").strip().casefold() in VAG_BRANDS]
        acquisition_snapshot = {
            "source_id": SOURCE_ID,
            "source_url": source["source_urls"]["json"],
            "source_revision": source["data_revision"],
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
            "source_file": "source.json",
            "source_file_bytes": source_json.stat().st_size,
            "source_snapshot_sha256": sha256_file(args.output_dir / "source.json"),
            "generation_count": len(generations),
            "verified_datapoints": sum(int(g.get("verified_datapoints") or 0) for g in generations),
            "vag_generation_count": len(vag_generations),
            "vag_fact_count": sum(int(g.get("verified_datapoints") or 0) for g in vag_generations),
        }
        write_json(args.output_dir / "acquisition-snapshot.json", acquisition_snapshot)
        source_json = args.output_dir / "source.json"
    else:
        source_json = args.input_json
        if source_json is None or not source_json.is_file():
            parser.error("--input-json must name an existing file")
        args.output_dir.mkdir(parents=True, exist_ok=True)
        destination = args.output_dir / "source.json"
        if source_json.resolve() != destination.resolve():
            if destination.exists():
                raise FileExistsError(f"Refusing to overwrite existing source JSON: {destination}")
            destination.write_bytes(source_json.read_bytes())
        source_json = destination
    manifest = build_pack(source_json, args.source_manifest, args.output_dir)
    print(json.dumps({"status": manifest["status"], "counts": manifest["counts"], "source_snapshot_sha256": manifest["source_snapshot_sha256"], "database_sha256": manifest["database"]["sha256"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
