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

  const packCountMatches = [...verifier.matchAll(/manifest\.packs\.length === (\d+)/g)];
  if (packCountMatches.length !== 1) fail("KBA research pack manifest cardinality: expected exactly one numeric pack-count assertion, found " + packCountMatches.length);
  const currentPackCount = Number(packCountMatches[0][1]);
  let expectedPackCount = currentPackCount;
  if (!verifier.includes("kbaDeSummary.id === kbaDe.id")) {
    if (!Number.isSafeInteger(currentPackCount) || currentPackCount < 12 || currentPackCount > 30) fail("KBA research pack manifest cardinality: unexpected pre-KBA pack count " + currentPackCount);
    expectedPackCount = currentPackCount + 1;
    const messageMatch = verifier.match(/"Expected [^"]*research packs[^"]*"/);
    if (!messageMatch) fail("KBA research pack manifest cardinality: assertion message anchor missing");
    verifier = verifier.replace(/manifest\.packs\.length === \d+/, "manifest.packs.length === " + expectedPackCount);
    verifier = verifier.replace(messageMatch[0], '"Expected ' + expectedPackCount + ' separately licensed research packs, including the DE-only KBA VAG stock research pack"');
  }

  const rdwBinding = '  const rdw = byId["rdw-vag-nl-eu-type-approval-research"];';
  const kbaBinding = '  const kbaDe = byId["kba-de-vag-stock-research"];';
  if (!verifier.includes(kbaBinding)) {
    if (!verifier.includes(rdwBinding)) fail("KBA pack registration: RDW binding must exist before KBA");
    verifier = replaceExactly(verifier, rdwBinding, rdwBinding + "\n" + kbaBinding, "KBA pack binding");
  }
  const requiredPackAssert = verifier.split("\n").find((line) => line.includes("assert(ob && vag && obdb && vehiclesdb && mechanicdb && wikidata && astra") && line.includes("rdw"));
  if (!requiredPackAssert) fail("KBA pack registration: required research-pack assertion anchor missing");
  if (!requiredPackAssert.includes("kbaDe")) {
    const updatedPackAssert = requiredPackAssert.replace(/&& rdw,/, "&& rdw && kbaDe,");
    if (updatedPackAssert === requiredPackAssert) fail("KBA pack registration: could not extend required-pack assertion");
    verifier = replaceExactly(verifier, requiredPackAssert, updatedPackAssert, "KBA required-pack assertion");
  }

  const rdwCountAssertion = '  assert(rdwSummary.counts.approvalScopes === 96519 && rdwSummary.counts.registrationObservations === 102662 && rdwSummary.counts.engineDesignationCandidates === 93836 && rdwSummary.counts.gearboxClassifications === 93548 && rdwSummary.counts.sourceRows === 604785 && rdwSummary.sourceSnapshotSha256 === "896a34b9b8377f2ed20c34d7e0e33b4cf2ce1958e2cdd2b7326ee8c3157b0706" && rdwSummary.databaseSha256 === rdw.database_sha256 && rdwSummary.sourceManifestSha256 === rdw.source_manifest_sha256, "RDW snapshot, database or source manifest provenance/counts changed");';
  const kbaReader = '  const kbaDeSummary = require(path.join(ROOT, "lib", "kba-de-stock-research-db.cjs")).getKbaSummary(RESEARCH);';
  const kbaAssertions = [
    '  assert(kbaDeSummary.id === kbaDe.id && kbaDeSummary.marketScope === "DE" && kbaDeSummary.license === "DL-DE-BY-2.0" && kbaDeSummary.rightsStatus === "approved_by_published_DL_DE_BY_2_0" && kbaDeSummary.researchPackIngested === true && kbaDeSummary.productDatabaseIngested === false && kbaDeSummary.productionImport === false && kbaDeSummary.productImportAllowed === false && kbaDeSummary.ruEaeuApplicability === false && kbaDeSummary.exactVehicleFitment === false && kbaDeSummary.exactEngineGearboxPair === false && kbaDeSummary.repairApplicability === false && kbaDeSummary.diagnosticExecutionAllowed === false, "KBA pack must remain separately namespaced DE-only aggregate stock research, never vehicle fitment");',
    '  assert(kbaDeSummary.counts.vagStockObservations === 264847 && kbaDeSummary.counts.manufacturerLabels === 8 && kbaDeSummary.counts.uniqueMakeTradeNamePairs === 802 && kbaDeSummary.counts.uniqueMakeTypeKeyPairs === 4155 && kbaDeSummary.counts.uniqueMakeTradeTypeReferenceDateTuples === 16301 && kbaDeSummary.counts.federalStates === 17 && kbaDeSummary.counts.referenceDates === 4 && kbaDeSummary.sourceSnapshotSha256 === kbaDe.source_snapshot_sha256 && kbaDeSummary.databaseSha256 === kbaDe.database_sha256 && kbaDeSummary.sourceManifestSha256 === kbaDe.source_manifest_sha256, "KBA source snapshot, database, licence or research counts changed");'
  ].join("\n");
  verifier = replaceExactly(verifier, rdwCountAssertion, rdwCountAssertion + "\n" + kbaReader + "\n" + kbaAssertions, "KBA runtime reader/rights/provenance/count verification");

  verifier = replaceExactly(verifier,
    '      rdw_nl_eu: {\n        marketScope: rdwSummary.marketScope,\n        approvalScopes: rdwSummary.counts.approvalScopes,\n        registrationObservations: rdwSummary.counts.registrationObservations,\n        engineDesignationCandidates: rdwSummary.counts.engineDesignationCandidates,\n        gearboxClassifications: rdwSummary.counts.gearboxClassifications,\n        sourceRows: rdwSummary.counts.sourceRows,\n        sourceFiles: rdwSummary.counts.sourceFiles,\n        productionImport: rdwSummary.productionImport,\n        ruEaeuApplicability: rdwSummary.ruEaeuApplicability,\n        exactVehicleFitment: rdwSummary.exactVehicleFitment,\n        exactEngineGearboxPair: rdwSummary.exactEngineGearboxPair,\n        repairApplicability: rdwSummary.repairApplicability,\n        diagnosticExecutionAllowed: rdwSummary.diagnosticExecutionAllowed,\n        sourceSnapshotSha256: rdwSummary.sourceSnapshotSha256,\n        sourceManifestSha256: rdwSummary.sourceManifestSha256,\n        databaseSha256: rdwSummary.databaseSha256,\n      },\n      production_fitment_rows_added: 0,\n',
    '      rdw_nl_eu: {\n        marketScope: rdwSummary.marketScope,\n        approvalScopes: rdwSummary.counts.approvalScopes,\n        registrationObservations: rdwSummary.counts.registrationObservations,\n        engineDesignationCandidates: rdwSummary.counts.engineDesignationCandidates,\n        gearboxClassifications: rdwSummary.counts.gearboxClassifications,\n        sourceRows: rdwSummary.counts.sourceRows,\n        sourceFiles: rdwSummary.counts.sourceFiles,\n        productionImport: rdwSummary.productionImport,\n        ruEaeuApplicability: rdwSummary.ruEaeuApplicability,\n        exactVehicleFitment: rdwSummary.exactVehicleFitment,\n        exactEngineGearboxPair: rdwSummary.exactEngineGearboxPair,\n        repairApplicability: rdwSummary.repairApplicability,\n        diagnosticExecutionAllowed: rdwSummary.diagnosticExecutionAllowed,\n        sourceSnapshotSha256: rdwSummary.sourceSnapshotSha256,\n        sourceManifestSha256: rdwSummary.sourceManifestSha256,\n        databaseSha256: rdwSummary.databaseSha256,\n      },\n      kba_de_vag_stock: {\n        marketScope: kbaDeSummary.marketScope,\n        vagStockObservations: kbaDeSummary.counts.vagStockObservations,\n        manufacturerLabels: kbaDeSummary.counts.manufacturerLabels,\n        uniqueMakeTradeNamePairs: kbaDeSummary.counts.uniqueMakeTradeNamePairs,\n        uniqueMakeTypeKeyPairs: kbaDeSummary.counts.uniqueMakeTypeKeyPairs,\n        uniqueMakeTradeTypeReferenceDateTuples: kbaDeSummary.counts.uniqueMakeTradeTypeReferenceDateTuples,\n        federalStates: kbaDeSummary.counts.federalStates,\n        referenceDates: kbaDeSummary.counts.referenceDates,\n        researchPackIngested: kbaDeSummary.researchPackIngested,\n        productDatabaseIngested: kbaDeSummary.productDatabaseIngested,\n        productionImport: kbaDeSummary.productionImport,\n        productImportAllowed: kbaDeSummary.productImportAllowed,\n        ruEaeuApplicability: kbaDeSummary.ruEaeuApplicability,\n        exactVehicleFitment: kbaDeSummary.exactVehicleFitment,\n        exactEngineGearboxPair: kbaDeSummary.exactEngineGearboxPair,\n        repairApplicability: kbaDeSummary.repairApplicability,\n        diagnosticExecutionAllowed: kbaDeSummary.diagnosticExecutionAllowed,\n        sourceSnapshotSha256: kbaDeSummary.sourceSnapshotSha256,\n        sourceManifestSha256: kbaDeSummary.sourceManifestSha256,\n        databaseSha256: kbaDeSummary.databaseSha256,\n      },\n      production_fitment_rows_added: 0,\n',
    "KBA verification report");

  test = replaceExactly(test,
    '  assert.match(result.rdw_nl_eu.sourceManifestSha256, /^[a-f0-9]{64}$/);\n  assert.match(result.rdw_nl_eu.databaseSha256, /^[a-f0-9]{64}$/);\n  assert.equal(result.mechanicdb_vag_dtc_candidates.displayStatus, "candidate_reference_visible_separate_namespace");\n',
    '  assert.match(result.rdw_nl_eu.sourceManifestSha256, /^[a-f0-9]{64}$/);\n  assert.match(result.rdw_nl_eu.databaseSha256, /^[a-f0-9]{64}$/);\n  assert.deepEqual(result.kba_de_vag_stock, {\n    marketScope: "DE", vagStockObservations: 264847, manufacturerLabels: 8,\n    uniqueMakeTradeNamePairs: 802, uniqueMakeTypeKeyPairs: 4155,\n    uniqueMakeTradeTypeReferenceDateTuples: 16301, federalStates: 17, referenceDates: 4,\n    researchPackIngested: true, productDatabaseIngested: false,\n    productionImport: false, productImportAllowed: false, ruEaeuApplicability: false,\n    exactVehicleFitment: false, exactEngineGearboxPair: false, repairApplicability: false,\n    diagnosticExecutionAllowed: false,\n    sourceSnapshotSha256: result.kba_de_vag_stock.sourceSnapshotSha256,\n    sourceManifestSha256: result.kba_de_vag_stock.sourceManifestSha256,\n    databaseSha256: result.kba_de_vag_stock.databaseSha256\n  });\n  assert.match(result.kba_de_vag_stock.sourceSnapshotSha256, /^[a-f0-9]{64}$/);\n  assert.match(result.kba_de_vag_stock.sourceManifestSha256, /^[a-f0-9]{64}$/);\n  assert.match(result.kba_de_vag_stock.databaseSha256, /^[a-f0-9]{64}$/);\n  assert.equal(result.mechanicdb_vag_dtc_candidates.displayStatus, "candidate_reference_visible_separate_namespace");\n',
    "KBA verifier regression assertions");

  fs.writeFileSync(verifierPath, verifier.replace(/\n/g, verifierNewline), "utf8");
  fs.writeFileSync(testPath, test.replace(/\n/g, testNewline), "utf8");
  return { status: "patched", files: ["scripts/verify-local-research-packs.cjs","tests/local-research-packs.test.cjs"], manifestPackCount: expectedPackCount };
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
