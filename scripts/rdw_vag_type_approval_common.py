#!/usr/bin/env python3
"""Rights-gated RDW VAG type-approval candidate pack utilities.

The pack is an EU type-approval / NL registration research supplement only.
It never asserts RU/EAEU applicability, VIN fitment or VAG factory gearbox codes.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PACK_ID = "rdw-vag-type-approval-cc0"
SOURCE_ID = "rdw-vag-type-approval-cc0"
LICENSE = "CC0-1.0"
LICENSE_URL = "https://creativecommons.org/publicdomain/zero/1.0/"
MARKET_SCOPE = "EU_TYPE_APPROVAL;NL_REGISTRATION_OBSERVATION"
PRECISION = "type_approval_variant_execution_candidate"
VAG_MAKES = {
    "VOLKSWAGEN", "VOLKSWAGEN AG", "VW", "AUDI", "AUDI AG",
    "SKODA", "ŠKODA", "SEAT", "CUPRA", "PORSCHE", "BENTLEY",
    "LAMBORGHINI", "BUGATTI",
}
FORBIDDEN_REGISTRY_FIELDS = {
    "kenteken", "houder", "houdergegevens", "tenaamstelling",
    "datum_tenaamstelling", "datum_tenaamstelling_dt", "wam_verzekerd",
}
DATASETS = {
    "m9d7-ebf2": "RDW vehicle registry",
    "4by9-ammk": "RDW TGK Aandrijving Uitvoering",
    "7rjk-eycs": "RDW TGK Versnelling Uitvoering",
    "byxc-wwua": "RDW TGK Basis Uitvoering",
    "x5v3-sewk": "RDW TGK Handelsbenaming Fabrikant",
}

DDL = """
PRAGMA foreign_keys=ON;
CREATE TABLE dataset_provenance(
  dataset_id TEXT PRIMARY KEY,
  source_name TEXT NOT NULL,
  source_url TEXT NOT NULL,
  data_license TEXT NOT NULL CHECK(data_license='CC0-1.0'),
  license_url TEXT NOT NULL,
  rights_status TEXT NOT NULL CHECK(rights_status='approved_by_published_license'),
  metadata_revision TEXT NOT NULL,
  metadata_sha256 TEXT NOT NULL CHECK(length(metadata_sha256)=64),
  query_sha256 TEXT NOT NULL CHECK(length(query_sha256)=64),
  snapshot_sha256 TEXT NOT NULL CHECK(length(snapshot_sha256)=64),
  fetched_at_utc TEXT NOT NULL,
  row_count INTEGER NOT NULL CHECK(row_count>=0)
);
CREATE TABLE source_snapshots(
  dataset_id TEXT NOT NULL REFERENCES dataset_provenance(dataset_id),
  page_number INTEGER NOT NULL CHECK(page_number>=0),
  request_url TEXT NOT NULL,
  response_sha256 TEXT NOT NULL CHECK(length(response_sha256)=64),
  byte_size INTEGER NOT NULL CHECK(byte_size>=0),
  row_count INTEGER NOT NULL CHECK(row_count>=0),
  snapshot_path TEXT NOT NULL,
  PRIMARY KEY(dataset_id,page_number)
);
CREATE TABLE vehicle_type_approval_candidates(
  vehicle_candidate_id TEXT PRIMARY KEY,
  make_name TEXT NOT NULL,
  model_name TEXT NOT NULL,
  manufacturer_type_code TEXT,
  type_approval_number TEXT NOT NULL,
  variant_code TEXT NOT NULL,
  execution_code TEXT NOT NULL,
  eu_vehicle_category TEXT NOT NULL CHECK(eu_vehicle_category='M1'),
  vehicle_kind TEXT,
  first_registration_seen TEXT,
  last_registration_seen TEXT,
  market_scope TEXT NOT NULL CHECK(market_scope='NL_REGISTRATION_OBSERVATION'),
  applicability_precision TEXT NOT NULL CHECK(applicability_precision='registration_type_approval_variant_execution_candidate'),
  verification_status TEXT NOT NULL CHECK(verification_status='source_published_candidate_not_vin_fitment'),
  source_id TEXT NOT NULL,
  source_revision TEXT NOT NULL,
  exact_vehicle_fitment INTEGER NOT NULL DEFAULT 0 CHECK(exact_vehicle_fitment=0),
  ru_eaeu_applicability INTEGER NOT NULL DEFAULT 0 CHECK(ru_eaeu_applicability=0),
  model_year_verified INTEGER NOT NULL DEFAULT 0 CHECK(model_year_verified=0),
  generation_verified INTEGER NOT NULL DEFAULT 0 CHECK(generation_verified=0)
);
CREATE TABLE approval_execution_revisions(
  revision_candidate_id TEXT PRIMARY KEY,
  type_approval_number TEXT NOT NULL,
  variant_code TEXT NOT NULL,
  execution_code TEXT NOT NULL,
  revision_number TEXT NOT NULL,
  vehicle_category TEXT,
  revision_start_date TEXT,
  revision_end_date TEXT,
  source_id TEXT NOT NULL,
  source_revision TEXT NOT NULL,
  applicability_precision TEXT NOT NULL CHECK(applicability_precision='type_approval_revision_candidate'),
  exact_vehicle_fitment INTEGER NOT NULL DEFAULT 0 CHECK(exact_vehicle_fitment=0)
);
CREATE TABLE engine_approval_candidates(
  engine_candidate_id TEXT PRIMARY KEY,
  type_approval_number TEXT NOT NULL,
  variant_code TEXT NOT NULL,
  execution_code TEXT NOT NULL,
  revision_number TEXT NOT NULL,
  sequence_number TEXT,
  rdw_motorcode TEXT NOT NULL,
  engine_type_approval_number TEXT,
  cylinder_count TEXT,
  displacement TEXT,
  code_namespace TEXT NOT NULL CHECK(code_namespace='RDW.motorcode'),
  vag_factory_engine_code_verified INTEGER NOT NULL DEFAULT 0 CHECK(vag_factory_engine_code_verified=0),
  source_id TEXT NOT NULL,
  source_revision TEXT NOT NULL,
  applicability_precision TEXT NOT NULL CHECK(applicability_precision='type_approval_variant_execution_candidate')
);
CREATE TABLE transmission_approval_candidates(
  transmission_candidate_id TEXT PRIMARY KEY,
  type_approval_number TEXT NOT NULL,
  variant_code TEXT NOT NULL,
  execution_code TEXT NOT NULL,
  revision_number TEXT NOT NULL,
  sequence_number TEXT,
  rdw_transmission_type_code TEXT NOT NULL,
  gear_count_min TEXT,
  gear_count_max TEXT,
  code_namespace TEXT NOT NULL CHECK(code_namespace='RDW.codetypeversnellingsbak'),
  vag_factory_gearbox_code_verified INTEGER NOT NULL DEFAULT 0 CHECK(vag_factory_gearbox_code_verified=0),
  source_id TEXT NOT NULL,
  source_revision TEXT NOT NULL,
  applicability_precision TEXT NOT NULL CHECK(applicability_precision='type_approval_variant_execution_candidate')
);
CREATE TABLE manufacturer_designation_candidates(
  designation_candidate_id TEXT PRIMARY KEY,
  type_approval_number TEXT NOT NULL,
  variant_code TEXT NOT NULL,
  execution_code TEXT NOT NULL,
  revision_number TEXT NOT NULL,
  manufacturer_trade_name TEXT,
  manufacturer_type_designation TEXT,
  source_id TEXT NOT NULL,
  source_revision TEXT NOT NULL,
  applicability_precision TEXT NOT NULL CHECK(applicability_precision='type_approval_variant_execution_candidate')
);
CREATE TABLE engine_transmission_pair_candidates(
  pair_candidate_id TEXT PRIMARY KEY,
  type_approval_number TEXT NOT NULL,
  variant_code TEXT NOT NULL,
  execution_code TEXT NOT NULL,
  revision_number TEXT NOT NULL,
  engine_candidate_id TEXT,
  transmission_candidate_id TEXT,
  engine_row_count INTEGER NOT NULL CHECK(engine_row_count>=0),
  transmission_row_count INTEGER NOT NULL CHECK(transmission_row_count>=0),
  pairing_status TEXT NOT NULL CHECK(pairing_status IN ('unique_source_rows_candidate','ambiguous_multiple_rows_candidate','incomplete_source_rows_candidate')),
  pairing_confirmed INTEGER NOT NULL DEFAULT 0 CHECK(pairing_confirmed=0),
  exact_vehicle_fitment INTEGER NOT NULL DEFAULT 0 CHECK(exact_vehicle_fitment=0),
  ru_eaeu_applicability INTEGER NOT NULL DEFAULT 0 CHECK(ru_eaeu_applicability=0),
  source_id TEXT NOT NULL,
  source_revision TEXT NOT NULL
);
CREATE INDEX idx_vehicle_approval ON vehicle_type_approval_candidates(type_approval_number,variant_code,execution_code);
CREATE INDEX idx_engine_approval ON engine_approval_candidates(type_approval_number,variant_code,execution_code,revision_number);
CREATE INDEX idx_transmission_approval ON transmission_approval_candidates(type_approval_number,variant_code,execution_code,revision_number);
CREATE INDEX idx_pair_approval ON engine_transmission_pair_candidates(type_approval_number,variant_code,execution_code,revision_number);
"""

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

def stable_id(*parts: Any) -> str:
    return sha256_bytes("|".join("" if p is None else str(p) for p in parts).encode("utf-8"))

def text_value(row: dict[str, Any], key: str) -> str | None:
    value = row.get(key)
    if value is None:
        return None
    result = str(value).strip()
    return result if result and result.upper() not in {"N/A", "NULL", "NONE"} else None

def make_is_vag(value: Any) -> bool:
    return str(value or "").strip().upper() in VAG_MAKES

def validate_lock(lock: dict[str, Any]) -> None:
    if lock.get("schema_version") != 1 or lock.get("pack_id") != PACK_ID:
        raise ValueError("RDW lock schema or pack identity mismatch")
    if lock.get("data_license") != LICENSE or lock.get("rights_status") != "approved_by_published_license":
        raise ValueError("RDW CC0 rights gate failed")
    rights = lock.get("rights", {})
    if any(rights.get(k) is not True for k in ("commercial_use_allowed","display_allowed","offline_cache_allowed","bulk_reuse_allowed","redistribution_allowed")):
        raise ValueError("RDW reuse scope is incomplete")
    if rights.get("share_alike_required") is not False:
        raise ValueError("CC0 pack must not acquire a share-alike restriction")
    if rights.get("attribution_required") is not False or rights.get("attribution_recommended") is not False:
        raise ValueError("Public attribution must remain disabled under the provider's open-data notice")
    if rights.get("public_attribution_allowed") is not False or rights.get("internal_provenance_retained") is not True:
        raise ValueError("Public attribution/internal provenance boundary failed")
    if lock.get("applicability_policy", {}).get("ru_eaeu_applicability") is not False:
        raise ValueError("RDW pack must not claim RU/EAEU applicability")
    required = {"m9d7-ebf2","4by9-ammk","7rjk-eycs","byxc-wwua","x5v3-sewk"}
    actual = {str(x.get("id")) for x in lock.get("datasets", []) if x.get("required", True)}
    if actual != required:
        raise ValueError("RDW required dataset set differs from the pinned lock")

def normalize_vehicle_rows(rows: list[dict[str, Any]], source_revision: str) -> list[dict[str, Any]]:
    out = {}
    for row in rows:
        if any(k in row for k in FORBIDDEN_REGISTRY_FIELDS):
            raise ValueError("Registration identifier or holder-related field appeared in the selected response")
        make = text_value(row, "merk")
        model = text_value(row, "handelsbenaming")
        approval = text_value(row, "typegoedkeuringsnummer")
        variant = text_value(row, "variant")
        execution = text_value(row, "uitvoering")
        category = text_value(row, "europese_voertuigcategorie")
        if not make_is_vag(make) or not model or not approval or not variant or not execution or category != "M1":
            continue
        key = (make.upper(), model.upper(), approval, variant, execution)
        item = {
            "vehicle_candidate_id": stable_id(*key),
            "make_name": make,
            "model_name": model,
            "manufacturer_type_code": text_value(row, "type"),
            "type_approval_number": approval,
            "variant_code": variant,
            "execution_code": execution,
            "eu_vehicle_category": "M1",
            "vehicle_kind": text_value(row, "voertuigsoort"),
            "first_registration_seen": text_value(row, "first_registration_seen"),
            "last_registration_seen": text_value(row, "last_registration_seen"),
            "market_scope": "NL_REGISTRATION_OBSERVATION",
            "applicability_precision": "registration_type_approval_variant_execution_candidate",
            "verification_status": "source_published_candidate_not_vin_fitment",
            "source_id": SOURCE_ID,
            "source_revision": source_revision,
            "exact_vehicle_fitment": 0,
            "ru_eaeu_applicability": 0,
            "model_year_verified": 0,
            "generation_verified": 0,
        }
        out[key] = item
    return list(out.values())

def normalize_engine_rows(rows: list[dict[str, Any]], source_revision: str) -> list[dict[str, Any]]:
    out = {}
    for row in rows:
        approval = text_value(row, "typegoedkeuringsnummer")
        variant = text_value(row, "codevarianttgk")
        execution = text_value(row, "codeuitvoeringtgk")
        revision = text_value(row, "volgnummerrevisieuitvoering") or "0"
        motorcode = text_value(row, "motorcode")
        if not all((approval, variant, execution, motorcode)):
            continue
        sequence = text_value(row, "volgnummeraandrijving")
        key = (approval, variant, execution, revision, sequence, motorcode)
        out[key] = {
            "engine_candidate_id": stable_id(*key),
            "type_approval_number": approval,
            "variant_code": variant,
            "execution_code": execution,
            "revision_number": revision,
            "sequence_number": sequence,
            "rdw_motorcode": motorcode,
            "engine_type_approval_number": text_value(row, "typegoedkeuringsnummermotor"),
            "cylinder_count": text_value(row, "aantalcilinders"),
            "displacement": text_value(row, "cilinderinhoud"),
            "code_namespace": "RDW.motorcode",
            "vag_factory_engine_code_verified": 0,
            "source_id": SOURCE_ID,
            "source_revision": source_revision,
            "applicability_precision": PRECISION,
        }
    return list(out.values())

def normalize_transmission_rows(rows: list[dict[str, Any]], source_revision: str) -> list[dict[str, Any]]:
    out = {}
    for row in rows:
        approval = text_value(row, "typegoedkeuringsnummer")
        variant = text_value(row, "codevarianttgk")
        execution = text_value(row, "codeuitvoeringtgk")
        revision = text_value(row, "volgnummerrevisieuitvoering") or "0"
        code = text_value(row, "codetypeversnellingsbak")
        if not all((approval, variant, execution, code)):
            continue
        sequence = text_value(row, "volgnummerversnelling")
        key = (approval, variant, execution, revision, sequence, code)
        out[key] = {
            "transmission_candidate_id": stable_id(*key),
            "type_approval_number": approval,
            "variant_code": variant,
            "execution_code": execution,
            "revision_number": revision,
            "sequence_number": sequence,
            "rdw_transmission_type_code": code,
            "gear_count_min": text_value(row, "aantalversnellingenondergrens"),
            "gear_count_max": text_value(row, "aantalversnellingenbovengrens"),
            "code_namespace": "RDW.codetypeversnellingsbak",
            "vag_factory_gearbox_code_verified": 0,
            "source_id": SOURCE_ID,
            "source_revision": source_revision,
            "applicability_precision": PRECISION,
        }
    return list(out.values())

def normalize_basis_rows(rows: list[dict[str, Any]], source_revision: str) -> list[dict[str, Any]]:
    out = {}
    for row in rows:
        approval = text_value(row, "typegoedkeuringsnummer")
        variant = text_value(row, "codevarianttgk")
        execution = text_value(row, "codeuitvoeringtgk")
        revision = text_value(row, "volgnummerrevisieuitvoering") or "0"
        if not all((approval, variant, execution)):
            continue
        category = text_value(row, "voertuigcategorie")
        if category and category.upper() != "M1":
            continue
        key = (approval, variant, execution, revision)
        out[key] = {
            "revision_candidate_id": stable_id(*key),
            "type_approval_number": approval,
            "variant_code": variant,
            "execution_code": execution,
            "revision_number": revision,
            "vehicle_category": text_value(row, "voertuigcategorie"),
            "revision_start_date": text_value(row, "begindatumrevisieuitvoering"),
            "revision_end_date": text_value(row, "einddatumrevisieuitvoering"),
            "source_id": SOURCE_ID,
            "source_revision": source_revision,
            "applicability_precision": "type_approval_revision_candidate",
            "exact_vehicle_fitment": 0,
        }
    return list(out.values())

def normalize_designation_rows(rows: list[dict[str, Any]], source_revision: str) -> list[dict[str, Any]]:
    out = {}
    for row in rows:
        approval = text_value(row, "typegoedkeuringsnummer")
        variant = text_value(row, "codevariantgk")
        execution = text_value(row, "codeuitvoeringtgk")
        revision = text_value(row, "volgnummerrevisieuitvoering") or "0"
        if not all((approval, variant, execution)):
            continue
        name = text_value(row, "handelsbenamingfabrikant")
        type_name = text_value(row, "typeaanduidingfabrikant")
        if not name and not type_name:
            continue
        key = (approval, variant, execution, revision, name, type_name, text_value(row, "volgnummerhandelsbenamingfabr"))
        out[key] = {
            "designation_candidate_id": stable_id(*key),
            "type_approval_number": approval,
            "variant_code": variant,
            "execution_code": execution,
            "revision_number": revision,
            "manufacturer_trade_name": name,
            "manufacturer_type_designation": type_name,
            "source_id": SOURCE_ID,
            "source_revision": source_revision,
            "applicability_precision": PRECISION,
        }
    return list(out.values())

def build_database(output_dir: Path, lock_path: Path, payloads: dict[str, list[dict[str, Any]]],
                   metadata: dict[str, dict[str, Any]], snapshots: list[dict[str, Any]],
                   queries: dict[str, str], fetched_at: str) -> dict[str, Any]:
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    validate_lock(lock)
    output_dir = Path(output_dir)
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError("Refusing to overwrite a non-empty RDW pack output directory")
    output_dir.mkdir(parents=True, exist_ok=True)
    snapshot_dir = output_dir / "snapshots"
    snapshot_dir.mkdir()
    license_text = (
        "Creative Commons CC0 1.0 Universal. The RDW data in this pack is marked for public-domain dedication "
        "or made available under CC0-1.0. See https://creativecommons.org/publicdomain/zero/1.0/ .\n"
    )
    attribution_text = (
        "CC0-1.0. Public attribution is intentionally omitted under the provider's open-data notice. "
        "Publisher identity, dataset URLs, revisions and hashes remain in the internal provenance manifest "
        "for audit and are not rendered in the product interface.\n"
    )
    (output_dir / "LICENSE-CC0-1.0.txt").write_text(license_text, encoding="utf-8")
    (output_dir / "ATTRIBUTION.md").write_text(attribution_text, encoding="utf-8")

    dataset_revisions = {}
    dataset_provenance = []
    for dataset_id, meta in metadata.items():
        revision = str(meta.get("rowsUpdatedAt") or meta.get("metadataUpdatedAt") or meta.get("viewLastModified") or sha256_bytes(canonical_json(meta))[:16])
        dataset_revisions[dataset_id] = revision
    revision_bundle = sha256_bytes(canonical_json(dataset_revisions))
    source_revision = "rdw-" + revision_bundle[:20]

    vehicles = normalize_vehicle_rows(payloads.get("m9d7-ebf2", []), source_revision)
    vehicle_keys = {(v["type_approval_number"],v["variant_code"],v["execution_code"]) for v in vehicles}
    engines = [r for r in normalize_engine_rows(payloads.get("4by9-ammk", []), source_revision) if (r["type_approval_number"],r["variant_code"],r["execution_code"]) in vehicle_keys]
    transmissions = [r for r in normalize_transmission_rows(payloads.get("7rjk-eycs", []), source_revision) if (r["type_approval_number"],r["variant_code"],r["execution_code"]) in vehicle_keys]
    basis = [r for r in normalize_basis_rows(payloads.get("byxc-wwua", []), source_revision) if (r["type_approval_number"],r["variant_code"],r["execution_code"]) in vehicle_keys]
    designations = [r for r in normalize_designation_rows(payloads.get("x5v3-sewk", []), source_revision) if (r["type_approval_number"],r["variant_code"],r["execution_code"]) in vehicle_keys]

    if not vehicles:
        raise ValueError("RDW VAG M1 registration query returned no eligible type-approval candidates")
    if not engines:
        raise ValueError("RDW TGK engine table returned no VAG approval-linked motorcode candidates")
    if not transmissions:
        raise ValueError("RDW TGK transmission table returned no VAG approval-linked transmission-type candidates")

    db_path = output_dir / "rdw-vag-type-approval.sqlite"
    db = sqlite3.connect(db_path)
    try:
        db.executescript(DDL)
        for dataset_id, meta in metadata.items():
            ds_snapshots = [s for s in snapshots if s["dataset_id"] == dataset_id]
            snap_sha = sha256_bytes("".join(s["response_sha256"] for s in ds_snapshots).encode("ascii"))
            query_sha = sha256_bytes(queries[dataset_id].encode("utf-8"))
            metadata_sha = meta["metadata_sha256"]
            revision = dataset_revisions[dataset_id]
            row_count = sum(s["row_count"] for s in ds_snapshots)
            dataset_provenance.append({
                "dataset_id": dataset_id,
                "source_name": DATASETS[dataset_id],
                "source_url": "https://opendata.rdw.nl/resource/" + dataset_id + ".json",
                "data_license": LICENSE,
                "license_url": LICENSE_URL,
                "rights_status": "approved_by_published_license",
                "metadata_revision": revision,
                "metadata_sha256": metadata_sha,
                "query_sha256": query_sha,
                "snapshot_sha256": snap_sha,
                "fetched_at_utc": fetched_at,
                "row_count": row_count,
            })
            db.execute(
                "INSERT INTO dataset_provenance VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                (dataset_id, DATASETS[dataset_id], "https://opendata.rdw.nl/resource/" + dataset_id + ".json",
                 LICENSE, LICENSE_URL, "approved_by_published_license", revision, metadata_sha,
                 query_sha, snap_sha, fetched_at, row_count)
            )
        for snap in snapshots:
            relative = "snapshots/" + snap["snapshot_name"]
            (snapshot_dir / snap["snapshot_name"]).write_bytes(snap["response_bytes"])
            db.execute(
                "INSERT INTO source_snapshots VALUES(?,?,?,?,?,?,?)",
                (snap["dataset_id"], snap["page_number"], snap["request_url"], snap["response_sha256"],
                 snap["byte_size"], snap["row_count"], relative)
            )
        db.executemany(
            "INSERT INTO vehicle_type_approval_candidates VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [(v["vehicle_candidate_id"],v["make_name"],v["model_name"],v["manufacturer_type_code"],v["type_approval_number"],
              v["variant_code"],v["execution_code"],v["eu_vehicle_category"],v["vehicle_kind"],v["first_registration_seen"],
              v["last_registration_seen"],v["market_scope"],v["applicability_precision"],v["verification_status"],v["source_id"],
              v["source_revision"],v["exact_vehicle_fitment"],v["ru_eaeu_applicability"],v["model_year_verified"],v["generation_verified"])
             for v in vehicles]
        )
        db.executemany(
            "INSERT INTO approval_execution_revisions VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            [(r["revision_candidate_id"],r["type_approval_number"],r["variant_code"],r["execution_code"],r["revision_number"],
              r["vehicle_category"],r["revision_start_date"],r["revision_end_date"],r["source_id"],r["source_revision"],
              r["applicability_precision"],r["exact_vehicle_fitment"])
             for r in basis]
        )
        db.executemany(
            "INSERT INTO engine_approval_candidates VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [(e["engine_candidate_id"],e["type_approval_number"],e["variant_code"],e["execution_code"],e["revision_number"],
              e["sequence_number"],e["rdw_motorcode"],e["engine_type_approval_number"],e["cylinder_count"],e["displacement"],
              e["code_namespace"],e["vag_factory_engine_code_verified"],e["source_id"],e["source_revision"],e["applicability_precision"])
             for e in engines]
        )
        db.executemany(
            "INSERT INTO transmission_approval_candidates VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [(t["transmission_candidate_id"],t["type_approval_number"],t["variant_code"],t["execution_code"],t["revision_number"],
              t["sequence_number"],t["rdw_transmission_type_code"],t["gear_count_min"],t["gear_count_max"],t["code_namespace"],
              t["vag_factory_gearbox_code_verified"],t["source_id"],t["source_revision"],t["applicability_precision"])
             for t in transmissions]
        )
        db.executemany(
            "INSERT INTO manufacturer_designation_candidates VALUES(?,?,?,?,?,?,?,?,?,?)",
            [(d["designation_candidate_id"],d["type_approval_number"],d["variant_code"],d["execution_code"],d["revision_number"],
              d["manufacturer_trade_name"],d["manufacturer_type_designation"],d["source_id"],d["source_revision"],d["applicability_precision"])
             for d in designations]
        )

        engine_groups = defaultdict(list)
        transmission_groups = defaultdict(list)
        for e in engines:
            engine_groups[(e["type_approval_number"],e["variant_code"],e["execution_code"],e["revision_number"])].append(e)
        for t in transmissions:
            transmission_groups[(t["type_approval_number"],t["variant_code"],t["execution_code"],t["revision_number"])].append(t)
        for key in sorted(set(engine_groups) | set(transmission_groups)):
            es = engine_groups.get(key, [])
            ts = transmission_groups.get(key, [])
            unique = len(es) == 1 and len(ts) == 1
            status = "unique_source_rows_candidate" if unique else (
                "ambiguous_multiple_rows_candidate" if es and ts else "incomplete_source_rows_candidate"
            )
            pair_id = stable_id(*key)
            db.execute(
                "INSERT INTO engine_transmission_pair_candidates VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (pair_id,*key,es[0]["engine_candidate_id"] if unique else None,
                 ts[0]["transmission_candidate_id"] if unique else None,len(es),len(ts),status,0,0,0,SOURCE_ID,source_revision)
            )
        db.commit()
        db.execute("PRAGMA foreign_key_check")
        if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("RDW pack SQLite integrity_check failed")
        if db.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("RDW pack SQLite foreign_key_check failed")
    finally:
        db.close()

    snapshot_files = sorted((snapshot_dir).glob("*.json"))
    snapshot_bundle_sha = sha256_bytes("".join(sha256_file(p) for p in snapshot_files).encode("ascii"))
    manifest = {
        "schema_version": 1,
        "pack_id": PACK_ID,
        "source_id": SOURCE_ID,
        "publisher": "RDW — Netherlands Vehicle Authority",
        "source_revision": source_revision,
        "dataset_revisions": dataset_revisions,
        "data_license": LICENSE,
        "license_url": LICENSE_URL,
        "rights_status": "approved_by_published_license",
        "market_scope": ["EU_TYPE_APPROVAL","NL_REGISTRATION_OBSERVATION"],
        "applicability_precision": PRECISION,
        "verification_status": "verified_source_candidate_pack_only",
        "exact_vehicle_fitment": False,
        "ru_eaeu_applicability": False,
        "generation_verified": False,
        "model_year_verified": False,
        "vag_factory_engine_code_verified": False,
        "vag_factory_gearbox_code_verified": False,
        "diagnostic_execution_allowed": False,
        "no_license_plate_retained": True,
        "no_personal_or_holder_data_retained": True,
        "source_manifest_sha256": sha256_file(lock_path),
        "source_snapshot_sha256": snapshot_bundle_sha,
        "database_sha256": sha256_file(db_path),
        "license_sha256": sha256_file(output_dir / "LICENSE-CC0-1.0.txt"),
        "attribution_sha256": sha256_file(output_dir / "ATTRIBUTION.md"),
        "fetched_at_utc": fetched_at,
        "dataset_provenance": dataset_provenance,
        "snapshot_count": len(snapshots),
        "counts": {
            "vehicle_variants": len(vehicles),
            "engine_candidates": len(engines),
            "transmission_candidates": len(transmissions),
            "approval_revision_candidates": len(basis),
            "manufacturer_designation_candidates": len(designations),
            "unique_source_row_pair_candidates": sum(1 for k in set(engine_groups)|set(transmission_groups) if len(engine_groups.get(k,[]))==1 and len(transmission_groups.get(k,[]))==1),
            "ambiguous_or_incomplete_pair_keys": sum(1 for k in set(engine_groups)|set(transmission_groups) if not (len(engine_groups.get(k,[]))==1 and len(transmission_groups.get(k,[]))==1)),
        },
        "pairing_rule": "Only a unique one-engine-row plus one-transmission-row key is represented as a candidate pair; pairing_confirmed remains false and no VIN fitment is asserted.",
        "limitations": [
            "EU type-approval / NL registration supplement only; no RU/EAEU applicability.",
            "RDW.motorcode is not automatically a VAG factory engine code.",
            "RDW.codetypeversnellingsbak is not a VAG factory gearbox code.",
            "Registration observations are not model-year or production-date claims.",
            "No generation, ECU, DTC, repair, wiring, pinout, torque or adaptation applicability.",
        ],
    }
    (output_dir / "manifest.json").write_bytes(canonical_json(manifest) + b"\n")
    return manifest

def verify_pack(output_dir: Path, lock_path: Path) -> dict[str, Any]:
    output_dir = Path(output_dir)
    lock = json.loads(Path(lock_path).read_text(encoding="utf-8"))
    validate_lock(lock)
    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("pack_id") != PACK_ID or manifest.get("data_license") != LICENSE:
        raise ValueError("RDW pack identity or license mismatch")
    if manifest.get("exact_vehicle_fitment") is not False or manifest.get("ru_eaeu_applicability") is not False:
        raise ValueError("RDW candidate-only scope was promoted")
    if manifest.get("no_license_plate_retained") is not True or manifest.get("no_personal_or_holder_data_retained") is not True:
        raise ValueError("RDW privacy minimisation evidence is missing")
    db_path = output_dir / "rdw-vag-type-approval.sqlite"
    if sha256_file(db_path) != manifest.get("database_sha256"):
        raise ValueError("RDW SQLite SHA-256 mismatch")
    if sha256_file(output_dir / "LICENSE-CC0-1.0.txt") != manifest.get("license_sha256"):
        raise ValueError("RDW license SHA-256 mismatch")
    notice = (output_dir / "ATTRIBUTION.md").read_text(encoding="utf-8")
    if "rdw" in notice.lower() or "opendata.rdw.nl" in notice.lower():
        raise ValueError("Public attribution notice must not identify the data provider")
    if sha256_file(output_dir / "ATTRIBUTION.md") != manifest.get("attribution_sha256"):
        raise ValueError("Public attribution notice SHA-256 mismatch")
    if sha256_file(Path(lock_path)) != manifest.get("source_manifest_sha256"):
        raise ValueError("RDW lock SHA-256 mismatch")
    snapshot_dir = output_dir / "snapshots"
    snapshot_files = sorted(snapshot_dir.glob("*.json"))
    snapshot_hash = sha256_bytes("".join(sha256_file(p) for p in snapshot_files).encode("ascii"))
    if snapshot_hash != manifest.get("source_snapshot_sha256"):
        raise ValueError("RDW snapshot bundle SHA-256 mismatch")
    metadata_files = manifest.get("metadata_files", [])
    if not metadata_files:
        raise ValueError("RDW raw metadata snapshots are missing")
    for item in metadata_files:
        metadata_path = output_dir / item["path"]
        if not metadata_path.is_file() or sha256_file(metadata_path) != item.get("sha256"):
            raise ValueError("RDW metadata snapshot SHA-256 mismatch")
        if metadata_path.stat().st_size != item.get("byte_size"):
            raise ValueError("RDW metadata snapshot byte-size mismatch")
        metadata_json = json.loads(metadata_path.read_text(encoding="utf-8"))
        if str(metadata_json.get("id")) != item.get("dataset_id"):
            raise ValueError("RDW metadata snapshot dataset identity mismatch")
    metadata_bundle = sha256_bytes("".join(x["sha256"] for x in sorted(metadata_files,key=lambda x:x["dataset_id"])).encode("ascii"))
    if metadata_bundle != manifest.get("metadata_bundle_sha256"):
        raise ValueError("RDW metadata bundle SHA-256 mismatch")
    metadata_by_id = {x["dataset_id"]:x["sha256"] for x in metadata_files}
    db = sqlite3.connect(f"file:{db_path.resolve().as_posix()}?mode=ro", uri=True)
    try:
        if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("RDW SQLite integrity_check failed")
        if db.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("RDW SQLite foreign_key_check failed")
        counts = {
            "vehicle_variants": db.execute("SELECT count(*) FROM vehicle_type_approval_candidates").fetchone()[0],
            "engine_candidates": db.execute("SELECT count(*) FROM engine_approval_candidates").fetchone()[0],
            "transmission_candidates": db.execute("SELECT count(*) FROM transmission_approval_candidates").fetchone()[0],
            "approval_revision_candidates": db.execute("SELECT count(*) FROM approval_execution_revisions").fetchone()[0],
            "manufacturer_designation_candidates": db.execute("SELECT count(*) FROM manufacturer_designation_candidates").fetchone()[0],
            "unique_source_row_pair_candidates": db.execute("SELECT count(*) FROM engine_transmission_pair_candidates WHERE pairing_status='unique_source_rows_candidate'").fetchone()[0],
            "ambiguous_or_incomplete_pair_keys": db.execute("SELECT count(*) FROM engine_transmission_pair_candidates WHERE pairing_status<>'unique_source_rows_candidate'").fetchone()[0],
        }
        if counts != manifest.get("counts"):
            raise ValueError("RDW pack row counts differ from manifest")
        if db.execute("SELECT count(*) FROM vehicle_type_approval_candidates WHERE exact_vehicle_fitment<>0 OR ru_eaeu_applicability<>0 OR model_year_verified<>0 OR generation_verified<>0").fetchone()[0]:
            raise ValueError("RDW vehicle candidates contain a promoted applicability claim")
        if db.execute("SELECT count(*) FROM engine_approval_candidates WHERE code_namespace<>'RDW.motorcode' OR vag_factory_engine_code_verified<>0").fetchone()[0]:
            raise ValueError("RDW engine namespace/verification gate failed")
        if db.execute("SELECT count(*) FROM transmission_approval_candidates WHERE code_namespace<>'RDW.codetypeversnellingsbak' OR vag_factory_gearbox_code_verified<>0").fetchone()[0]:
            raise ValueError("RDW transmission namespace/verification gate failed")
        if db.execute("SELECT count(*) FROM engine_transmission_pair_candidates WHERE pairing_confirmed<>0 OR exact_vehicle_fitment<>0 OR ru_eaeu_applicability<>0").fetchone()[0]:
            raise ValueError("RDW pair candidate was promoted")
        if db.execute("SELECT count(*) FROM engine_transmission_pair_candidates WHERE pairing_status='unique_source_rows_candidate' AND (engine_row_count<>1 OR transmission_row_count<>1 OR engine_candidate_id IS NULL OR transmission_candidate_id IS NULL)").fetchone()[0]:
            raise ValueError("RDW unique candidate pair has inconsistent row counts")
        if db.execute("SELECT count(*) FROM engine_transmission_pair_candidates WHERE pairing_status<>'unique_source_rows_candidate' AND (engine_candidate_id IS NOT NULL OR transmission_candidate_id IS NOT NULL)").fetchone()[0]:
            raise ValueError("RDW ambiguous pair was linked")
        snapshot_rows = db.execute("SELECT dataset_id,response_sha256,byte_size,row_count,snapshot_path FROM source_snapshots ORDER BY dataset_id,page_number").fetchall()
        if len(snapshot_rows) != manifest.get("snapshot_count"):
            raise ValueError("RDW snapshot row count differs from manifest")
        for dataset_id,response_hash,byte_size,row_count,snapshot_path in snapshot_rows:
            snapshot_path_obj = output_dir / snapshot_path
            if not snapshot_path_obj.is_file() or sha256_file(snapshot_path_obj) != response_hash:
                raise ValueError("RDW raw response snapshot SHA-256 mismatch")
            if snapshot_path_obj.stat().st_size != byte_size:
                raise ValueError("RDW raw response snapshot byte-size mismatch")
            response_json = json.loads(snapshot_path_obj.read_text(encoding="utf-8"))
            if not isinstance(response_json,list) or len(response_json) != row_count:
                raise ValueError("RDW raw response snapshot row-count mismatch")
            if dataset_id == "m9d7-ebf2":
                for row in response_json:
                    if set(str(k).lower() for k in row).intersection(FORBIDDEN_REGISTRY_FIELDS):
                        raise ValueError("RDW raw registration snapshot contains an excluded field")
        if db.execute("SELECT count(*) FROM source_snapshots WHERE length(response_sha256)<>64").fetchone()[0]:
            raise ValueError("RDW snapshot hash missing")
        provenance_rows = db.execute("SELECT dataset_id,metadata_sha256,query_sha256,snapshot_sha256,row_count FROM dataset_provenance ORDER BY dataset_id").fetchall()
        if len(provenance_rows) != len(metadata_files):
            raise ValueError("RDW dataset provenance count differs from metadata files")
        snapshot_by_dataset = defaultdict(list)
        for dataset_id,page_number,request_url,response_hash,row_count in db.execute("SELECT dataset_id,page_number,request_url,response_sha256,row_count FROM source_snapshots ORDER BY dataset_id,page_number"):
            snapshot_by_dataset[dataset_id].append((request_url,response_hash,row_count))
        for dataset_id,metadata_hash,query_hash,snapshot_hash,row_count in provenance_rows:
            if metadata_by_id.get(dataset_id) != metadata_hash:
                raise ValueError("RDW metadata hash differs between SQLite and manifest")
            entries = snapshot_by_dataset.get(dataset_id,[])
            expected_query_hash = sha256_bytes("\n".join(x[0] for x in entries).encode("utf-8"))
            expected_snapshot_hash = sha256_bytes("".join(x[1] for x in entries).encode("ascii"))
            if query_hash != expected_query_hash or snapshot_hash != expected_snapshot_hash:
                raise ValueError("RDW per-dataset query or snapshot provenance hash mismatch")
            if row_count != sum(x[2] for x in entries):
                raise ValueError("RDW per-dataset row count differs from snapshots")
        if db.execute("SELECT count(*) FROM dataset_provenance WHERE data_license<>'CC0-1.0' OR rights_status<>'approved_by_published_license'").fetchone()[0]:
            raise ValueError("RDW dataset rights gate failed")
        if db.execute("SELECT count(*) FROM vehicle_type_approval_candidates WHERE market_scope<>'NL_REGISTRATION_OBSERVATION' OR exact_vehicle_fitment<>0 OR ru_eaeu_applicability<>0").fetchone()[0]:
            raise ValueError("RDW vehicle market/applicability gate failed")
        if db.execute("SELECT count(*) FROM engine_transmission_pair_candidates WHERE pairing_confirmed<>0 OR exact_vehicle_fitment<>0 OR ru_eaeu_applicability<>0").fetchone()[0]:
            raise ValueError("RDW pair candidate was promoted")
    finally:
        db.close()
    return {"status":"verified_source_candidate_pack_only","counts":counts,"source_revision":manifest["source_revision"],"database_sha256":manifest["database_sha256"],"source_snapshot_sha256":manifest["source_snapshot_sha256"]}
