#!/usr/bin/env python3
"""Build a deterministic, rights-cleared Wikidata VAG identity candidate SQLite pack."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

PACK_ID = "wikidata-vag-identity-cc0"
QID_RE = re.compile(r"^Q[1-9][0-9]*$")
ALLOWED_PROPERTIES = {"P31", "P176", "P361", "P155", "P156", "P580", "P582", "P571", "P576"}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_snapshot(snapshot: dict[str, Any], lock: dict[str, Any]) -> list[dict[str, Any]]:
    if snapshot.get("schema_version") != 1 or lock.get("schema_version") != 1:
        raise ValueError("Unsupported Wikidata identity snapshot/lock schema")
    if snapshot.get("source_id") != PACK_ID or lock.get("source_id") != PACK_ID:
        raise ValueError("Wikidata identity source_id mismatch")
    if snapshot.get("data_license") != "CC0-1.0" or lock.get("data_license") != "CC0-1.0":
        raise ValueError("Structured-data license is not explicitly CC0-1.0")
    rights = lock.get("rights", {})
    for key in ("commercial_use_allowed", "display_allowed", "offline_cache_allowed", "redistribution_allowed"):
        if rights.get(key) is not True:
            raise ValueError(f"CC0 rights gate is not approved: {key}")
    if lock.get("rights_status") != "confirmed_by_published_CC0_license_for_structured_data":
        raise ValueError("Wikidata structured-data rights status is not approved")
    if snapshot.get("license_scope") != lock.get("license_scope"):
        raise ValueError("Snapshot and source lock license scopes differ")
    datetime.fromisoformat(str(snapshot.get("retrieved_at", "")).replace("Z", "+00:00"))
    records = snapshot.get("records")
    if not isinstance(records, list) or not records:
        raise ValueError("Wikidata identity snapshot contains no records")
    seen: set[str] = set()
    for row in records:
        qid = row.get("qid")
        if not isinstance(qid, str) or not QID_RE.fullmatch(qid) or qid in seen:
            raise ValueError(f"Invalid or duplicate Wikidata QID: {qid!r}")
        seen.add(qid)
        if not row.get("label") or not row.get("source_revision_id"):
            raise ValueError(f"Missing label or pinned entity revision for {qid}")
        if int(row["source_revision_id"]) <= 0:
            raise ValueError(f"Invalid entity revision for {qid}")
        datetime.fromisoformat(str(row.get("source_modified_at", "")).replace("Z", "+00:00"))
        expected_url = f"https://www.wikidata.org/w/index.php?title={qid}&oldid={row['source_revision_id']}"
        if row.get("source_url") != expected_url or row.get("source_reference_url") != f"https://www.wikidata.org/wiki/{qid}":
            raise ValueError(f"Source URL/revision mismatch for {qid}")
        if row.get("market_scope") != "UNKNOWN" or row.get("applicability_precision") != "global_model_generation_candidate":
            raise ValueError(f"Candidate market/applicability boundary changed for {qid}")
        if row.get("verification_status") != "community_reference_unverified":
            raise ValueError(f"Candidate verification status changed for {qid}")
        for field in ("exact_vehicle_fitment", "engine_fitment", "transmission_fitment", "ecu_fitment",
                      "diagnostic_execution_allowed", "repair_procedure_included", "oem_part_numbers_included"):
            if row.get(field) is not False:
                raise ValueError(f"Prohibited fitment/execution claim for {qid}: {field}")
        if not set(row.get("source_properties", [])).issubset(ALLOWED_PROPERTIES):
            raise ValueError(f"Unexpected Wikidata properties included for {qid}")
        for field in ("year_start", "year_end"):
            value = row.get(field)
            if value is not None and (not isinstance(value, int) or value < 1886 or value > 2100):
                raise ValueError(f"Invalid {field} for {qid}")
        if row.get("year_start") and row.get("year_end") and row["year_start"] > row["year_end"]:
            raise ValueError(f"Year interval is reversed for {qid}")
        for forbidden in ("engine_code", "transmission_code", "ecu_code", "dtc_code", "torque_value", "pinout"):
            if forbidden in row:
                raise ValueError(f"Forbidden technical field in identity snapshot: {forbidden}")
    return records


def build_pack(snapshot_path: Path, lock_path: Path, output_dir: Path) -> dict[str, Any]:
    snapshot = load_json(snapshot_path)
    lock = load_json(lock_path)
    records = validate_snapshot(snapshot, lock)
    output_dir.mkdir(parents=True, exist_ok=True)
    db_path = output_dir / "wikidata-vag-identity.sqlite"
    if db_path.exists():
        db_path.unlink()
    db = sqlite3.connect(db_path)
    try:
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA journal_mode=DELETE")
        db.execute("""
            CREATE TABLE identity_candidates (
                qid TEXT PRIMARY KEY,
                label TEXT NOT NULL,
                entity_kind TEXT NOT NULL,
                manufacturer TEXT,
                brand TEXT,
                model_series TEXT,
                follows TEXT,
                followed_by TEXT,
                start_date TEXT,
                end_date TEXT,
                year_start INTEGER,
                year_end INTEGER,
                date_evidence TEXT,
                source_revision_id INTEGER NOT NULL,
                source_modified_at TEXT NOT NULL,
                source_url TEXT NOT NULL,
                source_reference_url TEXT NOT NULL,
                source_properties_json TEXT NOT NULL,
                market_scope TEXT NOT NULL,
                applicability_precision TEXT NOT NULL,
                verification_status TEXT NOT NULL,
                exact_vehicle_fitment INTEGER NOT NULL CHECK(exact_vehicle_fitment=0),
                engine_fitment INTEGER NOT NULL CHECK(engine_fitment=0),
                transmission_fitment INTEGER NOT NULL CHECK(transmission_fitment=0),
                ecu_fitment INTEGER NOT NULL CHECK(ecu_fitment=0),
                diagnostic_execution_allowed INTEGER NOT NULL CHECK(diagnostic_execution_allowed=0),
                repair_procedure_included INTEGER NOT NULL CHECK(repair_procedure_included=0),
                oem_part_numbers_included INTEGER NOT NULL CHECK(oem_part_numbers_included=0),
                source_id TEXT NOT NULL,
                data_license TEXT NOT NULL,
                retrieved_at TEXT NOT NULL,
                raw_structured_record_json TEXT NOT NULL
            )
        """)
        db.execute("CREATE INDEX idx_wikidata_identity_label ON identity_candidates(label)")
        db.execute("CREATE INDEX idx_wikidata_identity_manufacturer ON identity_candidates(manufacturer)")
        db.execute("CREATE INDEX idx_wikidata_identity_series ON identity_candidates(model_series)")
        db.execute("BEGIN IMMEDIATE")
        for row in records:
            db.execute("""
                INSERT INTO identity_candidates VALUES (
                    :qid,:label,:entity_kind,:manufacturer,:brand,:model_series,:follows,:followed_by,
                    :start_date,:end_date,:year_start,:year_end,:date_evidence,:source_revision_id,
                    :source_modified_at,:source_url,:source_reference_url,:source_properties_json,
                    :market_scope,:applicability_precision,:verification_status,
                    0,0,0,0,0,0,0,:source_id,:data_license,:retrieved_at,:raw_structured_record_json
                )
            """, {
                **row,
                "source_properties_json": json.dumps(row["source_properties"], ensure_ascii=False, separators=(",", ":")),
                "source_id": PACK_ID,
                "data_license": "CC0-1.0",
                "retrieved_at": snapshot["retrieved_at"],
                "raw_structured_record_json": json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
            })
        db.commit()
        db.execute("PRAGMA user_version=1")
        integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise RuntimeError(f"SQLite integrity check failed: {integrity}")
    finally:
        db.close()

    db_hash = sha256_file(db_path)
    snapshot_hash = sha256_file(snapshot_path)
    lock_hash = sha256_file(lock_path)
    revisions = [int(row["source_revision_id"]) for row in records]
    manifest = {
        "schema_version": 1,
        "pack_id": PACK_ID,
        "source_id": PACK_ID,
        "source_name": lock["publisher"],
        "source_url": lock["source_url"],
        "data_license": lock["data_license"],
        "license_url": lock["source_license_url"],
        "license_scope": lock["license_scope"],
        "rights_status": lock["rights_status"],
        "commercial_use_allowed": True,
        "display_allowed": True,
        "offline_cache_allowed": True,
        "redistribution_allowed": True,
        "attribution_required": False,
        "attribution_recommended": True,
        "verification_status": "community_reference_unverified",
        "display_status": "candidate_reference_separate_namespace",
        "product_eligibility": "candidate_reference_only",
        "market_scope": "UNKNOWN",
        "applicability_precision": "global_model_generation_candidate",
        "exact_vehicle_fitment": False,
        "engine_fitment": False,
        "transmission_fitment": False,
        "ecu_fitment": False,
        "diagnostic_execution_allowed": False,
        "repair_procedure_included": False,
        "oem_part_numbers_included": False,
        "database_file": db_path.name,
        "database_sha256": db_hash,
        "source_snapshot_file": "snapshot.json",
        "source_snapshot_sha256": snapshot_hash,
        "source_manifest_file": "source-manifest.json",
        "source_manifest_sha256": lock_hash,
        "retrieved_at": snapshot["retrieved_at"],
        "source_revision_min": min(revisions),
        "source_revision_max": max(revisions),
        "counts": {
            "total": len(records),
            "with_year_start": sum(row["year_start"] is not None for row in records),
            "with_year_end": sum(row["year_end"] is not None for row in records),
            "exact_fitment_claims": 0,
            "engine_fitment_claims": 0,
            "transmission_fitment_claims": 0,
            "ecu_fitment_claims": 0
        },
        "limitations": lock["limitations"]
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output_dir / "source-manifest.json").write_bytes(lock_path.read_bytes())
    (output_dir / "snapshot.json").write_bytes(snapshot_path.read_bytes())
    (output_dir / "LICENSE-CC0-1.0.txt").write_text(
        "Wikidata structured data is made available under CC0 1.0 Universal.\n"
        "License: https://creativecommons.org/publicdomain/zero/1.0/\n"
        "Scope: structured data only; no article prose or media assets are included.\n",
        encoding="utf-8",
    )
    (output_dir / "ATTRIBUTION.txt").write_text(
        "Source: Wikidata contributors — structured vehicle model/generation statements.\n"
        "License: CC0-1.0. Attribution is not required; this notice is provided for provenance.\n"
        "Pinned QID revisions and item URLs are listed in snapshot.json.\n",
        encoding="utf-8",
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = build_pack(args.snapshot, args.lock, args.output)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
