#!/usr/bin/env python3
"""Fail-closed check that a fresh KBA probe matches the pinned source manifest."""
from __future__ import annotations
import argparse,json
from pathlib import Path
from urllib.parse import urlparse
SOURCE_ID="kba-de-whole-vehicle-type-approvals"
OFFICIAL={"www.kba.de","kba.de"}
def verify(probe_path:Path,manifest_path:Path)->dict:
 p=json.loads(probe_path.read_text(encoding="utf-8")); m=json.loads(manifest_path.read_text(encoding="utf-8-sig"))
 if p.get("source_id")!=SOURCE_ID or m.get("source_id")!=SOURCE_ID: raise ValueError("KBA source identity mismatch")
 if p.get("status")!="resource_acquired_schema_available" or p.get("probe_only") is not True: raise ValueError("KBA probe did not acquire a schema-verified source")
 if p.get("product_import_allowed") is not False or p.get("data_ingested") is not False: raise ValueError("KBA probe must remain outside product data")
 r=p.get("resource",{}); s=m.get("snapshot",{}); u=urlparse(r.get("final_url") or r.get("url") or "")
 if r.get("status")!=200 or u.scheme!="https" or u.hostname not in OFFICIAL: raise ValueError("KBA resource did not return HTTP 200 from the official HTTPS host")
 for a,b in (("sha256","file_sha256"),("bytes","byte_size"),("last_modified","last_modified"),("etag","etag")):
  if r.get(a)!=s.get(b): raise ValueError("Fresh KBA probe differs from pinned manifest: "+a)
 if s.get("file_sha256")!=s.get("source_snapshot_sha256") or m.get("source_snapshot_sha256")!=s.get("source_snapshot_sha256"): raise ValueError("KBA snapshot SHA-256 mismatch")
 if s.get("status")!="resource_acquired_schema_available" or s.get("downloaded") is not True: raise ValueError("KBA manifest snapshot is not acquired")
 if p.get("market_scope")!=["DE"] or m.get("market_scope")!=["DE"]: raise ValueError("KBA market scope must remain DE-only")
 rights=m.get("rights",{})
 if rights.get("rights_status")!="approved_by_published_DL_DE_BY_2_0": raise ValueError("KBA licence status mismatch")
 for k in ("commercial_use_allowed","display_allowed","offline_cache_allowed","bulk_reuse_allowed","redistribution_allowed","attribution_required"):
  if rights.get(k) is not True: raise ValueError("KBA rights condition missing: "+k)
 schema=p.get("workbook_schema") or {}; sheets=schema.get("sheets") or []
 if schema.get("sheet_count")!=1 or len(sheets)!=1: raise ValueError("KBA worksheet count changed")
 sh=sheets[0]; header=[None if x=="" else x for x in sh.get("header",[])]
 if sh.get("name")!=s.get("sheet_name") or sh.get("header_row_number")!=s.get("header_row_number") or header!=s.get("header"): raise ValueError("KBA worksheet header differs from pinned schema")
 if s.get("source_row_count")!=3782 or s.get("vag_related_label_candidate_count")!=918: raise ValueError("KBA reviewed row counts missing or changed")
 return {"status":"probe_matches_pinned_manifest","source_id":SOURCE_ID,"source_snapshot_sha256":s["source_snapshot_sha256"],"source_revision":s["source_revision"],"source_bytes":s["byte_size"],"source_rows":s["source_row_count"],"vag_related_label_candidates":s["vag_related_label_candidate_count"],"market_scope":"DE","product_import_allowed":False}
def main()->int:
 a=argparse.ArgumentParser(); a.add_argument("--probe",type=Path,required=True); a.add_argument("--source-manifest",type=Path,required=True); x=a.parse_args()
 print(json.dumps(verify(x.probe,x.source_manifest),ensure_ascii=False,indent=2)); return 0
if __name__=="__main__": raise SystemExit(main())
