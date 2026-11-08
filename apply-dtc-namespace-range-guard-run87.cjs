#!/usr/bin/env node
"use strict";
const fs=require("node:fs"),path=require("node:path");
const GENERIC_PATTERN="^(?:P0[0-9A-F]{3}|P2[0-9A-F]{3}|P34[0-9A-F]{2}|B0[0-9A-F]{3}|C0[0-9A-F]{3}|U0[0-9A-F]{3})$";
const MANUFACTURER_PATTERN="^(?:P1[0-9A-F]{3}|P3[0-3][0-9A-F]{2}|B[12][0-9A-F]{3}|C[12][0-9A-F]{3}|U[12][0-9A-F]{3})$";
const UNRESOLVED_PATTERN="^(?:P3[5-9][0-9A-F]{2}|U3[0-9A-F]{3}|B3[0-9A-F]{3}|C3[0-9A-F]{3})$";
function replaceOnce(s,a,b,label){const n=s.split(a).length-1;if(n!==1)throw new Error(label+": expected one patch anchor, found "+n);return s.replace(a,b);}
function read(root,rel){const f=path.join(root,rel);if(!fs.existsSync(f))throw new Error("run87 required file is missing: "+rel);return fs.readFileSync(f,"utf8");}
function apply(root){
 const files={core:"lib/local-core-db.cjs",tests:"tests/local-core-db.test.cjs",schema:"data/schemas/technical-record-payloads.schema.json",oemSchema:"data/schemas/oem-dtc-index.schema.json",docs:"docs/LOCAL_VEHICLE_CATALOG_IMPORT.md",policy:"data/policies/dtc-namespace-ranges.json"};
 let core=read(root,files.core),tests=read(root,files.tests),docs=read(root,files.docs);
 const policy=JSON.parse(read(root,files.policy));
 if(policy.namespaces?.generic_sae_iso?.pattern!==GENERIC_PATTERN||policy.namespaces?.manufacturer_controlled?.pattern!==MANUFACTURER_PATTERN||policy.namespaces?.unresolved_reserved?.pattern!==UNRESOLVED_PATTERN)throw new Error("run87 machine-readable DTC policy differs from the pinned patch contract");
 const marker="// run87: quarantine unresolved/reserved DTC ranges";
 const schema=JSON.parse(read(root,files.schema));
 const oemSchema=JSON.parse(read(root,files.oemSchema));
 if(core.includes(marker)){
  const patternsOk=core.includes("const GENERIC_OBD_DTC_CODE_RE = /"+GENERIC_PATTERN+"/;")&&core.includes("const MANUFACTURER_CONTROLLED_OBD_DTC_CODE_RE = /"+MANUFACTURER_PATTERN+"/;");
  const schemaOk=["code","dtc_code"].every(k=>schema.$defs?.dtc_generic?.properties?.[k]?.pattern===GENERIC_PATTERN&&schema.$defs?.dtc_vag_specific?.properties?.[k]?.pattern===MANUFACTURER_PATTERN);
  const oemRules=oemSchema.allOf||[];
  const oemOk=oemRules.every(r=>{const ns=r.if?.properties?.dtc_namespace?.const;const p=r.then?.properties?.dtc?.pattern;return ns==="generic_sae_iso"?p===GENERIC_PATTERN:(ns==="manufacturer_specific_vag"||ns==="manufacturer_specific_other")?p===MANUFACTURER_PATTERN:true;});
  if(!patternsOk||!schemaOk||!oemOk||!tests.includes("run87 quarantines unresolved/reserved DTC ranges from normalized namespaces")||!docs.includes("## DTC namespace code-range boundary (run87)"))throw new Error("run87 marker exists but companion contracts are incomplete");
  return {status:"already_applied",files:Object.values(files)};
 }
 if(!core.includes("// run86: separate generic SAE/ISO code ranges from manufacturer-controlled OBD-II ranges"))throw new Error("run87 requires the run86 DTC namespace guard first");
 const oldGeneric="const GENERIC_OBD_DTC_CODE_RE = /^(?:P0[0-9A-F]{3}|P2[0-9A-F]{3}|P34[0-9A-F]{2}|B0[0-9A-F]{3}|C0[0-9A-F]{3}|U0[0-9A-F]{3}|U3[0-9A-F]{3})$/;";
 const oldManufacturer="const MANUFACTURER_CONTROLLED_OBD_DTC_CODE_RE = /^(?:P1[0-9A-F]{3}|P3(?:[0-3]|[5-9])[0-9A-F]{2}|B[12][0-9A-F]{3}|C[12][0-9A-F]{3}|U[12][0-9A-F]{3})$/;";
 core=replaceOnce(core,oldGeneric,"const GENERIC_OBD_DTC_CODE_RE = /"+GENERIC_PATTERN+"/;\n"+marker, "generic range correction");
 core=replaceOnce(core,oldManufacturer,"const MANUFACTURER_CONTROLLED_OBD_DTC_CODE_RE = /"+MANUFACTURER_PATTERN+"/;","manufacturer range correction");
 for(const field of ["code","dtc_code"]){
  if(!schema.$defs?.dtc_generic?.properties?.[field]||!schema.$defs?.dtc_vag_specific?.properties?.[field])throw new Error("run87 technical schema DTC alias missing: "+field);
  schema.$defs.dtc_generic.properties[field].pattern=GENERIC_PATTERN;
  schema.$defs.dtc_vag_specific.properties[field].pattern=MANUFACTURER_PATTERN;
 }
 const oemRules=oemSchema.allOf||[];
 if(oemRules.length!==3)throw new Error("run87 OEM DTC schema must define three namespaces");
 for(const rule of oemRules){
  const ns=rule.if?.properties?.dtc_namespace?.const;
  if(ns==="generic_sae_iso")rule.then.properties.dtc.pattern=GENERIC_PATTERN;
  else if(ns==="manufacturer_specific_vag"||ns==="manufacturer_specific_other")rule.then.properties.dtc.pattern=MANUFACTURER_PATTERN;
 }
 const run87Test=[
 'test("run87 quarantines unresolved/reserved DTC ranges from normalized namespaces", (t) => {',
 '  const { dbPath } = fixture(t);',
 '  core.registerSource(dbPath, source());',
 '  const validPayload = { code: "P34C8", title: "Exact pinned generic P34 fixture", namespace: "SAE/ISO" };',
 '  const valid = { ...genericDtc(), natural_key: "run87:generic:P34C8", source_record_key: "run87:generic:P34C8", title: "P34C8", payload: validPayload, record_sha256: core.sha256(validPayload) };',
 '  const result = core.importPackage(dbPath, packageOf([valid], { package_id: "run87-generic-p34-valid" }));',
 '  assert.equal(result.inserted, 1);',
 '  for (const code of ["P35A6", "P39AB", "U3ABC", "B3ABC", "C3ABC"]) {',
 '    const payload = { code, title: "Unresolved/reserved range", namespace: "SAE/ISO" };',
 '    const invalid = { ...valid, natural_key: "run87:generic:" + code, source_record_key: "run87:generic:" + code, title: code, payload, record_sha256: core.sha256(payload) };',
 '    assert.throws(() => core.importPackage(dbPath, packageOf([invalid], { package_id: "run87-generic-invalid-" + code })), /outside generic SAE\\/ISO OBD-II ranges/);',
 '  }',
 '  for (const code of ["P35A6", "P39AB", "U3ABC", "B3ABC", "C3ABC"]) {',
 '    const payload = { code, description: "Unresolved/reserved range" };',
 '    const invalid = { record_type: "dtc_vag_specific", namespace: "vag_oem_specific", natural_key: "run87:vag:" + code, source_record_key: "run87:vag:" + code, title: code, market_scope: "ALL", applicability_precision: "exact_configuration", configuration_id: 1, ecu_id: 1, payload, record_sha256: core.sha256(payload) };',
 '    assert.throws(() => core.importPackage(dbPath, packageOf([invalid], { package_id: "run87-vag-invalid-" + code })), /outside manufacturer-controlled OBD-II ranges/);',
 '  }',
 '  const db = new DatabaseSync(dbPath, { readOnly: true });',
 '  assert.equal(db.prepare("SELECT count(*) AS n FROM technical_records").get().n, 1);',
 '  assert.equal(db.prepare("SELECT count(*) AS n FROM import_batches").get().n, 1);',
 '  db.close();',
 '});',
 ''].join("\n");
 if(!tests.includes("run87 quarantines unresolved/reserved DTC ranges from normalized namespaces"))tests += "\n"+run87Test;
 const oldHeading="## DTC namespace code-range boundary (run86)";
 const newSection=[
 "## DTC namespace code-range boundary (run87)",
 "",
 "The importer uses the machine-readable policy in `data/policies/dtc-namespace-ranges.json`. Generic SAE/ISO records are limited to P0xxx, P2xxx, P34xx, B0xxx, C0xxx and U0xxx. P34xx is accepted only when the exact identifier exists in the pinned source snapshot. Manufacturer-controlled ranges are limited to P1xxx, P30xx–P33xx, B1xxx–B2xxx, C1xxx–C2xxx and U1xxx–U2xxx. P35xx–P39xx, U3xxx, B3xxx and C3xxx are unresolved/reserved for this importer and are rejected from both normalized generic and manufacturer-specific namespaces. A manufacturer-controlled range does not prove VAG authorship, exact ECU fitment or repair applicability."
 ].join("\n");
 if(docs.includes(oldHeading))docs=docs.slice(0,docs.indexOf(oldHeading))+newSection+"\n";
 else if(!docs.includes("## DTC namespace code-range boundary (run87)"))throw new Error("run87 documentation anchor is missing");
 fs.writeFileSync(path.join(root,files.core),core,"utf8");
 fs.writeFileSync(path.join(root,files.tests),tests,"utf8");
 fs.writeFileSync(path.join(root,files.schema),JSON.stringify(schema,null,2)+"\n","utf8");
 fs.writeFileSync(path.join(root,files.oemSchema),JSON.stringify(oemSchema,null,2)+"\n","utf8");
 fs.writeFileSync(path.join(root,files.docs),docs,"utf8");
 return {status:"applied",files:Object.values(files),genericPattern:GENERIC_PATTERN,manufacturerPattern:MANUFACTURER_PATTERN,unresolvedPattern:UNRESOLVED_PATTERN};
}
const i=process.argv.indexOf("--desktop-root"),root=path.resolve(i>=0&&process.argv[i+1]?process.argv[i+1]:"desktop-source");
console.log(JSON.stringify(apply(root)));
