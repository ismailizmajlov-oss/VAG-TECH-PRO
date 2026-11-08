#!/usr/bin/env node
"use strict";
const fs=require("node:fs"),path=require("node:path");
const GENERIC_PATTERN="^(?:P0[0-9A-F]{3}|P2[0-9A-F]{3}|P34[0-9A-F]{2}|B0[0-9A-F]{3}|C0[0-9A-F]{3}|U0[0-9A-F]{3}|U3[0-9A-F]{3})$";
const VAG_PATTERN="^(?:P1[0-9A-F]{3}|P3(?:[0-3]|[5-9])[0-9A-F]{2}|B[12][0-9A-F]{3}|C[12][0-9A-F]{3}|U[12][0-9A-F]{3})$";
function replaceOnce(s,b,a,label){const n=s.split(b).length-1;if(n!==1)throw new Error(label+": expected one patch anchor, found "+n);return s.replace(b,a);}
function read(root,rel){const f=path.join(root,rel);if(!fs.existsSync(f))throw new Error("run86 required file is missing: "+rel);return fs.readFileSync(f,"utf8");}
function patchDtcCase(core,caseName,namespace,label){
 const token='case "'+caseName+'": {',start=core.indexOf(token);
 if(start<0)throw new Error(label+": case block is missing");
 const next=core.indexOf("    case ",start+token.length),end=next<0?core.length:next,block=core.slice(start,end);
 const anchor='      if (payload.code != null && payload.dtc_code != null && payload.code.trim() !== payload.dtc_code.trim()) technicalPayloadError(record, "code and dtc_code must match when both are supplied");';
 const replacement=anchor+"\n      validateDtcCodeNamespace(record, code, \""+namespace+"\");";
 return core.slice(0,start)+replaceOnce(block,anchor,replacement,label+" range guard")+core.slice(end);
}
function apply(root){
 const f={core:"lib/local-core-db.cjs",tests:"tests/local-core-db.test.cjs",schema:"data/schemas/technical-record-payloads.schema.json",docs:"docs/LOCAL_VEHICLE_CATALOG_IMPORT.md"};
 let core=read(root,f.core),tests=read(root,f.tests),docs=read(root,f.docs);
 const schema=JSON.parse(read(root,f.schema));
 const marker="// run86: separate generic SAE/ISO code ranges from manufacturer-controlled OBD-II ranges";
 if(core.includes(marker)){
  if(!tests.includes("run86 rejects manufacturer-controlled DTC ranges in generic records")||!tests.includes("run86 rejects generic DTC ranges in VAG-specific records")||
   schema.$defs?.dtc_generic?.properties?.code?.pattern!==GENERIC_PATTERN||schema.$defs?.dtc_vag_specific?.properties?.code?.pattern!==VAG_PATTERN||

   !docs.includes("## DTC namespace code-range boundary (run86)"))throw new Error("run86 marker exists but companion contracts are missing");
  return {status:"already_applied",files:Object.values(f)};
 }
 const anchor="function validateTechnicalPayload(record) {";
 const helper=[marker,"const GENERIC_OBD_DTC_CODE_RE = /"+GENERIC_PATTERN+"/;","const MANUFACTURER_CONTROLLED_OBD_DTC_CODE_RE = /"+VAG_PATTERN+"/;",
  "function validateDtcCodeNamespace(record, code, namespace) {",'  const normalized = typeof code === "string" ? code.trim().toUpperCase() : "";',
  '  if (namespace === "generic_sae_iso_obd2" && !GENERIC_OBD_DTC_CODE_RE.test(normalized)) technicalPayloadError(record, "code is outside generic SAE/ISO OBD-II ranges; manufacturer-controlled codes cannot be imported as generic");',
  '  if (namespace === "vag_oem_specific" && !MANUFACTURER_CONTROLLED_OBD_DTC_CODE_RE.test(normalized)) technicalPayloadError(record, "code is outside manufacturer-controlled OBD-II ranges; generic SAE/ISO codes cannot be imported as VAG-specific");',
  "}",anchor].join("\n");
 core=replaceOnce(core,anchor,helper,"DTC range helper");
 core=patchDtcCase(core,"dtc_generic","generic_sae_iso_obd2","generic DTC");
 core=patchDtcCase(core,"dtc_vag_specific","vag_oem_specific","VAG-specific DTC");
 for(const field of ["code","dtc_code"]){
  if(!schema.$defs?.dtc_generic?.properties?.[field]||!schema.$defs?.dtc_vag_specific?.properties?.[field])throw new Error("technical schema DTC alias missing: "+field);
  schema.$defs.dtc_generic.properties[field].pattern=GENERIC_PATTERN;schema.$defs.dtc_vag_specific.properties[field].pattern=VAG_PATTERN;
 }
 const testAnchor='test("rejects a generic DTC record that tries to claim VAG or ECU applicability", (t) => {';
 if(!tests.includes("run86 rejects manufacturer-controlled DTC ranges in generic records")){
  const additions=[
   'test("run86 rejects manufacturer-controlled DTC ranges in generic records", (t) => {','  const { dbPath } = fixture(t);','  core.registerSource(dbPath, source());',
   '  const validPayload = { code: "P34C8", title: "Generic P34 range", namespace: "SAE/ISO" };',
   '  const valid = { ...genericDtc(), natural_key: "generic:P34C8", source_record_key: "obd:P34C8", title: "P34C8", payload: validPayload, record_sha256: core.sha256(validPayload) };',
   '  const result = core.importPackage(dbPath, packageOf([valid], { package_id: "run86-generic-boundary-valid" }));','  assert.equal(result.inserted, 1);',
   '  const invalidPayload = { code: "P1A00", title: "Manufacturer-controlled range", namespace: "SAE/ISO" };',
   '  const invalid = { ...valid, natural_key: "generic:P1A00", source_record_key: "obd:P1A00", title: "P1A00", payload: invalidPayload, record_sha256: core.sha256(invalidPayload) };',
   '  assert.throws(() => core.importPackage(dbPath, packageOf([invalid], { package_id: "run86-generic-boundary-invalid" })), /outside generic SAE\\/ISO OBD-II ranges/);',
   '  const db = new DatabaseSync(dbPath, { readOnly: true });','  assert.equal(db.prepare("SELECT count(*) AS n FROM technical_records").get().n, 1);',
   '  assert.equal(db.prepare("SELECT count(*) AS n FROM import_batches").get().n, 1);','  db.close();','});',"",
   'test("run86 rejects generic DTC ranges in VAG-specific records", (t) => {','  const { dbPath } = fixture(t);','  core.registerSource(dbPath, source());',
   '  const payload = { code: "P0300", description: "Generic SAE/ISO misfire code" };',
   '  const invalid = { record_type: "dtc_vag_specific", namespace: "vag_oem_specific", natural_key: "vag:P0300", source_record_key: "vag:P0300",',
   '    title: "P0300", market_scope: "ALL", applicability_precision: "exact_configuration", configuration_id: 1, ecu_id: 1, payload, record_sha256: core.sha256(payload) };',
   '  assert.throws(() => core.importPackage(dbPath, packageOf([invalid], { package_id: "run86-vag-boundary-invalid" })), /outside manufacturer-controlled OBD-II ranges/);',
   '  const db = new DatabaseSync(dbPath, { readOnly: true });','  assert.equal(db.prepare("SELECT count(*) AS n FROM technical_records").get().n, 0);',
   '  assert.equal(db.prepare("SELECT count(*) AS n FROM import_batches").get().n, 0);','  db.close();','});',"",testAnchor
  ].join("\n");
  tests=replaceOnce(tests,testAnchor,additions,"run86 tests");
 }
 if(!docs.includes("## DTC namespace code-range boundary (run86)"))docs += ["","","## DTC namespace code-range boundary (run86)","",
  "The offline importer validates the five-character OBD-II code range as well as the declared namespace. Generic SAE/ISO records are limited to P0xxx, P2xxx, P34xx, B0xxx, C0xxx, U0xxx and U3xxx. VAG-specific OBD-II candidates are limited to manufacturer-controlled P1xxx, P30xx–P33xx, P35xx–P39xx, B1xxx–B2xxx, C1xxx–C2xxx and U1xxx–U2xxx ranges. A code in a generic range cannot be labelled VAG-specific, and a manufacturer-controlled range cannot be imported as generic. This range check is a classification guard, not evidence of OEM authorship, exact ECU fitment or repair applicability; all VAG-specific records still require exact configuration/ECU links, source provenance, rights clearance and technical review.",""].join("\n");
 fs.writeFileSync(path.join(root,f.core),core,"utf8");fs.writeFileSync(path.join(root,f.tests),tests,"utf8");
 fs.writeFileSync(path.join(root,f.schema),JSON.stringify(schema,null,2)+"\n","utf8");
 fs.writeFileSync(path.join(root,f.docs),docs,"utf8");
 return {status:"applied",files:Object.values(f),genericPattern:GENERIC_PATTERN,vagPattern:VAG_PATTERN};
}
const i=process.argv.indexOf("--desktop-root"),root=path.resolve(i>=0&&process.argv[i+1]?process.argv[i+1]:"desktop-source");
console.log(JSON.stringify(apply(root)));
