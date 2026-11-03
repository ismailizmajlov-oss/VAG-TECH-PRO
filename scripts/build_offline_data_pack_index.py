#!/usr/bin/env python3
"""Assemble and verify separate licensed SQLite data packs for the Windows desktop target.

No source databases are merged. Each pack keeps its own license, attribution, provenance,
market scope, and applicability boundary.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ARTIFACTS = {
    "obdex": ("vag-tech-pro-obdex-cc0-2026-11-02", "obdex-generic-cc0"),
    "vehiclesdb": ("vag-identity-vehiclesdb-cc-by-4.0", "vehiclesdb-vag-identity"),
    "odbl": ("vag-engine-candidates-research-odbl", "vag-engine-candidates-odbl"),
    "obdb": ("obdb-vag-research-cc-by-sa", "obdb-vag-signals-cc-by-sa"),
}


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


def find_one(root: Path, filename: str) -> Path:
    matches = [p for p in root.rglob(filename) if p.is_file()]
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one {filename} under {root}, found {len(matches)}")
    return matches[0]


def sqlite_readonly(path: Path) -> sqlite3.Connection:
    uri = f"file:{path.resolve().as_posix()}?mode=ro"
    db = sqlite3.connect(uri, uri=True)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA query_only=ON")
    if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        db.close()
        raise ValueError(f"SQLite integrity_check failed: {path}")
    if db.execute("PRAGMA foreign_key_check").fetchall():
        db.close()
        raise ValueError(f"SQLite foreign_key_check failed: {path}")
    return db


def table_names(db: sqlite3.Connection) -> set[str]:
    return {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def count(db: sqlite3.Connection, table: str) -> int:
    return int(db.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0])


def relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def collect_bundle_files(root: Path) -> list[dict[str, Any]]:
    files = []
    for path in sorted(p for p in root.rglob("*") if p.is_file() and p.name != "offline-data-pack-index.json"):
        files.append({
            "path": relative(root, path),
            "byte_size": path.stat().st_size,
            "sha256": sha256_file(path),
        })
    return files


def inspect_obdex(root: Path) -> dict[str, Any]:
    db_path = find_one(root, "obdex-generic-research.sqlite")
    report_path = find_one(root, "OBDex-SQLITE-REPORT.json")
    source_manifest_path = find_one(root, "OBDex-SOURCE-MANIFEST.json")
    license_path = find_one(root, "UPSTREAM-LICENSE.txt")
    report = read_json(report_path)
    source_manifest = read_json(source_manifest_path)
    license_text = " ".join(license_path.read_text(encoding="utf-8-sig").split()).lower()
    if "cc0 1.0 universal" not in license_text or "applies to the data files" not in license_text:
        raise ValueError("OBDex CC0 data-license scope check failed")
    if source_manifest.get("data_license") != "CC0-1.0":
        raise ValueError("OBDex data license mismatch")
    reference_policy = source_manifest.get("source_reference_policy", {})
    if reference_policy.get("validation") != "syntax_only" or reference_policy.get("external_fetch") is not False:
        raise ValueError("OBDex external source references must remain syntax-only and unfetched")
    if reference_policy.get("rights_review") != "not_inherited_from_cc0_dataset":
        raise ValueError("OBDex external source-document rights boundary is missing")
    if sha256_file(license_path) != source_manifest.get("license_sha256"):
        raise ValueError("OBDex license hash mismatch")
    if sha256_file(db_path) != report.get("database_sha256"):
        raise ValueError("OBDex database hash mismatch")
    if report.get("status") != "validated_research_only" or report.get("integrity_check") != "ok":
        raise ValueError("OBDex source workflow report is not validated")
    if report.get("source_reference_validation") != "syntax_only_http_or_https_not_fetched":
        raise ValueError("OBDex source-reference validation policy is missing")
    if report.get("generic_dtcs") != 9533 or report.get("pids") != 132:
        raise ValueError("OBDex expected DTC/PID counts changed")
    if report.get("vag_specific_dtc_rows") != 0 or report.get("fitment_claims") != 0 or report.get("production_rows") != 0:
        raise ValueError("OBDex generic-only boundary failed")
    if source_manifest.get("scope", {}).get("manufacturer_specific_codes_included") is not False:
        raise ValueError("OBDex source manifest claims manufacturer-specific DTCs")
    if source_manifest.get("scope", {}).get("exact_vag_fitment") is not False:
        raise ValueError("OBDex source manifest claims exact VAG fitment")
    if source_manifest.get("scope", {}).get("repair_procedures_or_pinouts_included") is not False:
        raise ValueError("OBDex source manifest claims repair procedures or pinouts")

    source_root = root / "source"
    for item in source_manifest.get("source_files", []):
        path = source_root / Path(item["path"])
        if not path.is_file() or path.stat().st_size != item["bytes"] or sha256_file(path) != item["sha256"]:
            raise ValueError(f"OBDex upstream snapshot hash mismatch: {item['path']}")

    db = sqlite_readonly(db_path)
    tables = table_names(db)
    if not {"source_registry", "generic_dtc_research", "generic_pid_research", "database_info"}.issubset(tables):
        raise ValueError("OBDex SQLite schema mismatch")
    dtc_count = count(db, "generic_dtc_research")
    pid_count = count(db, "generic_pid_research")
    if dtc_count != 9533 or pid_count != 132:
        raise ValueError("OBDex SQLite row counts mismatch")
    if db.execute("SELECT count(*) FROM generic_dtc_research WHERE namespace<>'generic_sae_iso_obd2' OR vehicle_fitment_claim<>0").fetchone()[0]:
        raise ValueError("OBDex contains non-generic or fitment-claim DTC rows")
    if db.execute("SELECT count(*) FROM generic_pid_research WHERE vehicle_fitment_claim<>0").fetchone()[0]:
        raise ValueError("OBDex PID rows contain vehicle-fitment claims")
    if db.execute("SELECT count(*) FROM source_registry WHERE license_id<>'CC0-1.0' OR verification_status<>'license_verified_research_only'").fetchone()[0]:
        raise ValueError("OBDex source registry license/status mismatch")
    db.close()
    return {
        "pack_id": "obdex-generic-cc0",
        "artifact_name": ARTIFACTS["obdex"][0],
        "relative_dir": relative(root.parent, root),
        "database_path": relative(root.parent, db_path),
        "database_sha256": sha256_file(db_path),
        "manifest_path": relative(root.parent, source_manifest_path),
        "manifest_sha256": sha256_file(source_manifest_path),
        "report_path": relative(root.parent, report_path),
        "license": "CC0-1.0",
        "license_files": [relative(root.parent, license_path)],
        "attribution_files": [relative(root.parent, source_manifest_path)],
        "status": "verified_research_only",
        "product_eligibility": "generic_obd2_reference_only",
        "market_scope": "global_generic_not_market_specific",
        "applicability_precision": "generic_code_only_no_vehicle_fitment",
        "counts": {"generic_dtcs": dtc_count, "pids": pid_count},
        "source_revision": source_manifest.get("commit_sha"),
        "warnings": [
            "Generic SAE/ISO OBD-II only; never map these records to a VAG ECU or exact vehicle without independent evidence.",
            "Source descriptions and cause/repair suggestions are unreviewed and are not verified repair procedures.",
            "No vehicle-fitment or exact diagnostic test-plan claim is made.",
        ],
    }


def inspect_vehiclesdb(root: Path) -> dict[str, Any]:
    db_path = find_one(root, "vag-identity-vehiclesdb.sqlite")
    manifest_path = find_one(root, "manifest.json")
    license_path = find_one(root, "LICENSE.txt")
    attribution_path = find_one(root, "ATTRIBUTION.md")
    upstream_manifest_path = find_one(root, "UPSTREAM-MANIFEST.json")
    manifest = read_json(manifest_path)
    upstream = read_json(upstream_manifest_path)
    if manifest.get("status") != "identity_candidate_pack_verified" or manifest.get("dataset_license") != "CC-BY-4.0":
        raise ValueError("VehiclesDB pack status/license mismatch")
    if manifest.get("ru_evidence_present") is not False or manifest.get("fitment_claim") is not False:
        raise ValueError("VehiclesDB Russian-market or fitment claim failed")
    if manifest.get("generation_data_included") is not False or manifest.get("model_year_data_included") is not False:
        raise ValueError("VehiclesDB generation/year boundary failed")
    if manifest.get("engine_codes_included") is not False or manifest.get("gearbox_codes_included") is not False:
        raise ValueError("VehiclesDB engine/gearbox code boundary failed")
    if upstream.get("version") != manifest.get("dataset_version") or upstream.get("license") != "CC-BY-4.0":
        raise ValueError("VehiclesDB upstream manifest mismatch")
    if sha256_file(db_path) != manifest.get("database_sha256"):
        raise ValueError("VehiclesDB SQLite hash mismatch")
    for path, key in (
        (license_path, "LICENSE"),
        (attribution_path, "ATTRIBUTION.md"),
        (upstream_manifest_path, "manifest.json"),
    ):
        if sha256_file(path) != manifest["source_snapshot_sha256"][key]:
            raise ValueError(f"VehiclesDB source snapshot hash mismatch: {path.name}")
    license_text = " ".join(license_path.read_text(encoding="utf-8-sig").split()).lower()
    if "creative commons attribution 4.0 international" not in license_text or "even commercially" not in license_text:
        raise ValueError("VehiclesDB CC BY 4.0 commercial-use text missing")
    if "VehiclesDB" not in attribution_path.read_text(encoding="utf-8-sig"):
        raise ValueError("VehiclesDB attribution file missing")

    db = sqlite_readonly(db_path)
    if not {"dataset_provenance", "source_file_artifacts", "source_registry", "model_candidates", "model_market_evidence"}.issubset(table_names(db)):
        raise ValueError("VehiclesDB SQLite schema mismatch")
    counts = {
        "sources": count(db, "source_registry"),
        "source_files": count(db, "source_file_artifacts"),
        "models": count(db, "model_candidates"),
        "market_evidence": count(db, "model_market_evidence"),
    }
    if counts != manifest.get("counts"):
        raise ValueError(f"VehiclesDB count mismatch: {counts} != {manifest.get('counts')}")
    if counts != {"sources": 14, "source_files": 4, "models": 260, "market_evidence": 1524}:
        raise ValueError("VehiclesDB expected snapshot counts changed")
    if db.execute("SELECT count(*) FROM model_market_evidence WHERE country_code IN ('ru','th')").fetchone()[0]:
        raise ValueError("VehiclesDB pack includes a prohibited market")
    if db.execute("SELECT count(*) FROM source_registry WHERE rights_status<>'approved_by_published_license'").fetchone()[0]:
        raise ValueError("VehiclesDB source rights status mismatch")
    if db.execute("SELECT count(*) FROM model_candidates WHERE fitment_status<>'not_established' OR year_start IS NOT NULL OR year_end IS NOT NULL OR applicability_precision<>'make_model_name_only' OR verification_status<>'identity_candidate'").fetchone()[0]:
        raise ValueError("VehiclesDB model candidate boundary failed")
    if db.execute("SELECT count(*) FROM model_market_evidence WHERE applicability_precision<>'market_presence_only' OR verification_status<>'source_published_presence_evidence'").fetchone()[0]:
        raise ValueError("VehiclesDB market-evidence precision mismatch")
    if db.execute("""SELECT count(*) FROM model_market_evidence e
                     JOIN source_registry s ON s.source_id=e.source_id
                     WHERE s.country_code<>e.country_code""").fetchone()[0]:
        raise ValueError("VehiclesDB market evidence/source country mismatch")
    countries = sorted(row[0] for row in db.execute("SELECT DISTINCT country_code FROM model_market_evidence"))
    if countries != manifest["market_scope_countries"] or "ru" in countries or "th" in countries:
        raise ValueError("VehiclesDB market-scope summary mismatch")
    db.close()
    return {
        "pack_id": "vehiclesdb-vag-identity",
        "artifact_name": ARTIFACTS["vehiclesdb"][0],
        "relative_dir": relative(root.parent, root),
        "database_path": relative(root.parent, db_path),
        "database_sha256": sha256_file(db_path),
        "manifest_path": relative(root.parent, manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "license": "CC-BY-4.0",
        "license_files": [relative(root.parent, license_path)],
        "attribution_files": [relative(root.parent, attribution_path), relative(root.parent, upstream_manifest_path)],
        "status": "verified_identity_candidate_pack",
        "product_eligibility": "make_model_identity_candidate_only_foreign_market_presence",
        "market_scope": countries,
        "applicability_precision": "make_model_name_only",
        "counts": counts,
        "make_counts": manifest.get("make_counts", {}),
        "source_revision": manifest.get("upstream_tag"),
        "warnings": [
            "Foreign-market model presence only; no Russian/EAEU market evidence.",
            "No generations, model years, engine codes, gearbox codes, ECU fitment, PR codes or VIN build sheets.",
            "Model names are identity candidates, not exact vehicle fitment.",
        ],
    }


def inspect_odbl(root: Path) -> dict[str, Any]:
    db_path = find_one(root, "vag-engine-candidates-research.sqlite")
    manifest_path = find_one(root, "vag-engine-candidates-research.manifest.json")
    license_path = find_one(root, "LICENSE-DATA")
    manifest = read_json(manifest_path)
    if manifest.get("status") != "research_only" or manifest.get("license") != "ODbL-1.0":
        raise ValueError("ODbL pack status/license mismatch")
    if manifest.get("share_alike_required") is not True or manifest.get("market_scope") != "UNKNOWN":
        raise ValueError("ODbL share-alike/market-scope boundary failed")
    if manifest.get("production_import") is not False or manifest.get("exact_vehicle_fitment") is not False:
        raise ValueError("ODbL pack cannot be production or exact fitment")
    if manifest.get("rights_review_status") != "research_only_upstream_provenance_not_independently_verified":
        raise ValueError("ODbL provenance limitation missing")
    if sha256_file(db_path) != manifest.get("database_sha256") or sha256_file(license_path) != manifest.get("license_sha256"):
        raise ValueError("ODbL database/license hash mismatch")
    license_text = " ".join(license_path.read_text(encoding="utf-8-sig").split()).lower()
    if "open database license (odbl) v1.0" not in license_text or "share-alike" not in license_text:
        raise ValueError("ODbL license text missing")
    db = sqlite_readonly(db_path)
    counts = {
        "makes": count(db, "make_candidates"),
        "models": count(db, "model_candidates"),
        "generations": count(db, "generation_candidates"),
        "engine_variants": count(db, "engine_variant_candidates"),
    }
    if counts != manifest.get("counts") or counts != {"makes": 5, "models": 233, "generations": 823, "engine_variants": 5081}:
        raise ValueError("ODbL candidate counts mismatch")
    bad_candidates = db.execute(
        """SELECT
             (SELECT count(*) FROM make_candidates WHERE market_scope<>'UNKNOWN' OR review_status<>'candidate' OR applicability_precision<>'make_name_candidate')
           + (SELECT count(*) FROM model_candidates WHERE market_scope<>'UNKNOWN' OR review_status<>'candidate' OR applicability_precision<>'model_name_candidate')
           + (SELECT count(*) FROM generation_candidates WHERE market_scope<>'UNKNOWN' OR review_status<>'candidate' OR applicability_precision<>'generation_name_candidate')
           + (SELECT count(*) FROM engine_variant_candidates WHERE engine_code IS NOT NULL OR gearbox_code IS NOT NULL OR market_scope<>'UNKNOWN' OR review_status<>'candidate' OR applicability_precision<>'engine_variant_description_only' OR code_extraction_status<>'not_provided')"""
    ).fetchone()[0]
    if bad_candidates:
        raise ValueError("ODbL candidate code/market/applicability boundary failed")
    if db.execute("SELECT count(*) FROM research_sources WHERE rights_review_status<>'research_only_upstream_provenance_not_independently_verified' OR publication_status<>'research_only'").fetchone()[0]:
        raise ValueError("ODbL source rights-review status mismatch")
    if count(db, "source_file_artifacts") != 6 or count(db, "research_sources") != 5:
        raise ValueError("ODbL source artifact provenance count mismatch")
    db.close()
    return {
        "pack_id": "vag-engine-candidates-odbl",
        "artifact_name": ARTIFACTS["odbl"][0],
        "relative_dir": relative(root.parent, root),
        "database_path": relative(root.parent, db_path),
        "database_sha256": sha256_file(db_path),
        "manifest_path": relative(root.parent, manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "license": "ODbL-1.0",
        "license_files": [relative(root.parent, license_path)],
        "attribution_files": [relative(root.parent, manifest_path)],
        "status": "research_only",
        "product_eligibility": "not_eligible_pending_upstream_provenance_review",
        "market_scope": "UNKNOWN",
        "applicability_precision": manifest.get("applicability_precision"),
        "counts": counts,
        "source_revision": manifest.get("revision"),
        "warnings": [
            "ODbL 1.0 share-alike obligations apply to this separate database.",
            "Upstream provenance from autoevolution.com has not been independently verified; research only.",
            "No market scope, exact engine codes, gearbox codes, ECU fitment or exact vehicle fitment.",
        ],
    }


def inspect_obdb(root: Path) -> dict[str, Any]:
    db_path = find_one(root, "vag-obdb-research.sqlite")
    manifest_path = find_one(root, "manifest.json")
    attribution_path = find_one(root, "ATTRIBUTION.txt")
    manifest = read_json(manifest_path)
    if manifest.get("license_id") != "CC-BY-SA-4.0" or manifest.get("share_alike_required") is not True:
        raise ValueError("OBDb CC BY-SA license/share-alike mismatch")
    if manifest.get("commercial_use_allowed") is not True or manifest.get("display_allowed") is not True or manifest.get("cache_allowed") is not True:
        raise ValueError("OBDb published license permissions are incomplete")
    if sha256_file(db_path) != manifest.get("database_sha256"):
        raise ValueError("OBDb SQLite hash mismatch")
    if "CC BY-SA 4.0" not in attribution_path.read_text(encoding="utf-8-sig"):
        raise ValueError("OBDb attribution/share-alike notice missing")
    for source in manifest.get("sources", []):
        license_path = root / source["license_copy"]
        if sha256_file(license_path) != source["license_sha256"]:
            raise ValueError(f"OBDb source license hash mismatch: {source['source_id']}")
        for item in source.get("files", {}).values():
            path = root / item["path"]
            if not path.is_file() or path.stat().st_size != item["bytes"] or sha256_file(path) != item["sha256"]:
                raise ValueError(f"OBDb source snapshot mismatch: {source['source_id']}")

    db = sqlite_readonly(db_path)
    tables = table_names(db)
    if not {"source_registry", "generation_candidates", "ecu_candidates", "command_candidates", "signal_candidates"}.issubset(tables):
        raise ValueError("OBDb SQLite schema mismatch")
    if {"dtc_codes", "repair_procedures", "wiring_diagrams", "pinouts"} & tables:
        raise ValueError("OBDb signal pack must not masquerade as DTC/repair/wiring data")
    counts = {
        "sources": count(db, "source_registry"),
        "generations": count(db, "generation_candidates"),
        "ecus": count(db, "ecu_candidates"),
        "commands": count(db, "command_candidates"),
        "signals": count(db, "signal_candidates"),
    }
    if counts != manifest.get("counts") or counts != {
        "sources": 6, "generations": 32, "ecus": 15, "commands": 2315, "signals": 2480
    }:
        raise ValueError("OBDb research counts mismatch")
    if db.execute("SELECT count(*) FROM source_registry WHERE license_id<>'CC-BY-SA-4.0' OR market_scope<>'UNKNOWN' OR verification_status<>'unverified_community_candidate' OR execution_allowed<>0").fetchone()[0]:
        raise ValueError("OBDb source registry boundary failed")
    if db.execute("SELECT count(*) FROM generation_candidates WHERE market_scope<>'UNKNOWN' OR verification_status<>'unverified_community_candidate'").fetchone()[0]:
        raise ValueError("OBDb generation candidate boundary failed")
    if db.execute("SELECT count(*) FROM ecu_candidates WHERE market_scope<>'UNKNOWN' OR verification_status<>'unverified_community_candidate'").fetchone()[0]:
        raise ValueError("OBDb ECU candidate boundary failed")
    if db.execute("SELECT count(*) FROM command_candidates WHERE service_id<>'22' OR execution_allowed<>0 OR market_scope<>'UNKNOWN' OR verification_status<>'unverified_community_candidate'").fetchone()[0]:
        raise ValueError("OBDb command execution/applicability boundary failed")
    if db.execute("SELECT count(*) FROM signal_candidates WHERE market_scope<>'UNKNOWN' OR verification_status<>'unverified_community_candidate'").fetchone()[0]:
        raise ValueError("OBDb signal applicability boundary failed")
    db.close()
    license_files = sorted(
        relative(root, root / source["license_copy"]) for source in manifest["sources"]
    )
    return {
        "pack_id": "obdb-vag-signals-cc-by-sa",
        "artifact_name": ARTIFACTS["obdb"][0],
        "relative_dir": relative(root.parent, root),
        "database_path": relative(root.parent, db_path),
        "database_sha256": sha256_file(db_path),
        "manifest_path": relative(root.parent, manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "license": "CC-BY-SA-4.0",
        "license_files": license_files,
        "attribution_files": [relative(root.parent, attribution_path), relative(root.parent, manifest_path)],
        "status": "verified_research_only",
        "product_eligibility": "not_eligible_until_manual_vehicle_validation",
        "market_scope": "UNKNOWN",
        "applicability_precision": "vehicle_model_candidate",
        "counts": counts,
        "source_revisions": {s["source_id"]: s["commit_sha"] for s in manifest["sources"]},
        "warnings": [
            "Community-authored UDS 0x22 signal candidates only; no commands are executed.",
            "No exact generation, engine, gearbox, PR-code, ECU hardware or VIN fitment is established.",
            "No DTC definitions, repair procedures, factory wiring diagrams, pinouts, torque values or service schedules.",
            "CC BY-SA 4.0 share-alike and attribution obligations apply to this separate database.",
        ],
    }


def verify_bundle(root: Path) -> dict[str, Any]:
    index_path = root / "offline-data-pack-index.json"
    index = read_json(index_path)
    if index.get("bundle_status") != "verified_offline_data_packs_not_installer":
        raise ValueError("Offline bundle status is invalid")
    if index.get("target_platform") != "windows-x64" or index.get("database_count") != 4:
        raise ValueError("Offline bundle target/database count mismatch")
    if index.get("license_separation_policy", {}).get("merged_databases") is not False:
        raise ValueError("The separate licensed SQLite databases must not be merged")
    listed = {item["path"]: item for item in index.get("bundle_files", [])}
    actual = {
        relative(root, p): p for p in root.rglob("*")
        if p.is_file() and p.name != "offline-data-pack-index.json"
    }
    if set(listed) != set(actual):
        raise ValueError("Bundle file list does not match actual files")
    for path, metadata in listed.items():
        file_path = actual[path]
        if file_path.stat().st_size != metadata["byte_size"] or sha256_file(file_path) != metadata["sha256"]:
            raise ValueError(f"Bundle file hash/size mismatch: {path}")

    expected_ids = {
        "obdex-generic-cc0",
        "vehiclesdb-vag-identity",
        "vag-engine-candidates-odbl",
        "obdb-vag-signals-cc-by-sa",
    }
    packs = {pack["pack_id"]: pack for pack in index.get("packs", [])}
    if set(packs) != expected_ids:
        raise ValueError("Offline bundle pack index is incomplete or has unexpected packs")
    inspectors = {
        "obdex-generic-cc0": inspect_obdex,
        "vehiclesdb-vag-identity": inspect_vehiclesdb,
        "vag-engine-candidates-odbl": inspect_odbl,
        "obdb-vag-signals-cc-by-sa": inspect_obdb,
    }
    for pack_id, pack in packs.items():
        db_path = root / pack["database_path"]
        manifest_path = root / pack["manifest_path"]
        if sha256_file(db_path) != pack["database_sha256"] or sha256_file(manifest_path) != pack["manifest_sha256"]:
            raise ValueError(f"Pack database/manifest hash mismatch: {pack_id}")
        for license_path in pack["license_files"]:
            if not (root / license_path).is_file():
                raise ValueError(f"Missing license file for {pack_id}: {license_path}")
        for attribution_path in pack["attribution_files"]:
            if not (root / attribution_path).is_file():
                raise ValueError(f"Missing attribution file for {pack_id}: {attribution_path}")
        pack_dir = root / pack["relative_dir"]
        fresh = inspectors[pack_id](pack_dir)
        for key in (
            "artifact_name", "relative_dir", "database_path", "database_sha256",
            "manifest_path", "manifest_sha256", "license", "license_files",
            "attribution_files", "status", "product_eligibility", "market_scope",
            "applicability_precision", "counts", "source_revision", "source_revisions",
            "make_counts", "warnings",
        ):
            if fresh.get(key) != pack.get(key):
                raise ValueError(f"Pack index metadata drift for {pack_id}.{key}")
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".exe", ".msi"}:
            raise ValueError("Data bundle unexpectedly contains an installer executable")
    return {
        "status": "verified",
        "target_platform": "windows-x64",
        "database_count": len(packs),
        "file_count": len(listed),
        "pack_ids": sorted(packs),
    }


def build(input_dir: Path, output_dir: Path) -> dict[str, Any]:
    input_dir = input_dir.resolve()
    output_dir = output_dir.resolve()
    if not input_dir.is_dir():
        raise FileNotFoundError(f"Downloaded workflow artifacts directory is missing: {input_dir}")
    if output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite existing offline bundle: {output_dir}")
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    temp_dir = Path(tempfile.mkdtemp(prefix="vag-offline-packs-", dir=output_dir.parent))
    try:
        pack_descriptors = []
        for key, (artifact_name, target_name) in ARTIFACTS.items():
            source_dir = input_dir / artifact_name
            if not source_dir.is_dir():
                raise FileNotFoundError(f"Required upstream artifact is missing: {artifact_name}")
            target_dir = temp_dir / target_name
            shutil.copytree(source_dir, target_dir)
            inspector = {
                "obdex": inspect_obdex,
                "vehiclesdb": inspect_vehiclesdb,
                "odbl": inspect_odbl,
                "obdb": inspect_obdb,
            }[key]
            pack_descriptors.append(inspector(target_dir))

        index = {
            "schema_version": 1,
            "bundle_id": "vag-tech-pro-windows-offline-data-packs",
            "bundle_status": "verified_offline_data_packs_not_installer",
            "target_platform": "windows-x64",
            "database_count": 4,
            "built_at_utc": datetime.now(timezone.utc).isoformat(),
            "source_commit_sha": os.environ.get("GITHUB_SHA"),
            "workflow_run_id": os.environ.get("GITHUB_RUN_ID"),
            "license_separation_policy": {
                "merged_databases": False,
                "description": "Each SQLite file remains an independent database under its own license. No rows are merged across packs.",
                "share_alike_obligations_are_scoped_to_their_own_pack": True,
                "attribution_and_license_notices_retained": True,
            },
            "product_import_policy": [
                "Generic OBD-II DTCs remain in the generic_sae_iso_obd2 namespace and are never relabeled VAG-specific.",
                "Identity and community records remain candidates unless exact applicability is independently confirmed.",
                "ODbL engine/generation candidate data is research-only pending upstream provenance review.",
                "Community UDS 0x22 signal data is read-only reference material; command execution is disabled.",
                "No pack in this bundle supplies verified VAG repair procedures, factory wiring diagrams, pinouts, torque values, adaptations or service schedules.",
            ],
            "packs": pack_descriptors,
            "bundle_files": collect_bundle_files(temp_dir),
        }
        (temp_dir / "offline-data-pack-index.json").write_text(
            json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        verification = verify_bundle(temp_dir)
        if verification["status"] != "verified":
            raise RuntimeError("Offline data pack bundle verification failed")
        os.replace(temp_dir, output_dir)
        return verification
    except Exception:
        try:
            shutil.rmtree(temp_dir)
        except OSError:
            pass
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = build(args.input_dir, args.output_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
