#!/usr/bin/env python3
"""Verify the isolated MechanicDB Audi/VW DTC candidate pack."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fail(message: str) -> None:
    raise SystemExit(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        fail("Pack manifest is missing")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    if manifest.get("data_license") != "ODbL-1.0":
        fail("ODbL license is missing")
    if manifest.get("rights_status") != "approved_by_published_license":
        fail("Published-license rights gate failed")
    if not all(manifest.get(key) is True for key in (
        "commercial_use_allowed_under_odbl", "display_allowed", "offline_cache_allowed",
        "redistribution_allowed_under_odbl", "share_alike_required", "attribution_required"
    )):
        fail("Commercial/display/cache/redistribution/share-alike rights are incomplete")
    if manifest.get("market_scope") != "UNKNOWN":
        fail("The source must remain market-unknown")
    if manifest.get("applicability_precision") != "manufacturer_make_candidate":
        fail("The source must remain make-level candidate precision")
    if manifest.get("verification_status") != "community_reference_unverified":
        fail("Community data cannot be promoted to verified")
    if manifest.get("display_status") != "hidden_pending_technical_review":
        fail("Candidate pack must remain hidden pending technical review")
    if manifest.get("exact_vehicle_fitment") is not False:
        fail("Exact vehicle fitment must remain false")
    if manifest.get("ecu_fitment") is not False or manifest.get("pr_code_fitment") is not False:
        fail("ECU and PR-code fitment must remain false")
    if manifest.get("diagnostic_execution_allowed") is not False:
        fail("Diagnostic execution must remain disabled")
    if manifest.get("repair_procedures_included") is not False or manifest.get("oem_part_numbers_included") is not False:
        fail("Repair procedures and OEM part numbers must not be included")
    counts = manifest.get("counts", {})
    if counts.get("manufacturer_controlled_candidates") != 2 or counts.get("generic_dtc_rows") != 0:
        fail("The pack must contain exactly two manufacturer candidates and zero generic rows")
    if counts.get("repair_procedure_rows") != 0 or counts.get("part_rows") != 0:
        fail("The pack must not contain community repair or parts rows")

    for relative, expected in manifest.get("pack_files", {}).items():
        path = root / relative
        if not path.is_file():
            fail(f"Missing pack file: {relative}")
        if sha256_file(path) != expected.get("sha256"):
            fail(f"SHA-256 mismatch: {relative}")
        if path.stat().st_size != expected.get("byte_size"):
            fail(f"Byte-size mismatch: {relative}")

    for relative, item in manifest.get("source_files", {}).items():
        path = root / relative
        if not path.is_file() or sha256_file(path) != item.get("sha256"):
            fail(f"Source snapshot hash mismatch: {relative}")

    attribution = (root / "ATTRIBUTION.txt").read_text(encoding="utf-8")
    if "MechanicDB" not in attribution or "ODbL" not in attribution or "Wal33D" not in attribution:
        fail("Attribution is incomplete")
    if not (root / "upstream" / "LICENSE-ODbL.txt").is_file():
        fail("ODbL license text is missing")
    if not (root / "upstream" / "LICENSE-MIT.txt").is_file():
        fail("Upstream MIT notice is missing")
    if not (root / "upstream" / "SOURCES.md").is_file():
        fail("Upstream provenance documentation is missing")

    db_path = root / manifest["database_path"]
    if sha256_file(db_path) != manifest["database_sha256"]:
        fail("SQLite database SHA-256 mismatch")
    sums_path = root / "SHA256SUMS.txt"
    if not sums_path.is_file():
        fail("SHA256SUMS.txt is missing")
    for line in sums_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        expected_hash, relative = line.split("  ", 1)
        path = root / relative
        if not path.is_file() or sha256_file(path) != expected_hash:
            fail(f"SHA256SUMS verification failed: {relative}")

    connection = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    try:
        if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            fail("SQLite integrity_check failed")
        if connection.execute("PRAGMA foreign_key_check").fetchall():
            fail("SQLite foreign_key_check failed")
        if connection.execute("PRAGMA user_version").fetchone()[0] != 1:
            fail("Unexpected SQLite schema version")
        rows = connection.execute(
            """
            SELECT oem_make,dtc_code,namespace,verification_status,market_scope,
                   applicability_precision,vehicle_fitment_claim,ecu_fitment_claim,
                   pr_code_claim,diagnostic_execution_allowed,repair_procedure_included,
                   oem_part_number_included,source_file,source_line_no,source_line_sha256
            FROM dtc_candidates ORDER BY oem_make,dtc_code
            """
        ).fetchall()
        if len(rows) != 2:
            fail(f"Expected 2 candidate rows, found {len(rows)}")
        expected_codes = {("Audi", "P3000"), ("Volkswagen", "P1128")}
        if {(row[0], row[1]) for row in rows} != expected_codes:
            fail("Unexpected Audi/VW DTC candidate set")
        raw_lines = (root / "upstream" / "dtc_codes.csv").read_bytes().splitlines(keepends=True)
        for row in rows:
            if row[2] != "manufacturer_controlled_candidate" or row[3] != "community_reference_unverified":
                fail("DTC namespace or review status was promoted")
            if row[4] != "UNKNOWN" or row[5] != "manufacturer_make_candidate":
                fail("Market/applicability precision was overstated")
            if any(value != 0 for value in row[6:12]):
                fail("A prohibited fitment, execution, repair or OEM-parts claim is present")
            line_no = row[13]
            if line_no <= 1 or line_no > len(raw_lines):
                fail("Invalid source line number")
            if hashlib.sha256(raw_lines[line_no - 1]).hexdigest() != row[14]:
                fail("Source-line SHA-256 mismatch")
            if row[12] != "upstream/dtc_codes.csv":
                fail("Candidate points to an unexpected source file")
        source_rights = connection.execute(
            "SELECT data_license,rights_status,commercial_use_allowed,display_allowed,"
            "offline_cache_allowed,redistribution_allowed,share_alike_required,"
            "market_scope,technical_review_status FROM source_registry"
        ).fetchone()
        if source_rights != (
            "ODbL-1.0", "approved_by_published_license", 1, 1, 1, 1, 1,
            "UNKNOWN", "community_reference_unverified"
        ):
            fail("SQLite source registry rights or candidate status are inconsistent")
    finally:
        connection.close()

    print(json.dumps({
        "status": "verified_research_only_candidate_pack",
        "database_sha256": manifest["database_sha256"],
        "source_snapshot_sha256": manifest["source_snapshot_sha256"],
        "manufacturer_candidates": counts["manufacturer_controlled_candidates"],
        "generic_dtc_rows": 0,
        "repair_procedure_rows": 0,
        "part_rows": 0,
        "market_scope": "UNKNOWN",
        "applicability_precision": "manufacturer_make_candidate",
        "exact_vehicle_fitment": False,
        "diagnostic_execution_allowed": False,
        "display_status": "hidden_pending_technical_review",
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
