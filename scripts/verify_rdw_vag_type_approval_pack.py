#!/usr/bin/env python3
"""Independent verifier for the RDW VAG type-approval research SQLite pack."""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

FORBIDDEN = (
    "kenteken", "vin", "chassisnummer", "houder", "owner",
    "tenaamstelling", "address", "postcode", "persoon", "person",
)
SOURCE_ID = "rdw-eu-vag-type-approval-open-data-nl"
PACK_ID = "rdw-vag-type-approval-nl-research"


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_json(value: Any) -> str:
    return sha256_bytes(canonical_json(value))


def safe_record(record: dict[str, Any]) -> None:
    for key in record:
        lowered = str(key).lower()
        if any(token in lowered for token in FORBIDDEN):
            raise RuntimeError(f"Forbidden identity/personal-data key in RDW projection: {key}")


def registration_scope_key(record: dict[str, Any]) -> dict[str, str]:
    return {
        "typegoedkeuringsnummer": str(record.get("typegoedkeuringsnummer") or "").strip(),
        "variant": str(record.get("variant") or "").strip(),
        "version": str(record.get("uitvoering") or "").strip(),
        "revision": str(record.get("volgnummer_wijziging_eu_typegoedkeuring") or "").strip(),
    }


def tgk_scope_key(record: dict[str, Any], variant_field: str) -> dict[str, str]:
    return {
        "typegoedkeuringsnummer": str(record.get("typegoedkeuringsnummer") or "").strip(),
        "variant": str(record.get(variant_field) or "").strip(),
        "version": str(record.get("codeuitvoeringtgk") or "").strip(),
        "revision": str(record.get("volgnummerrevisieuitvoering") or "").strip(),
    }


def scope_id(key: dict[str, str]) -> str:
    return sha256_json(key)


def verify_pack(root: Path) -> dict[str, Any]:
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("pack_id") != PACK_ID or manifest.get("source_id") != SOURCE_ID:
        raise RuntimeError("RDW pack/source identity mismatch")
    if manifest.get("license") != "CC0-1.0" or manifest.get("rights_status") != "approved_by_published_CC0_license":
        raise RuntimeError("RDW pack license/rights status mismatch")
    if manifest.get("snapshot_kind") != "filtered_source_projection_not_full_upstream_snapshot":
        raise RuntimeError("RDW snapshot kind is not explicitly marked as a filtered projection")
    if manifest.get("full_upstream_snapshot") is not False or manifest.get("source_snapshot_sha256") is not None:
        raise RuntimeError("RDW filtered projection must not claim a full upstream snapshot")
    policy = manifest.get("import_policy", {})
    if (
        policy.get("research_pack_only") is not True
        or policy.get("product_import_allowed") is not False
        or policy.get("production_import_allowed") is not False
        or policy.get("ru_eaeu_applicability") is not False
        or policy.get("engine_gearbox_pair_claims") is not False
    ):
        raise RuntimeError("RDW pack production/applicability policy is not fail-closed")
    applicability = manifest.get("applicability", {})
    if any(applicability.get(key) is not False for key in (
        "individual_vehicle_fitment", "production_fitment", "ru_eaeu_applicability",
        "exact_vag_engine_code", "exact_vag_gearbox_code", "exact_engine_gearbox_pair",
        "ecu_dtc_repair_applicability",
    )):
        raise RuntimeError("RDW pack contains a prohibited fitment claim")
    if applicability.get("model_year") is not None or applicability.get("generation") is not None:
        raise RuntimeError("RDW pack must not infer model year or generation")

    projection_entries = manifest.get("source_projections")
    if not isinstance(projection_entries, list) or len(projection_entries) != 6:
        raise RuntimeError("RDW pack must contain exactly six source projections")
    projection_hash_input = []
    projection_rows: dict[str, list[dict[str, Any]]] = {}
    projection_names = set()
    for item in projection_entries:
        name = item["dataset_name"]
        if name in projection_names:
            raise RuntimeError(f"Duplicate RDW source projection: {name}")
        projection_names.add(name)
        path = root / item["projection_path"]
        raw = path.read_bytes()
        if sha256_bytes(raw) != item["projection_sha256"]:
            raise RuntimeError(f"RDW source projection SHA-256 mismatch: {name}")
        projection = json.loads(raw.decode("utf-8"))
        if (
            projection.get("dataset_id") != item["dataset_id"]
            or projection.get("license") != "CC0-1.0"
            or projection.get("market_scope") != ["NL"]
            or projection.get("source_revision") != item["source_revision"]
            or projection.get("row_count") != item["row_count"]
        ):
            raise RuntimeError(f"RDW source projection metadata mismatch: {name}")
        rows = projection.get("rows")
        if not isinstance(rows, list) or len(rows) != item["row_count"]:
            raise RuntimeError(f"RDW source projection row count mismatch: {name}")
        for row in rows:
            record = row.get("record")
            if not isinstance(record, dict):
                raise RuntimeError(f"RDW projection contains a non-object record: {name}")
            safe_record(record)
            if sha256_json(record) != row.get("source_row_sha256"):
                raise RuntimeError(f"RDW source row hash mismatch: {name}")
            variant_field = "variant" if name == "registered_vehicle_identity" else (
                "codevariantgk" if name == "tgk_trade_name" else "codevarianttgk"
            )
            key = registration_scope_key(record) if name == "registered_vehicle_identity" else tgk_scope_key(record, variant_field)
            if any(not key[field] for field in ("typegoedkeuringsnummer", "variant", "version", "revision")):
                raise RuntimeError(f"RDW projection row has incomplete exact scope: {name}")
            if scope_id(key) != row.get("scope_id"):
                raise RuntimeError(f"RDW projection row scope hash mismatch: {name}")
        projection_rows[name] = rows
        projection_hash_input.append({
            "dataset_id": item["dataset_id"],
            "source_revision": item["source_revision"],
            "query_sha256": item["query_sha256"],
            "projection_sha256": item["projection_sha256"],
        })
    if projection_names != {
        "registered_vehicle_identity", "tgk_drive", "tgk_gearbox",
        "tgk_base", "tgk_make", "tgk_trade_name",
    }:
        raise RuntimeError("RDW projection dataset set is incomplete or unexpected")
    expected_bundle_hash = sha256_json(sorted(projection_hash_input, key=lambda value: value["dataset_id"]))
    if expected_bundle_hash != manifest.get("source_projection_bundle_sha256"):
        raise RuntimeError("RDW source projection bundle SHA-256 mismatch")

    db_info = manifest.get("database", {})
    database_path = root / db_info.get("path", "")
    database_bytes = database_path.read_bytes()
    if sha256_bytes(database_bytes) != db_info.get("sha256") or len(database_bytes) != db_info.get("bytes"):
        raise RuntimeError("RDW SQLite database SHA-256/size mismatch")
    if not (root / "ATTRIBUTION.md").is_file() or "CC0" not in (root / "ATTRIBUTION.md").read_text(encoding="utf-8"):
        raise RuntimeError("RDW attribution notice is missing")

    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    try:
        if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("RDW SQLite integrity_check failed")
        if connection.execute("PRAGMA foreign_key_check").fetchall():
            raise RuntimeError("RDW SQLite foreign-key check failed")
        tables = {
            row[0] for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('table','view')"
            )
        }
        if any("pair" in name.lower() for name in tables):
            raise RuntimeError("RDW SQLite contains a forbidden engine/gearbox pair table or view")
        source_rows = connection.execute("SELECT * FROM source_registry ORDER BY dataset_name").fetchall()
        if len(source_rows) != 6:
            raise RuntimeError("RDW SQLite source registry count is not six")
        source_by_name = {row["dataset_name"]: row for row in source_rows}
        table_by_dataset = {
            "registered_vehicle_identity": "registration_observation",
            "tgk_drive": "tgk_drive",
            "tgk_gearbox": "tgk_gearbox",
            "tgk_base": "tgk_base",
            "tgk_make": "tgk_make",
            "tgk_trade_name": "tgk_trade_name",
        }
        entry_by_name = {item["dataset_name"]: item for item in projection_entries}
        for name, table in table_by_dataset.items():
            source = source_by_name.get(name)
            entry = entry_by_name[name]
            if source is None:
                raise RuntimeError(f"RDW SQLite source registry is missing {name}")
            if (
                source["dataset_id"] != entry["dataset_id"]
                or source["license_id"] != "CC0-1.0"
                or source["rights_status"] != "approved_by_published_CC0_license"
                or source["source_revision"] != entry["source_revision"]
                or source["query_sha256"] != entry["query_sha256"]
                or source["projection_sha256"] != entry["projection_sha256"]
                or source["row_count"] != entry["row_count"]
                or source["market_scope"] != "NL"
                or source["production_import_allowed"] != 0
            ):
                raise RuntimeError(f"RDW SQLite source registry mismatch: {name}")
            actual_count = connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            if actual_count != entry["row_count"]:
                raise RuntimeError(f"RDW SQLite row count mismatch: {table}")
            variant_field = None if name == "registered_vehicle_identity" else (
                "codevariantgk" if name == "tgk_trade_name" else "codevarianttgk"
            )
            for row in connection.execute(
                f"SELECT source_row_sha256,scope_id,market_scope,license_id,raw_record_json FROM {table}"
            ):
                record = json.loads(row["raw_record_json"])
                safe_record(record)
                if sha256_json(record) != row["source_row_sha256"]:
                    raise RuntimeError(f"RDW SQLite row hash mismatch: {table}")
                if row["market_scope"] != "NL" or row["license_id"] != "CC0-1.0":
                    raise RuntimeError(f"RDW SQLite row rights/market mismatch: {table}")
                key = registration_scope_key(record) if variant_field is None else tgk_scope_key(record, variant_field)
                if scope_id(key) != row["scope_id"]:
                    raise RuntimeError(f"RDW SQLite exact scope mismatch: {table}")

        scope_rows = connection.execute(
            "SELECT scope_id,type_approval_number,variant,version,revision,market_scope,model_year,generation,"
            "individual_vehicle_fitment,production_fitment,ru_eaeu_applicability,exact_vag_engine_code,"
            "exact_vag_gearbox_code,exact_engine_gearbox_pair,ecu_dtc_repair_applicability FROM approval_scope"
        ).fetchall()
        if len(scope_rows) != manifest["counts"]["approval_scope"]:
            raise RuntimeError("RDW SQLite approval-scope count mismatch")
        for row in scope_rows:
            key = {
                "typegoedkeuringsnummer": row["type_approval_number"],
                "variant": row["variant"],
                "version": row["version"],
                "revision": row["revision"],
            }
            if scope_id(key) != row["scope_id"]:
                raise RuntimeError("RDW SQLite approval-scope key hash mismatch")
            if (
                row["market_scope"] != "NL" or row["model_year"] is not None or row["generation"] is not None
                or any(row[name] != 0 for name in (
                    "individual_vehicle_fitment", "production_fitment", "ru_eaeu_applicability",
                    "exact_vag_engine_code", "exact_vag_gearbox_code", "exact_engine_gearbox_pair",
                    "ecu_dtc_repair_applicability",
                ))
            ):
                raise RuntimeError("RDW SQLite approval-scope applicability policy failed")

        counts = {
            "approval_scope": len(scope_rows),
            "registration_observation": connection.execute("SELECT count(*) FROM registration_observation").fetchone()[0],
            "tgk_drive": connection.execute("SELECT count(*) FROM tgk_drive").fetchone()[0],
            "tgk_gearbox": connection.execute("SELECT count(*) FROM tgk_gearbox").fetchone()[0],
            "tgk_base": connection.execute("SELECT count(*) FROM tgk_base").fetchone()[0],
            "tgk_make": connection.execute("SELECT count(*) FROM tgk_make").fetchone()[0],
            "tgk_trade_name": connection.execute("SELECT count(*) FROM tgk_trade_name").fetchone()[0],
        }
        if counts != manifest.get("counts"):
            raise RuntimeError("RDW SQLite table counts differ from the pack manifest")
        info = connection.execute("SELECT * FROM database_info WHERE id=1").fetchone()
        if (
            info is None
            or info["source_id"] != SOURCE_ID
            or info["source_projection_bundle_sha256"] != expected_bundle_hash
            or info["production_import_allowed"] != 0
            or info["engine_gearbox_pair_claims"] != 0
            or info["ru_eaeu_applicability"] != 0
        ):
            raise RuntimeError("RDW SQLite database_info safety/provenance check failed")
    finally:
        connection.close()

    return {
        "status": "verified_research_only",
        "pack_id": PACK_ID,
        "database_sha256": db_info["sha256"],
        "source_projection_bundle_sha256": expected_bundle_hash,
        "counts": manifest["counts"],
        "market_scope": manifest["market_scope"],
        "product_import_allowed": False,
        "engine_gearbox_pair_claims": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pack-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify_pack(args.pack_dir), ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
