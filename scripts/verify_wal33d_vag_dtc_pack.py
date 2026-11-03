#!/usr/bin/env python3
"""Independent verifier for the isolated Wal33D VAG DTC candidate SQLite pack."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
from pathlib import Path
from typing import Any

CODE_RE = re.compile(r"^([PBCU][0-9A-F]{4})\s+-\s+(.+?)\s*$")
MANUFACTURER_CODE_RE = re.compile(
    r"^(?:P1[0-9A-F]{3}|P3[0-3][0-9A-F]{2}|B[12][0-9A-F]{3}|C[12][0-9A-F]{3}|U[12][0-9A-F]{3})$"
)
EXPECTED_COUNTS = {"Volkswagen": 528, "Audi": 2, "total": 530}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def verify(root: Path) -> dict[str, Any]:
    root = root.resolve()
    manifest_path = root / "manifest.json"
    declaration_path = root / "source-declaration.json"
    db_path = root / "vag-oem-dtc-candidates.sqlite"
    license_path = root / "LICENSES" / "Wal33D-MIT-LICENSE.txt"
    attribution_path = root / "ATTRIBUTION.txt"
    readme_path = root / "README.md"

    manifest = read_json(manifest_path)
    declaration = read_json(declaration_path)
    if manifest.get("pack_id") != "wal33d-vag-oem-dtc-mit":
        raise ValueError("Unexpected pack ID")
    if manifest.get("source_commit_sha") != "04c43d72e7db7197658b6f72fe582c5076d9eee8":
        raise ValueError("Source revision is not the reviewed immutable commit")
    if manifest.get("dataset_license") != "MIT" or manifest.get("rights_confirmed") is not False:
        raise ValueError("MIT declaration/research-only rights boundary failed")
    if manifest.get("market_scope") != "UNKNOWN":
        raise ValueError("Market scope must remain UNKNOWN")
    if manifest.get("verification_status") != "unverified_candidate":
        raise ValueError("Candidate verification status was incorrectly promoted")
    if manifest.get("exact_vehicle_fitment") is not False or manifest.get("ecu_fitment_confirmed") is not False:
        raise ValueError("Exact vehicle/ECU fitment must remain false")
    if manifest.get("execution_allowed") is not False:
        raise ValueError("Diagnostic execution must remain disabled")
    if manifest.get("counts") != EXPECTED_COUNTS:
        raise ValueError(f"Unexpected candidate counts: {manifest.get('counts')}")
    if declaration.get("commit_sha") != manifest.get("source_commit_sha"):
        raise ValueError("Source declaration and pack manifest revisions differ")
    if declaration.get("rights_confirmed") is not False:
        raise ValueError("Source declaration must retain unconfirmed upstream provenance")

    if not license_path.is_file() or sha256_file(license_path) != manifest.get("license_sha256"):
        raise ValueError("MIT license file missing or hash mismatch")
    license_text = license_path.read_text(encoding="utf-8-sig")
    if "MIT License" not in license_text or "Copyright (c) 2024 Wal33D" not in license_text:
        raise ValueError("Pinned MIT license text does not match the reviewed source")
    if not attribution_path.is_file() or "Wal33D" not in attribution_path.read_text(encoding="utf-8-sig"):
        raise ValueError("Required source attribution is missing")
    if not readme_path.is_file():
        raise ValueError("Research pack README is missing")

    source_files = manifest.get("source_files", [])
    if len(source_files) != 4:
        raise ValueError("Expected four pinned upstream source files")
    for item in source_files:
        path = root / item["path"]
        if not path.is_file():
            raise ValueError(f"Missing pinned source snapshot: {item['path']}")
        if path.stat().st_size != item["byte_size"] or sha256_file(path) != item["sha256"]:
            raise ValueError(f"Pinned source snapshot hash/size mismatch: {item['source_path']}")
    upstream_license = root / "upstream" / "LICENSE"
    upstream_readme = root / "upstream" / "README.md"
    if sha256_file(upstream_license) != manifest.get("license_sha256"):
        raise ValueError("Upstream license copy does not match the license manifest")
    if sha256_file(upstream_readme) != manifest.get("readme_sha256"):
        raise ValueError("Upstream README hash mismatch")

    if not db_path.is_file() or sha256_file(db_path) != manifest.get("database_sha256"):
        raise ValueError("SQLite database missing or hash mismatch")

    uri = f"file:{db_path.resolve().as_posix()}?mode=ro"
    db = sqlite3.connect(uri, uri=True)
    db.row_factory = sqlite3.Row
    try:
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("SQLite integrity_check failed")
        if db.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("SQLite foreign_key_check failed")
        tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {"source_registry", "source_files", "dtc_candidates", "database_info"}.issubset(tables):
            raise ValueError("SQLite schema is incomplete")
        if db.execute("PRAGMA user_version").fetchone()[0] != 1:
            raise ValueError("Unexpected SQLite user_version")

        source = db.execute("SELECT * FROM source_registry").fetchall()
        if len(source) != 1:
            raise ValueError("Expected exactly one source registry row")
        source = source[0]
        if source["license_id"] != "MIT" or source["rights_confirmed"] != 0:
            raise ValueError("SQLite source registry rights boundary failed")
        if source["market_scope"] != "UNKNOWN" or source["verification_status"] != "unverified_candidate":
            raise ValueError("SQLite source registry candidate boundary failed")
        if source["product_eligibility"] != "research_only_pending_record_provenance_and_vehicle_validation":
            raise ValueError("SQLite source registry product eligibility was promoted")

        stored_files = db.execute("SELECT * FROM source_files ORDER BY source_path").fetchall()
        if len(stored_files) != 4:
            raise ValueError("SQLite source_files count mismatch")
        manifest_by_source = {item["source_path"]: item for item in source_files}
        for item in stored_files:
            expected = manifest_by_source.get(item["source_path"])
            if not expected or item["sha256"] != expected["sha256"] or item["byte_size"] != expected["byte_size"]:
                raise ValueError(f"SQLite source file provenance mismatch: {item['source_path']}")
            if item["source_url"] != expected["source_url"]:
                raise ValueError(f"SQLite source URL mismatch: {item['source_path']}")

        rows = db.execute("SELECT * FROM dtc_candidates ORDER BY make,code").fetchall()
        counts = {
            "Volkswagen": sum(1 for row in rows if row["make"] == "Volkswagen"),
            "Audi": sum(1 for row in rows if row["make"] == "Audi"),
            "total": len(rows),
        }
        if counts != EXPECTED_COUNTS:
            raise ValueError(f"SQLite row counts mismatch: {counts}")
        if db.execute(
            """
            SELECT count(*) FROM dtc_candidates
            WHERE code_namespace<>'manufacturer_controlled_candidate'
               OR market_scope<>'UNKNOWN'
               OR applicability_precision<>'manufacturer_make_candidate'
               OR verification_status<>'unverified_candidate'
               OR fitment_confirmed<>0
               OR ecu_fitment_confirmed<>0
               OR execution_allowed<>0
               OR license_id<>'MIT'
            """
        ).fetchone()[0]:
            raise ValueError("DTC candidate status/namespace/rights boundary failed")

        seen = set()
        for row in rows:
            if not MANUFACTURER_CODE_RE.fullmatch(row["code"]):
                raise ValueError(f"Generic or malformed DTC entered the VAG candidate pack: {row['code']}")
            key = (row["make"], row["code"])
            if key in seen:
                raise ValueError(f"Duplicate make/code pair: {key}")
            seen.add(key)
            source_path = root / "upstream" / row["source_path"]
            lines = source_path.read_text(encoding="utf-8-sig").splitlines()
            if row["source_line_number"] > len(lines):
                raise ValueError(f"Invalid source line reference: {key}")
            source_line = lines[row["source_line_number"] - 1]
            if sha256_bytes(source_line.encode("utf-8")) != row["source_record_sha256"]:
                raise ValueError(f"Source record SHA-256 mismatch: {key}")
            match = CODE_RE.fullmatch(source_line.strip())
            if not match or match.group(1) != row["code"] or match.group(2).strip() != row["description"]:
                raise ValueError(f"Source record content mismatch: {key}")

        required = {
            ("Volkswagen", "P1128"),
            ("Audi", "P3000"),
            ("Audi", "P3100"),
        }
        if not required.issubset(seen):
            raise ValueError("Expected known manufacturer-controlled sample codes are missing")
        if any(code in {row["code"] for row in rows} for code in ("P0011", "P0420", "P0A08", "P2A00")):
            raise ValueError("Generic SAE/ISO code leaked into manufacturer-specific pack")

        info = dict(db.execute("SELECT key,value FROM database_info").fetchall())
        if info.get("generic_dtc_rows") != "0" or info.get("exact_fitment_rows") != "0" or info.get("execution_enabled_rows") != "0":
            raise ValueError("SQLite database_info safety boundary failed")
    finally:
        db.close()

    return {
        "status": "verified_research_only",
        "pack_id": manifest["pack_id"],
        "database_sha256": manifest["database_sha256"],
        "counts": EXPECTED_COUNTS,
        "market_scope": "UNKNOWN",
        "verification_status": "unverified_candidate",
        "rights_confirmed": False,
        "exact_fitment": False,
        "execution_enabled": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.root)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
