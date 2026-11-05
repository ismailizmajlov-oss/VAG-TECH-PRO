#!/usr/bin/env python3
"""Independently verify the ODbL Audi/VW candidate DTC and community repair-lead pack."""

from __future__ import annotations
import argparse, hashlib, json, sqlite3
from pathlib import Path

PINNED_REVISION = "c788dfe9ed1517d4cd0be27f5aacb4776abf4864"

def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()

def fail(message: str):
    raise SystemExit(message)

def physical_lines(path: Path):
    return path.read_bytes().splitlines(keepends=True)

def verify_line(root, table_row, expected_file):
    rel, line_no, line_hash, file_hash, revision = table_row
    source = root / rel
    lines = physical_lines(source)
    if revision != PINNED_REVISION or rel != expected_file or line_no <= 1 or line_no > len(lines):
        fail(f"Unexpected source lineage: {rel} line {line_no}")
    if sha256_file(source) != file_hash or hashlib.sha256(lines[line_no-1]).hexdigest() != line_hash:
        fail(f"Source file/line hash mismatch: {rel} line {line_no}")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",required=True,type=Path)
    a=p.parse_args()
    root=a.root.resolve()
    m=json.loads((root/"manifest.json").read_text(encoding="utf-8"))
    if m.get("schema_version")!=2 or m.get("source_revision")!=PINNED_REVISION:
        fail("Unsupported pack schema or upstream revision")
    if m.get("data_license")!="ODbL-1.0" or m.get("rights_status")!="approved_by_published_license":
        fail("ODbL rights gate failed")
    if not all(m.get(k) is True for k in ("commercial_use_allowed","commercial_use_allowed_under_odbl","display_allowed","offline_cache_allowed","redistribution_allowed","redistribution_allowed_under_odbl","share_alike_required","attribution_required")):
        fail("Published ODbL rights are incomplete")
    for rel,meta in m["source_files"].items():
        if not meta.get("source_url","").startswith("https://raw.githubusercontent.com/MechanicDB/MechanicDB-public/"):
            fail(f"Unpinned source URL: {rel}")
        f=root/rel
        if not f.is_file() or f.stat().st_size!=meta["byte_size"] or sha256_file(f)!=meta["sha256"]:
            fail(f"Source file hash mismatch: {rel}")
    for rel,meta in m["pack_files"].items():
        f=root/rel
        if not f.is_file() or f.stat().st_size!=meta["byte_size"] or sha256_file(f)!=meta["sha256"]:
            fail(f"Pack file hash mismatch: {rel}")
    dbpath=root/m["database_path"]
    if sha256_file(dbpath)!=m["database_sha256"]: fail("SQLite database hash mismatch")
    db=sqlite3.connect(f"file:{dbpath.as_posix()}?mode=ro",uri=True)
    db.row_factory=sqlite3.Row
    try:
        if db.execute("PRAGMA integrity_check").fetchone()[0]!="ok" or db.execute("PRAGMA foreign_key_check").fetchall():
            fail("SQLite integrity/foreign-key check failed")
        if db.execute("PRAGMA user_version").fetchone()[0]!=2: fail("Unexpected SQLite schema version")
        source=db.execute("SELECT * FROM source_registry").fetchone()
        if not source or source["data_license"]!="ODbL-1.0" or source["rights_status"]!="approved_by_published_license" or source["commercial_use_allowed"]!=1 or source["display_allowed"]!=1 or source["offline_cache_allowed"]!=1 or source["redistribution_allowed"]!=1 or source["share_alike_required"]!=1 or source["market_scope"]!="UNKNOWN" or source["technical_review_status"]!="community_reference_unverified":
            fail("SQLite source registry rights/provenance mismatch")
        dtcs=db.execute("SELECT * FROM dtc_candidates ORDER BY oem_make").fetchall()
        if {(r["oem_make"],r["dtc_code"]) for r in dtcs}!={("Audi","P3000"),("Volkswagen","P1128")}:
            fail("Unexpected DTC candidate rows")
        for r in dtcs:
            if r["namespace"]!="manufacturer_controlled_candidate" or r["verification_status"]!="community_reference_unverified" or r["market_scope"]!="UNKNOWN" or r["applicability_precision"]!="manufacturer_make_candidate" or any(r[k]!=0 for k in ("vehicle_fitment_claim","ecu_fitment_claim","pr_code_claim","diagnostic_execution_allowed","repair_procedure_included","oem_part_number_included")):
                fail("DTC candidate was promoted beyond make-level reference")
            verify_line(root,(r["source_file"],r["source_line_no"],r["source_line_sha256"],r["source_file_sha256"],r["source_revision"]),"upstream/dtc_codes.csv")
        fixes=db.execute("SELECT * FROM community_fix_candidates ORDER BY fix_id").fetchall()
        if len(fixes)!=6 or {r["fix_id"] for r in fixes}!={33105,33106,33107,54784,54785,54786}:
            fail("Unexpected community repair-lead rows")
        for r in fixes:
            if r["namespace"]!="community_repair_lead" or r["verification_status"]!="community_reference_unverified" or r["market_scope"]!="UNKNOWN" or r["applicability_precision"]!="manufacturer_make_candidate" or any(r[k]!=0 for k in ("diagnostic_execution_allowed","manufacturer_procedure","oem_part_number","cost_estimates_included")):
                fail("Community repair lead was promoted to OEM/verified/executable status")
            verify_line(root,(r["source_file"],r["source_line_no"],r["source_line_sha256"],r["source_file_sha256"],r["source_revision"]),"upstream/diagnostic_fixes.csv")
        parts=db.execute("SELECT * FROM community_part_candidates ORDER BY part_id").fetchall()
        if len(parts)!=6 or {r["part_id"] for r in parts}!={45037,45038,45039,72741,72742,72743}:
            fail("Unexpected community part-name candidate rows")
        for r in parts:
            if r["namespace"]!="community_part_name_candidate" or r["verification_status"]!="community_reference_unverified" or r["market_scope"]!="UNKNOWN" or r["applicability_precision"]!="manufacturer_make_candidate" or r["oem_part_number"]!=0:
                fail("Community part name was promoted to OEM part number")
            verify_line(root,(r["source_file"],r["source_line_no"],r["source_line_sha256"],r["source_file_sha256"],r["source_revision"]),"upstream/replacement_parts.csv")
    finally:
        db.close()
    fix_evidence={(x["fix_id"],x["source_file"],x["source_line_no"],x["source_line_sha256"]) for x in m.get("community_fix_line_evidence",[])}
    part_evidence={(x["part_id"],x["fix_id"],x["source_file"],x["source_line_no"],x["source_line_sha256"]) for x in m.get("community_part_line_evidence",[])}
    if len(fix_evidence)!=6 or len(part_evidence)!=6: fail("Pack manifest per-line repair/part evidence is incomplete")
    workflow=m.get("source_workflow",{})
    if workflow.get("workflow_file")!=".github/workflows/acquire-mechanicdb-vag-repair-leads-run72.yml" or workflow.get("commit")!=__import__("os").environ.get("GITHUB_SHA",workflow.get("commit")): fail("Acquisition workflow provenance mismatch")
    counts=m["counts"]
    if counts.get("manufacturer_controlled_candidates")!=2 or counts.get("generic_dtc_rows")!=0 or counts.get("community_repair_lead_rows")!=6 or counts.get("community_part_candidate_rows")!=6 or counts.get("repair_procedure_rows")!=0 or counts.get("part_rows")!=0:
        fail("Pack manifest counts or namespace boundary mismatch")
    if m.get("market_scope")!="UNKNOWN" or m.get("applicability_precision")!="manufacturer_make_candidate" or m.get("exact_vehicle_fitment") is not False or m.get("diagnostic_execution_allowed") is not False or m.get("repair_procedures_included") is not False or m.get("oem_part_numbers_included") is not False or m.get("community_repair_leads_verified") is not False:
        fail("Pack applicability/execution/verification boundary changed")
    print(json.dumps({"status":"verified_candidate_and_community_lead_pack","counts":counts,
        "database_sha256":m["database_sha256"],"source_snapshot_sha256":m["source_snapshot_sha256"],
        "market_scope":"UNKNOWN","applicability_precision":"manufacturer_make_candidate",
        "diagnostic_execution_allowed":False,"OEM_repair_procedures":0,"OEM_part_numbers":0},ensure_ascii=False,indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
