#!/usr/bin/env node
"use strict";
const fs = require("node:fs");
const path = require("node:path");

function fail(message) { throw new Error(message); }
function replaceExactly(source, before, after, label) {
  const count = source.split(before).length - 1;
  if (count === 0 && source.includes(after)) return source;
  if (count !== 1) fail(label + ": expected exactly one original block, found " + count);
  return source.replace(before, after);
}
function safeTarget(root, relative) {
  const target = path.resolve(root, relative), rel = path.relative(root, target);
  if (!rel || rel === ".." || rel.startsWith(".." + path.sep) || path.isAbsolute(rel)) fail("Target escaped desktop root: " + relative);
  return target;
}
function patch(desktopRoot) {
  const root = path.resolve(desktopRoot);
  if (!fs.statSync(root).isDirectory()) fail("Desktop source root is not a directory");
  const verifierPath = safeTarget(root, "scripts/verify-local-research-packs.cjs");
  const testPath = safeTarget(root, "tests/local-research-packs.test.cjs");
  const verifierOriginal = fs.readFileSync(verifierPath, "utf8");
  const testOriginal = fs.readFileSync(testPath, "utf8");
  const verifierNewline = verifierOriginal.includes("\r\n") ? "\r\n" : "\n";
  const testNewline = testOriginal.includes("\r\n") ? "\r\n" : "\n";
  let verifier = verifierOriginal.replace(/\r\n/g, "\n");
  let test = testOriginal.replace(/\r\n/g, "\n");

  verifier = replaceExactly(verifier,
    '  assert(manifest.schema_version === 1 && Array.isArray(manifest.packs) && manifest.packs.length === 11, "Expected eleven separately licensed research packs, including NL-only RDW approval research");\n  const packIds = manifest.packs.map((pack) => pack.id);\n  assert(packIds.every((id) => typeof id === "string" && id.length > 0) && new Set(packIds).size === packIds.length, "Research pack IDs must be non-empty and unique");\n  const byId = Object.fromEntries(manifest.packs.map((pack) => [pack.id, pack]));\n',
    '  assert(manifest.schema_version === 1 && Array.isArray(manifest.packs) && manifest.packs.length === 12, "Expected twelve separately licensed research packs, including DE-only KBA aggregate stock research");\n  const packIds = manifest.packs.map((pack) => pack.id);\n  assert(packIds.every((id) => typeof id === "string" && id.length > 0) && new Set(packIds).size === packIds.length, "Research pack IDs must be non-empty and unique");\n  const byId = Object.fromEntries(manifest.packs.map((pack) => [pack.id, pack]));\n',
    "KBA research pack manifest cardinality");

  verifier = replaceExactly(verifier,
    '  const astra = byId["astra-fedro-tas-type-approvals-open-data-ch"];\n  const rdw = byId["rdw-vag-nl-eu-type-approval-research"];\n  assert(wikidataGenerations, "Wikidata generation candidate pack must be registered");\n  assert(ob && vag && obdb && vehiclesdb && mechanicdb && wikidata && astra && rdw, "Required generic, candidate, CH-only and NL-only research packs must be registered");\n',
    '  const astra = byId["astra-fedro-tas-type-approvals-open-data-ch"];\n  const rdw = byId["rdw-vag-nl-eu-type-approval-research"];\n  const kbaDe = byId["kba-de-vag-stock-research"];\n  assert(wikidataGenerations, "Wikidata generation candidate pack must be registered");\n  assert(ob && vag && obdb && vehiclesdb && mechanicdb && wikidata && astra && rdw && kbaDe, "Required generic, candidate, CH-only, NL-only and DE-only research packs must be registered");\n',
    "KBA pack registration");

  verifier = replaceExactly(verifier,
    '  const rdwSummary = require(path.join(ROOT, "lib", "rdw-vag-research-db.cjs")).getRdwSummary(RESEARCH);\n  assert(wikidataGenerationSummary.counts.memberEntities === 109 && wikidataGenerationSummary.generationVerified === false, "Wikidata generation candidate runtime verification failed");\n',
    '  const rdwSummary = require(path.join(ROOT, "lib", "rdw-vag-research-db.cjs")).getRdwSummary(RESEARCH);\n  const kbaDeSummary = require(path.join(ROOT, "lib", "kba-de-stock-research-db.cjs")).getKbaSummary(RESEARCH);\n  assert(wikidataGenerationSummary.counts.memberEntities === 109 && wikidataGenerationSummary.generationVerified === false, "Wikidata generation candidate runtime verification failed");\n',
    "KBA runtime reader");

  verifier = replaceExactly(verifier,
    '  assert(rdwSummary.counts.approvalScopes === 96519 && rdwSummary.counts.registrationObservations === 102662 && rdwSummary.counts.engineDesignationCandidates === 93836 && rdwSummary.counts.gearboxClassifications === 93548 && rdwSummary.counts.sourceRows === 604785 && rdwSummary.sourceSnapshotSha256 === "896a34b9b8377f2ed20c34d7e0e33b4cf2ce1958e2cdd2b7326ee8c3157b0706" && rdwSummary.databaseSha256 === rdw.database_sha256 && rdwSummary.sourceManifestSha256 === rdw.source_manifest_sha256, "RDW snapshot, database or source manifest provenance/counts changed");\n',
    '  assert(rdwSummary.counts.approvalScopes === 96519 && rdwSummary.counts.registrationObservations === 102662 && rdwSummary.counts.engineDesignationCandidates === 93836 && rdwSummary.counts.gearboxClassifications === 93548 && rdwSummary.counts.sourceRows === 604785 && rdwSummary.sourceSnapshotSha256 === "896a34b9b8377f2ed20c34d7e0e33b4cf2ce1958e2cdd2b7326ee8c3157b0706" && rdwSummary.databaseSha256 === rdw.database_sha256 && rdwSummary.sourceManifestSha256 === rdw.source_manifest_sha256, "RDW snapshot, database or source manifest provenance/counts changed");\n  assert(kbaDeSummary.id === kbaDe.id && kbaDeSummary.marketScope === "DE" && kbaDeSummary.license === "DL-DE-BY-2.0" && kbaDeSummary.rightsStatus === "approved_by_published_DL_DE_BY_2_0" && kbaDeSummary.productionImport === false && kbaDeSummary.productImportAllowed === false && kbaDeSummary.ruEaeuApplicability === false && kbaDeSummary.exactVehicleFitment === false && kbaDeSummary.exactEngineGearboxPair === false && kbaDeSummary.repairApplicability === false && kbaDeSummary.diagnosticExecutionAllowed === false, "KBA pack must remain separately namespaced DE-only aggregate stock research, never vehicle fitment");\n  assert(kbaDeSummary.counts.vagStockObservations === 264847 && kbaDeSummary.counts.manufacturerLabels === 8 && kbaDeSummary.counts.uniqueMakeTradeNamePairs === 802 && kbaDeSummary.counts.uniqueMakeTypeKeyPairs === 4155 && kbaDeSummary.counts.uniqueMakeTradeTypeReferenceDateTuples === 16301 && kbaDeSummary.counts.federalStates === 17 && kbaDeSummary.counts.referenceDates === 4 && kbaDeSummary.sourceSnapshotSha256 === kbaDe.source_snapshot_sha256 && kbaDeSummary.databaseSha256 === kbaDe.database_sha256 && kbaDeSummary.sourceManifestSha256 === kbaDe.source_manifest_sha256, "KBA source snapshot, database, licence or research counts changed");\n',
    "KBA runtime rights/provenance/count verification");

  verifier = replaceExactly(verifier,
    '      rdw_nl_eu: {\n        marketScope: rdwSummary.marketScope,\n        approvalScopes: rdwSummary.counts.approvalScopes,\n        registrationObservations: rdwSummary.counts.registrationObservations,\n        engineDesignationCandidates: rdwSummary.counts.engineDesignationCandidates,\n        gearboxClassifications: rdwSummary.counts.gearboxClassifications,\n        sourceRows: rdwSummary.counts.sourceRows,\n        sourceFiles: rdwSummary.counts.sourceFiles,\n        productionImport: rdwSummary.productionImport,\n        ruEaeuApplicability: rdwSummary.ruEaeuApplicability,\n        exactVehicleFitment: rdwSummary.exactVehicleFitment,\n        exactEngineGearboxPair: rdwSummary.exactEngineGearboxPair,\n        repairApplicability: rdwSummary.repairApplicability,\n        diagnosticExecutionAllowed: rdwSummary.diagnosticExecutionAllowed,\n        sourceSnapshotSha256: rdwSummary.sourceSnapshotSha256,\n        sourceManifestSha256: rdwSummary.sourceManifestSha256,\n        databaseSha256: rdwSummary.databaseSha256,\n      },\n      production_fitment_rows_added: 0,\n',
    '      rdw_nl_eu: {\n        marketScope: rdwSummary.marketScope,\n        approvalScopes: rdwSummary.counts.approvalScopes,\n        registrationObservations: rdwSummary.counts.registrationObservations,\n        engineDesignationCandidates: rdwSummary.counts.engineDesignationCandidates,\n        gearboxClassifications: rdwSummary.counts.gearboxClassifications,\n        sourceRows: rdwSummary.counts.sourceRows,\n        sourceFiles: rdwSummary.counts.sourceFiles,\n        productionImport: rdwSummary.productionImport,\n        ruEaeuApplicability: rdwSummary.ruEaeuApplicability,\n        exactVehicleFitment: rdwSummary.exactVehicleFitment,\n        exactEngineGearboxPair: rdwSummary.exactEngineGearboxPair,\n        repairApplicability: rdwSummary.repairApplicability,\n        diagnosticExecutionAllowed: rdwSummary.diagnosticExecutionAllowed,\n        sourceSnapshotSha256: rdwSummary.sourceSnapshotSha256,\n        sourceManifestSha256: rdwSummary.sourceManifestSha256,\n        databaseSha256: rdwSummary.databaseSha256,\n      },\n      kba_de_vag_stock: {\n        marketScope: kbaDeSummary.marketScope,\n        vagStockObservations: kbaDeSummary.counts.vagStockObservations,\n        manufacturerLabels: kbaDeSummary.counts.manufacturerLabels,\n        uniqueMakeTradeNamePairs: kbaDeSummary.counts.uniqueMakeTradeNamePairs,\n        uniqueMakeTypeKeyPairs: kbaDeSummary.counts.uniqueMakeTypeKeyPairs,\n        uniqueMakeTradeTypeReferenceDateTuples: kbaDeSummary.counts.uniqueMakeTradeTypeReferenceDateTuples,\n        federalStates: kbaDeSummary.counts.federalStates,\n        referenceDates: kbaDeSummary.counts.referenceDates,\n        productionImport: kbaDeSummary.productionImport,\n        productImportAllowed: kbaDeSummary.productImportAllowed,\n        ruEaeuApplicability: kbaDeSummary.ruEaeuApplicability,\n        exactVehicleFitment: kbaDeSummary.exactVehicleFitment,\n        exactEngineGearboxPair: kbaDeSummary.exactEngineGearboxPair,\n        repairApplicability: kbaDeSummary.repairApplicability,\n        diagnosticExecutionAllowed: kbaDeSummary.diagnosticExecutionAllowed,\n        sourceSnapshotSha256: kbaDeSummary.sourceSnapshotSha256,\n        sourceManifestSha256: kbaDeSummary.sourceManifestSha256,\n        databaseSha256: kbaDeSummary.databaseSha256,\n      },\n      production_fitment_rows_added: 0,\n',
    "KBA verification report");

  test = replaceExactly(test,
    '  assert.match(result.rdw_nl_eu.sourceManifestSha256, /^[a-f0-9]{64}$/);\n  assert.match(result.rdw_nl_eu.databaseSha256, /^[a-f0-9]{64}$/);\n  assert.equal(result.mechanicdb_vag_dtc_candidates.displayStatus, "candidate_reference_visible_separate_namespace");\n',
    '  assert.match(result.rdw_nl_eu.sourceManifestSha256, /^[a-f0-9]{64}$/);\n  assert.match(result.rdw_nl_eu.databaseSha256, /^[a-f0-9]{64}$/);\n  assert.deepEqual(result.kba_de_vag_stock, {\n    marketScope: "DE", vagStockObservations: 264847, manufacturerLabels: 8,\n    uniqueMakeTradeNamePairs: 802, uniqueMakeTypeKeyPairs: 4155,\n    uniqueMakeTradeTypeReferenceDateTuples: 16301, federalStates: 17, referenceDates: 4,\n    productionImport: false, productImportAllowed: false, ruEaeuApplicability: false,\n    exactVehicleFitment: false, exactEngineGearboxPair: false, repairApplicability: false,\n    diagnosticExecutionAllowed: false,\n    sourceSnapshotSha256: result.kba_de_vag_stock.sourceSnapshotSha256,\n    sourceManifestSha256: result.kba_de_vag_stock.sourceManifestSha256,\n    databaseSha256: result.kba_de_vag_stock.databaseSha256\n  });\n  assert.match(result.kba_de_vag_stock.sourceSnapshotSha256, /^[a-f0-9]{64}$/);\n  assert.match(result.kba_de_vag_stock.sourceManifestSha256, /^[a-f0-9]{64}$/);\n  assert.match(result.kba_de_vag_stock.databaseSha256, /^[a-f0-9]{64}$/);\n  assert.equal(result.mechanicdb_vag_dtc_candidates.displayStatus, "candidate_reference_visible_separate_namespace");\n',
    "KBA verifier regression assertions");

  fs.writeFileSync(verifierPath, verifier.replace(/\n/g, verifierNewline), "utf8");
  fs.writeFileSync(testPath, test.replace(/\n/g, testNewline), "utf8");
  return { status: "patched", files: ["scripts/verify-local-research-packs.cjs","tests/local-research-packs.test.cjs"], manifestPackCount: 12 };
}
function main() {
  const index = process.argv.indexOf("--desktop-root");
  if (index < 0 || !process.argv[index + 1]) fail("Usage: node apply-kba-de-vag-research-verification-run1.cjs --desktop-root <desktop-source>");
  const result = patch(process.argv[index + 1]);
  process.stdout.write(JSON.stringify({ patch: "run1-kba-de-vag-stock-verification", ...result }) + "\n");
}
if (require.main === module) {
  try { main(); }
  catch (error) { console.error("KBA research verifier patch failed: " + error.message); process.exitCode = 1; }
}
module.exports = { patch };
