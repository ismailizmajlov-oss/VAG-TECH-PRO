#!/usr/bin/env python3
"""Fail-closed verifier for the OBDb VAG CC BY-SA research pack."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
from pathlib import Path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "dist/obdb-vag-research").resolve()
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("license_id") != "CC-BY-SA-4.0" or manifest.get("share_alike_required") is not True:
        raise SystemExit("Pack license/share-alike gate failed")
    database_path = root / manifest["database_file"]
    if digest(database_path) != manifest["database_sha256"]:
        raise SystemExit("SQLite SHA-256 does not match manifest")
    for source in manifest["sources"]:
        if source.get("market_scope") != "UNKNOWN" or source.get("verification_status") != "unverified_community_candidate":
            raise SystemExit("A source has an unsafe market or verification status")
        if source.get("execution_allowed") is not False:
            raise SystemExit("ECU command execution must remain disabled")
        license_path = root / source["license_copy"]
        if digest(license_path) != source["license_sha256"]:
            raise SystemExit("Upstream license copy hash mismatch")
        if "Attribution-ShareAlike 4.0 International" not in license_path.read_text(encoding="utf-8"):
            raise SystemExit("An upstream repository does not carry the expected CC BY-SA 4.0 license")
        for item in source["files"].values():
            file_path = root / item["path"]
            if digest(file_path) != item["sha256"] or file_path.stat().st_size != item["bytes"]:
                raise SystemExit(f"Upstream snapshot hash mismatch: {item['path']}")

    db = sqlite3.connect(f"file:{database_path.as_posix()}?mode=ro", uri=True)
    db.execute("PRAGMA query_only=ON")
    if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        raise SystemExit("SQLite integrity check failed")
    if db.execute("PRAGMA foreign_key_check").fetchall():
        raise SystemExit("SQLite foreign-key check failed")
    counts = {
        "sources": db.execute("SELECT count(*) FROM source_registry").fetchone()[0],
        "generations": db.execute("SELECT count(*) FROM generation_candidates").fetchone()[0],
        "ecus": db.execute("SELECT count(*) FROM ecu_candidates").fetchone()[0],
        "commands": db.execute("SELECT count(*) FROM command_candidates").fetchone()[0],
        "signals": db.execute("SELECT count(*) FROM signal_candidates").fetchone()[0],
    }
    if counts != manifest["counts"]:
        raise SystemExit(f"Manifest/database count mismatch: {counts} != {manifest['counts']}")
    checks = [
        ("source_registry", "market_scope", "UNKNOWN"),
        ("source_registry", "verification_status", "unverified_community_candidate"),
        ("command_candidates", "market_scope", "UNKNOWN"),
        ("command_candidates", "verification_status", "unverified_community_candidate"),
        ("command_candidates", "service_id", "22"),
        ("signal_candidates", "market_scope", "UNKNOWN"),
        ("signal_candidates", "verification_status", "unverified_community_candidate"),
        ("generation_candidates", "market_scope", "UNKNOWN"),
        ("generation_candidates", "verification_status", "unverified_community_candidate"),
    ]
    for table, column, expected in checks:
        bad = db.execute(f'SELECT count(*) FROM "{table}" WHERE "{column}" <> ?', (expected,)).fetchone()[0]
        if bad:
            raise SystemExit(f"Unsafe {table}.{column} rows: {bad}")
    if db.execute("SELECT count(*) FROM command_candidates WHERE execution_allowed <> 0").fetchone()[0]:
        raise SystemExit("A command is marked executable")
    if db.execute("SELECT count(*) FROM source_registry WHERE license_id <> 'CC-BY-SA-4.0' OR share_alike_required <> 1 OR execution_allowed <> 0").fetchone()[0]:
        raise SystemExit("Source registry license/execution gate failed")
    if db.execute("SELECT count(*) FROM command_candidates WHERE length(ecu_header) <> 3 OR service_id <> '22'").fetchone()[0]:
        raise SystemExit("Invalid ECU header or non-UDS-0x22 command found")
    db.close()
    result = {
        "status": "verified",
        "database_sha256": manifest["database_sha256"],
        "license": manifest["license_id"],
        "counts": counts,
        "market_scope": "UNKNOWN",
        "verification_status": "unverified_community_candidate",
        "execution_allowed": False,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
