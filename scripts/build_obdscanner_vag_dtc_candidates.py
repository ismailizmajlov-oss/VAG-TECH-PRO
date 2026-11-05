#!/usr/bin/env python3
"""Build a separately namespaced, candidate-only VAG-family P1xxx DTC research pack.

The source is a pinned OBDScanner snapshot. Its DTC file declares Wal33D's MIT
DTC database as its upstream source. This pack is not OEM-confirmed and must
never be merged into the generic SAE/ISO DTC namespace or diagnostic workflow.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import shutil
import sqlite3
from pathlib import Path
from typing import Any

PACK_ID = "obdscanner-vag-dtc-candidates-mit"
OBDSCANNER_REPO = "https://github.com/parhipov/OBDScanner"
UPSTREAM_REPO = "https://github.com/Wal33D/dtc-database"
OBDSCANNER_REVISION = "af1ca44704281e1ff3e2ed84cb55bd92dd9bb996"
SOURCE_RELATIVE = "upstream/vag.json"
DATABASE_NAME = "obdscanner-vag-dtc-candidates.sqlite"
EXPECTED_CODES = 528

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def canonical(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: canonical(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [canonical(item) for item in value]
    return value

def canonical_bytes(value: Any) -> bytes:
    return json.dumps(canonical(value), ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")

def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        raise SystemExit(f"Invalid source JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise SystemExit("Source JSON root must be an object")
    return value

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-file", required=True, type=Path)
    parser.add_argument("--obdscanner-license", required=True, type=Path)
    parser.add_argument("--upstream-license", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--source-revision", default=OBDSCANNER_REVISION)
    args = parser.parse_args()

    if args.source_revision != OBDSCANNER_REVISION:
        raise SystemExit("Unexpected OBDScanner revision; review and update the pinned source before importing")
    for item in (args.source_file, args.obdscanner_license, args.upstream_license):
        if not item.is_file():
            raise SystemExit(f"Required source/licence file is missing: {item}")

    raw = args.source_file.read_bytes()
    payload = read_json(args.source_file)
    if payload.get("set") != "vag":
        raise SystemExit("Source DTC set is not explicitly labelled 'vag'")
    if "Wal33D" not in str(payload.get("source", "")) or "MIT" not in str(payload.get("source", "")):
        raise SystemExit("Source does not declare the expected Wal33D MIT upstream")
    codes = payload.get("codes")
    if not isinstance(codes, dict) or len(codes) != EXPECTED_CODES:
        raise SystemExit(f"Expected exactly {EXPECTED_CODES} DTC candidates, got {len(codes) if isinstance(codes, dict) else 'invalid'}")

    rows: list[tuple[Any, ...]] = []
    seen: set[str] = set()
    for code, definition in sorted(codes.items()):
        if not isinstance(code, str) or len(code) != 5 or not code.startswith("P1") or not code[2:].isalnum():
            raise SystemExit(f"Non-manufacturer-specific or malformed code in VAG-family pack: {code!r}")
        if code in seen:
            raise SystemExit(f"Duplicate DTC code: {code}")
        seen.add(code)
        if not isinstance(definition, dict):
            raise SystemExit(f"Invalid definition for {code}")
        title_en = definition.get("en")
        title_ru = definition.get("ru")
        if not isinstance(title_en, str) or not title_en.strip() or not isinstance(title_ru, str) or not title_ru.strip():
            raise SystemExit(f"Missing English/Russian source labels for {code}")
        record_hash = sha256(canonical_bytes(definition))
        rows.append((
            code, title_en.strip(), title_ru.strip(),
            "vag_family_candidate", "community_reference_unverified", "UNKNOWN",
            "manufacturer_family_candidate", 0, 0, 0, 0, 0,
            args.source_revision, SOURCE_RELATIVE, sha256(raw), record_hash,
            "MIT", OBDSCANNER_REPO, UPSTREAM_REPO, "obdscanner-vag-dtc-candidates",
        ))

    if len(rows) != EXPECTED_CODES or any(not code.startswith("P1") for code in seen):
        raise SystemExit("DTC candidate namespace/count gate failed")

    output = args.output_dir.resolve()
    if output.exists():
        shutil.rmtree(output)
    (output / "upstream").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(args.source_file, output / SOURCE_RELATIVE)
    shutil.copyfile(args.obdscanner_license, output / "LICENSE-OBDSCANNER-MIT.txt")
    shutil.copyfile(args.upstream_license, output / "LICENSE-WAL33D-MIT.txt")

    source_hash = sha256(raw)
    obd_license_hash = sha256((output / "LICENSE-OBDSCANNER-MIT.txt").read_bytes())
    upstream_license_hash = sha256((output / "LICENSE-WAL33D-MIT.txt").read_bytes())
    source_url = f"https://raw.githubusercontent.com/parhipov/OBDScanner/{args.source_revision}/core/data/dtc/vag.json"
    built_at = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

    attribution = f"""OBDScanner VAG-family DTC candidate data
Direct source snapshot: {OBDSCANNER_REPO}/tree/{args.source_revision}
Source file: core/data/dtc/vag.json
Source file SHA-256: {source_hash}
Upstream DTC database: {UPSTREAM_REPO}
Upstream attribution: Wal33D / Waleed Judah
OBDScanner attribution: Pavel Arkhipov
Data licence: MIT. Both MIT notices are included in this pack.

IMPORTANT LIMITATIONS
The source file labels this code family as "vag". That label is not OEM confirmation.
The 528 P1xxx definitions are community/source-family candidates only. They have
no exact model, generation, year, market, engine, gearbox, ECU, PR-code or VIN
applicability. They are not approved diagnostic tests, repair instructions,
adaptations, pinouts, torque values or OEM part mappings. Do not execute or
recommend repairs from this pack. The generic SAE/ISO DTC database remains separate.
"""
    (output / "ATTRIBUTION.txt").write_text(attribution, encoding="utf-8")

    database = output / DATABASE_NAME
    db = sqlite3.connect(database)
    try:
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA journal_mode=DELETE")
        db.execute("PRAGMA synchronous=FULL")
        db.executescript("""
        CREATE TABLE source_registry (
          source_id TEXT PRIMARY KEY,
          publisher TEXT NOT NULL,
          repository_url TEXT NOT NULL,
          source_revision TEXT NOT NULL,
          source_file TEXT NOT NULL,
          source_file_sha256 TEXT NOT NULL CHECK(length(source_file_sha256)=64),
          upstream_repository_url TEXT NOT NULL,
          data_license TEXT NOT NULL CHECK(data_license='MIT'),
          upstream_license TEXT NOT NULL CHECK(upstream_license='MIT'),
          rights_status TEXT NOT NULL CHECK(rights_status='approved_by_published_license'),
          commercial_use_allowed INTEGER NOT NULL CHECK(commercial_use_allowed=1),
          display_allowed INTEGER NOT NULL CHECK(display_allowed=1),
          offline_cache_allowed INTEGER NOT NULL CHECK(offline_cache_allowed=1),
          redistribution_allowed INTEGER NOT NULL CHECK(redistribution_allowed=1),
          attribution_required INTEGER NOT NULL CHECK(attribution_required=1),
          share_alike_required INTEGER NOT NULL CHECK(share_alike_required=0),
          market_scope TEXT NOT NULL CHECK(market_scope='UNKNOWN'),
          applicability_precision TEXT NOT NULL CHECK(applicability_precision='manufacturer_family_candidate'),
          verification_status TEXT NOT NULL CHECK(verification_status='community_reference_unverified'),
          vag_oem_confirmation INTEGER NOT NULL CHECK(vag_oem_confirmation=0),
          exact_vehicle_fitment INTEGER NOT NULL CHECK(exact_vehicle_fitment=0),
          ecu_fitment INTEGER NOT NULL CHECK(ecu_fitment=0),
          diagnostic_execution_allowed INTEGER NOT NULL CHECK(diagnostic_execution_allowed=0),
          repair_procedures_included INTEGER NOT NULL CHECK(repair_procedures_included=0),
          oem_part_numbers_included INTEGER NOT NULL CHECK(oem_part_numbers_included=0)
        ) WITHOUT ROWID;

        CREATE TABLE dtc_candidates (
          dtc_code TEXT PRIMARY KEY CHECK(dtc_code GLOB 'P1[0-9][0-9][0-9]'),
          title_en TEXT NOT NULL,
          title_ru TEXT NOT NULL,
          namespace TEXT NOT NULL CHECK(namespace='vag_family_candidate'),
          verification_status TEXT NOT NULL CHECK(verification_status='community_reference_unverified'),
          market_scope TEXT NOT NULL CHECK(market_scope='UNKNOWN'),
          applicability_precision TEXT NOT NULL CHECK(applicability_precision='manufacturer_family_candidate'),
          vehicle_fitment_claim INTEGER NOT NULL CHECK(vehicle_fitment_claim=0),
          ecu_fitment_claim INTEGER NOT NULL CHECK(ecu_fitment_claim=0),
          diagnostic_execution_allowed INTEGER NOT NULL CHECK(diagnostic_execution_allowed=0),
          repair_procedure_included INTEGER NOT NULL CHECK(repair_procedure_included=0),
          oem_part_number_included INTEGER NOT NULL CHECK(oem_part_number_included=0),
          source_revision TEXT NOT NULL,
          source_file TEXT NOT NULL,
          source_file_sha256 TEXT NOT NULL CHECK(length(source_file_sha256)=64),
          source_record_sha256 TEXT NOT NULL CHECK(length(source_record_sha256)=64),
          data_license TEXT NOT NULL CHECK(data_license='MIT'),
          source_url TEXT NOT NULL,
          upstream_source_url TEXT NOT NULL,
          source_id TEXT NOT NULL REFERENCES source_registry(source_id)
        ) WITHOUT ROWID;
        """)
        db.execute("BEGIN IMMEDIATE")
        db.execute("""
          INSERT INTO source_registry VALUES (
            ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?
          )
        """, (
            "obdscanner-vag-dtc-candidates", "OBDScanner / Pavel Arkhipov",
            OBDSCANNER_REPO, args.source_revision, SOURCE_RELATIVE, source_hash,
            UPSTREAM_REPO, "MIT", "MIT", "approved_by_published_license",
            1, 1, 1, 1, 1, 0, "UNKNOWN", "manufacturer_family_candidate",
            "community_reference_unverified", 0, 0, 0, 0, 0, 0,
        ))
        db.executemany("""
          INSERT INTO dtc_candidates VALUES (
            ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?
          )
        """, rows)
        db.execute("COMMIT")
        integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
        foreign_keys = db.execute("PRAGMA foreign_key_check").fetchall()
        if integrity != "ok" or foreign_keys:
            raise SystemExit(f"SQLite integrity failure: {integrity}; foreign keys={foreign_keys}")
        count = db.execute("SELECT count(*) FROM dtc_candidates").fetchone()[0]
        unsafe = db.execute("""
          SELECT count(*) FROM dtc_candidates
          WHERE namespace!='vag_family_candidate'
             OR verification_status!='community_reference_unverified'
             OR market_scope!='UNKNOWN'
             OR applicability_precision!='manufacturer_family_candidate'
             OR vehicle_fitment_claim!=0 OR ecu_fitment_claim!=0
             OR diagnostic_execution_allowed!=0 OR repair_procedure_included!=0
             OR oem_part_number_included!=0
        """).fetchone()[0]
        if count != EXPECTED_CODES or unsafe != 0:
            raise SystemExit(f"SQLite candidate-only gate failed: count={count}, unsafe={unsafe}")
        db.execute("PRAGMA optimize")
    finally:
        db.close()

    database_hash = sha256(database.read_bytes())
    attribution_hash = sha256((output / "ATTRIBUTION.txt").read_bytes())
    manifest = {
        "schema_version": 1,
        "pack_id": PACK_ID,
        "kind": "vag_family_dtc_candidates",
        "publisher": "OBDScanner / Pavel Arkhipov",
        "upstream_publisher": "Wal33D / Waleed Judah",
        "source_repository": OBDSCANNER_REPO,
        "source_revision": args.source_revision,
        "source_revision_type": "pinned_git_commit",
        "source_file": SOURCE_RELATIVE,
        "source_file_url": source_url,
        "source_file_sha256": source_hash,
        "source_snapshot_sha256": source_hash,
        "source_file_byte_size": len(raw),
        "upstream_source_repository": UPSTREAM_REPO,
        "upstream_revision": None,
        "upstream_revision_note": "The OBDScanner snapshot does not record the exact Wal33D commit from which this file was copied; the direct OBDScanner source file is pinned by source_revision and SHA-256.",
        "data_license": "MIT",
        "upstream_data_license": "MIT",
        "license_file": "LICENSE-OBDSCANNER-MIT.txt",
        "license_file_sha256": obd_license_hash,
        "upstream_license_file": "LICENSE-WAL33D-MIT.txt",
        "upstream_license_file_sha256": upstream_license_hash,
        "attribution_file": "ATTRIBUTION.txt",
        "attribution_sha256": attribution_hash,
        "rights_status": "approved_by_published_license",
        "commercial_use_allowed": True,
        "display_allowed": True,
        "offline_cache_allowed": True,
        "redistribution_allowed": True,
        "attribution_required": True,
        "share_alike_required": False,
        "namespace": "vag_family_candidate",
        "verification_status": "community_reference_unverified",
        "display_status": "candidate_reference_visible_separate_namespace",
        "product_eligibility": "candidate_reference_only_visible_separate_namespace",
        "market_scope": "UNKNOWN",
        "applicability_precision": "manufacturer_family_candidate",
        "vag_oem_confirmation": False,
        "exact_vehicle_fitment": False,
        "ecu_fitment": False,
        "diagnostic_execution_allowed": False,
        "repair_procedures_included": False,
        "oem_part_numbers_included": False,
        "database_file": DATABASE_NAME,
        "database_sha256": database_hash,
        "built_at_utc": built_at,
        "counts": {
            "manufacturer_family_candidates": EXPECTED_CODES,
            "p1xxx_candidates": EXPECTED_CODES,
            "generic_dtc_rows": 0,
            "unsafe_rows": 0,
        },
        "record_hash_algorithm": "SHA-256 over canonical UTF-8 JSON for each source definition object",
        "limitations": [
            "The upstream 'vag' family label is not OEM confirmation.",
            "All 528 P1xxx definitions remain community_reference_unverified.",
            "No model, generation, year, market, engine, gearbox, ECU, PR-code or VIN applicability is provided.",
            "No diagnostic execution, test plan, repair procedure, adaptation, pinout, torque value or OEM part mapping is included.",
            "The pack is visible only in a separate research tab and is never searched by the generic SAE/ISO DTC lookup.",
            "The exact Wal33D upstream commit is not recorded by the OBDScanner snapshot; the direct OBDScanner source commit and file hash are pinned."
        ],
    }
    manifest_path = output / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest_hash = sha256(manifest_path.read_bytes())

    sums = [
        f"{source_hash}  {SOURCE_RELATIVE}",
        f"{obd_license_hash}  LICENSE-OBDSCANNER-MIT.txt",
        f"{upstream_license_hash}  LICENSE-WAL33D-MIT.txt",
        f"{attribution_hash}  ATTRIBUTION.txt",
        f"{database_hash}  {DATABASE_NAME}",
    ]
    (output / "SHA256SUMS.txt").write_text("\n".join(sums) + "\n", encoding="utf-8")

    print(json.dumps({
        "status": "verified_candidate_reference_only",
        "pack_id": PACK_ID,
        "source_revision": args.source_revision,
        "source_file_sha256": source_hash,
        "source_manifest_sha256": manifest_hash,
        "database_sha256": database_hash,
        "license": "MIT",
        "market_scope": "UNKNOWN",
        "applicability_precision": "manufacturer_family_candidate",
        "verification_status": "community_reference_unverified",
        "counts": manifest["counts"],
        "exact_vehicle_fitment": False,
        "vag_oem_confirmation": False,
        "diagnostic_execution_allowed": False,
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
