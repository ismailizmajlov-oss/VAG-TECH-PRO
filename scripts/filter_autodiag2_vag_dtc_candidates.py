#!/usr/bin/env python3
"""Fail-closed filtering of AutoDiag2 VAG DTC candidates before redistribution.

AutoDiag2's generic-manufacturer ECU labels (for example, ECU manufacturer
"generic", model "audi") are not proof of VAG ECU identity. Make-level rows
must not be presented as VAG-specific DTCs. Only candidate rows explicitly
linked by the upstream source to a VAG vehicle configuration and a
non-generic ECU identity can remain in this research-only pack.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

PACK_ID = "autodiag2-vag-community-v6"
GENERIC_ECU_MANUFACTURERS = {"", "generic", "generic_ecu", "unknown", "n/a", "na"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def count(conn: sqlite3.Connection, table: str, where: str = "") -> int:
    sql = f'SELECT COUNT(*) FROM "{table}"'
    if where:
        sql += f" WHERE {where}"
    return int(conn.execute(sql).fetchone()[0])


def require_columns(conn: sqlite3.Connection, table: str, required: set[str]) -> None:
    columns = {str(row[1]) for row in conn.execute(f'PRAGMA table_info("{table}")')}
    missing = sorted(required - columns)
    if missing:
        raise RuntimeError(f"{table} is missing required columns: {', '.join(missing)}")


def filter_pack(pack_dir: Path) -> dict[str, Any]:
    db_path = pack_dir / "autodiag2-vag-community.sqlite"
    manifest_path = pack_dir / "manifest.json"
    attribution_path = pack_dir / "ATTRIBUTION.txt"
    if not db_path.is_file() or not manifest_path.is_file() or not attribution_path.is_file():
        raise RuntimeError("Candidate pack is incomplete")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("pack_id") != PACK_ID:
        raise RuntimeError("Unexpected candidate pack ID")
    license_meta = manifest.get("license") or {}
    if license_meta.get("database") != "ODbL-1.0" or license_meta.get("contents") != "DbCL-1.0":
        raise RuntimeError("Candidate pack license metadata is not the pinned ODbL/DbCL split")
    if license_meta.get("commercial_use_allowed") is not True:
        raise RuntimeError("Commercial-use right is not explicitly declared")
    if license_meta.get("display_allowed") is not True:
        raise RuntimeError("Display right is not explicitly declared")
    if license_meta.get("offline_cache_allowed") is not True:
        raise RuntimeError("Offline-cache right is not explicitly declared")
    if license_meta.get("redistribution_allowed") is not True:
        raise RuntimeError("Redistribution right is not explicitly declared")
    if license_meta.get("separate_pack_required") is not True:
        raise RuntimeError("ODbL candidate pack must remain separate from the main proprietary database")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        integrity_before = str(conn.execute("PRAGMA integrity_check").fetchone()[0])
        if integrity_before != "ok":
            raise RuntimeError(f"Input candidate database integrity failed: {integrity_before}")
        if conn.execute("PRAGMA foreign_key_check").fetchall():
            raise RuntimeError("Input candidate database has foreign-key violations")
        for table, columns in {
            "source_registry": {"source_id", "database_license", "contents_license"},
            "dtc_candidates": {"id", "source_scope", "ecu_manufacturer", "namespace"},
            "dtc_fitment_candidates": {"dtc_candidate_id"},
            "engine_candidates": {"engine_code", "engine_code_quality"},
        }.items():
            require_columns(conn, table, columns)

        source = conn.execute(
            "SELECT source_id,database_license,contents_license FROM source_registry"
        ).fetchall()
        if len(source) != 1 or source[0]["source_id"] != PACK_ID:
            raise RuntimeError("Candidate pack source registry does not match the pinned source")
        if source[0]["database_license"] != "ODbL-1.0" or source[0]["contents_license"] != "DbCL-1.0":
            raise RuntimeError("Candidate pack source registry license mismatch")

        before = {
            "dtc_candidates": count(conn, "dtc_candidates"),
            "make_level_dtc_candidates": count(conn, "dtc_candidates", "source_scope='make_level'"),
            "vehicle_ecu_linked_dtc_candidates": count(conn, "dtc_candidates", "source_scope='vehicle_ecu_linked'"),
            "dtc_fitment_candidate_links": count(conn, "dtc_fitment_candidates"),
        }
        removal_reasons = {
            "unattributed_make_level": 0,
            "generic_or_unknown_ecu_identity": 0,
            "missing_vehicle_configuration_link": 0,
        }
        remove_ids: list[int] = []
        rows = conn.execute(
            """
            SELECT d.id, d.source_scope, lower(trim(coalesce(d.ecu_manufacturer,''))) AS ecu_manufacturer,
                   EXISTS(
                     SELECT 1 FROM dtc_fitment_candidates f
                     WHERE f.dtc_candidate_id=d.id
                   ) AS has_vehicle_configuration_link
            FROM dtc_candidates d
            ORDER BY d.id
            """
        ).fetchall()
        for row in rows:
            reason = None
            if row["source_scope"] != "vehicle_ecu_linked":
                reason = "unattributed_make_level"
            elif row["ecu_manufacturer"] in GENERIC_ECU_MANUFACTURERS:
                reason = "generic_or_unknown_ecu_identity"
            elif not row["has_vehicle_configuration_link"]:
                reason = "missing_vehicle_configuration_link"
            if reason:
                remove_ids.append(int(row["id"]))
                removal_reasons[reason] += 1

        conn.execute("BEGIN IMMEDIATE")
        if remove_ids:
            conn.execute("CREATE TEMP TABLE remove_dtc_ids(id INTEGER PRIMARY KEY)")
            conn.executemany(
                "INSERT INTO remove_dtc_ids(id) VALUES(?)",
                [(candidate_id,) for candidate_id in remove_ids],
            )
            conn.execute(
                "DELETE FROM dtc_fitment_candidates WHERE dtc_candidate_id IN (SELECT id FROM remove_dtc_ids)"
            )
            conn.execute(
                "DELETE FROM dtc_candidates WHERE id IN (SELECT id FROM remove_dtc_ids)"
            )
        conn.execute(
            """
            UPDATE engine_candidates
            SET engine_code_quality = CASE
              WHEN engine_code IS NULL OR trim(engine_code) = ''
                THEN 'unclassified_source_label'
              ELSE 'unverified_source_code_field'
            END
            """
        )
        conn.commit()

        integrity_after = str(conn.execute("PRAGMA integrity_check").fetchone()[0])
        fk_after = conn.execute("PRAGMA foreign_key_check").fetchall()
        if integrity_after != "ok" or fk_after:
            raise RuntimeError(
                f"Filtered candidate database integrity failed: {integrity_after}; FK issues={len(fk_after)}"
            )

        remaining_bad = conn.execute(
            """
            SELECT d.id
            FROM dtc_candidates d
            WHERE d.source_scope <> 'vehicle_ecu_linked'
               OR lower(trim(coalesce(d.ecu_manufacturer,''))) IN ('','generic','generic_ecu','unknown','n/a','na')
               OR NOT EXISTS (
                 SELECT 1 FROM dtc_fitment_candidates f WHERE f.dtc_candidate_id=d.id
               )
            LIMIT 1
            """
        ).fetchone()
        if remaining_bad:
            raise RuntimeError(f"Unattributed DTC candidate remained after filtering: {remaining_bad['id']}")

        counts = dict(manifest.get("counts") or {})
        counts.update({
            "dtc_candidates": count(conn, "dtc_candidates"),
            "vehicle_ecu_linked_dtc_candidates": count(conn, "dtc_candidates", "source_scope='vehicle_ecu_linked'"),
            "make_level_dtc_candidates": count(conn, "dtc_candidates", "source_scope='make_level'"),
            "dtc_fitment_candidate_links": count(conn, "dtc_fitment_candidates"),
            "generic_dtc_rows_in_pack": count(conn, "dtc_candidates", "namespace='generic_obd2'"),
            "vag_specific_dtc_verified_rows": 0,
            "engine_code_candidates_unverified": count(
                conn, "engine_candidates", "engine_code IS NOT NULL AND trim(engine_code) <> ''"
            ),
            "engine_codes_verified": 0,
            "transmission_records": 0,
        })
        invalid_engine_quality = count(
            conn, "engine_candidates",
            "engine_code_quality NOT IN ('unverified_source_code_field','unclassified_source_label')"
        )
        if invalid_engine_quality:
            raise RuntimeError("Unverified engine-code shape heuristic remained in the candidate pack")
        if counts["make_level_dtc_candidates"] != 0 or counts["generic_dtc_rows_in_pack"] != 0:
            raise RuntimeError("Unattributed or generic DTC rows remain in the VAG candidate pack")
    finally:
        conn.close()

    manifest["counts"] = counts
    excluded = dict(manifest.get("excluded_dtc_counts") or {})
    for key, value in removal_reasons.items():
        excluded[key] = int(excluded.get(key, 0)) + value
    manifest["excluded_dtc_counts"] = excluded
    manifest["dtc_candidate_policy"] = {
        "make_level_generic_ecu_labels_are_not_vag_attribution": True,
        "require_vehicle_configuration_link": True,
        "require_non_generic_ecu_manufacturer": True,
        "retained_records_are_still_unverified_candidates": True,
        "vag_specific_verified_rows": 0,
        "diagnostic_execution_allowed": False,
        "repair_advice_approved": False,
    }
    manifest["engine_code_policy"] = {
        "source_code_field_is_not_factory_code_proof": True,
        "shape_heuristic_is_not_used_for_verification": True,
        "all_nonempty_source_codes_remain_unverified": True,
        "verified_factory_engine_codes": 0,
        "transmission_codes_in_engine_field_are_not_reclassified": True,
    }
    manifest["transmission_policy"] = {
        "transmission_records_present": False,
        "do_not_infer_gearbox_from_engine_source_field": True,
    }
    manifest["candidate_sqlite_integrity"] = integrity_after
    manifest["candidate_sqlite_foreign_key_issues"] = 0
    manifest["candidate_database_sha256"] = sha256_file(db_path)
    manifest["dtc_policy_filtered"] = True
    manifest["dtc_policy_removal_counts"] = removal_reasons

    attribution = (
        "Contains a filtered candidate subset from AutoDiag2/database, release v6, "
        "https://github.com/autodiag2/database. Source database licensed under ODbL-1.0; "
        "database contents licensed under DbCL-1.0. This derived database is distributed under ODbL-1.0 "
        "and must remain available under that license when publicly conveyed. Attribution and source links "
        "are preserved in this pack. Upstream data is community-contributed and is not an OEM repair manual. "
        "All retained records are unverified candidates; market scope is UNKNOWN. No diagnostic execution "
        "or repair advice is approved. Generic-manufacturer make-level DTC labels are excluded because an "
        "ECU model string such as 'audi' or 'volkswagen' is not proof of a VAG ECU or OEM DTC attribution. "
        "Only candidates linked by the upstream data to a vehicle configuration and a non-generic ECU identity "
        "may remain, and those candidates still require independent technical review. No gearbox/transmission "
        "mapping is supplied by this source schema."
    )
    attribution_path.write_text(attribution + "\n", encoding="utf-8")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    checksum_files = [
        "autodiag2-vag-community.sqlite",
        "manifest.json",
        "ATTRIBUTION.txt",
        "upstream/LICENSE",
        "upstream/README.md",
    ]
    lines = []
    for name in checksum_files:
        path = pack_dir / name
        if not path.is_file():
            raise RuntimeError(f"Required pack file is missing: {name}")
        lines.append(f"{sha256_file(path)}  {name}\n")
    (pack_dir / "SHA256SUMS.txt").write_text("".join(lines), encoding="utf-8")

    return {
        "status": "passed",
        "before": before,
        "after": counts,
        "removed": removal_reasons,
        "candidate_database_sha256": manifest["candidate_database_sha256"],
        "manifest_sha256": sha256_file(manifest_path),
        "attribution_sha256": sha256_file(attribution_path),
        "integrity": integrity_after,
        "foreign_key_issues": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pack-dir", default="research-output/autodiag2-vag-community")
    args = parser.parse_args()
    result = filter_pack(Path(args.pack_dir))
    print("AUTODIAG2_VAG_DTC_POLICY=" + json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
