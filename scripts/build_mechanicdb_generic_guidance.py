#!/usr/bin/env python3
"""Build a provenance-preserving, generic-only MechanicDB guidance SQLite pack."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sqlite3
import tempfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SOURCE_REPOSITORY = "https://github.com/MechanicDB/MechanicDB-public"
SOURCE_REVISION = "c788dfe9ed1517d4cd0be27f5aacb4776abf4864"
RAW_BASE = f"https://raw.githubusercontent.com/MechanicDB/MechanicDB-public/{SOURCE_REVISION}/"
SOURCE_ID = "mechanicdb-public-generic-repair-guidance"
ODBL_URL = "https://opendatacommons.org/licenses/odbl/1-0/"
ATTRIBUTION = "MechanicDB — https://github.com/MechanicDB/MechanicDB-public"

EXPECTED_FILES = {
    "dtc_codes.csv": {
        "git_blob_sha1": "34fa7dd7a1cbdd5b0d2675f2c77a2b659c6069b4",
        "purpose": "Generic SAE DTC identifier crosswalk only; descriptions are not imported",
        "record_count": 90,
    },
    "diagnostic_fixes.csv": {
        "git_blob_sha1": "5238ab82447a26e14227e932126d068ab47bf6e3",
        "purpose": "MechanicDB-authored generic diagnostic guidance; OEM-linked rows are excluded",
        "record_count": 326,
    },
    "LICENSE": {
        "git_blob_sha1": "20e7514419d20bdbcc89d6a2ebcff90d0d3575a8",
        "purpose": "Published ODbL sample-dataset licensing notice",
        "record_count": None,
    },
    "LICENSE-upstream.txt": {
        "git_blob_sha1": "9cbfaae3f07b8daa1685b4587e36c604a7a4ded1",
        "purpose": "Preserved upstream MIT attribution notice",
        "record_count": None,
    },
    "SOURCES.md": {
        "git_blob_sha1": "99301063307b9fd10bef7b84cd5c9e7066aeceb9",
        "purpose": "Provenance statement for authored guidance; verified but not bundled",
        "record_count": None,
    },
    "DATA_DICTIONARY.md": {
        "git_blob_sha1": "808dea805df7d86b3ee1bf301fcef5455df25176",
        "purpose": "Field semantics and consideration-order definition; verified but not bundled",
        "record_count": None,
    },
}

ATTRIBUTION_TEXT = """# Attribution and data license

This separate generic repair-guidance database is adapted from the free public sample published by **MechanicDB / DataEngineered**:

- Source: https://github.com/MechanicDB/MechanicDB-public
- Pinned revision: c788dfe9ed1517d4cd0be27f5aacb4776abf4864
- Data license: Open Database License (ODbL) v1.0 — https://opendatacommons.org/licenses/odbl/1-0/
- Attribution: **MechanicDB** (link to the source repository).
- Share-Alike: this adapted database is also made available under ODbL v1.0.

The pack contains only generic SAE/ISO DTC identifiers and MechanicDB-authored generic diagnostic guidance. It does not contain the sample's DTC descriptions, detailed code explanations, manufacturer-labelled rows, parts mappings, costs, labor estimates, or OEM repair content. The upstream MIT notice is preserved separately for attribution transparency.

No VAG-specific definition, model/generation/year fitment, engine/gearbox/ECU fitment, RU/EAEU market applicability, OEM repair procedure, or diagnostic command is asserted.

The guidance is educational generic reference material, has not been independently reviewed by a VAG engineer, and must not replace the exact manufacturer's service information. Safety-critical work must follow the applicable OEM procedure.
"""


def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob_sha1(data: bytes) -> str:
    header = b"blob " + str(len(data)).encode("ascii") + b"\0"
    return hashlib.sha1(header + data).hexdigest()


def download_sources(source_dir: Path) -> None:
    source_dir.mkdir(parents=True, exist_ok=True)
    for name in EXPECTED_FILES:
        target = source_dir / name
        if not target.exists():
            request = urllib.request.Request(
                RAW_BASE + name,
                headers={"User-Agent": "VAG-TECH-PRO-source-verifier/1.0"},
            )
            with urllib.request.urlopen(request, timeout=45) as response:
                target.write_bytes(response.read())


def read_source_file(source_dir: Path, name: str) -> tuple[bytes, dict]:
    path = source_dir / name
    if not path.is_file():
        fail(f"missing source file: {name}")
    raw = path.read_bytes()
    actual_blob = git_blob_sha1(raw)
    expected_blob = EXPECTED_FILES[name]["git_blob_sha1"]
    if actual_blob != expected_blob:
        fail(f"pinned Git blob SHA-1 mismatch for {name}: {actual_blob}")
    return raw, {
        "source_url": RAW_BASE + name,
        "git_blob_sha1": actual_blob,
        "sha256": sha256(raw),
        "byte_size": len(raw),
        "record_count": EXPECTED_FILES[name]["record_count"],
        "purpose": EXPECTED_FILES[name]["purpose"],
    }


def parse_pipe_csv(raw: bytes, name: str) -> tuple[list[dict[str, str]], list[bytes]]:
    physical_lines = raw.splitlines(keepends=True)
    try:
        decoded = raw.decode("utf-8-sig")
        rows = list(csv.DictReader(io.StringIO(decoded, newline=""), delimiter="|", strict=True))
    except (UnicodeDecodeError, csv.Error) as error:
        fail(f"cannot parse {name}: {error}")
    if len(physical_lines) != len(rows) + 1:
        fail(f"{name} is not one-record-per-physical-line; row-level evidence is unsafe")
    if not rows:
        fail(f"{name} is empty")
    for row_number, row in enumerate(rows, start=2):
        if any("\n" in value or "\r" in value for value in row.values() if value is not None):
            fail(f"{name}:{row_number} contains an embedded line break")
    return rows, physical_lines


def is_generic_sae_code(code: str) -> bool:
    if not re.fullmatch(r"[PBCU][0-9A-F]{4}", code):
        return False
    family = code[0]
    digits = code[1:]
    if family == "P":
        return digits[0] in ("0", "2") or 0x34 <= int(digits[:2], 16) <= 0x39
    if family in ("B", "C"):
        return digits[0] == "0"
    return digits[0] in ("0", "3")


def logical_content_hash(
    source_info: dict[str, dict],
    generic_codes: list[dict],
    generic_fixes: list[dict],
) -> str:
    source_files = [
        {
            "source_file_id": name,
            "source_url": info["source_url"],
            "git_blob_sha1": info["git_blob_sha1"],
            "sha256": info["sha256"],
            "byte_size": info["byte_size"],
            "record_count": info["record_count"],
            "purpose": info["purpose"],
        }
        for name, info in sorted(source_info.items())
    ]
    codes = [
        {key: row[key] for key in (
            "dtc_code", "source_record_id", "system_category", "source_file_sha256",
            "source_line_no", "source_line_sha256",
        )}
        for row in sorted(generic_codes, key=lambda item: item["dtc_code"])
    ]
    guidance = [
        {key: row[key] for key in (
            "guidance_id", "dtc_code", "consideration_order", "skill_level", "title",
            "instructions", "action_type", "rationale", "source_file_sha256",
            "source_line_no", "source_line_sha256",
        )}
        for row in sorted(generic_fixes, key=lambda item: (
            item["dtc_code"], item["consideration_order"], item["guidance_id"]
        ))
    ]
    payload = {
        "source_revision": SOURCE_REVISION,
        "data_license": "ODbL-1.0",
        "namespace": "generic_sae_iso",
        "manufacturer": "UNKNOWN",
        "market_scope": "UNKNOWN",
        "applicability_level": "generic_only",
        "vag_specific": False,
        "diagnostic_execution_allowed": False,
        "source_files": source_files,
        "generic_dtc_references": codes,
        "generic_repair_guidance": guidance,
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(canonical.encode("utf-8"))


def create_database(
    database_path: Path,
    schema_path: Path,
    source_info: dict[str, dict],
    generic_codes: list[dict],
    generic_fixes: list[dict],
    logical_hash: str,
) -> None:
    if database_path.exists():
        database_path.unlink()
    connection = sqlite3.connect(database_path)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(schema_path.read_text(encoding="utf-8"))
        connection.execute("PRAGMA user_version = 1")

        source_registry = (
            SOURCE_ID,
            "MechanicDB / DataEngineered",
            SOURCE_REPOSITORY,
            SOURCE_REVISION,
            "ODbL-1.0",
            ODBL_URL,
            "approved_by_published_license",
            1, 1, 1, 1, 1, 1,
            ATTRIBUTION,
            "UNKNOWN",
            "generic_code_only",
            "not_independently_reviewed",
            "not_assessed",
        )
        connection.execute(
            """INSERT INTO source_registry (
              source_id,publisher,repository_url,source_revision,data_license,license_url,
              rights_status,commercial_use_allowed,display_allowed,offline_cache_allowed,
              redistribution_allowed,share_alike_required,attribution_required,attribution_text,
              market_scope,applicability_precision,technical_review_status,safety_review_status
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            source_registry,
        )

        for name, info in source_info.items():
            connection.execute(
                """INSERT INTO source_files (
                  source_file_id,source_id,source_url,git_blob_sha1,sha256,byte_size,record_count,purpose
                ) VALUES (?,?,?,?,?,?,?,?)""",
                (
                    name, SOURCE_ID, info["source_url"], info["git_blob_sha1"],
                    info["sha256"], info["byte_size"], info["record_count"], info["purpose"],
                ),
            )

        for item in generic_codes:
            connection.execute(
                """INSERT INTO generic_dtc_references (
                  dtc_code,source_record_id,system_category,namespace,manufacturer,market_scope,
                  applicability_level,vag_specific,diagnostic_execution_allowed,technical_review_status,
                  source_file_id,source_revision,source_file_sha256,source_line_no,source_line_sha256
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    item["dtc_code"], item["source_record_id"], item["system_category"],
                    "generic_sae_iso", "UNKNOWN", "UNKNOWN", "generic_only", 0, 0,
                    "not_independently_reviewed", "dtc_codes.csv", SOURCE_REVISION,
                    item["source_file_sha256"], item["source_line_no"], item["source_line_sha256"],
                ),
            )

        for item in generic_fixes:
            connection.execute(
                """INSERT INTO generic_repair_guidance (
                  guidance_id,dtc_code,consideration_order,skill_level,title,instructions,
                  action_type,rationale,namespace,manufacturer,market_scope,applicability_level,
                  vag_specific,diagnostic_execution_allowed,technical_review_status,safety_review_status,
                  source_file_id,source_revision,source_file_sha256,source_line_no,source_line_sha256,
                  source_license
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    item["guidance_id"], item["dtc_code"], item["consideration_order"],
                    item["skill_level"], item["title"], item["instructions"], item["action_type"],
                    item["rationale"], "generic_sae_iso", "UNKNOWN", "UNKNOWN", "generic_only",
                    0, 0, "not_independently_reviewed", "not_assessed",
                    "diagnostic_fixes.csv", SOURCE_REVISION, item["source_file_sha256"],
                    item["source_line_no"], item["source_line_sha256"], "ODbL-1.0",
                ),
            )

        metadata = {
            "pack_id": "mechanicdb-generic-repair-guidance-odbl",
            "schema_version": "1",
            "source_revision": SOURCE_REVISION,
            "namespace": "generic_sae_iso",
            "market_scope": "UNKNOWN",
            "technical_review_status": "not_independently_reviewed",
            "logical_content_sha256": logical_hash,
        }
        connection.executemany(
            "INSERT INTO pack_metadata(key,value) VALUES (?,?)",
            sorted(metadata.items()),
        )
        connection.commit()

        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        foreign_key_errors = connection.execute("PRAGMA foreign_key_check").fetchall()
        if integrity != "ok" or foreign_key_errors:
            fail(f"SQLite integrity failed: {integrity}; foreign-key errors={foreign_key_errors}")
        if connection.execute("SELECT count(*) FROM generic_dtc_references").fetchone()[0] != 75:
            fail("SQLite generic DTC count is not 75")
        if connection.execute("SELECT count(*) FROM generic_repair_guidance").fetchone()[0] != 275:
            fail("SQLite generic guidance count is not 275")
    finally:
        connection.close()


def build(source_dir: Path, output_dir: Path, schema_path: Path) -> dict:
    download_sources(source_dir)
    raw_files: dict[str, bytes] = {}
    source_info: dict[str, dict] = {}
    for name in EXPECTED_FILES:
        raw, info = read_source_file(source_dir, name)
        raw_files[name] = raw
        source_info[name] = info

    codes, code_lines = parse_pipe_csv(raw_files["dtc_codes.csv"], "dtc_codes.csv")
    fixes, fix_lines = parse_pipe_csv(raw_files["diagnostic_fixes.csv"], "diagnostic_fixes.csv")

    if len(codes) != 90 or len(fixes) != 326:
        fail(f"pinned sample row counts changed: codes={len(codes)}, fixes={len(fixes)}")

    code_by_id: dict[str, dict] = {}
    generic_codes: list[dict] = []
    oem_codes: list[dict] = []
    for index, row in enumerate(codes, start=2):
        code_id = row.get("code_id", "")
        code = row.get("dtc_code", "").upper()
        if not code_id or code_id in code_by_id:
            fail(f"missing or duplicate source code_id at dtc_codes.csv:{index}")
        code_by_id[code_id] = row
        if row.get("is_oem_specific") not in ("0", "1"):
            fail(f"invalid is_oem_specific flag at dtc_codes.csv:{index}")
        if row.get("is_oem_specific") == "0":
            if row.get("oem_make", ""):
                fail(f"generic row has an OEM make label at dtc_codes.csv:{index}")
            if not is_generic_sae_code(code):
                fail(f"generic row is outside the allowed SAE ranges: {code}")
            generic_codes.append({
                "dtc_code": code,
                "source_record_id": code_id,
                "system_category": row.get("system_category", ""),
                "source_file_sha256": source_info["dtc_codes.csv"]["sha256"],
                "source_line_no": index,
                "source_line_sha256": sha256(code_lines[index - 1]),
            })
        else:
            oem_codes.append(row)

    if len(generic_codes) != 75 or len(oem_codes) != 15:
        fail(f"unexpected namespace counts: generic={len(generic_codes)}, OEM-labelled={len(oem_codes)}")
    if len({row["dtc_code"] for row in generic_codes}) != len(generic_codes):
        fail("duplicate generic SAE DTC identifiers")
    if sum(1 for row in oem_codes if row.get("oem_make") == "Audi") != 1:
        fail("pinned sample's Audi-labelled exclusion count changed")
    if sum(1 for row in oem_codes if row.get("oem_make") == "Volkswagen") != 1:
        fail("pinned sample's Volkswagen-labelled exclusion count changed")

    generic_by_source_id = {row["source_record_id"]: row["dtc_code"] for row in generic_codes}
    generic_fixes: list[dict] = []
    oem_fix_count = 0
    orphan_count = 0
    seen_fix_ids: set[str] = set()
    for index, row in enumerate(fixes, start=2):
        fix_id = row.get("fix_id", "")
        code_id = row.get("code_id", "")
        if not fix_id or fix_id in seen_fix_ids:
            fail(f"missing or duplicate fix_id at diagnostic_fixes.csv:{index}")
        seen_fix_ids.add(fix_id)
        code_row = code_by_id.get(code_id)
        if code_row is None:
            orphan_count += 1
            continue
        if code_row.get("is_oem_specific") == "1":
            oem_fix_count += 1
            continue
        if code_id not in generic_by_source_id:
            fail(f"generic fix does not resolve to the generic namespace at line {index}")
        try:
            consideration_order = int(row.get("probability_rank", ""))
        except ValueError:
            fail(f"invalid consideration order at diagnostic_fixes.csv:{index}")
        title = row.get("fix_title", "").strip()
        instructions = row.get("step_by_step_instructions", "").strip()
        if not title or not instructions or consideration_order < 1:
            fail(f"incomplete guidance row at diagnostic_fixes.csv:{index}")
        generic_fixes.append({
            "guidance_id": fix_id,
            "dtc_code": generic_by_source_id[code_id],
            "consideration_order": consideration_order,
            "skill_level": row.get("difficulty_level", "").strip(),
            "title": title,
            "instructions": instructions,
            "action_type": row.get("action_type", "").strip() or None,
            "rationale": row.get("procedure_rationale", "").strip() or None,
            "source_file_sha256": source_info["diagnostic_fixes.csv"]["sha256"],
            "source_line_no": index,
            "source_line_sha256": sha256(fix_lines[index - 1]),
        })

    if len(generic_fixes) != 275 or oem_fix_count != 51 or orphan_count != 0:
        fail(f"unexpected guidance counts: generic={len(generic_fixes)}, OEM-excluded={oem_fix_count}, orphan={orphan_count}")

    logical_hash = logical_content_hash(source_info, generic_codes, generic_fixes)
    output_dir.mkdir(parents=True, exist_ok=True)
    database_path = output_dir / "generic-repair-guidance.sqlite"
    create_database(database_path, schema_path, source_info, generic_codes, generic_fixes, logical_hash)

    license_odbl = output_dir / "LICENSE-ODbL.txt"
    license_mit = output_dir / "LICENSE-MIT.txt"
    attribution_file = output_dir / "ATTRIBUTION.md"
    license_odbl.write_bytes(raw_files["LICENSE"])
    license_mit.write_bytes(raw_files["LICENSE-upstream.txt"])
    attribution_file.write_text(ATTRIBUTION_TEXT, encoding="utf-8", newline="\n")

    source_snapshot_payload = [
        {"path": name, "sha256": source_info[name]["sha256"]}
        for name in sorted(source_info)
    ]
    source_snapshot_sha256 = sha256(
        json.dumps(source_snapshot_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    database_sha256 = sha256(database_path.read_bytes())
    manifest = {
        "schema_version": 1,
        "pack_id": "mechanicdb-generic-repair-guidance-odbl",
        "publisher": "MechanicDB / DataEngineered",
        "source_repository": SOURCE_REPOSITORY,
        "source_revision": SOURCE_REVISION,
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "data_license": "ODbL-1.0",
        "data_license_url": ODBL_URL,
        "rights_status": "approved_by_published_license",
        "commercial_use_allowed": True,
        "display_allowed": True,
        "offline_cache_allowed": True,
        "redistribution_allowed": True,
        "share_alike_required": True,
        "attribution_required": True,
        "attribution_text": ATTRIBUTION,
        "source_snapshot_sha256": source_snapshot_sha256,
        "logical_content_sha256": logical_hash,
        "database_file": database_path.name,
        "database_sha256": database_sha256,
        "counts": {
            "generic_sae_dtc_references": len(generic_codes),
            "generic_authored_guidance": len(generic_fixes),
            "manufacturer_labelled_dtc_rows_excluded": len(oem_codes),
            "manufacturer_labelled_guidance_rows_excluded": oem_fix_count,
            "orphan_guidance_rows": orphan_count,
            "generic_dtc_descriptions_copied": 0,
            "detailed_code_explanations_copied": 0,
            "replacement_parts_rows_copied": 0,
            "cost_or_labor_estimates_copied": 0,
        },
        "source_files": source_info,
        "pack_files": {
            "generic-repair-guidance.sqlite": {
                "sha256": database_sha256,
                "byte_size": database_path.stat().st_size,
            },
            "LICENSE-ODbL.txt": {
                "sha256": sha256(license_odbl.read_bytes()),
                "byte_size": license_odbl.stat().st_size,
            },
            "LICENSE-MIT.txt": {
                "sha256": sha256(license_mit.read_bytes()),
                "byte_size": license_mit.stat().st_size,
            },
            "ATTRIBUTION.md": {
                "sha256": sha256(attribution_file.read_bytes()),
                "byte_size": attribution_file.stat().st_size,
            },
            "schema_sql_sha256": sha256(schema_path.read_bytes()),
        },
        "scope": {
            "namespace": "generic_sae_iso",
            "manufacturer": "UNKNOWN",
            "market_scope": "UNKNOWN",
            "applicability_level": "generic_only",
            "vag_specific": False,
            "exact_vehicle_fitment": False,
            "model_generation_year_fitment": False,
            "engine_gearbox_fitment": False,
            "ecu_fitment": False,
            "pr_code_fitment": False,
            "vin_fitment": False,
            "diagnostic_execution_allowed": False,
            "oem_repair_procedure": False,
            "technical_review_status": "not_independently_reviewed",
            "safety_review_status": "not_assessed",
        },
        "limitations": [
            "Generic educational reference only; not VAG-specific and not an OEM workshop procedure.",
            "No Russian or EAEU market applicability is established.",
            "No model, generation, year, engine, gearbox, ECU, PR-code or VIN fitment is established.",
            "The source probability_rank is authored consideration order, not measured probability; it is stored as consideration_order.",
            "Do not execute diagnostic commands or use these steps as a substitute for the exact OEM service procedure.",
            "Safety-critical systems require the applicable manufacturer procedure and safety instructions.",
        ],
        "exclusions": [
            "All 15 manufacturer-labelled DTC rows and their 51 associated guidance rows.",
            "All DTC descriptions and detailed code explanations.",
            "All replacement-parts mappings, cost estimates and labor estimates.",
            "All OEM procedures, wiring diagrams, pinouts, torque values, adaptations and ECU applicability.",
        ],
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("build/generic-repair-guidance"))
    parser.add_argument("--schema", type=Path, default=Path("data/sql/generic-repair-guidance.sql"))
    args = parser.parse_args()

    if args.source_dir:
        source_dir = args.source_dir.resolve()
        source_dir.mkdir(parents=True, exist_ok=True)
        manifest = build(source_dir, args.output_dir.resolve(), args.schema.resolve())
    else:
        with tempfile.TemporaryDirectory(prefix="vag-tech-pro-mechanicdb-") as temp:
            manifest = build(Path(temp), args.output_dir.resolve(), args.schema.resolve())

    print(json.dumps({
        "pack_id": manifest["pack_id"],
        "database_sha256": manifest["database_sha256"],
        "source_snapshot_sha256": manifest["source_snapshot_sha256"],
        "counts": manifest["counts"],
        "market_scope": manifest["scope"]["market_scope"],
        "namespace": manifest["scope"]["namespace"],
    }, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
