#!/usr/bin/env python3
"""Import pinned ODbL VAG identity/engine-variant candidates into a separate research SQLite.

This database is NOT production fitment data. Market scope remains UNKNOWN; engine and
gearbox codes are deliberately NULL. Public redistribution of an adapted database must
retain the ODbL 1.0 share-alike terms and attribution.
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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DATASET = "vehicle-makes-models"
LICENSE_ID = "ODbL-1.0"
LICENSE_URL = "https://opendatacommons.org/licenses/odbl/1-0/"
FORBIDDEN_CODE_KEYS = {
    "enginecode", "gearboxcode", "transmissioncode", "engineid", "gearboxid",
    "transmissionid", "ecu", "ecucode", "ecuid",
}


DDL = """
PRAGMA foreign_keys=ON;
CREATE TABLE research_sources(
 source_id TEXT PRIMARY KEY,
 publisher TEXT NOT NULL,
 dataset TEXT NOT NULL,
 upstream_revision TEXT NOT NULL,
 source_url TEXT NOT NULL,
 upstream_source TEXT NOT NULL,
 license TEXT NOT NULL CHECK(license='ODbL-1.0'),
 license_url TEXT NOT NULL,
 license_sha256 TEXT NOT NULL CHECK(length(license_sha256)=64),
 attribution TEXT NOT NULL,
 share_alike TEXT NOT NULL CHECK(share_alike='ODbL-1.0'),
 rights_status TEXT NOT NULL CHECK(rights_status='upstream_declared_ODbL_1_0'),
 rights_review_status TEXT NOT NULL CHECK(rights_review_status='research_only_upstream_provenance_not_independently_verified'),
 source_sha256 TEXT NOT NULL CHECK(length(source_sha256)=64),
 source_file_manifest_json TEXT NOT NULL,
 market_scope TEXT NOT NULL CHECK(market_scope='UNKNOWN'),
 publication_status TEXT NOT NULL CHECK(publication_status='research_only'),
 imported_at_utc TEXT NOT NULL
);
CREATE TABLE source_file_artifacts(
 artifact_id INTEGER PRIMARY KEY,
 source_id TEXT REFERENCES research_sources(source_id),
 relative_path TEXT NOT NULL,
 file_kind TEXT NOT NULL CHECK(file_kind IN ('source_json','license_text')),
 byte_size INTEGER NOT NULL CHECK(byte_size>0),
 sha256 TEXT NOT NULL CHECK(length(sha256)=64),
 source_url TEXT NOT NULL,
 UNIQUE(source_id,relative_path)
);
CREATE TABLE make_candidates(
 make_candidate_id INTEGER PRIMARY KEY,
 source_id TEXT NOT NULL REFERENCES research_sources(source_id),
 brand_key TEXT NOT NULL,
 make_name TEXT NOT NULL,
 raw_json TEXT NOT NULL,
 record_sha256 TEXT NOT NULL CHECK(length(record_sha256)=64),
 market_scope TEXT NOT NULL CHECK(market_scope='UNKNOWN'),
 applicability_precision TEXT NOT NULL CHECK(applicability_precision='make_name_candidate'),
 review_status TEXT NOT NULL CHECK(review_status='candidate')
);
CREATE TABLE model_candidates(
 model_candidate_id INTEGER PRIMARY KEY,
 make_candidate_id INTEGER NOT NULL REFERENCES make_candidates(make_candidate_id),
 model_index INTEGER NOT NULL,
 model_name TEXT NOT NULL,
 year_start INTEGER,
 year_end INTEGER,
 year_start_raw TEXT,
 year_end_raw TEXT,
 year_range_status TEXT NOT NULL CHECK(year_range_status IN ('known_range','partial_range','not_provided','source_text_unparsed')),
 raw_json TEXT NOT NULL,
 record_sha256 TEXT NOT NULL CHECK(length(record_sha256)=64),
 market_scope TEXT NOT NULL CHECK(market_scope='UNKNOWN'),
 applicability_precision TEXT NOT NULL CHECK(applicability_precision='model_name_candidate'),
 review_status TEXT NOT NULL CHECK(review_status='candidate'),
 UNIQUE(make_candidate_id,model_index),
 CHECK(year_start IS NULL OR year_end IS NULL OR year_start<=year_end)
);
CREATE TABLE generation_candidates(
 generation_candidate_id INTEGER PRIMARY KEY,
 model_candidate_id INTEGER NOT NULL REFERENCES model_candidates(model_candidate_id),
 generation_index INTEGER NOT NULL,
 generation_name TEXT NOT NULL,
 year_start INTEGER,
 year_end INTEGER,
 year_start_raw TEXT,
 year_end_raw TEXT,
 year_range_status TEXT NOT NULL CHECK(year_range_status IN ('known_range','partial_range','not_provided','source_text_unparsed')),
 body_type TEXT,
 raw_json TEXT NOT NULL,
 record_sha256 TEXT NOT NULL CHECK(length(record_sha256)=64),
 market_scope TEXT NOT NULL CHECK(market_scope='UNKNOWN'),
 applicability_precision TEXT NOT NULL CHECK(applicability_precision='generation_name_candidate'),
 review_status TEXT NOT NULL CHECK(review_status='candidate'),
 UNIQUE(model_candidate_id,generation_index),
 CHECK(year_start IS NULL OR year_end IS NULL OR year_start<=year_end)
);
CREATE TABLE engine_variant_candidates(
 engine_candidate_id INTEGER PRIMARY KEY,
 generation_candidate_id INTEGER NOT NULL REFERENCES generation_candidates(generation_candidate_id),
 engine_index INTEGER NOT NULL,
 engine_label TEXT NOT NULL,
 fuel_type TEXT,
 cylinders INTEGER,
 displacement_cc INTEGER,
 power_hp REAL,
 torque_nm REAL,
 transmission_description TEXT,
 drivetrain TEXT,
 raw_specs_json TEXT NOT NULL,
 raw_engine_json TEXT NOT NULL,
 record_sha256 TEXT NOT NULL CHECK(length(record_sha256)=64),
 engine_code TEXT,
 gearbox_code TEXT,
 code_extraction_status TEXT NOT NULL CHECK(code_extraction_status='not_provided'),
 market_scope TEXT NOT NULL CHECK(market_scope='UNKNOWN'),
 applicability_precision TEXT NOT NULL CHECK(applicability_precision='engine_variant_description_only'),
 review_status TEXT NOT NULL CHECK(review_status='candidate'),
 UNIQUE(generation_candidate_id,engine_index),
 CHECK(engine_code IS NULL AND gearbox_code IS NULL)
);
CREATE INDEX idx_candidate_model_name ON model_candidates(model_name);
CREATE INDEX idx_candidate_generation_name ON generation_candidates(generation_name);
CREATE INDEX idx_candidate_engine_label ON engine_variant_candidates(engine_label);
CREATE INDEX idx_candidate_source_market ON research_sources(market_scope,publication_status);
"""


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def record_hash(value: Any) -> str:
    return sha256_bytes(canonical_json(value).encode("utf-8"))


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name}: JSON root must be an object")
    return value


def parse_year(value: Any) -> tuple[int | None, str | None, str]:
    if value is None or str(value).strip() == "":
        return None, None, "not_provided"
    raw = str(value).strip()
    if re.fullmatch(r"\d{4}", raw):
        year = int(raw)
        if 1886 <= year <= 2035:
            return year, raw, "known_range"
    return None, raw, "source_text_unparsed"


def parse_year_range(start_value: Any, end_value: Any) -> tuple[int | None, int | None, str | None, str | None, str]:
    start, start_raw, start_status = parse_year(start_value)
    end, end_raw, end_status = parse_year(end_value)
    if start is not None and end is not None:
        if start > end:
            raise ValueError(f"Invalid year range: {start}>{end}")
        status = "known_range"
    elif start is not None or end is not None:
        status = "partial_range"
    elif start_raw is not None or end_raw is not None:
        status = "source_text_unparsed"
    else:
        status = "not_provided"
    return start, end, start_raw, end_raw, status


def numeric_or_none(value: Any, cast: type) -> Any:
    if value is None or str(value).strip() == "":
        return None
    try:
        return cast(value)
    except (TypeError, ValueError, OverflowError):
        return None


def validate_license(path: Path) -> tuple[str, str]:
    if not path.is_file() or path.stat().st_size <= 0:
        raise ValueError("LICENSE-DATA is missing or empty")
    raw = path.read_bytes()
    text = raw.decode("utf-8-sig")
    normalized = " ".join(text.split()).lower()
    required = (
        "open database license (odbl) v1.0",
        "opendatacommons.org/licenses/odbl/1-0/",
        "share-alike",
        "autoevolution.com",
    )
    missing = [phrase for phrase in required if phrase not in normalized]
    if missing:
        raise ValueError(f"LICENSE-DATA does not confirm the pinned ODbL terms: {missing}")
    return text, sha256_bytes(raw)


def validate_lock(lock: dict[str, Any]) -> None:
    if lock.get("dataset") != DATASET or lock.get("license") != LICENSE_ID:
        raise ValueError("ODbL source lock dataset/license mismatch")
    if lock.get("license_url") != LICENSE_URL or lock.get("share_alike_required") is not True:
        raise ValueError("ODbL license URL or share-alike requirement changed")
    if lock.get("market_scope") != "UNKNOWN":
        raise ValueError("This upstream dataset has no confirmed market scope")
    if lock.get("applicability_policy", {}).get("exact_vehicle_fitment") is not False:
        raise ValueError("ODbL candidate data cannot claim exact vehicle fitment")
    if lock.get("applicability_policy", {}).get("exact_engine_codes_included") is not False:
        raise ValueError("ODbL candidate data cannot claim exact engine codes")
    if lock.get("applicability_policy", {}).get("exact_gearbox_codes_included") is not False:
        raise ValueError("ODbL candidate data cannot claim exact gearbox codes")
    if not isinstance(lock.get("brands"), list) or not isinstance(lock.get("source_files"), dict):
        raise ValueError("ODbL source lock is missing brand/source-file mappings")
    if len(lock["brands"]) != len(set(lock["brands"])) or set(lock["brands"]) != set(lock["source_files"]):
        raise ValueError("ODbL brand and source-file lock entries are inconsistent")
    if not re.fullmatch(r"[0-9a-f]{40}", str(lock.get("revision", ""))):
        raise ValueError("ODbL source revision must be a pinned 40-character Git commit SHA")


def input_file_manifest(input_dir: Path, lock: dict[str, Any], license_path: Path) -> tuple[dict[str, dict[str, Any]], str]:
    files: dict[str, dict[str, Any]] = {}
    for brand, relative_path in lock["source_files"].items():
        if brand not in lock["brands"]:
            raise ValueError(f"Unexpected source-file brand in lock: {brand}")
        path = input_dir / f"{brand}.json"
        if not path.is_file() or path.stat().st_size <= 0:
            raise ValueError(f"Missing or empty pinned source file: {path}")
        raw = path.read_bytes()
        source_url = f"https://raw.githubusercontent.com/gor3a/vehicle-makes-models/{lock['revision']}/{relative_path}"
        files[relative_path] = {
            "path": path,
            "file_kind": "source_json",
            "byte_size": len(raw),
            "sha256": sha256_bytes(raw),
            "source_url": source_url,
            "source_id": f"{lock['source_id_prefix']}-{brand}-{lock['revision'][:12]}",
        }
    license_raw = license_path.read_bytes()
    files[lock["license_file"]] = {
        "path": license_path,
        "file_kind": "license_text",
        "byte_size": len(license_raw),
        "sha256": sha256_bytes(license_raw),
        "source_url": f"https://raw.githubusercontent.com/gor3a/vehicle-makes-models/{lock['revision']}/{lock['license_file']}",
        "source_id": None,
    }
    return files, sha256_bytes(license_raw)


def reject_explicit_codes(engine: dict[str, Any]) -> None:
    for key in engine:
        normalized = re.sub(r"[^a-z0-9]", "", str(key).lower())
        if normalized in FORBIDDEN_CODE_KEYS:
            raise ValueError(f"Upstream added a code/ECU field requiring manual review: {key}")


def build_database(
    temp_db_path: Path,
    lock: dict[str, Any],
    input_dir: Path,
    file_manifest: dict[str, dict[str, Any]],
    license_sha256: str,
) -> tuple[dict[str, int], dict[str, str]]:
    db = sqlite3.connect(temp_db_path)
    try:
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA journal_mode=DELETE")
        db.execute("PRAGMA synchronous=FULL")
        db.executescript(DDL)
        counts = {"makes": 0, "models": 0, "generations": 0, "engine_variants": 0}
        source_hashes: dict[str, str] = {}
        imported_at = datetime.now(timezone.utc).isoformat()
        license_file = file_manifest[lock["license_file"]]

        db.execute("BEGIN IMMEDIATE")
        for brand in lock["brands"]:
            path = input_dir / f"{brand}.json"
            raw_bytes = path.read_bytes()
            payload = json.loads(raw_bytes.decode("utf-8-sig"))
            if payload.get("group") != brand:
                raise ValueError(f"{path}: group mismatch; expected {brand!r}")
            makes = payload.get("makes")
            if not isinstance(makes, list) or not makes:
                raise ValueError(f"{path}: non-empty makes array is required")
            digest = sha256_bytes(raw_bytes)
            source_hashes[brand] = digest
            source_id = f"{lock['source_id_prefix']}-{brand}-{lock['revision'][:12]}"
            source_url = f"{lock['repository_url']}/blob/{lock['revision']}/{lock['source_files'][brand]}"
            per_source_files = {
                lock["source_files"][brand]: {
                    "byte_size": len(raw_bytes), "sha256": digest,
                },
                lock["license_file"]: {
                    "byte_size": license_file["byte_size"], "sha256": license_sha256,
                },
            }
            db.execute(
                """INSERT INTO research_sources
                   (source_id,publisher,dataset,upstream_revision,source_url,upstream_source,
                    license,license_url,license_sha256,attribution,share_alike,rights_status,
                    rights_review_status,source_sha256,source_file_manifest_json,market_scope,
                    publication_status,imported_at_utc)
                   VALUES(?,?,?,?,?,?,?, ?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    source_id, lock["publisher"], lock["dataset"], lock["revision"], source_url,
                    lock["upstream_source"], LICENSE_ID, LICENSE_URL, license_sha256,
                    lock["attribution"], LICENSE_ID, "upstream_declared_ODbL_1_0",
                    "research_only_upstream_provenance_not_independently_verified",
                    digest, canonical_json(per_source_files), "UNKNOWN", "research_only", imported_at,
                ),
            )
            db.execute(
                """INSERT INTO source_file_artifacts
                   (source_id,relative_path,file_kind,byte_size,sha256,source_url)
                   VALUES(?,?,'source_json',?,?,?)""",
                (
                    source_id, lock["source_files"][brand], len(raw_bytes), digest,
                    file_manifest[lock["source_files"][brand]]["source_url"],
                ),
            )

            for make in makes:
                if not isinstance(make, dict) or not str(make.get("name", "")).strip():
                    raise ValueError(f"{path}: make entry without a name")
                make_json = canonical_json(make)
                cur = db.execute(
                    """INSERT INTO make_candidates
                       (source_id,brand_key,make_name,raw_json,record_sha256,market_scope,
                        applicability_precision,review_status)
                       VALUES(?,?,?,?,?,'UNKNOWN','make_name_candidate','candidate')""",
                    (source_id, brand, str(make["name"]).strip(), make_json, record_hash(make)),
                )
                make_id = cur.lastrowid
                counts["makes"] += 1

                models = make.get("models", [])
                if not isinstance(models, list):
                    raise ValueError(f"{path}: models must be an array")
                for model_index, model in enumerate(models):
                    if not isinstance(model, dict) or not str(model.get("name", "")).strip():
                        raise ValueError(f"{path}: model entry without a name")
                    ys, ye, ys_raw, ye_raw, yr_status = parse_year_range(model.get("yearStart"), model.get("yearEnd"))
                    model_json = canonical_json(model)
                    cur = db.execute(
                        """INSERT INTO model_candidates
                           (make_candidate_id,model_index,model_name,year_start,year_end,
                            year_start_raw,year_end_raw,year_range_status,raw_json,record_sha256,
                            market_scope,applicability_precision,review_status)
                           VALUES(?,?,?,?,?,?,?,?,?,?,'UNKNOWN','model_name_candidate','candidate')""",
                        (make_id, model_index, str(model["name"]).strip(), ys, ye, ys_raw, ye_raw,
                         yr_status, model_json, record_hash(model)),
                    )
                    model_id = cur.lastrowid
                    counts["models"] += 1

                    generations = model.get("generations", [])
                    if not isinstance(generations, list):
                        raise ValueError(f"{path}: generations must be an array")
                    for generation_index, generation in enumerate(generations):
                        if not isinstance(generation, dict) or not str(generation.get("name", "")).strip():
                            raise ValueError(f"{path}: generation entry without a name")
                        gs, ge, gs_raw, ge_raw, gr_status = parse_year_range(
                            generation.get("yearStart"), generation.get("yearEnd")
                        )
                        generation_json = canonical_json(generation)
                        cur = db.execute(
                            """INSERT INTO generation_candidates
                               (model_candidate_id,generation_index,generation_name,year_start,year_end,
                                year_start_raw,year_end_raw,year_range_status,body_type,raw_json,
                                record_sha256,market_scope,applicability_precision,review_status)
                               VALUES(?,?,?,?,?,?,?,?,?,?,?,'UNKNOWN','generation_name_candidate','candidate')""",
                            (model_id, generation_index, str(generation["name"]).strip(), gs, ge,
                             gs_raw, ge_raw, gr_status, generation.get("bodyType"), generation_json,
                             record_hash(generation)),
                        )
                        generation_id = cur.lastrowid
                        counts["generations"] += 1

                        engines = generation.get("engines", [])
                        if not isinstance(engines, list):
                            raise ValueError(f"{path}: engines must be an array")
                        for engine_index, engine in enumerate(engines):
                            if not isinstance(engine, dict):
                                raise ValueError(f"{path}: engine variant must be an object")
                            reject_explicit_codes(engine)
                            label = str(engine.get("label") or engine.get("name") or "").strip()
                            if not label:
                                raise ValueError(f"{path}: engine variant without a descriptive label")
                            specs = engine.get("specs", {})
                            if not isinstance(specs, dict):
                                raise ValueError(f"{path}: engine specs must be an object")
                            db.execute(
                                """INSERT INTO engine_variant_candidates
                                   (generation_candidate_id,engine_index,engine_label,fuel_type,cylinders,
                                    displacement_cc,power_hp,torque_nm,transmission_description,drivetrain,
                                    raw_specs_json,raw_engine_json,record_sha256,engine_code,gearbox_code,
                                    code_extraction_status,market_scope,applicability_precision,review_status)
                                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,NULL,NULL,'not_provided','UNKNOWN',
                                          'engine_variant_description_only','candidate')""",
                                (
                                    generation_id, engine_index, label, engine.get("fuelType"),
                                    numeric_or_none(engine.get("cylinders"), int),
                                    numeric_or_none(engine.get("displacementCc"), int),
                                    numeric_or_none(engine.get("powerHp"), float),
                                    numeric_or_none(engine.get("torqueNm"), float),
                                    engine.get("transmission"), engine.get("drivetrain"),
                                    canonical_json(specs), canonical_json(engine), record_hash(engine),
                                ),
                            )
                            counts["engine_variants"] += 1

        db.execute(
            """INSERT INTO source_file_artifacts
               (source_id,relative_path,file_kind,byte_size,sha256,source_url)
               VALUES(NULL,?,'license_text',?,?,?)""",
            (
                lock["license_file"], license_file["byte_size"], license_sha256,
                license_file["source_url"],
            ),
        )
        db.commit()
        if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("SQLite integrity_check failed")
        if db.execute("PRAGMA foreign_key_check").fetchall():
            raise RuntimeError("SQLite foreign_key_check failed")
        actual = {
            "makes": db.execute("SELECT count(*) FROM make_candidates").fetchone()[0],
            "models": db.execute("SELECT count(*) FROM model_candidates").fetchone()[0],
            "generations": db.execute("SELECT count(*) FROM generation_candidates").fetchone()[0],
            "engine_variants": db.execute("SELECT count(*) FROM engine_variant_candidates").fetchone()[0],
        }
        if actual != counts:
            raise RuntimeError(f"SQLite count mismatch: {actual} != {counts}")
        db.close()
        return counts, source_hashes
    except Exception:
        try:
            db.rollback()
        except sqlite3.Error:
            pass
        db.close()
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lock", required=True, type=Path)
    parser.add_argument("--input-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    args = parser.parse_args()

    lock = read_json(args.lock)
    validate_lock(lock)
    license_path = args.input_dir / lock["license_file"]
    license_text, license_sha256 = validate_license(license_path)
    files, computed_license_hash = input_file_manifest(args.input_dir, lock, license_path)
    if computed_license_hash != license_sha256:
        raise RuntimeError("License SHA-256 changed during input validation")

    expected_paths = set(lock["source_files"].values()) | {lock["license_file"]}
    if set(files) != expected_paths:
        raise ValueError("Downloaded source-file set does not match the lock file")
    for brand in lock["brands"]:
        if brand not in lock["source_files"]:
            raise ValueError(f"Lock is missing source file for {brand}")

    output = args.output.resolve()
    manifest_path = args.manifest.resolve()
    license_output = output.parent / lock["license_file"]
    for target in (output, manifest_path, license_output):
        if target.exists():
            raise FileExistsError(f"Refusing to overwrite existing data artifact: {target}")
    output.parent.mkdir(parents=True, exist_ok=True)

    fd, temp_db_name = tempfile.mkstemp(prefix="vag-engine-candidates-", suffix=".sqlite.tmp", dir=output.parent)
    os.close(fd)
    temp_db_path = Path(temp_db_name)
    temp_manifest_path = output.parent / f".{manifest_path.name}.tmp"
    try:
        counts, source_hashes = build_database(
            temp_db_path, lock, args.input_dir, files, license_sha256
        )
        expected = lock["expected_counts"]
        if counts != expected:
            raise ValueError(f"Candidate data count mismatch: {counts} != {expected}")
        database_hash = sha256_file(temp_db_path)
        file_summary = {
            name: {
                "byte_size": entry["byte_size"],
                "sha256": entry["sha256"],
                "source_url": entry["source_url"],
                "file_kind": entry["file_kind"],
            }
            for name, entry in sorted(files.items())
        }
        manifest = {
            "schema_version": 1,
            "dataset": lock["dataset"],
            "publisher": lock["publisher"],
            "repository_url": lock["repository_url"],
            "revision": lock["revision"],
            "upstream_source": lock["upstream_source"],
            "license": LICENSE_ID,
            "license_url": LICENSE_URL,
            "license_sha256": license_sha256,
            "license_file": lock["license_file"],
            "attribution": lock["attribution"],
            "share_alike": LICENSE_ID,
            "share_alike_required": True,
            "rights_status": "upstream_declared_ODbL_1_0",
            "rights_review_status": "research_only_upstream_provenance_not_independently_verified",
            "source_sha256": source_hashes,
            "source_files": file_summary,
            "database_file": output.name,
            "database_sha256": database_hash,
            "counts": counts,
            "expected_counts": expected,
            "market_scope": "UNKNOWN",
            "applicability_precision": {
                "make": "make_name_candidate",
                "model": "model_name_candidate",
                "generation": "generation_name_candidate",
                "engine_variant": "engine_variant_description_only",
            },
            "engine_codes_included": False,
            "gearbox_codes_included": False,
            "ecu_fitment_included": False,
            "exact_vehicle_fitment": False,
            "production_import": False,
            "status": "research_only",
            "built_at_utc": datetime.now(timezone.utc).isoformat(),
            "integrity_check": "ok",
            "foreign_key_errors": 0,
        }
        temp_manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        shutil.copy2(license_path, license_output)
        os.replace(temp_db_path, output)
        os.replace(temp_manifest_path, manifest_path)
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
        return 0
    except Exception:
        for path in (temp_db_path, temp_manifest_path, output, manifest_path, license_output):
            try:
                if path.exists():
                    path.unlink()
            except OSError:
                pass
        raise


if __name__ == "__main__":
    raise SystemExit(main())
