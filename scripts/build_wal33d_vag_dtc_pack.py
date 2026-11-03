#!/usr/bin/env python3
"""Build an isolated, research-only SQLite pack from the pinned Wal33D VAG DTC files.

The pack contains manufacturer-controlled code-range candidates only. It deliberately
excludes generic SAE/ISO ranges and never asserts model/year/engine/ECU fitment.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sqlite3
import tempfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SOURCE_MANIFEST = Path("data/source-manifests/wal33d-dtc-candidate.json")
MAX_SOURCE_BYTES = 2_000_000
TIMEOUT_SECONDS = 30
CODE_RE = re.compile(r"^([PBCU][0-9A-F]{4})\s+-\s+(.+?)\s*$")
MANUFACTURER_CODE_RE = re.compile(
    r"^(?:P1[0-9A-F]{3}|P3[0-3][0-9A-F]{2}|B[12][0-9A-F]{3}|C[12][0-9A-F]{3}|U[12][0-9A-F]{3})$"
)
EXPECTED_COUNTS = {"Volkswagen": 528, "Audi": 2, "total": 530}
SOURCE_PATHS_BY_MAKE = {
    "Volkswagen": "data/source-data/volkswagen_codes.txt",
    "Audi": "data/source-data/audi_codes.txt",
}


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


def fetch_pinned(repository: str, commit_sha: str, source_path: str) -> bytes:
    if not re.fullmatch(r"[0-9a-f]{40}", commit_sha):
        raise ValueError("Source commit must be a full immutable Git SHA")
    url = f"https://raw.githubusercontent.com/{repository}/{commit_sha}/{source_path}"
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "VAG-TECH-PRO-offline-data-builder/1.0", "Accept": "text/plain"},
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        final_url = response.geturl()
        if not final_url.startswith("https://raw.githubusercontent.com/"):
            raise ValueError(f"Unexpected upstream redirect: {final_url}")
        if response.status != 200:
            raise ValueError(f"Unexpected upstream HTTP status: {response.status}")
        data = response.read(MAX_SOURCE_BYTES + 1)
    if not data or len(data) > MAX_SOURCE_BYTES:
        raise ValueError(f"Source file is empty or exceeds {MAX_SOURCE_BYTES} bytes: {source_path}")
    return data


def parse_source_file(make: str, source_path: str, raw: bytes, source_id: str) -> tuple[list[dict[str, Any]], dict[str, int]]:
    text = raw.decode("utf-8-sig")
    included: list[dict[str, Any]] = []
    generic_count = 0
    malformed_count = 0
    blank_count = 0

    for line_number, original_line in enumerate(text.splitlines(), start=1):
        line = original_line.strip()
        if not line:
            blank_count += 1
            continue
        match = CODE_RE.fullmatch(line)
        if not match:
            malformed_count += 1
            continue
        code, description = match.groups()
        if not MANUFACTURER_CODE_RE.fullmatch(code):
            generic_count += 1
            continue
        included.append({
            "make": make,
            "code": code,
            "description": description.strip(),
            "code_namespace": "manufacturer_controlled_candidate",
            "code_family": code[:2] + "xxx",
            "source_id": source_id,
            "source_path": source_path,
            "source_line_number": line_number,
            "source_record_sha256": sha256_bytes(original_line.encode("utf-8")),
            "license_id": "MIT",
            "market_scope": "UNKNOWN",
            "applicability_precision": "manufacturer_make_candidate",
            "verification_status": "unverified_candidate",
            "fitment_confirmed": 0,
            "ecu_fitment_confirmed": 0,
            "execution_allowed": 0,
            "rights_status": "repository_MIT_license_declared; upstream_record_provenance_not_independently_verified",
        })

    return included, {
        "included_manufacturer_specific": len(included),
        "excluded_generic_range": generic_count,
        "excluded_malformed_or_unrecognized": malformed_count,
        "blank_lines": blank_count,
    }


def create_database(path: Path, source_manifest: dict[str, Any], fetched: dict[str, bytes],
                    file_metadata: list[dict[str, Any]], candidates: list[dict[str, Any]],
                    counts: dict[str, int]) -> None:
    db = sqlite3.connect(path)
    try:
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA journal_mode=DELETE")
        db.execute("PRAGMA synchronous=FULL")
        db.execute("PRAGMA user_version=1")
        db.executescript(
            """
            CREATE TABLE source_registry (
                source_id TEXT PRIMARY KEY,
                publisher TEXT NOT NULL,
                repository_url TEXT NOT NULL,
                commit_sha TEXT NOT NULL,
                commit_date_utc TEXT NOT NULL,
                license_id TEXT NOT NULL,
                license_url TEXT NOT NULL,
                license_scope TEXT NOT NULL,
                rights_status TEXT NOT NULL,
                rights_confirmed INTEGER NOT NULL CHECK (rights_confirmed IN (0,1)),
                commercial_use_allowed INTEGER NOT NULL CHECK (commercial_use_allowed IN (0,1)),
                display_allowed INTEGER NOT NULL CHECK (display_allowed IN (0,1)),
                offline_cache_allowed INTEGER NOT NULL CHECK (offline_cache_allowed IN (0,1)),
                redistribution_allowed INTEGER NOT NULL CHECK (redistribution_allowed IN (0,1)),
                market_scope TEXT NOT NULL,
                verification_status TEXT NOT NULL,
                product_eligibility TEXT NOT NULL,
                attribution TEXT NOT NULL
            );

            CREATE TABLE source_files (
                source_id TEXT NOT NULL REFERENCES source_registry(source_id),
                source_path TEXT NOT NULL,
                local_path TEXT NOT NULL,
                source_url TEXT NOT NULL,
                byte_size INTEGER NOT NULL CHECK (byte_size > 0),
                sha256 TEXT NOT NULL CHECK (length(sha256)=64),
                PRIMARY KEY (source_id, source_path)
            );

            CREATE TABLE dtc_candidates (
                dtc_id INTEGER PRIMARY KEY,
                make TEXT NOT NULL,
                code TEXT NOT NULL,
                description TEXT NOT NULL,
                code_namespace TEXT NOT NULL CHECK (code_namespace='manufacturer_controlled_candidate'),
                code_family TEXT NOT NULL,
                source_id TEXT NOT NULL REFERENCES source_registry(source_id),
                source_path TEXT NOT NULL,
                source_line_number INTEGER NOT NULL CHECK (source_line_number > 0),
                source_record_sha256 TEXT NOT NULL CHECK (length(source_record_sha256)=64),
                license_id TEXT NOT NULL CHECK (license_id='MIT'),
                market_scope TEXT NOT NULL CHECK (market_scope='UNKNOWN'),
                applicability_precision TEXT NOT NULL CHECK (applicability_precision='manufacturer_make_candidate'),
                verification_status TEXT NOT NULL CHECK (verification_status='unverified_candidate'),
                fitment_confirmed INTEGER NOT NULL DEFAULT 0 CHECK (fitment_confirmed=0),
                ecu_fitment_confirmed INTEGER NOT NULL DEFAULT 0 CHECK (ecu_fitment_confirmed=0),
                execution_allowed INTEGER NOT NULL DEFAULT 0 CHECK (execution_allowed=0),
                rights_status TEXT NOT NULL,
                UNIQUE (make, code)
            );

            CREATE TABLE database_info (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE INDEX idx_dtc_candidates_make_code ON dtc_candidates(make, code);
            CREATE INDEX idx_dtc_candidates_code ON dtc_candidates(code);
            """
        )
        source_id = source_manifest["source_id"]
        attribution = f"{source_manifest['publisher']}; {source_manifest['repository_url']}; commit {source_manifest['commit_sha']}; MIT License."
        with db:
            db.execute(
                """
                INSERT INTO source_registry VALUES (
                    ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?
                )
                """,
                (
                    source_id,
                    source_manifest["publisher"],
                    source_manifest["repository_url"],
                    source_manifest["commit_sha"],
                    source_manifest["commit_date_utc"],
                    source_manifest["license_id"],
                    source_manifest["license_url"],
                    source_manifest["license_scope"],
                    source_manifest["rights_status"],
                    int(source_manifest["rights_confirmed"]),
                    int(source_manifest["commercial_use_allowed"]),
                    int(source_manifest["display_allowed"]),
                    int(source_manifest["offline_cache_allowed"]),
                    int(source_manifest["redistribution_allowed"]),
                    source_manifest["market_scope"],
                    source_manifest["verification_status"],
                    source_manifest["product_eligibility"],
                    attribution,
                ),
            )
            db.executemany(
                """
                INSERT INTO source_files (source_id,source_path,local_path,source_url,byte_size,sha256)
                VALUES (?,?,?,?,?,?)
                """,
                [
                    (source_id, item["source_path"], item["path"], item["source_url"], item["byte_size"], item["sha256"])
                    for item in file_metadata
                ],
            )
            db.executemany(
                """
                INSERT INTO dtc_candidates (
                    make,code,description,code_namespace,code_family,source_id,source_path,
                    source_line_number,source_record_sha256,license_id,market_scope,
                    applicability_precision,verification_status,fitment_confirmed,
                    ecu_fitment_confirmed,execution_allowed,rights_status
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                [
                    (
                        row["make"], row["code"], row["description"], row["code_namespace"],
                        row["code_family"], row["source_id"], row["source_path"],
                        row["source_line_number"], row["source_record_sha256"], row["license_id"],
                        row["market_scope"], row["applicability_precision"],
                        row["verification_status"], row["fitment_confirmed"],
                        row["ecu_fitment_confirmed"], row["execution_allowed"], row["rights_status"],
                    )
                    for row in candidates
                ],
            )
            info = {
                "schema_version": "1",
                "source_id": source_id,
                "source_commit_sha": source_manifest["commit_sha"],
                "license_id": source_manifest["license_id"],
                "market_scope": "UNKNOWN",
                "verification_status": "unverified_candidate",
                "record_count": str(counts["total"]),
                "volkswagen_count": str(counts["Volkswagen"]),
                "audi_count": str(counts["Audi"]),
                "generic_dtc_rows": "0",
                "exact_fitment_rows": "0",
                "execution_enabled_rows": "0",
            }
            db.executemany("INSERT INTO database_info(key,value) VALUES (?,?)", sorted(info.items()))
        if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("SQLite integrity_check failed after build")
        if db.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("SQLite foreign_key_check failed after build")
    finally:
        db.close()


def build(manifest_path: Path, output_dir: Path) -> dict[str, Any]:
    declaration = read_json(manifest_path)
    if declaration.get("schema_version") != 1 or declaration.get("source_id") != "wal33d-dtc-database":
        raise ValueError("Unexpected Wal33D source declaration")
    if declaration.get("commit_sha") != "04c43d72e7db7197658b6f72fe582c5076d9eee8":
        raise ValueError("Wal33D source revision changed; review and pin a new revision explicitly")
    if declaration.get("license_id") != "MIT" or declaration.get("rights_confirmed") is not False:
        raise ValueError("Wal33D rights/applicability boundary changed unexpectedly")
    if declaration.get("market_scope") != "UNKNOWN" or declaration.get("verification_status") != "unverified_candidate":
        raise ValueError("Wal33D candidate boundary changed unexpectedly")
    if output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite existing pack directory: {output_dir}")
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    temp_dir = Path(tempfile.mkdtemp(prefix="wal33d-vag-dtc-", dir=output_dir.parent))
    try:
        fetched: dict[str, bytes] = {}
        source_files: list[dict[str, Any]] = []
        for source_path in declaration["source_files"]:
            raw = fetch_pinned(declaration["repository"], declaration["commit_sha"], source_path)
            fetched[source_path] = raw
            local_path = Path("upstream") / source_path
            target = temp_dir / local_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            source_files.append({
                "source_path": source_path,
                "path": local_path.as_posix(),
                "source_url": f"https://raw.githubusercontent.com/{declaration['repository']}/{declaration['commit_sha']}/{source_path}",
                "byte_size": len(raw),
                "sha256": sha256_bytes(raw),
            })

        license_text = fetched["LICENSE"].decode("utf-8-sig")
        readme_text = fetched["README.md"].decode("utf-8-sig")
        if "MIT License" not in license_text or "Copyright (c) 2024 Wal33D" not in license_text:
            raise ValueError("Pinned MIT license notice did not match the reviewed source")
        readme_normalized = " ".join(readme_text.split()).lower()
        if "license" not in readme_normalized or "mit" not in readme_normalized or "manufacturer-specific definitions" not in readme_normalized:
            raise ValueError("Pinned README no longer declares the reviewed database/license scope")

        candidates: list[dict[str, Any]] = []
        excluded: dict[str, dict[str, int]] = {}
        for make, source_path in SOURCE_PATHS_BY_MAKE.items():
            rows, stats = parse_source_file(make, source_path, fetched[source_path], declaration["source_id"])
            candidates.extend(rows)
            excluded[make] = stats

        counts = {
            "Volkswagen": sum(1 for row in candidates if row["make"] == "Volkswagen"),
            "Audi": sum(1 for row in candidates if row["make"] == "Audi"),
            "total": len(candidates),
        }
        if counts != EXPECTED_COUNTS or counts != declaration["expected_counts"]:
            raise ValueError(f"Source counts changed; expected {EXPECTED_COUNTS}, got {counts}")
        if excluded["Volkswagen"]["excluded_generic_range"] != 0:
            raise ValueError("Unexpected generic-range Volkswagen records")
        if excluded["Audi"]["excluded_generic_range"] != 126 or excluded["Audi"]["excluded_malformed_or_unrecognized"] != 1:
            raise ValueError(f"Audi source filtering changed unexpectedly: {excluded['Audi']}")
        keys = [(row["make"], row["code"]) for row in candidates]
        if len(keys) != len(set(keys)):
            raise ValueError("Duplicate make/code records detected")
        if any(not MANUFACTURER_CODE_RE.fullmatch(row["code"]) for row in candidates):
            raise ValueError("Generic or malformed code entered the manufacturer-specific pack")

        licenses_dir = temp_dir / "LICENSES"
        licenses_dir.mkdir(parents=True, exist_ok=True)
        license_copy = licenses_dir / "Wal33D-MIT-LICENSE.txt"
        license_copy.write_bytes(fetched["LICENSE"])
        (temp_dir / "ATTRIBUTION.txt").write_text(
            attribution_text(declaration), encoding="utf-8"
        )
        (temp_dir / "README.md").write_text(readme_text_for_pack(declaration, counts, excluded), encoding="utf-8")
        (temp_dir / "source-declaration.json").write_text(
            json.dumps(declaration, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

        db_path = temp_dir / "vag-oem-dtc-candidates.sqlite"
        create_database(db_path, declaration, fetched, source_files, candidates, counts)
        manifest = {
            "schema_version": 1,
            "pack_id": "wal33d-vag-oem-dtc-mit",
            "status": "validated_research_only",
            "publisher": declaration["publisher"],
            "source_id": declaration["source_id"],
            "repository": declaration["repository"],
            "repository_url": declaration["repository_url"],
            "source_commit_sha": declaration["commit_sha"],
            "source_commit_date_utc": declaration["commit_date_utc"],
            "dataset_license": declaration["license_id"],
            "license_url": declaration["license_url"],
            "license_scope": declaration["license_scope"],
            "license_file": "LICENSES/Wal33D-MIT-LICENSE.txt",
            "license_sha256": sha256_bytes(fetched["LICENSE"]),
            "readme_sha256": sha256_bytes(fetched["README.md"]),
            "rights_status": declaration["rights_status"],
            "rights_confirmed": False,
            "commercial_use_allowed": True,
            "display_allowed": True,
            "offline_cache_allowed": True,
            "redistribution_allowed": True,
            "market_scope": "UNKNOWN",
            "applicability_precision": "manufacturer_make_candidate",
            "verification_status": "unverified_candidate",
            "product_eligibility": "research_only_pending_record_provenance_and_vehicle_validation",
            "exact_vehicle_fitment": False,
            "ecu_fitment_confirmed": False,
            "execution_allowed": False,
            "counts": counts,
            "excluded_counts": excluded,
            "source_files": source_files,
            "database_file": db_path.name,
            "database_sha256": sha256_file(db_path),
            "limitations": declaration["limitations"],
            "attribution": f"{declaration['publisher']} — {declaration['repository_url']} — commit {declaration['commit_sha']} — MIT License.",
            "built_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        (temp_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        os.replace(temp_dir, output_dir)
        return {
            "status": "validated_research_only",
            "database": str(output_dir / db_path.name),
            "database_sha256": manifest["database_sha256"],
            "counts": counts,
            "excluded_counts": excluded,
            "rights_confirmed": False,
            "market_scope": "UNKNOWN",
            "verification_status": "unverified_candidate",
        }
    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise


def attribution_text(declaration: dict[str, Any]) -> str:
    return (
        "Source attribution\n"
        f"Publisher: {declaration['publisher']}\n"
        f"Repository: {declaration['repository_url']}\n"
        f"Immutable revision: {declaration['commit_sha']}\n"
        "License: MIT; retain this notice and the complete upstream license text.\n"
        "Rights boundary: the repository declares MIT at repository level, but the "
        "upstream origin of individual DTC records has not been independently verified. "
        "This pack is research-only and not approved production repair data.\n"
    )


def readme_text_for_pack(declaration: dict[str, Any], counts: dict[str, int],
                         excluded: dict[str, dict[str, int]]) -> str:
    return (
        "# Wal33D VAG make-labelled DTC candidates\n\n"
        "This is an isolated research-only SQLite pack. It is not a factory VAG DTC catalogue.\n\n"
        f"- Volkswagen: {counts['Volkswagen']} manufacturer-controlled candidates\n"
        f"- Audi: {counts['Audi']} manufacturer-controlled candidates\n"
        f"- Total: {counts['total']}\n"
        f"- Audi generic-range rows excluded: {excluded['Audi']['excluded_generic_range']}\n"
        f"- Audi malformed/unrecognized rows excluded: {excluded['Audi']['excluded_malformed_or_unrecognized']}\n"
        f"- Source revision: {declaration['commit_sha']}\n"
        "- License declared by repository: MIT; retain LICENSES/Wal33D-MIT-LICENSE.txt and attribution.\n"
        "- Market scope: UNKNOWN.\n"
        "- Applicability: make-label candidate only; no model/year/engine/transmission/ECU/PR-code mapping.\n"
        "- Verification: unverified candidate; no execution or repair instruction is enabled.\n\n"
        "The Audi source file also contains generic SAE/ISO ranges. Those rows are excluded so "
        "generic DTCs remain in the separate CC0 OBDex pack. No Skoda or SEAT source files are "
        "present in this pinned upstream revision. No procedures, test plans, wiring diagrams, "
        "pinouts, torque values, adaptations or service schedules are included.\n\n"
        "The repository-level MIT declaration is recorded, but individual record provenance and "
        "technical accuracy are not independently verified. Do not use these candidates to select "
        "parts, execute tests, or assert exact vehicle applicability.\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=SOURCE_MANIFEST)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = build(args.manifest.resolve(), args.output.resolve())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
