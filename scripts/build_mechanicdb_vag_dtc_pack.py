#!/usr/bin/env python3
"""Build an isolated, ODbL-licensed, candidate-only Audi/VW DTC research pack."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path

EXPECTED_MAKES = {"Audi", "Volkswagen"}
COPIED_FILES = {
    "dtc_codes.csv": "upstream/dtc_codes.csv",
    "LICENSE": "upstream/LICENSE-ODbL.txt",
    "LICENSE-upstream.txt": "upstream/LICENSE-MIT.txt",
    "SOURCES.md": "upstream/SOURCES.md",
    "DATA_DICTIONARY.md": "upstream/DATA_DICTIONARY.md",
}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_blob_sha1(repo: Path, file_path: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), "hash-object", str(file_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def load_manifest(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise ValueError("Unsupported source manifest schema")
    if data.get("source_revision") != "c788dfe9ed1517d4cd0be27f5aacb4776abf4864":
        raise ValueError("The MechanicDB snapshot revision is not the pinned revision")
    if data.get("data_license") != "ODbL-1.0" or data.get("rights_status") != "approved_by_published_license":
        raise ValueError("The source license/rights gate is not satisfied")
    for key in ("commercial_use_status", "display_allowed", "cache_allowed", "redistribution_allowed", "share_alike_required"):
        if key not in data:
            raise ValueError(f"Source manifest is missing {key}")
    if data["display_allowed"] is not True or data["cache_allowed"] is not True or data["redistribution_allowed"] is not True:
        raise ValueError("The source manifest does not permit display, caching and redistribution")
    if data["share_alike_required"] is not True:
        raise ValueError("ODbL share-alike must remain enabled")
    return data


def read_selected_rows(upstream: Path, manifest: dict) -> tuple[list[dict], dict]:
    source = upstream / "dtc_codes.csv"
    raw_lines = source.read_bytes().splitlines(keepends=True)
    expected = manifest["selected_records"]["manufacturer_dtc_candidates"]
    expected_by_key = {(item["fields"]["oem_make"], item["fields"]["dtc_code"]): item for item in expected}
    found: dict[tuple[str, str], dict] = {}

    with source.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="|")
        for row in reader:
            make = (row.get("oem_make") or "").strip()
            code = (row.get("dtc_code") or "").strip().upper()
            if row.get("is_oem_specific") != "1" or make not in EXPECTED_MAKES:
                continue
            key = (make, code)
            if key in found:
                raise ValueError(f"Duplicate manufacturer DTC candidate: {key}")
            if key not in expected_by_key:
                raise ValueError(f"Unexpected Audi/VW candidate not pinned in the review manifest: {key}")
            expected_item = expected_by_key[key]
            if reader.line_num != expected_item["line_no"]:
                raise ValueError(f"{key} moved from pinned line {expected_item['line_no']} to {reader.line_num}")
            for field, value in expected_item["fields"].items():
                if row.get(field) != value:
                    raise ValueError(f"{key} field {field} differs from the reviewed manifest")
            line_no = reader.line_num
            if line_no < 1 or line_no > len(raw_lines):
                raise ValueError(f"Invalid physical source line number for {key}")
            found[key] = {
                "fields": dict(row),
                "line_no": line_no,
                "line_sha256": sha256_bytes(raw_lines[line_no - 1]),
            }

    if set(found) != set(expected_by_key):
        missing = sorted(set(expected_by_key) - set(found))
        raise ValueError(f"Pinned Audi/VW candidate rows were not found: {missing}")
    if len(found) != 2:
        raise ValueError(f"Expected exactly two Audi/VW manufacturer candidates, found {len(found)}")
    return [found[key] for key in sorted(found)], {"physical_line_count": len(raw_lines)}


def build_database(
    db_path: Path,
    manifest: dict,
    source_files: dict,
    selected_rows: list[dict],
    snapshot_sha256: str,
) -> None:
    if db_path.exists():
        db_path.unlink()
    connection = sqlite3.connect(db_path)
    try:
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA journal_mode=DELETE")
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute("PRAGMA application_id=1448368196")
        connection.execute("PRAGMA user_version=1")
        connection.executescript(
            """
            CREATE TABLE source_registry (
              source_id TEXT PRIMARY KEY,
              publisher TEXT NOT NULL,
              repository_url TEXT NOT NULL,
              source_revision TEXT NOT NULL,
              data_license TEXT NOT NULL CHECK(data_license='ODbL-1.0'),
              documentation_license TEXT NOT NULL CHECK(documentation_license='CC-BY-4.0'),
              upstream_license TEXT NOT NULL CHECK(upstream_license='MIT'),
              rights_status TEXT NOT NULL CHECK(rights_status='approved_by_published_license'),
              commercial_use_allowed INTEGER NOT NULL CHECK(commercial_use_allowed=1),
              display_allowed INTEGER NOT NULL CHECK(display_allowed=1),
              offline_cache_allowed INTEGER NOT NULL CHECK(offline_cache_allowed=1),
              redistribution_allowed INTEGER NOT NULL CHECK(redistribution_allowed=1),
              share_alike_required INTEGER NOT NULL CHECK(share_alike_required=1),
              attribution_required INTEGER NOT NULL CHECK(attribution_required=1),
              market_scope TEXT NOT NULL CHECK(market_scope='UNKNOWN'),
              applicability_precision TEXT NOT NULL CHECK(applicability_precision='manufacturer_make_candidate'),
              technical_review_status TEXT NOT NULL CHECK(technical_review_status='community_reference_unverified'),
              source_snapshot_sha256 TEXT NOT NULL CHECK(length(source_snapshot_sha256)=64)
            );

            CREATE TABLE source_files (
              relative_path TEXT PRIMARY KEY,
              source_url TEXT NOT NULL,
              source_revision TEXT NOT NULL,
              git_blob_sha1 TEXT NOT NULL CHECK(length(git_blob_sha1)=40),
              sha256 TEXT NOT NULL CHECK(length(sha256)=64),
              byte_size INTEGER NOT NULL CHECK(byte_size>0),
              file_kind TEXT NOT NULL
            );

            CREATE TABLE dtc_candidates (
              id INTEGER PRIMARY KEY,
              code_id INTEGER NOT NULL,
              dtc_code TEXT NOT NULL CHECK(length(dtc_code)=5),
              oem_make TEXT NOT NULL CHECK(oem_make IN ('Audi','Volkswagen')),
              system_category TEXT NOT NULL,
              fault_family TEXT NOT NULL,
              short_description TEXT NOT NULL,
              detailed_technical_explanation TEXT NOT NULL,
              namespace TEXT NOT NULL CHECK(namespace='manufacturer_controlled_candidate'),
              verification_status TEXT NOT NULL CHECK(verification_status='community_reference_unverified'),
              market_scope TEXT NOT NULL CHECK(market_scope='UNKNOWN'),
              applicability_precision TEXT NOT NULL CHECK(applicability_precision='manufacturer_make_candidate'),
              vehicle_fitment_claim INTEGER NOT NULL CHECK(vehicle_fitment_claim=0),
              ecu_fitment_claim INTEGER NOT NULL CHECK(ecu_fitment_claim=0),
              pr_code_claim INTEGER NOT NULL CHECK(pr_code_claim=0),
              diagnostic_execution_allowed INTEGER NOT NULL CHECK(diagnostic_execution_allowed=0),
              repair_procedure_included INTEGER NOT NULL CHECK(repair_procedure_included=0),
              oem_part_number_included INTEGER NOT NULL CHECK(oem_part_number_included=0),
              source_file TEXT NOT NULL REFERENCES source_files(relative_path),
              source_line_no INTEGER NOT NULL CHECK(source_line_no>1),
              source_line_sha256 TEXT NOT NULL CHECK(length(source_line_sha256)=64),
              source_file_sha256 TEXT NOT NULL CHECK(length(source_file_sha256)=64),
              source_revision TEXT NOT NULL,
              UNIQUE(oem_make,dtc_code,source_revision)
            );

            CREATE TABLE pack_metadata (
              key TEXT PRIMARY KEY,
              value TEXT NOT NULL
            );

            CREATE INDEX idx_dtc_candidate_make_code ON dtc_candidates(oem_make,dtc_code);
            CREATE INDEX idx_dtc_candidate_namespace ON dtc_candidates(namespace,verification_status);
            """
        )
        source_id = manifest["source_id"]
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            """
            INSERT INTO source_registry VALUES
            (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                source_id,
                manifest["publisher"],
                manifest["repository"],
                manifest["source_revision"],
                manifest["data_license"],
                manifest["documentation_license"],
                manifest["upstream_license"],
                manifest["rights_status"],
                1,
                1,
                1,
                1,
                1,
                1,
                "UNKNOWN",
                "manufacturer_make_candidate",
                "community_reference_unverified",
                snapshot_sha256,
            ),
        )
        for relative_path, item in source_files.items():
            connection.execute(
                "INSERT INTO source_files VALUES (?,?,?,?,?,?,?)",
                (
                    relative_path,
                    item["source_url"],
                    manifest["source_revision"],
                    item["git_blob_sha1"],
                    item["sha256"],
                    item["byte_size"],
                    item["file_kind"],
                ),
            )
        dtc_file = source_files["upstream/dtc_codes.csv"]
        for item in selected_rows:
            fields = item["fields"]
            connection.execute(
                """
                INSERT INTO dtc_candidates (
                  code_id,dtc_code,oem_make,system_category,fault_family,short_description,
                  detailed_technical_explanation,namespace,verification_status,market_scope,
                  applicability_precision,vehicle_fitment_claim,ecu_fitment_claim,pr_code_claim,
                  diagnostic_execution_allowed,repair_procedure_included,oem_part_number_included,
                  source_file,source_line_no,source_line_sha256,source_file_sha256,source_revision
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    int(fields["code_id"]),
                    fields["dtc_code"],
                    fields["oem_make"],
                    fields["system_category"],
                    fields["fault_family"],
                    fields["short_description"],
                    fields["detailed_technical_explanation"],
                    "manufacturer_controlled_candidate",
                    "community_reference_unverified",
                    "UNKNOWN",
                    "manufacturer_make_candidate",
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    "upstream/dtc_codes.csv",
                    item["line_no"],
                    item["line_sha256"],
                    dtc_file["sha256"],
                    manifest["source_revision"],
                ),
            )
        metadata = {
            "pack_id": "mechanicdb-vag-dtc-candidates-odbl",
            "schema_version": "1",
            "product_eligibility": "candidate_reference_only_hidden",
            "generic_dtc_rows": "0",
            "manufacturer_candidate_rows": str(len(selected_rows)),
            "exact_vehicle_fitment": "false",
            "repair_procedures_included": "false",
            "oem_part_numbers_included": "false",
            "diagnostic_execution_allowed": "false",
            "market_scope": "UNKNOWN",
            "applicability_precision": "manufacturer_make_candidate",
            "source_snapshot_sha256": snapshot_sha256,
        }
        connection.executemany("INSERT INTO pack_metadata(key,value) VALUES (?,?)", sorted(metadata.items()))
        connection.commit()
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        foreign_keys = connection.execute("PRAGMA foreign_key_check").fetchall()
        if integrity != "ok" or foreign_keys:
            raise RuntimeError(f"SQLite integrity failure: {integrity}; foreign keys: {foreign_keys[:5]}")
        connection.execute("VACUUM")
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream-dir", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    upstream = args.upstream_dir.resolve()
    if not (upstream / ".git").exists():
        raise SystemExit("The pinned upstream Git repository is required")
    manifest = load_manifest(args.manifest)
    revision = subprocess.run(
        ["git", "-C", str(upstream), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if revision != manifest["source_revision"]:
        raise SystemExit(f"Upstream revision mismatch: {revision}")

    selected_rows, source_shape = read_selected_rows(upstream, manifest)
    output = args.output.resolve()
    if output.exists():
        shutil.rmtree(output)
    (output / "upstream").mkdir(parents=True)

    source_files: dict[str, dict] = {}
    for upstream_name, relative_path in COPIED_FILES.items():
        source_path = upstream / upstream_name
        if not source_path.is_file():
            raise SystemExit(f"Missing pinned upstream file: {upstream_name}")
        declared = manifest["source_files"][upstream_name]
        actual_git_sha = git_blob_sha1(upstream, source_path)
        if actual_git_sha != declared["git_blob_sha1"]:
            raise SystemExit(f"Git blob SHA-1 mismatch for {upstream_name}")
        destination = output / relative_path
        shutil.copyfile(source_path, destination)
        source_files[relative_path] = {
            "source_url": declared["url"],
            "git_blob_sha1": actual_git_sha,
            "sha256": sha256_file(destination),
            "byte_size": destination.stat().st_size,
            "file_kind": (
                "source_data" if upstream_name == "dtc_codes.csv"
                else "license_text" if upstream_name.startswith("LICENSE")
                else "attribution_documentation"
            ),
        }

    snapshot_material = json.dumps(
        {key: value["sha256"] for key, value in sorted(source_files.items())},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    snapshot_sha256 = sha256_bytes(snapshot_material)
    db_path = output / "mechanicdb-vag-dtc-candidates.sqlite"
    build_database(db_path, manifest, source_files, selected_rows, snapshot_sha256)

    attribution = (
        "Contains a selected Audi/Volkswagen manufacturer-labelled DTC sample from "
        "MechanicDB / MechanicDB-public, pinned revision "
        f"{manifest['source_revision']}.\n"
        "Dataset license: Open Database License (ODbL) v1.0. Attribution and share-alike "
        "obligations apply to this separate database. The free sample is used; no paid/full "
        "database content is included.\n"
        "The DTC code spine is attributed by MechanicDB to Wal33D / Waleed Judah's "
        "MIT-licensed dtc-database compilation. The upstream MIT notice is preserved.\n"
        "Only two make-labelled candidates are included (Audi P3000 and Volkswagen P1128). "
        "They are community reference candidates, not OEM-confirmed definitions. Market, "
        "model, generation, year, engine, gearbox, ECU, PR-code and VIN applicability are "
        "unknown. No repair procedures, parts, test plans or executable diagnostics are included.\n"
    )
    (output / "ATTRIBUTION.txt").write_text(attribution, encoding="utf-8", newline="\n")

    file_hashes = {
        path.relative_to(output).as_posix(): {
            "sha256": sha256_file(path),
            "byte_size": path.stat().st_size,
        }
        for path in sorted(output.rglob("*"))
        if path.is_file()
    }
    pack_manifest = {
        "schema_version": 1,
        "pack_id": "mechanicdb-vag-dtc-candidates-odbl",
        "publisher": manifest["publisher"],
        "source_repository": manifest["repository"],
        "source_revision": manifest["source_revision"],
        "snapshot_date": manifest["snapshot_date"],
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "data_license": "ODbL-1.0",
        "data_license_url": manifest["data_license_url"],
        "upstream_license": "MIT",
        "documentation_license": "CC-BY-4.0",
        "rights_status": "approved_by_published_license",
        "commercial_use_allowed_under_odbl": True,
        "display_allowed": True,
        "offline_cache_allowed": True,
        "redistribution_allowed_under_odbl": True,
        "share_alike_required": True,
        "attribution_required": True,
        "source_snapshot_sha256": snapshot_sha256,
        "database_path": db_path.name,
        "database_sha256": sha256_file(db_path),
        "counts": {
            "manufacturer_controlled_candidates": len(selected_rows),
            "audi_candidates": sum(1 for item in selected_rows if item["fields"]["oem_make"] == "Audi"),
            "volkswagen_candidates": sum(1 for item in selected_rows if item["fields"]["oem_make"] == "Volkswagen"),
            "generic_dtc_rows": 0,
            "repair_procedure_rows": 0,
            "part_rows": 0,
        },
        "market_scope": "UNKNOWN",
        "applicability_precision": "manufacturer_make_candidate",
        "verification_status": "community_reference_unverified",
        "product_eligibility": "candidate_reference_only_hidden_pending_technical_review",
        "display_status": "hidden_pending_technical_review",
        "exact_vehicle_fitment": False,
        "ecu_fitment": False,
        "pr_code_fitment": False,
        "diagnostic_execution_allowed": False,
        "repair_procedures_included": False,
        "oem_part_numbers_included": False,
        "source_line_evidence": [
            {
                "oem_make": item["fields"]["oem_make"],
                "dtc_code": item["fields"]["dtc_code"],
                "source_file": "upstream/dtc_codes.csv",
                "source_line_no": item["line_no"],
                "source_line_sha256": item["line_sha256"],
            }
            for item in selected_rows
        ],
        "source_files": source_files,
        "pack_files": file_hashes,
        "source_shape": source_shape,
        "exclusions": [
            "Generic SAE/ISO rows are not copied into this pack; they remain in the separate CC0 OBDex pack.",
            "Community diagnostic fixes and replacement-part mappings are not copied or exposed.",
            "No exact vehicle, ECU, engine, gearbox, PR-code, VIN or market applicability is asserted.",
        ],
    }
    manifest_path = output / "manifest.json"
    manifest_path.write_text(
        json.dumps(pack_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    checksum_paths = [
        path for path in sorted(output.rglob("*"))
        if path.is_file() and path.name != "SHA256SUMS.txt"
    ]
    sums = "\n".join(f"{sha256_file(path)}  {path.relative_to(output).as_posix()}" for path in checksum_paths) + "\n"
    (output / "SHA256SUMS.txt").write_text(sums, encoding="utf-8", newline="\n")

    print(json.dumps({
        "status": "built_candidate_only",
        "pack_id": pack_manifest["pack_id"],
        "database_sha256": pack_manifest["database_sha256"],
        "source_snapshot_sha256": snapshot_sha256,
        "counts": pack_manifest["counts"],
        "market_scope": pack_manifest["market_scope"],
        "applicability_precision": pack_manifest["applicability_precision"],
        "product_eligibility": pack_manifest["product_eligibility"],
        "output": str(output),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
