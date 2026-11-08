#!/usr/bin/env node
"use strict";
const fs=require("node:fs"),path=require("node:path");
const GENERIC_PATTERN="^(?:P0[0-9A-F]{3}|P2[0-9A-F]{3}|B0[0-9A-F]{3}|C0[0-9A-F]{3}|U0[0-9A-F]{3})$";
const MANUFACTURER_PATTERN="^(?:P1[0-9A-F]{3}|P3[0-3][0-9A-F]{2}|B[12][0-9A-F]{3}|C[12][0-9A-F]{3}|U[12][0-9A-F]{3})$";
const UNRESOLVED_PATTERN="^(?:P3[4-9][0-9A-F]{2}|U3[0-9A-F]{3}|B3[0-9A-F]{3}|C3[0-9A-F]{3})$";
function replaceOnce(s,a,b,label){const n=s.split(a).length-1;if(n!==1)throw new Error(label+": expected one patch anchor, found "+n);return s.replace(a,b);}
function read(root,rel){const f=path.join(root,rel);if(!fs.existsSync(f))throw new Error("run87 required file is missing: "+rel);return fs.readFileSync(f,"utf8");}
function ensureOemSchema(root,rel){const target=path.join(root,rel);if(fs.existsSync(target))return;const canonical=path.join(__dirname,rel);if(!fs.existsSync(canonical))throw new Error("canonical OEM DTC index schema is missing from repository: "+rel);fs.mkdirSync(path.dirname(target),{recursive:true});fs.copyFileSync(canonical,target);}
function apply(root){
 const files={core:"lib/local-core-db.cjs",tests:"tests/local-core-db.test.cjs",schema:"data/schemas/technical-record-payloads.schema.json",oemSchema:"data/schemas/oem-dtc-index.schema.json",docs:"docs/LOCAL_VEHICLE_CATALOG_IMPORT.md",policy:"data/policies/dtc-namespace-ranges.json",ui:"components/diagnostic-worksheet.tsx",uiTests:"tests/diagnostic-worksheet.test.cjs"};
 let core=read(root,files.core),tests=read(root,files.tests),docs=read(root,files.docs),ui=read(root,files.ui),uiTests=read(root,files.uiTests);
 const policy=JSON.parse(read(root,files.policy));
 if(policy.namespaces?.generic_sae_iso?.pattern!==GENERIC_PATTERN||policy.namespaces?.manufacturer_controlled?.pattern!==MANUFACTURER_PATTERN||policy.namespaces?.unresolved_reserved?.pattern!==UNRESOLVED_PATTERN)throw new Error("run87 machine-readable DTC policy differs from the pinned patch contract");
 const marker="// run87: quarantine unresolved/reserved DTC ranges";
 const schema=JSON.parse(read(root,files.schema));
 ensureOemSchema(root,files.oemSchema);
 const oemSchema=JSON.parse(read(root,files.oemSchema));
 if(core.includes(marker)){
  const patternsOk=core.includes("const GENERIC_OBD_DTC_CODE_RE = /"+GENERIC_PATTERN+"/;")&&core.includes("const MANUFACTURER_CONTROLLED_OBD_DTC_CODE_RE = /"+MANUFACTURER_PATTERN+"/;");
  const schemaOk=["code","dtc_code"].every(k=>schema.$defs?.dtc_generic?.properties?.[k]?.pattern===GENERIC_PATTERN&&schema.$defs?.dtc_vag_specific?.properties?.[k]?.pattern===MANUFACTURER_PATTERN);
  const oemRules=oemSchema.allOf||[];
  const oemOk=oemRules.every(r=>{const ns=r.if?.properties?.dtc_namespace?.const;const p=r.then?.properties?.dtc?.pattern;return ns==="generic_sae_iso"?p===GENERIC_PATTERN:(ns==="manufacturer_specific_vag"||ns==="manufacturer_specific_other")?p===MANUFACTURER_PATTERN:true;});
  if(!patternsOk||!schemaOk||!oemOk||!tests.includes("run87 quarantines unresolved/reserved DTC ranges from normalized namespaces")||!docs.includes("## DTC namespace code-range boundary (run87)")||!ui.includes("allocationUnverified")||!uiTests.includes("unverified mixed P3 and U3 allocations"))throw new Error("run87 marker exists but companion contracts are incomplete");
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
 '  const validPayload = { code: "P2ABC", title: "Generic SAE/ISO boundary fixture", namespace: "SAE/ISO" };',
 '  const valid = { ...genericDtc(), natural_key: "run87:generic:P2ABC", source_record_key: "run87:generic:P2ABC", title: "P2ABC", payload: validPayload, record_sha256: core.sha256(validPayload) };',
 '  const result = core.importPackage(dbPath, packageOf([valid], { package_id: "run87-generic-p34-valid" }));',
 '  assert.equal(result.inserted, 1);',
 '',
 '',
 '',
 '  for (const code of ["P3400", "P3497", "P34C8", "P3500", "P39AB", "U3ABC", "B3ABC", "C3ABC"]) {',
 '    const payload = { code, title: "Unresolved/reserved range", namespace: "SAE/ISO" };',
 '    const invalid = { ...valid, natural_key: "run87:generic:" + code, source_record_key: "run87:generic:" + code, title: code, payload, record_sha256: core.sha256(payload) };',
 '    assert.throws(() => core.importPackage(dbPath, packageOf([invalid], { package_id: "run87-generic-invalid-" + code })), /outside generic SAE\\/ISO OBD-II ranges/);',
 '  }',
 '  for (const code of ["P3400", "P3497", "P34C8", "P3500", "P39AB", "U3ABC", "B3ABC", "C3ABC"]) {',
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
 if(!ui.includes("allocationUnverified")){
  ui=replaceOnce(ui,'      {dtcResults.map((row) => <article className="diagnostic-dtc-result" key={`${row.code}-${row.sourceRecordSha256}`}>','      {dtcResults.map((row) => {\n        const allocationUnverified = /^(?:P3[4-9]|U3|B3|C3)/.test(row.code.toUpperCase());\n        return <article className="diagnostic-dtc-result" key={`${row.code}-${row.sourceRecordSha256}`}>',"DTC UI map");
  ui=replaceOnce(ui,'<small>GENERIC SAE/ISO · {row.category || "без категории"}</small>','<small>{allocationUnverified ? "КЛАССИФИКАЦИЯ НЕ ПРОВЕРЕНА" : "GENERIC SAE/ISO"} · {row.category || "без категории"}</small>',"DTC UI label");
  ui=replaceOnce(ui,'<span>RESEARCH ONLY</span>','<span>{allocationUnverified ? "UNVERIFIED" : "RESEARCH ONLY"}</span>',"DTC UI badge");
  ui=replaceOnce(ui,'<div className="diagnostic-dtc-warning">Не VAG-specific. Не подтверждает наличие неисправности в выбранном автомобиле, конкретном ECU или применимость тест-плана. Не является указанием на замену детали.</div>','{allocationUnverified ? <div className="diagnostic-dtc-warning">Источник OBDex помечает запись как общий код, но точная классификация диапазона по актуальному SAE J2012DA не подтверждена. Запись остаётся исследовательской и не считается нормализованным generic или VAG-specific DTC.</div> : <div className="diagnostic-dtc-warning">Не VAG-specific. Не подтверждает наличие неисправности в выбранном автомобиле, конкретном ECU или применимость тест-плана. Не является указанием на замену детали.</div>}',"DTC UI warning");
  ui=replaceOnce(ui,'generic_sae_iso_obd2 · fitment claim: {String(row.fitmentClaim)}','source namespace: {row.namespace} · upstream label: generic_sae_iso_obd2 · normalized namespace: {allocationUnverified ? "unknown/quarantined" : "generic_sae_iso"} · fitment claim: {String(row.fitmentClaim)}',"DTC UI provenance");
  ui=replaceOnce(ui,'      </article>)}','      </article>})}',"DTC UI map close");
 }
 const uiTest='\ntest("unverified mixed P3 and U3 allocations are visibly quarantined in generic research results", () => {\n  assert.match(component, /allocationUnverified/);\n  assert.match(component, /P3\\[4-9\\]/);\n  assert.match(component, /U3/);\n  assert.match(component, /КЛАССИФИКАЦИЯ НЕ ПРОВЕРЕНА/);\n  assert.match(component, /unknown\\/quarantined/);\n  assert.match(component, /SAE J2012DA/);\n});\n';
 if(!uiTests.includes("unverified mixed P3 and U3 allocations"))uiTests+=uiTest;
 const oldHeading="## DTC namespace code-range boundary (run86)";
 const newSection=[
 "## DTC namespace code-range boundary (run87)",
 "",
 "The importer uses the machine-readable policy in `data/policies/dtc-namespace-ranges.json`. Generic SAE/ISO records are limited to P0xxx, P2xxx, B0xxx, C0xxx and U0xxx. The P3xxx family is mixed: P30xx-P33xx are manufacturer-controlled, while P34xx-P39xx remain unresolved/quarantined until exact current SAE J2012/J2012DA assignments are independently verified. The current licensed J2012DA_202607 annex has not been acquired. Upstream OBDex labels 155 P34xx rows generic, but that CC0 data label does not establish current standards allocation; all P34xx rows stay in the isolated research pack and are rejected from normalized generic and VAG-specific namespaces. U3xxx, B3xxx and C3xxx remain quarantined as well. A manufacturer-controlled range never proves VAG authorship, ECU fitment or repair applicability."
 ].join("\n");
 if(docs.includes(oldHeading))docs=docs.slice(0,docs.indexOf(oldHeading))+newSection+"\n";
 else if(!docs.includes("## DTC namespace code-range boundary (run87)"))throw new Error("run87 documentation anchor is missing");
 fs.writeFileSync(path.join(root,files.core),core,"utf8");
 fs.writeFileSync(path.join(root,files.tests),tests,"utf8");
 fs.writeFileSync(path.join(root,files.schema),JSON.stringify(schema,null,2)+"\n","utf8");
 fs.writeFileSync(path.join(root,files.oemSchema),JSON.stringify(oemSchema,null,2)+"\n","utf8");
 fs.writeFileSync(path.join(root,files.docs),docs,"utf8");
 fs.writeFileSync(path.join(root,files.ui),ui,"utf8");
 fs.writeFileSync(path.join(root,files.uiTests),uiTests,"utf8");
 return {status:"applied",files:Object.values(files),genericPattern:GENERIC_PATTERN,manufacturerPattern:MANUFACTURER_PATTERN,unresolvedPattern:UNRESOLVED_PATTERN};
}
const i=process.argv.indexOf("--desktop-root"),root=path.resolve(i>=0&&process.argv[i+1]?process.argv[i+1]:"desktop-source");
console.log(JSON.stringify(apply(root)));
