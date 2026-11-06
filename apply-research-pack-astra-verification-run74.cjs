#!/usr/bin/env node
"use strict";

const fs = require("node:fs");
const path = require("node:path");

function argument(name) {
  const index = process.argv.indexOf(name);
  return index >= 0 ? process.argv[index + 1] : null;
}
function replaceExactly(source, before, after, label) {
  const count = source.split(before).length - 1;
  if (count === 0 && source.includes(after)) return source;
  if (count !== 1) throw new Error(label + ": expected exactly one original block, found " + count);
  return source.replace(before, after);
}
function safeTarget(root, relative) {
  const target = path.resolve(root, relative);
  const rel = path.relative(root, target);
  if (!rel || rel === ".." || rel.startsWith(".." + path.sep) || path.isAbsolute(rel)) {
    throw new Error("Target escaped desktop root: " + relative);
  }
  return target;
}

function main() {
  const desktopRootArg = argument("--desktop-root");
  if (!desktopRootArg) throw new Error("Usage: node apply-research-pack-astra-verification-run74.cjs --desktop-root <desktop-source>");
  const desktopRoot = path.resolve(desktopRootArg);
  if (!fs.statSync(desktopRoot).isDirectory()) throw new Error("Desktop source root is not a directory");

  const verifierPath = safeTarget(desktopRoot, "scripts/verify-local-research-packs.cjs");
  const testPath = safeTarget(desktopRoot, "tests/local-research-packs.test.cjs");
  const verifierOriginal = fs.readFileSync(verifierPath, "utf8");
  const testOriginal = fs.readFileSync(testPath, "utf8");
  const verifierNewline = verifierOriginal.includes("\r\n") ? "\r\n" : "\n";
  const testNewline = testOriginal.includes("\r\n") ? "\r\n" : "\n";
  let verifier = verifierOriginal.replace(/\r\n/g, "\n");
  let test = testOriginal.replace(/\r\n/g, "\n");

  verifier = replaceExactly(verifier,
    '  assert(manifest.schema_version === 1 && Array.isArray(manifest.packs) && manifest.packs.length === 9, "Expected nine separately licensed research packs (AutoDiag2 is verified separately)");\n  const byId = Object.fromEntries(manifest.packs.map((pack) => [pack.id, pack]));\n',
    '  assert(manifest.schema_version === 1 && Array.isArray(manifest.packs) && manifest.packs.length === 10, "Expected ten registered research packs, including the CH-only ASTRA and AutoDiag2 packs");\n  const packIds = manifest.packs.map((pack) => pack.id);\n  assert(packIds.every((id) => typeof id === "string" && id.length > 0) && new Set(packIds).size === packIds.length, "Research pack IDs must be non-empty and unique");\n  const byId = Object.fromEntries(manifest.packs.map((pack) => [pack.id, pack]));\n',
    "research pack manifest cardinality/uniqueness");

  verifier = replaceExactly(verifier,
    '  const wikidata = byId["wikidata-vag-model-taxonomy-cc0"];\n  const wikidataGenerations = byId["wikidata-vag-generation-candidates-cc0"];\n  assert(wikidataGenerations, "Wikidata generation candidate pack must be registered");\n  assert(ob && vag && obdb && vehiclesdb && mechanicdb && wikidata, "All six research packs must be registered");\n',
    '  const wikidata = byId["wikidata-vag-model-taxonomy-cc0"];\n  const wikidataGenerations = byId["wikidata-vag-generation-candidates-cc0"];\n  const astra = byId["astra-fedro-tas-type-approvals-open-data-ch"];\n  assert(wikidataGenerations, "Wikidata generation candidate pack must be registered");\n  assert(ob && vag && obdb && vehiclesdb && mechanicdb && wikidata && astra, "Required generic, candidate and CH-only research packs must be registered");\n',
    "ASTRA pack registration");

  verifier = replaceExactly(verifier,
    '  const wikidataGenerationSummary = localResearch.getWikidataGenerationSummary(RESEARCH);\n  assert(wikidataGenerationSummary.counts.memberEntities === 109 && wikidataGenerationSummary.generationVerified === false, "Wikidata generation candidate runtime verification failed");\n  assert(wikidataSummary && wikidataSummary.counts?.models === 521 && wikidataSummary.counts?.russianLabels === 285 && wikidataSummary.marketScope === "UNKNOWN" && wikidataSummary.fitmentClaim === false, "Wikidata runtime pack verification failed");\n',
    '  const wikidataGenerationSummary = localResearch.getWikidataGenerationSummary(RESEARCH);\n  const astraSummary = require(path.join(ROOT, "lib", "astra-ch-tas-db.cjs")).getAstraSummary(RESEARCH);\n  assert(wikidataGenerationSummary.counts.memberEntities === 109 && wikidataGenerationSummary.generationVerified === false, "Wikidata generation candidate runtime verification failed");\n  assert(wikidataSummary && wikidataSummary.counts?.models === 521 && wikidataSummary.counts?.russianLabels === 285 && wikidataSummary.marketScope === "UNKNOWN" && wikidataSummary.fitmentClaim === false, "Wikidata runtime pack verification failed");\n  assert(astraSummary.id === astra.id && astraSummary.marketScope === "CH" && astraSummary.productionImport === false && astraSummary.ruEaeuApplicability === false && astraSummary.exactVehicleFitment === false && astraSummary.repairApplicability === false && astraSummary.diagnosticExecutionAllowed === false, "ASTRA pack must remain separately namespaced CH-only homologation research, never production fitment");\n  assert(astraSummary.counts.approvals === 45215 && astraSummary.counts.emissionsGearboxRows === 53414 && astraSummary.counts.linkedScopeRows === 33909 && astraSummary.counts.exactScopeLinks === 5420 && astraSummary.counts.wildcardScopeLinks === 28489 && astraSummary.counts.unlinkedScopeRows === 19505, "ASTRA source snapshot counts or exact/wildcard applicability boundaries changed");\n',
    "ASTRA runtime rights/provenance/count verification");

  verifier = replaceExactly(verifier,
    '      wikidata_vag_taxonomy: wikidataSummary.counts,\n      wikidata_vag_generation_candidates: wikidataGenerationSummary.counts,\n      production_fitment_rows_added: 0,\n',
    '      wikidata_vag_taxonomy: wikidataSummary.counts,\n      wikidata_vag_generation_candidates: wikidataGenerationSummary.counts,\n      astra_ch_tas: {\n        marketScope: astraSummary.marketScope,\n        approvals: astraSummary.counts.approvals,\n        emissionsGearboxRows: astraSummary.counts.emissionsGearboxRows,\n        linkedScopeRows: astraSummary.counts.linkedScopeRows,\n        exactScopeLinks: astraSummary.counts.exactScopeLinks,\n        wildcardScopeLinks: astraSummary.counts.wildcardScopeLinks,\n        unlinkedScopeRows: astraSummary.counts.unlinkedScopeRows,\n        productionImport: astraSummary.productionImport,\n        ruEaeuApplicability: astraSummary.ruEaeuApplicability,\n        exactVehicleFitment: astraSummary.exactVehicleFitment,\n        repairApplicability: astraSummary.repairApplicability,\n        diagnosticExecutionAllowed: astraSummary.diagnosticExecutionAllowed,\n        databaseSha256: astraSummary.databaseSha256,\n      },\n      production_fitment_rows_added: 0,\n',
    "ASTRA verification report");

  test = replaceExactly(test,
    '  assert.deepEqual(result.wikidata_vag_generation_candidates, { memberEntities: 109, modelMemberLinks: 125, sourceBindings: 187, modelsWithMembers: 32, manufacturers: 6, russianLabels: 83, dateStatements: 155 });\n  assert.equal(result.mechanicdb_vag_dtc_candidates.displayStatus, "candidate_reference_visible_separate_namespace");\n',
    '  assert.deepEqual(result.wikidata_vag_generation_candidates, { memberEntities: 109, modelMemberLinks: 125, sourceBindings: 187, modelsWithMembers: 32, manufacturers: 6, russianLabels: 83, dateStatements: 155 });\n  assert.deepEqual(result.astra_ch_tas, {\n    marketScope: "CH",\n    approvals: 45215,\n    emissionsGearboxRows: 53414,\n    linkedScopeRows: 33909,\n    exactScopeLinks: 5420,\n    wildcardScopeLinks: 28489,\n    unlinkedScopeRows: 19505,\n    productionImport: false,\n    ruEaeuApplicability: false,\n    exactVehicleFitment: false,\n    repairApplicability: false,\n    diagnosticExecutionAllowed: false,\n    databaseSha256: "161800c884f6cdcc3b52c8cc87df51a2d853e7cbc640dea18847f40c0576b7f5"\n  });\n  assert.equal(result.mechanicdb_vag_dtc_candidates.displayStatus, "candidate_reference_visible_separate_namespace");\n',
    "ASTRA regression assertions");

  fs.writeFileSync(verifierPath, verifier.replace(/\n/g, verifierNewline), "utf8");
  fs.writeFileSync(testPath, test.replace(/\n/g, testNewline), "utf8");
  console.log(JSON.stringify({ status: "patched", patch: "run74-astra-ch-research-pack-verification", manifestPackCount: 10, astraPackId: "astra-fedro-tas-type-approvals-open-data-ch", files: ["scripts/verify-local-research-packs.cjs", "tests/local-research-packs.test.cjs"] }));
}

try { main(); }
catch (error) { console.error("Run74 ASTRA research-pack verifier patch failed: " + error.message); process.exitCode = 1; }
