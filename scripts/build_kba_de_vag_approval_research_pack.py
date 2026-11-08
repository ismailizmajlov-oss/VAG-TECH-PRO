#!/usr/bin/env python3
"""Build and verify a separate DE-only KBA approval metadata research pack."""
from __future__ import annotations
import argparse, hashlib, json, os, shutil, sqlite3, tempfile, zipfile
from datetime import date, datetime
from pathlib import Path
from typing import Any
from openpyxl import load_workbook

SOURCE_ID="kba-de-whole-vehicle-type-approvals"
PACK_ID="kba-de-vag-type-approval-research"
SOURCE_URL="https://www.kba.de/DE/Themen/Typgenehmigung/Informationen_TGV/Liste_erteilter_Typgenehmigungen/liste_typgenehmigungen_Excel.xlsx?__blob=publicationFile&v=13"
CATALOG_URL="https://www.govdata.de/suche/daten/liste-der-erteilten-typgenehmigungen-gesamtfahrzeug?ids=1cb74abc-7356-49bf-bb07-ef5dd9d7abfb"
LICENSE_ID="DL-DE-BY-2.0"
LICENSE_URL="https://www.govdata.de/dl-de/by-2-0"
HEADER_ROW=3
HEADER=["Hersteller","Handelsname","Typbezeichnung","Genehmigungsobjekt","Typgenehmigungsnummer","Technischer Dienst","Vorgangsart","Datum der Genehmigung","Mitgliedstaat Typgenehmigung(en) Emissionen",None,"Technischer Dienst Emission",None,"Zuordnung Handelsnamen zu Typgenehmigung Emissionen","Zuordnung Handelsnamen zu Typgenehmigung Emissionen"]
VAG_LABELS={"Volkswagen AG":"recognized_make_label_candidate","Audi AG":"recognized_make_label_candidate","AUDI AG":"recognized_make_label_candidate","SEAT S.A.":"recognized_make_label_candidate","Seat S.A.":"recognized_make_label_candidate","Audi Sport GmbH":"group_relation_requires_review","Audi_Sport":"unresolved_source_label","Audi Sport":"unresolved_source_label"}
VAG_COUNTS={"Volkswagen AG":450,"Audi AG":353,"AUDI AG":28,"Audi Sport GmbH":52,"Audi_Sport":22,"Audi Sport":1,"SEAT S.A.":8,"Seat S.A.":4}
EXCLUDED={"Bugatti Automobiles S.A.S.":"Historical/current group relationship is not established by this KBA row; excluded from the VAG-related candidate filter."}

def sha(b:bytes)->str: return hashlib.sha256(b).hexdigest()
def fsha(p:Path)->str:
 h=hashlib.sha256()
 with p.open("rb") as f:
  for c in iter(lambda:f.read(1024*1024),b""): h.update(c)
 return h.hexdigest()
def builder_sha256()->str: return fsha(Path(__file__).resolve())
def canon(v:Any)->bytes: return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
def norm(v:Any)->str|None:
 if v is None: return None
 if isinstance(v,(datetime,date)): return v.isoformat()
 if isinstance(v,float) and v.is_integer(): return str(int(v))
 return str(v)
def row_sha(n:int,cells:list[str|None])->str: return sha(canon({"source_row_number":n,"cells":cells}))

def safe_xlsx(p:Path)->None:
 if p.stat().st_size<100 or p.stat().st_size>50*1024*1024: raise ValueError("KBA XLSX size outside safe bounds")
 with zipfile.ZipFile(p) as z:
  names=set(); infos=z.infolist()
  if len(infos)>2000 or sum(x.file_size for x in infos)>200*1024*1024: raise ValueError("KBA XLSX archive exceeds safe bounds")
  for x in infos:
   n=x.filename.replace("\\","/")
   if n.startswith("/") or n==".." or n.startswith("../") or "/../" in n: raise ValueError("Unsafe XLSX ZIP path")
   if x.file_size>200*1024*1024 or (x.compress_size and x.file_size/x.compress_size>250): raise ValueError("Unsafe XLSX ZIP member")
   names.add(n)
  if z.testzip() is not None or "[Content_Types].xml" not in names or "xl/workbook.xml" not in names: raise ValueError("Invalid XLSX container")

def read_manifest(p:Path)->tuple[dict[str,Any],bytes]:
 raw=p.read_bytes(); m=json.loads(raw.decode("utf-8-sig")); s=m.get("snapshot",{}); r=m.get("rights",{})
 if m.get("source_id")!=SOURCE_ID or m.get("resource_url")!=SOURCE_URL or m.get("catalog_url")!=CATALOG_URL or m.get("market_scope")!=["DE"]: raise ValueError("KBA source identity/URL/market mismatch")
 if m.get("product_import_allowed") is not False or m.get("data_ingested") is not False: raise ValueError("KBA source must remain outside product database")
 if r.get("rights_status")!="approved_by_published_DL_DE_BY_2_0" or not r.get("reviewed_at_utc"): raise ValueError("KBA published licence review is not confirmed")
 for k in ("commercial_use_allowed","display_allowed","offline_cache_allowed","bulk_reuse_allowed","redistribution_allowed","attribution_required"):
  if r.get(k) is not True: raise ValueError("KBA rights/attribution condition missing: "+k)
 if s.get("status")!="resource_acquired_schema_available" or s.get("downloaded") is not True: raise ValueError("KBA source snapshot is not acquired/schema-reviewed")
 if s.get("file_sha256")!=s.get("source_snapshot_sha256") or m.get("source_snapshot_sha256")!=s.get("source_snapshot_sha256"): raise ValueError("KBA source snapshot hashes differ")
 if m.get("source_revision")!=s.get("source_revision") or s.get("source_revision")!="last-modified:"+s.get("last_modified","")+";etag:"+s.get("etag","").strip('"'): raise ValueError("KBA source revision/HTTP metadata mismatch")
 if s.get("header_row_number")!=HEADER_ROW or s.get("header")!=HEADER or s.get("sheet_count")!=1 or s.get("sheet_name")!="Tabelle1": raise ValueError("KBA worksheet schema mismatch")
 if s.get("source_row_count")!=3782 or s.get("source_manufacturer_label_count")!=116 or s.get("vag_related_label_candidate_count")!=918 or s.get("vag_related_label_candidate_counts")!=VAG_COUNTS or s.get("excluded_source_label_candidate_counts")!={"Bugatti Automobiles S.A.S.":14}: raise ValueError("KBA reviewed source counts changed")
 return m,raw

def extract(p:Path)->tuple[list[dict[str,Any]],dict[str,Any]]:
 safe_xlsx(p); wb=load_workbook(p,read_only=False,data_only=True)
 try:
  if len(wb.sheetnames)!=1 or wb.sheetnames[0]!="Tabelle1": raise ValueError("KBA worksheet count/name changed")
  ws=wb["Tabelle1"]; hdr=[norm(ws.cell(HEADER_ROW,c).value) for c in range(1,15)]
  if hdr!=HEADER: raise ValueError("KBA header changed")
  rows=0; labels=set(); counts={}; excluded={}; out=[]
  for n in range(HEADER_ROW+1,ws.max_row+1):
   c=[norm(ws.cell(n,k).value) for k in range(1,15)]
   if not c[0] or not c[0].strip(): continue
   rows+=1; label=c[0].strip(); labels.add(label)
   if label in EXCLUDED: excluded[label]=excluded.get(label,0)+1
   if label not in VAG_LABELS: continue
   counts[label]=counts.get(label,0)+1
   out.append({"source_row_number":n,"manufacturer_label":label,"manufacturer_label_mapping_status":VAG_LABELS[label],
    "trade_name_raw":c[1],"type_designation_raw":c[2],"approval_object_raw":c[3],"type_approval_number_raw":c[4],
    "technical_service_raw":c[5],"procedure_type_raw":c[6],"approval_date_raw":c[7],"emissions_member_state_raw":c[8],
    "technical_service_emission_raw":c[10],"emissions_mapping_1_raw":c[12],"emissions_mapping_2_raw":c[13],
    "raw_cells_json":json.dumps(c,ensure_ascii=False,separators=(",",":")),"source_record_sha256":row_sha(n,c)})
  return out,{"source_rows":rows,"source_manufacturer_labels":len(labels),"vag_related_label_candidates":len(out),
   "manufacturer_label_counts":dict(sorted(counts.items())),"excluded_source_label_counts":dict(sorted(excluded.items())),
   "date_min":min((x["approval_date_raw"] for x in out if x["approval_date_raw"]),default=None),
   "date_max":max((x["approval_date_raw"] for x in out if x["approval_date_raw"]),default=None)}
 finally: wb.close()

def build_db(p:Path,records:list[dict[str,Any]],m:dict[str,Any],manifest_sha:str,attribution:str)->dict[str,Any]:
 s=m["snapshot"]; r=m["rights"]; db=sqlite3.connect(p); db.execute("PRAGMA foreign_keys=ON")
 db.executescript("""
 CREATE TABLE source_registry(source_id TEXT PRIMARY KEY,publisher TEXT NOT NULL,source_url TEXT NOT NULL,catalog_url TEXT NOT NULL,license_id TEXT NOT NULL,license_url TEXT NOT NULL,rights_status TEXT NOT NULL,commercial_use_allowed INTEGER NOT NULL CHECK(commercial_use_allowed=1),display_allowed INTEGER NOT NULL CHECK(display_allowed=1),offline_cache_allowed INTEGER NOT NULL CHECK(offline_cache_allowed=1),bulk_reuse_allowed INTEGER NOT NULL CHECK(bulk_reuse_allowed=1),redistribution_allowed INTEGER NOT NULL CHECK(redistribution_allowed=1),attribution_required INTEGER NOT NULL CHECK(attribution_required=1),attribution_text TEXT NOT NULL,source_revision TEXT NOT NULL,source_snapshot_sha256 TEXT NOT NULL CHECK(length(source_snapshot_sha256)=64),source_manifest_sha256 TEXT NOT NULL CHECK(length(source_manifest_sha256)=64),market_scope TEXT NOT NULL CHECK(market_scope='DE'),applicability_precision TEXT NOT NULL CHECK(applicability_precision='type_approval_document_metadata_only'),review_status TEXT NOT NULL CHECK(review_status='research_only'),product_import_allowed INTEGER NOT NULL CHECK(product_import_allowed=0),exact_vehicle_fitment INTEGER NOT NULL CHECK(exact_vehicle_fitment=0),exact_engine_gearbox_pair INTEGER NOT NULL CHECK(exact_engine_gearbox_pair=0),ru_eaeu_applicability INTEGER NOT NULL CHECK(ru_eaeu_applicability=0),ecu_fitment INTEGER NOT NULL CHECK(ecu_fitment=0),dtc_fitment INTEGER NOT NULL CHECK(dtc_fitment=0),repair_applicability INTEGER NOT NULL CHECK(repair_applicability=0)) STRICT;
 CREATE TABLE source_files(source_id TEXT NOT NULL REFERENCES source_registry(source_id),file_name TEXT NOT NULL,sha256 TEXT NOT NULL CHECK(length(sha256)=64),byte_size INTEGER NOT NULL CHECK(byte_size>0),source_row_count INTEGER NOT NULL,filtered_row_count INTEGER NOT NULL,sheet_name TEXT NOT NULL,header_row_number INTEGER NOT NULL,header_json TEXT NOT NULL CHECK(json_valid(header_json)),last_modified TEXT NOT NULL,etag TEXT NOT NULL,probed_at TEXT NOT NULL,PRIMARY KEY(source_id,file_name)) STRICT;
 CREATE TABLE source_label_policy(manufacturer_label TEXT PRIMARY KEY,mapping_status TEXT NOT NULL,included INTEGER NOT NULL CHECK(included IN (0,1)),policy_note TEXT NOT NULL) STRICT;
 CREATE TABLE approval_records(id INTEGER PRIMARY KEY,source_id TEXT NOT NULL REFERENCES source_registry(source_id),source_row_number INTEGER NOT NULL,manufacturer_label TEXT NOT NULL,manufacturer_label_mapping_status TEXT NOT NULL,trade_name_raw TEXT,type_designation_raw TEXT,approval_object_raw TEXT,type_approval_number_raw TEXT,technical_service_raw TEXT,procedure_type_raw TEXT,approval_date_raw TEXT,emissions_member_state_raw TEXT,technical_service_emission_raw TEXT,emissions_mapping_1_raw TEXT,emissions_mapping_2_raw TEXT,raw_cells_json TEXT NOT NULL CHECK(json_valid(raw_cells_json)),source_record_sha256 TEXT NOT NULL CHECK(length(source_record_sha256)=64),source_revision TEXT NOT NULL,source_snapshot_sha256 TEXT NOT NULL CHECK(length(source_snapshot_sha256)=64),market_scope TEXT NOT NULL CHECK(market_scope='DE'),applicability_precision TEXT NOT NULL CHECK(applicability_precision='type_approval_document_metadata_only'),review_status TEXT NOT NULL CHECK(review_status='research_only'),exact_vehicle_fitment INTEGER NOT NULL CHECK(exact_vehicle_fitment=0),model_year INTEGER CHECK(model_year IS NULL),generation TEXT CHECK(generation IS NULL),engine_code TEXT CHECK(engine_code IS NULL),gearbox_code TEXT CHECK(gearbox_code IS NULL),exact_engine_gearbox_pair INTEGER NOT NULL CHECK(exact_engine_gearbox_pair=0),ru_eaeu_applicability INTEGER NOT NULL CHECK(ru_eaeu_applicability=0),ecu_fitment INTEGER NOT NULL CHECK(ecu_fitment=0),dtc_fitment INTEGER NOT NULL CHECK(dtc_fitment=0),repair_applicability INTEGER NOT NULL CHECK(repair_applicability=0),UNIQUE(source_id,source_revision,source_row_number)) STRICT;
 CREATE INDEX idx_kba_appr_make ON approval_records(manufacturer_label);
 CREATE INDEX idx_kba_appr_trade ON approval_records(trade_name_raw);
 CREATE INDEX idx_kba_appr_type ON approval_records(type_designation_raw);
 CREATE INDEX idx_kba_appr_number ON approval_records(type_approval_number_raw);
 CREATE INDEX idx_kba_appr_date ON approval_records(approval_date_raw);
 CREATE VIEW v_approval_records AS SELECT id,source_row_number,manufacturer_label,manufacturer_label_mapping_status,trade_name_raw,type_designation_raw,approval_object_raw,type_approval_number_raw,technical_service_raw,procedure_type_raw,approval_date_raw,emissions_member_state_raw,source_record_sha256,source_revision,source_snapshot_sha256,market_scope,applicability_precision,review_status,exact_vehicle_fitment,model_year,generation,engine_code,gearbox_code,exact_engine_gearbox_pair,ru_eaeu_applicability,ecu_fitment,dtc_fitment,repair_applicability FROM approval_records;
 """)
 rv=(SOURCE_ID,"Kraftfahrt-Bundesamt (KBA), Germany",SOURCE_URL,CATALOG_URL,LICENSE_ID,LICENSE_URL,r["rights_status"],1,1,1,1,1,1,attribution,s["source_revision"],s["source_snapshot_sha256"],manifest_sha,"DE","type_approval_document_metadata_only","research_only",0,0,0,0,0,0,0)
 db.execute("INSERT INTO source_registry VALUES("+",".join(["?"]*len(rv))+")",rv)
 fv=(SOURCE_ID,"kba-whole-vehicle-type-approvals.xlsx",s["file_sha256"],s["byte_size"],s["source_row_count"],len(records),s["sheet_name"],s["header_row_number"],json.dumps(s["header"],ensure_ascii=False),s["last_modified"],s["etag"],s["probed_at_utc"])
 db.execute("INSERT INTO source_files VALUES("+",".join(["?"]*len(fv))+")",fv)
 for label,status in VAG_LABELS.items():
  note={"recognized_make_label_candidate":"Exact source label; no alias normalization or vehicle fitment.","group_relation_requires_review":"Exact source label; corporate relationship not used as technical applicability.","unresolved_source_label":"Exact source label; no canonical make mapping."}[status]
  db.execute("INSERT INTO source_label_policy VALUES(?,?,1,?)",(label,status,note))
 for label,note in EXCLUDED.items(): db.execute("INSERT INTO source_label_policy VALUES(?,?,0,?)",(label,"excluded_unresolved_group_relation",note))
 cols=["source_id","source_row_number","manufacturer_label","manufacturer_label_mapping_status","trade_name_raw","type_designation_raw","approval_object_raw","type_approval_number_raw","technical_service_raw","procedure_type_raw","approval_date_raw","emissions_member_state_raw","technical_service_emission_raw","emissions_mapping_1_raw","emissions_mapping_2_raw","raw_cells_json","source_record_sha256","source_revision","source_snapshot_sha256","market_scope","applicability_precision","review_status","exact_vehicle_fitment","model_year","generation","engine_code","gearbox_code","exact_engine_gearbox_pair","ru_eaeu_applicability","ecu_fitment","dtc_fitment","repair_applicability"]
 vals=[]
 for x in records:
  vals.append((SOURCE_ID,x["source_row_number"],x["manufacturer_label"],x["manufacturer_label_mapping_status"],x["trade_name_raw"],x["type_designation_raw"],x["approval_object_raw"],x["type_approval_number_raw"],x["technical_service_raw"],x["procedure_type_raw"],x["approval_date_raw"],x["emissions_member_state_raw"],x["technical_service_emission_raw"],x["emissions_mapping_1_raw"],x["emissions_mapping_2_raw"],x["raw_cells_json"],x["source_record_sha256"],s["source_revision"],s["source_snapshot_sha256"],"DE","type_approval_document_metadata_only","research_only",0,None,None,None,None,0,0,0,0,0))
 db.executemany("INSERT INTO approval_records("+",".join(cols)+") VALUES("+",".join(["?"]*len(cols))+")",vals); db.commit()
 if db.execute("PRAGMA integrity_check").fetchone()[0]!="ok" or db.execute("PRAGMA foreign_key_check").fetchall(): raise ValueError("KBA SQLite integrity/foreign-key check failed")
 counts={"approval_records":db.execute("SELECT count(*) FROM approval_records").fetchone()[0],"manufacturer_labels":db.execute("SELECT count(DISTINCT manufacturer_label) FROM approval_records").fetchone()[0],"distinct_approval_numbers":db.execute("SELECT count(DISTINCT type_approval_number_raw) FROM approval_records").fetchone()[0]}
 bad=db.execute("SELECT count(*) FROM approval_records WHERE market_scope!='DE' OR applicability_precision!='type_approval_document_metadata_only' OR review_status!='research_only' OR exact_vehicle_fitment!=0 OR model_year IS NOT NULL OR generation IS NOT NULL OR engine_code IS NOT NULL OR gearbox_code IS NOT NULL OR exact_engine_gearbox_pair!=0 OR ru_eaeu_applicability!=0 OR ecu_fitment!=0 OR dtc_fitment!=0 OR repair_applicability!=0").fetchone()[0]
 if bad: raise ValueError("KBA SQLite applicability boundary violation")
 db.close(); return counts

def verify_pack(out:Path)->dict[str,Any]:
 m=json.loads((out/"manifest.json").read_text(encoding="utf-8"))
 if m.get("build_script_sha256")!=builder_sha256(): raise ValueError("KBA builder source SHA-256 mismatch")
 if any(m.get(k) is not False for k in ("research_pack_ingested","product_database_ingested","product_import_allowed","production_import")): raise ValueError("KBA pack crossed product boundary")
 if (m.get("market_scope"),m.get("applicability_precision"),m.get("review_status"))!=("DE","type_approval_document_metadata_only","research_only"): raise ValueError("KBA pack scope/status mismatch")
 for name,meta in m["files"].items():
  p=out/name
  if not p.is_file() or p.stat().st_size!=meta["byte_size"] or fsha(p)!=meta["sha256"]: raise ValueError("KBA pack file hash/size mismatch: "+name)
 if m["files"]["source-snapshot.xlsx"]["sha256"]!=m["source_snapshot_sha256"] or m["files"]["source-manifest.json"]["sha256"]!=m["source_manifest_sha256"]: raise ValueError("KBA source snapshot/manifest hash mismatch")
 if m["files"]["LICENSE.txt"]["sha256"]!=m["license_sha256"] or m["files"]["RIGHTS-EVIDENCE.json"]["sha256"]!=m["rights_evidence_sha256"] or m["files"]["ATTRIBUTION.md"]["sha256"]!=m["attribution_sha256"]: raise ValueError("KBA rights/attribution hash mismatch")
 attribution_text=(out/"ATTRIBUTION.md").read_text(encoding="utf-8")
 if "DL-DE BY 2.0" not in (out/"LICENSE.txt").read_text(encoding="utf-8") or SOURCE_URL not in attribution_text or "DL-DE BY 2.0" not in attribution_text or "Modified data" not in attribution_text: raise ValueError("KBA licence/attribution notice incomplete")
 db=sqlite3.connect("file:"+str((out/"kba-de-vag-approvals.sqlite").resolve())+"?mode=ro",uri=True)
 try:
  if db.execute("PRAGMA integrity_check").fetchone()[0]!="ok" or db.execute("PRAGMA foreign_key_check").fetchall(): raise ValueError("KBA SQLite integrity/foreign-key check failed")
  if db.execute("SELECT count(*) FROM approval_records").fetchone()[0]!=m["counts"]["approval_records"]: raise ValueError("KBA SQLite record count mismatch")
  labels={x[0] for x in db.execute("SELECT DISTINCT manufacturer_label FROM approval_records")}
  if labels!=set(VAG_LABELS): raise ValueError("KBA exact-label filter mismatch")
  label_counts=dict(db.execute("SELECT manufacturer_label,count(*) FROM approval_records GROUP BY manufacturer_label"))
  if label_counts!=m["counts"]["manufacturer_label_counts"]: raise ValueError("KBA manufacturer-label counts mismatch")
  bad=db.execute("SELECT count(*) FROM approval_records WHERE market_scope!='DE' OR applicability_precision!='type_approval_document_metadata_only' OR review_status!='research_only' OR exact_vehicle_fitment!=0 OR model_year IS NOT NULL OR generation IS NOT NULL OR engine_code IS NOT NULL OR gearbox_code IS NOT NULL OR exact_engine_gearbox_pair!=0 OR ru_eaeu_applicability!=0 OR ecu_fitment!=0 OR dtc_fitment!=0 OR repair_applicability!=0").fetchone()[0]
  if bad: raise ValueError("KBA applicability flags escaped research-only boundary")
  for n,raw,digest,rev,snap in db.execute("SELECT source_row_number,raw_cells_json,source_record_sha256,source_revision,source_snapshot_sha256 FROM approval_records"):
   if row_sha(n,json.loads(raw))!=digest or rev!=m["source_revision"] or snap!=m["source_snapshot_sha256"]: raise ValueError("KBA row provenance/hash mismatch")
  reg=db.execute("SELECT source_id,source_revision,source_snapshot_sha256,source_manifest_sha256,market_scope,applicability_precision,review_status,product_import_allowed FROM source_registry").fetchone()
  expected=(SOURCE_ID,m["source_revision"],m["source_snapshot_sha256"],m["source_manifest_sha256"],"DE","type_approval_document_metadata_only","research_only",0)
  if reg!=expected: raise ValueError("KBA SQLite source registry mismatch")
  sf=db.execute("SELECT sha256,byte_size,source_row_count,filtered_row_count,sheet_name,header_row_number,last_modified,etag FROM source_files").fetchone()
  exp=(m["source_file_sha256"],m["source_file_bytes"],m["counts"]["source_rows"],m["counts"]["approval_records"],"Tabelle1",3,m["source_file_last_modified"],m["source_file_etag"])
  if sf!=exp: raise ValueError("KBA SQLite source-file provenance mismatch")
 finally: db.close()
 return m

def build_pack(xlsx:Path,source_manifest:Path,out:Path)->dict[str,Any]:
 if out.exists(): raise FileExistsError("Refusing to overwrite existing KBA pack")
 out.parent.mkdir(parents=True,exist_ok=True); stage=Path(tempfile.mkdtemp(prefix=out.name+".staging-",dir=out.parent))
 try:
  m,raw=read_manifest(source_manifest); s=m["snapshot"]
  if fsha(xlsx)!=s["file_sha256"] or xlsx.stat().st_size!=s["byte_size"]: raise ValueError("KBA XLSX differs from pinned SHA-256/size")
  records,ex=extract(xlsx)
  if ex["source_rows"]!=s["source_row_count"] or ex["source_manufacturer_labels"]!=s["source_manufacturer_label_count"] or ex["manufacturer_label_counts"]!=s["vag_related_label_candidate_counts"] or ex["vag_related_label_candidates"]!=s["vag_related_label_candidate_count"] or ex["excluded_source_label_counts"]!=s["excluded_source_label_candidate_counts"] or ex["date_min"]!=s["approval_date_min"] or ex["date_max"]!=s["approval_date_max"]: raise ValueError("KBA workbook counts differ from reviewed snapshot")
  shutil.copy2(xlsx,stage/"source-snapshot.xlsx"); shutil.copy2(source_manifest,stage/"source-manifest.json")
  attribution="Source: Kraftfahrt-Bundesamt (KBA), Liste der erteilten Typgenehmigungen (Gesamtfahrzeug); KBA resource: "+SOURCE_URL+"; GovData catalogue: "+CATALOG_URL+"; DL-DE BY 2.0 ("+LICENSE_ID+") ("+LICENSE_URL+"). Modified data: exact manufacturer-label candidate filter, row normalization, SQLite indexing and per-row SHA-256 provenance. Original labels are preserved without alias normalization."
  (stage/"LICENSE.txt").write_text("Datenlizenz Deutschland – Namensnennung – Version 2.0 (DL-DE BY 2.0)\nOfficial licence: "+LICENSE_URL+"\nReuse requires attribution and a notice where data has been modified.\n",encoding="utf-8")
  (stage/"ATTRIBUTION.md").write_text(attribution+"\n",encoding="utf-8")
  rights={"source_id":SOURCE_ID,"rights_status":m["rights"]["rights_status"],"license_id":LICENSE_ID,"license_url":LICENSE_URL,"source_url":SOURCE_URL,"catalog_url":CATALOG_URL,"commercial_use_allowed":True,"display_allowed":True,"offline_cache_allowed":True,"bulk_reuse_allowed":True,"redistribution_allowed":True,"attribution_required":True,"reviewed_at_utc":m["rights"]["reviewed_at_utc"],"scope":"DE KBA approval metadata only"}
  (stage/"RIGHTS-EVIDENCE.json").write_text(json.dumps(rights,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
  dbp=stage/"kba-de-vag-approvals.sqlite"; counts=build_db(dbp,records,m,sha(raw),attribution)
  report={"status":"verified_research_only","pack_id":PACK_ID,"source_id":SOURCE_ID,"source_revision":s["source_revision"],"source_snapshot_sha256":s["source_snapshot_sha256"],"source_manifest_sha256":sha(raw),"builder_script_sha256":builder_sha256(),"database_sha256":fsha(dbp),"counts":{**ex,**counts},"product_database_ingested":False,"product_import_allowed":False,"ru_eaeu_applicability":False,"exact_engine_gearbox_pair_claim":False}
  (stage/"build-report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
  names=["source-snapshot.xlsx","source-manifest.json","LICENSE.txt","ATTRIBUTION.md","RIGHTS-EVIDENCE.json","kba-de-vag-approvals.sqlite","build-report.json"]
  files={n:{"byte_size":(stage/n).stat().st_size,"sha256":fsha(stage/n)} for n in names}
  manifest={"schema_version":1,"pack_id":PACK_ID,"source_id":SOURCE_ID,"publisher":"Kraftfahrt-Bundesamt (KBA), Germany","source_url":SOURCE_URL,"catalog_url":CATALOG_URL,"license_id":LICENSE_ID,"license_url":LICENSE_URL,"rights_status":m["rights"]["rights_status"],"commercial_use_allowed":True,"display_allowed":True,"offline_cache_allowed":True,"bulk_reuse_allowed":True,"redistribution_allowed":True,"attribution_required":True,"share_alike_required":False,"source_revision":s["source_revision"],"source_snapshot_sha256":s["source_snapshot_sha256"],"source_manifest_sha256":sha(raw),"build_script_sha256":builder_sha256(),"source_file_sha256":s["file_sha256"],"source_file_bytes":s["byte_size"],"source_file_last_modified":s["last_modified"],"source_file_etag":s["etag"],"source_row_hash_method":"SHA-256 over canonical UTF-8 JSON {source_row_number,cells}; cells preserve 14 source columns as strings/nulls; raw XLSX SHA-256 pins exact workbook bytes.","market_scope":"DE","applicability_precision":"type_approval_document_metadata_only","review_status":"research_only","counts":{**ex,**counts,"source_file_rows":s["source_row_count"],"exact_vag_label_whitelist_count":len(VAG_LABELS)},"manufacturer_label_policy":{"included_exact_labels":VAG_LABELS,"excluded_exact_labels":EXCLUDED,"matching":"exact string equality only; no fuzzy matching, case folding or alias normalization"},"applicability":{"individual_vehicle_fitment":False,"exact_vehicle_fitment":False,"model_year":False,"generation":False,"engine_code":False,"gearbox_code":False,"exact_engine_gearbox_pair":False,"ecu_fitment":False,"dtc_fitment":False,"repair_applicability":False,"diagnostic_execution_allowed":False,"ru_eaeu_applicability":False},"research_pack_built":True,"research_pack_ingested":False,"product_database_ingested":False,"product_import_allowed":False,"production_import":False,"files":files,"database_sha256":files["kba-de-vag-approvals.sqlite"]["sha256"],"license_sha256":files["LICENSE.txt"]["sha256"],"rights_evidence_sha256":files["RIGHTS-EVIDENCE.json"]["sha256"],"attribution_sha256":files["ATTRIBUTION.md"]["sha256"],"limitations":["DE whole-vehicle approval metadata only; not a build sheet.","No model-year, generation, engine/gearbox code, ECU, DTC or repair applicability.","No Russian/EAEU applicability.","Audi Sport labels remain unresolved; Bugatti Automobiles S.A.S. is excluded."]}
  (stage/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
  verify_pack(stage); os.replace(stage,out); return manifest
 except Exception:
  shutil.rmtree(stage,ignore_errors=True); raise

def main()->int:
 p=argparse.ArgumentParser(); p.add_argument("--xlsx",type=Path,required=True); p.add_argument("--source-manifest",type=Path,required=True); p.add_argument("--out",type=Path,required=True); p.add_argument("--verify",action="store_true"); a=p.parse_args()
 m=verify_pack(a.out) if a.verify else build_pack(a.xlsx,a.source_manifest,a.out)
 print(json.dumps({"status":"verified","pack_id":m["pack_id"],"source_revision":m["source_revision"],"source_snapshot_sha256":m["source_snapshot_sha256"],"database_sha256":m["database_sha256"],"counts":m["counts"],"product_import_allowed":False,"market_scope":"DE"},ensure_ascii=False,indent=2))
 return 0
if __name__=="__main__": raise SystemExit(main())
