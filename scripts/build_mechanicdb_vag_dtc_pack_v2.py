#!/usr/bin/env python3
"""Build an isolated ODbL Audi/VW make-candidate pack with community repair leads."""

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

PINNED_REVISION = "c788dfe9ed1517d4cd0be27f5aacb4776abf4864"
EXPECTED_MAKES = {"Audi", "Volkswagen"}
COPIED_FILES = {
    "dtc_codes.csv": "upstream/dtc_codes.csv",
    "diagnostic_fixes.csv": "upstream/diagnostic_fixes.csv",
    "replacement_parts.csv": "upstream/replacement_parts.csv",
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
        check=True, capture_output=True, text=True,
    )
    return result.stdout.strip()


def load_manifest(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or data.get("source_revision") != PINNED_REVISION:
        raise ValueError("Unsupported or unpinned MechanicDB source manifest")
    if data.get("data_license") != "ODbL-1.0" or data.get("rights_status") != "approved_by_published_license":
        raise ValueError("Published ODbL rights gate is not satisfied")
    if not all(data.get(key) is True for key in ("display_allowed", "cache_allowed", "redistribution_allowed", "share_alike_required")):
        raise ValueError("Display, offline-cache, redistribution and share-alike rights are required")
    policy = data.get("product_policy", {})
    if policy.get("display_status") != "candidate_reference_visible_separate_namespace":
        raise ValueError("Candidate-only display policy is missing")
    if policy.get("repair_procedure_status") != "community_authored_not_factory_not_verified":
        raise ValueError("Community repair-lead status is missing")
    if any(policy.get(key) is not False for key in (
        "vehicle_fitment_claim", "ecu_fitment_claim", "pr_code_claim",
        "production_import", "oem_part_numbers_included",
        "cost_or_labor_estimates_included", "external_part_search_urls_included",
        "diagnostic_execution_allowed",
    )):
        raise ValueError("A prohibited fitment, execution, OEM-part or price claim is enabled")
    return data


def read_selected(upstream: Path, manifest: dict, filename: str, selection_key: str, key_field: str):
    source = upstream / filename
    raw_lines = source.read_bytes().splitlines(keepends=True)
    expected = manifest["selected_records"][selection_key]
    expected_by_key = {str(item["fields"][key_field]): item for item in expected}
    found = {}
    with source.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="|")
        for row in reader:
            key = str((row.get(key_field) or "").strip())
            if key not in expected_by_key:
                continue
            if key in found:
                raise ValueError(f"Duplicate selected {filename} row: {key}")
            item = expected_by_key[key]
            if reader.line_num != item["line_no"]:
                raise ValueError(f"{filename} {key} moved from line {item['line_no']} to {reader.line_num}")
            for field, value in item["fields"].items():
                if row.get(field) != value:
                    raise ValueError(f"{filename} {key} field {field} differs from the reviewed manifest")
            if reader.line_num < 2 or reader.line_num > len(raw_lines):
                raise ValueError(f"Invalid physical source line for {filename} {key}")
            found[key] = {
                "fields": dict(row),
                "line_no": reader.line_num,
                "line_sha256": sha256_bytes(raw_lines[reader.line_num - 1]),
            }
    if set(found) != set(expected_by_key):
        raise ValueError(f"Selected {filename} rows missing: {sorted(set(expected_by_key)-set(found))}")
    return [found[key] for key in sorted(found)], len(raw_lines)


def build_database(db_path: Path, manifest: dict, source_files: dict, dtcs: list, fixes: list, parts: list, snapshot_sha256: str):
    if db_path.exists():
        db_path.unlink()
    db = sqlite3.connect(db_path)
    try:
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA journal_mode=DELETE")
        db.execute("PRAGMA synchronous=FULL")
        db.execute("PRAGMA application_id=1448368196")
        db.execute("PRAGMA user_version=2")
        db.executescript("""
        CREATE TABLE source_registry (
          source_id TEXT PRIMARY KEY, publisher TEXT NOT NULL, repository_url TEXT NOT NULL,
          source_revision TEXT NOT NULL, data_license TEXT NOT NULL CHECK(data_license='ODbL-1.0'),
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
          relative_path TEXT PRIMARY KEY, source_url TEXT NOT NULL, source_revision TEXT NOT NULL,
          git_blob_sha1 TEXT NOT NULL CHECK(length(git_blob_sha1)=40),
          sha256 TEXT NOT NULL CHECK(length(sha256)=64), byte_size INTEGER NOT NULL CHECK(byte_size>0),
          file_kind TEXT NOT NULL
        );
        CREATE TABLE dtc_candidates (
          id INTEGER PRIMARY KEY, code_id INTEGER NOT NULL UNIQUE, dtc_code TEXT NOT NULL CHECK(length(dtc_code)=5),
          oem_make TEXT NOT NULL CHECK(oem_make IN ('Audi','Volkswagen')), system_category TEXT NOT NULL,
          fault_family TEXT NOT NULL, short_description TEXT NOT NULL, detailed_technical_explanation TEXT NOT NULL,
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
          source_revision TEXT NOT NULL, UNIQUE(oem_make,dtc_code,source_revision)
        );
        CREATE TABLE community_fix_candidates (
          fix_id INTEGER PRIMARY KEY, code_id INTEGER NOT NULL REFERENCES dtc_candidates(code_id),
          dtc_code TEXT NOT NULL, oem_make TEXT NOT NULL CHECK(oem_make IN ('Audi','Volkswagen')),
          fix_title TEXT NOT NULL, consideration_order INTEGER NOT NULL CHECK(consideration_order BETWEEN 1 AND 9),
          difficulty_level TEXT NOT NULL, step_by_step_instructions TEXT NOT NULL,
          action_type TEXT NOT NULL, procedure_rationale TEXT NOT NULL,
          namespace TEXT NOT NULL CHECK(namespace='community_repair_lead'),
          verification_status TEXT NOT NULL CHECK(verification_status='community_reference_unverified'),
          market_scope TEXT NOT NULL CHECK(market_scope='UNKNOWN'),
          applicability_precision TEXT NOT NULL CHECK(applicability_precision='manufacturer_make_candidate'),
          diagnostic_execution_allowed INTEGER NOT NULL CHECK(diagnostic_execution_allowed=0),
          manufacturer_procedure INTEGER NOT NULL CHECK(manufacturer_procedure=0),
          oem_part_number INTEGER NOT NULL CHECK(oem_part_number=0),
          cost_estimates_included INTEGER NOT NULL CHECK(cost_estimates_included=0),
          source_file TEXT NOT NULL REFERENCES source_files(relative_path),
          source_line_no INTEGER NOT NULL CHECK(source_line_no>1),
          source_line_sha256 TEXT NOT NULL CHECK(length(source_line_sha256)=64),
          source_file_sha256 TEXT NOT NULL CHECK(length(source_file_sha256)=64),
          source_revision TEXT NOT NULL
        );
        CREATE TABLE community_part_candidates (
          part_id INTEGER PRIMARY KEY, fix_id INTEGER NOT NULL REFERENCES community_fix_candidates(fix_id),
          part_name TEXT NOT NULL, namespace TEXT NOT NULL CHECK(namespace='community_part_name_candidate'),
          verification_status TEXT NOT NULL CHECK(verification_status='community_reference_unverified'),
          market_scope TEXT NOT NULL CHECK(market_scope='UNKNOWN'),
          applicability_precision TEXT NOT NULL CHECK(applicability_precision='manufacturer_make_candidate'),
          oem_part_number INTEGER NOT NULL CHECK(oem_part_number=0),
          source_file TEXT NOT NULL REFERENCES source_files(relative_path),
          source_line_no INTEGER NOT NULL CHECK(source_line_no>1),
          source_line_sha256 TEXT NOT NULL CHECK(length(source_line_sha256)=64),
          source_file_sha256 TEXT NOT NULL CHECK(length(source_file_sha256)=64),
          source_revision TEXT NOT NULL
        );
        CREATE TABLE pack_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE INDEX idx_candidate_make_code ON dtc_candidates(oem_make,dtc_code);
        CREATE INDEX idx_fix_candidate_code ON community_fix_candidates(oem_make,dtc_code,consideration_order);
        CREATE INDEX idx_part_candidate_fix ON community_part_candidates(fix_id);
        """)
        db.execute("BEGIN IMMEDIATE")
        db.execute("INSERT INTO source_registry VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            manifest["source_id"], manifest["publisher"], manifest["repository"], manifest["source_revision"],
            manifest["data_license"], manifest["documentation_license"], manifest["upstream_license"],
            manifest["rights_status"], 1, 1, 1, 1, 1, 1, "UNKNOWN",
            "manufacturer_make_candidate", "community_reference_unverified", snapshot_sha256,
        ))
        for relative, item in source_files.items():
            db.execute("INSERT INTO source_files VALUES (?,?,?,?,?,?,?)", (
                relative, item["source_url"], manifest["source_revision"], item["git_blob_sha1"],
                item["sha256"], item["byte_size"], item["file_kind"],
            ))
        dtc_file = source_files["upstream/dtc_codes.csv"]
        dtc_by_id = {}
        for item in dtcs:
            f = item["fields"]
            code_id = int(f["code_id"])
            dtc_by_id[code_id] = {"code": f["dtc_code"], "make": f["oem_make"]}
            db.execute("""INSERT INTO dtc_candidates (
              code_id,dtc_code,oem_make,system_category,fault_family,short_description,detailed_technical_explanation,
              namespace,verification_status,market_scope,applicability_precision,vehicle_fitment_claim,ecu_fitment_claim,
              pr_code_claim,diagnostic_execution_allowed,repair_procedure_included,oem_part_number_included,
              source_file,source_line_no,source_line_sha256,source_file_sha256,source_revision
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
                code_id, f["dtc_code"], f["oem_make"], f["system_category"], f["fault_family"],
                f["short_description"], f["detailed_technical_explanation"], "manufacturer_controlled_candidate",
                "community_reference_unverified", "UNKNOWN", "manufacturer_make_candidate",
                0,0,0,0,0,0, "upstream/dtc_codes.csv", item["line_no"], item["line_sha256"],
                dtc_file["sha256"], manifest["source_revision"],
            ))
        fix_file = source_files["upstream/diagnostic_fixes.csv"]
        fix_ids = set()
        for item in fixes:
            f = item["fields"]
            fix_id, code_id = int(f["fix_id"]), int(f["code_id"])
            if code_id not in dtc_by_id:
                raise ValueError(f"Community fix {fix_id} does not reference a selected Audi/VW candidate")
            context = dtc_by_id[code_id]
            db.execute("""INSERT INTO community_fix_candidates (
              fix_id,code_id,dtc_code,oem_make,fix_title,consideration_order,difficulty_level,
              step_by_step_instructions,action_type,procedure_rationale,namespace,verification_status,
              market_scope,applicability_precision,diagnostic_execution_allowed,manufacturer_procedure,
              oem_part_number,cost_estimates_included,source_file,source_line_no,source_line_sha256,
              source_file_sha256,source_revision
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
                fix_id, code_id, context["code"], context["make"], f["fix_title"], int(f["probability_rank"]),
                f["difficulty_level"], f["step_by_step_instructions"], f.get("action_type") or "",
                f.get("procedure_rationale") or "", "community_repair_lead", "community_reference_unverified",
                "UNKNOWN", "manufacturer_make_candidate", 0,0,0,0, "upstream/diagnostic_fixes.csv",
                item["line_no"], item["line_sha256"], fix_file["sha256"], manifest["source_revision"],
            ))
            fix_ids.add(fix_id)
        part_file = source_files["upstream/replacement_parts.csv"]
        for item in parts:
            f = item["fields"]
            fix_id = int(f["fix_id"])
            if fix_id not in fix_ids:
                raise ValueError(f"Community part {f['part_id']} has no selected fix candidate")
            db.execute("""INSERT INTO community_part_candidates (
              part_id,fix_id,part_name,namespace,verification_status,market_scope,applicability_precision,
              oem_part_number,source_file,source_line_no,source_line_sha256,source_file_sha256,source_revision
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
                int(f["part_id"]), fix_id, f["part_name"], "community_part_name_candidate",
                "community_reference_unverified", "UNKNOWN", "manufacturer_make_candidate", 0,
                "upstream/replacement_parts.csv", item["line_no"], item["line_sha256"],
                part_file["sha256"], manifest["source_revision"],
            ))
        metadata = {
            "pack_id": "mechanicdb-vag-dtc-candidates-odbl",
            "schema_version": "2",
            "manufacturer_candidate_rows": str(len(dtcs)),
            "generic_dtc_rows": "0",
            "community_repair_lead_rows": str(len(fixes)),
            "community_part_candidate_rows": str(len(parts)),
            "verified_repair_procedure_rows": "0",
            "oem_part_number_rows": "0",
            "market_scope": "UNKNOWN",
            "applicability_precision": "manufacturer_make_candidate",
            "diagnostic_execution_allowed": "false",
            "source_snapshot_sha256": snapshot_sha256,
        }
        db.executemany("INSERT INTO pack_metadata VALUES (?,?)", sorted(metadata.items()))
        db.commit()
        if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok" or db.execute("PRAGMA foreign_key_check").fetchall():
            raise RuntimeError("SQLite integrity or foreign-key check failed")
        db.execute("VACUUM")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream-dir", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    upstream = args.upstream_dir.resolve()
    if not (upstream / ".git").exists():
        raise SystemExit("Pinned upstream Git repository is required")
    manifest = load_manifest(args.manifest)
    revision = subprocess.run(["git","-C",str(upstream),"rev-parse","HEAD"], check=True, capture_output=True, text=True).stdout.strip()
    if revision != manifest["source_revision"]:
        raise SystemExit(f"Upstream revision mismatch: {revision}")

    dtcs, _ = read_selected(upstream, manifest, "dtc_codes.csv", "manufacturer_dtc_candidates", "dtc_code")
    fixes, _ = read_selected(upstream, manifest, "diagnostic_fixes.csv", "community_fix_candidates", "fix_id")
    parts, _ = read_selected(upstream, manifest, "replacement_parts.csv", "community_part_candidates", "part_id")
    if len(dtcs) != 2 or len(fixes) != 6 or len(parts) != 6:
        raise SystemExit("Unexpected selected candidate/fix/part row counts")
    selected_codes = {int(x["fields"]["code_id"]) for x in dtcs}
    if {int(x["fields"]["code_id"]) for x in fixes} != selected_codes:
        raise SystemExit("Repair leads must map only to the two selected Audi/VW make candidates")

    output = args.output.resolve()
    if output.exists():
        shutil.rmtree(output)
    (output / "upstream").mkdir(parents=True)
    source_files = {}
    for name, relative in COPIED_FILES.items():
        src = upstream / name
        declared = manifest["source_files"][name]
        if not src.is_file() or git_blob_sha1(upstream, src) != declared["git_blob_sha1"]:
            raise SystemExit(f"Pinned upstream Git blob mismatch: {name}")
        dst = output / relative
        shutil.copyfile(src, dst)
        source_files[relative] = {
            "source_url": declared["url"],
            "git_blob_sha1": declared["git_blob_sha1"],
            "sha256": sha256_file(dst),
            "byte_size": dst.stat().st_size,
            "file_kind": "source_data" if name.endswith(".csv") else "license_text" if name.startswith("LICENSE") else "attribution_documentation",
        }
    snapshot_material = json.dumps({k:v["sha256"] for k,v in sorted(source_files.items())}, sort_keys=True, separators=(",",":")).encode()
    snapshot_sha256 = sha256_bytes(snapshot_material)
    db_path = output / "mechanicdb-vag-dtc-candidates.sqlite"
    build_database(db_path, manifest, source_files, dtcs, fixes, parts, snapshot_sha256)

    attribution = (
        "Selected free MechanicDB / MechanicDB-public sample, pinned revision " + manifest["source_revision"] + ".\n"
        "Dataset license: ODbL v1.0; attribution and share-alike apply to this separate SQLite database.\n"
        "Upstream DTC code spine is attributed by MechanicDB to Wal33D / Waleed Judah's MIT-licensed compilation; the MIT notice is preserved.\n"
        "Included: two make-labelled DTC candidates (Audi P3000 and Volkswagen P1128), six community-authored repair leads, and six generic part-name candidates.\n"
        "These are not OEM-confirmed definitions or factory procedures. No exact model, generation, year, engine, gearbox, ECU, PR-code, VIN or market applicability is asserted.\n"
        "Repair-lead order is an authored consideration order, not probability or success likelihood. Difficulty labels are publisher editorial labels, not OEM safety ratings.\n"
        "No cost/labour estimates, external part-search URLs or OEM part numbers are included. Diagnostic execution is disabled; follow the vehicle manufacturer's safety/service documentation.\n"
    )
    (output / "ATTRIBUTION.txt").write_text(attribution, encoding="utf-8", newline="\n")
    file_hashes = {
        p.relative_to(output).as_posix(): {"sha256":sha256_file(p),"byte_size":p.stat().st_size}
        for p in sorted(output.rglob("*")) if p.is_file()
    }
    sums = "".join(f"{v['sha256']}  {k}\n" for k,v in sorted(file_hashes.items()))
    (output / "SHA256SUMS.txt").write_text(sums, encoding="utf-8", newline="\n")
    pack_files = {
        p.relative_to(output).as_posix(): {"sha256":sha256_file(p),"byte_size":p.stat().st_size}
        for p in sorted(output.rglob("*")) if p.is_file()
    }
    dtc_evidence = [{"oem_make":x["fields"]["oem_make"],"dtc_code":x["fields"]["dtc_code"],"source_file":"upstream/dtc_codes.csv","source_line_no":x["line_no"],"source_line_sha256":x["line_sha256"]} for x in dtcs]
    fix_evidence = [{"fix_id":x["fields"]["fix_id"],"code_id":x["fields"]["code_id"],"source_file":"upstream/diagnostic_fixes.csv","source_line_no":x["line_no"],"source_line_sha256":x["line_sha256"]} for x in fixes]
    part_evidence = [{"part_id":x["fields"]["part_id"],"fix_id":x["fields"]["fix_id"],"source_file":"upstream/replacement_parts.csv","source_line_no":x["line_no"],"source_line_sha256":x["line_sha256"]} for x in parts]
    pack_manifest = {
        "schema_version":2,"pack_id":"mechanicdb-vag-dtc-candidates-odbl","publisher":manifest["publisher"],
        "source_repository":manifest["repository"],"source_revision":manifest["source_revision"],"snapshot_date":manifest["snapshot_date"],
        "built_at_utc":datetime.now(timezone.utc).isoformat(),"data_license":"ODbL-1.0",
        "data_license_url":manifest["data_license_url"],"upstream_license":"MIT","documentation_license":"CC-BY-4.0",
        "commercial_use_allowed":True,"commercial_use_allowed_under_odbl":True,"cache_allowed":True,
        "redistribution_allowed":True,"redistribution_allowed_under_odbl":True,"offline_cache_allowed":True,
        "rights_status":"approved_by_published_license","commercial_use_allowed":True,"display_allowed":True,
        "offline_cache_allowed":True,"redistribution_allowed":True,"share_alike_required":True,"attribution_required":True,
        "source_snapshot_sha256":snapshot_sha256,"database_path":db_path.name,"database_sha256":sha256_file(db_path),
        "source_workflow":{"workflow_file":".github/workflows/acquire-mechanicdb-vag-repair-leads-run72.yml",
            "run_id":int(__import__("os").environ.get("GITHUB_RUN_ID","0")),"artifact_id":None,
            "commit":__import__("os").environ.get("GITHUB_SHA",revision if "revision" in locals() else PINNED_REVISION),"artifact_sha256":None},
        "counts":{"manufacturer_controlled_candidates":2,"audi_candidates":1,"volkswagen_candidates":1,"generic_dtc_rows":0,
                  "repair_procedure_rows":0,"part_rows":0,"community_repair_lead_rows":6,"community_part_candidate_rows":6},
        "market_scope":"UNKNOWN","applicability_precision":"manufacturer_make_candidate",
        "verification_status":"community_reference_unverified","product_eligibility":"candidate_reference_only_visible_separate_namespace",
        "display_status":"candidate_reference_visible_separate_namespace","exact_vehicle_fitment":False,"ecu_fitment":False,
        "pr_code_fitment":False,"diagnostic_execution_allowed":False,"repair_procedures_included":False,
        "community_repair_leads_included":True,"community_repair_leads_verified":False,
        "oem_part_numbers_included":False,"community_part_names_included":True,
        "cost_or_labor_estimates_included":False,"external_part_search_urls_included":False,
        "source_line_evidence":dtc_evidence,"community_fix_line_evidence":fix_evidence,
        "community_part_line_evidence":part_evidence,"source_files":source_files,"pack_files":pack_files,
        "exclusions":[
            "Generic SAE/ISO DTC definitions are excluded; they remain in the separate CC0 OBDex and ODbL generic-guidance namespaces.",
            "Non-VAG OEM candidate rows are excluded.",
            "Only two make-labelled candidates are included; they are not OEM-confirmed or exact-vehicle verified.",
            "Six community-authored repair leads are displayed only as unverified research references, never as factory procedures or executable test plans.",
            "Six part names are generic community candidates, not OEM part numbers or confirmed parts for any vehicle.",
            "US cost/labour estimates and external Amazon search URLs are excluded.",
            "No exact model, generation, year, engine, gearbox, ECU, PR-code, VIN or market applicability is asserted."
        ],
        "display_policy":{
            "status":"candidate_reference_visible_separate_namespace","purpose":"read_only_research_reference_only",
            "namespace":"manufacturer_controlled_candidate","repair_lead_namespace":"community_repair_lead",
            "repair_leads_visible":True,"repair_leads_verified":False,"part_names_visible":True,
            "exact_vehicle_fitment":False,"vag_oem_confirmation":False,"diagnostic_execution_allowed":False,
            "manufacturer_repair_procedure":False,"oem_part_numbers_included":False,
            "cost_or_labor_estimates_included":False,"external_part_search_urls_included":False,
            "warning":"Community make-labelled DTC and repair-lead candidates only. Not OEM-confirmed, not exact-vehicle applicable and not diagnostic execution instructions. Repair order is consideration order, not probability. No OEM part numbers."
        }
    }
    (output / "manifest.json").write_text(json.dumps(pack_manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":"built_candidate_research_pack","database_sha256":pack_manifest["database_sha256"],
        "source_snapshot_sha256":snapshot_sha256,"counts":pack_manifest["counts"],"market_scope":"UNKNOWN",
        "applicability_precision":"manufacturer_make_candidate","diagnostic_execution_allowed":False},ensure_ascii=False,indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
