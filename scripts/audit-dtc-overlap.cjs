#!/usr/bin/env node
"use strict";
const GENERIC_DTC_CODE_RE = /^(?:P0[0-9A-F]{3}|P2[0-9A-F]{3}|P34[0-9A-F]{2}|B0[0-9A-F]{3}|C0[0-9A-F]{3}|U0[0-9A-F]{3})$/;
const MANUFACTURER_DTC_CODE_RE = /^(?:P1[0-9A-F]{3}|P3[0-3][0-9A-F]{2}|B[12][0-9A-F]{3}|C[12][0-9A-F]{3}|U[12][0-9A-F]{3})$/;
const VAG_MANUFACTURERS = new Set(["VOLKSWAGEN","AUDI","SKODA","SEAT","CUPRA"]);
function normalizeCode(value) { return typeof value === "string" ? value.trim().toUpperCase() : ""; }
function classifyDtcCode(value) {
  const code = normalizeCode(value);
  if (!/^[PBCU][0-9A-F]{4}$/.test(code)) return "unknown";
  if (GENERIC_DTC_CODE_RE.test(code)) return "generic_sae_iso";
  if (MANUFACTURER_DTC_CODE_RE.test(code)) return "manufacturer_controlled";
  return "unknown";
}
function canonicalNamespace(value) {
  if (value === "generic_sae_iso" || value === "generic_sae_iso_obd2") return "generic_sae_iso";
  if (value === "manufacturer_specific_vag" || value === "vag_oem_specific") return "manufacturer_specific_vag";
  if (value === "manufacturer_specific_other") return "manufacturer_specific_other";
  return "unknown";
}
function auditDtcRows(rows) {
  if (!Array.isArray(rows)) throw new TypeError("DTC rows must be an array");
  const violations = [], codeNamespaces = new Map();
  const counts = { generic_sae_iso: 0, manufacturer_specific_vag: 0, manufacturer_specific_other: 0, unknown: 0 };
  for (const [index, row] of rows.entries()) {
    if (!row || typeof row !== "object" || Array.isArray(row)) { violations.push({index,reason:"row must be an object"}); continue; }
    const code = normalizeCode(row.dtc_code ?? row.code);
    const namespace = canonicalNamespace(row.dtc_namespace ?? row.namespace);
    const manufacturer = typeof row.manufacturer === "string" ? row.manufacturer.trim().toUpperCase() : "UNKNOWN";
    const classification = classifyDtcCode(code);
    counts[namespace] += 1;
    if (namespace === "generic_sae_iso") {
      if (classification !== "generic_sae_iso") violations.push({index,code,namespace,reason:"generic namespace contains a manufacturer-controlled, reserved or malformed code"});
      if (manufacturer !== "UNKNOWN") violations.push({index,code,namespace,reason:"generic namespace must use UNKNOWN manufacturer"});
    } else if (namespace === "manufacturer_specific_vag") {
      if (classification !== "manufacturer_controlled") violations.push({index,code,namespace,reason:"VAG-specific namespace contains a generic, reserved or malformed code"});
      if (!VAG_MANUFACTURERS.has(manufacturer)) violations.push({index,code,namespace,reason:"VAG-specific namespace requires a VAG Group manufacturer"});
    } else if (namespace === "manufacturer_specific_other") {
      if (classification !== "manufacturer_controlled") violations.push({index,code,namespace,reason:"other-OEM namespace contains a generic, reserved or malformed code"});
      if (manufacturer !== "OTHER") violations.push({index,code,namespace,reason:"other-OEM namespace must use OTHER manufacturer"});
    }
    if (code && namespace !== "unknown") {
      const seen = codeNamespaces.get(code) || new Set(); seen.add(namespace); codeNamespaces.set(code,seen);
    }
  }
  const overlaps = [...codeNamespaces.entries()].filter(([,ns]) => ns.has("generic_sae_iso") && (ns.has("manufacturer_specific_vag") || ns.has("manufacturer_specific_other"))).map(([code])=>code).sort();
  for (const code of overlaps) violations.push({code,reason:"same DTC identifier appears in generic and manufacturer-specific namespaces"});
  return {status:violations.length?"failed":"passed",row_count:rows.length,counts,cross_namespace_overlap_count:overlaps.length,cross_namespace_overlaps:overlaps,violations};
}
module.exports={GENERIC_DTC_CODE_RE,MANUFACTURER_DTC_CODE_RE,classifyDtcCode,auditDtcRows};
if(require.main===module){
  const fs=require("node:fs"),input=process.argv[2];
  if(!input){process.stderr.write("Usage: node scripts/audit-dtc-overlap.cjs <dtc-records.json>\n");process.exitCode=2;}
  else{const result=auditDtcRows(JSON.parse(fs.readFileSync(input,"utf8")));process.stdout.write(JSON.stringify(result,null,2)+"\n");if(result.status!=="passed")process.exitCode=1;}
}
