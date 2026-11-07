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
  const target = path.resolve(root, relative), rel = path.relative(root, target);
  if (!rel || rel === ".." || rel.startsWith(".." + path.sep) || path.isAbsolute(rel)) throw new Error("Target escaped desktop root: " + relative);
  return target;
}
function main() {
  const desktopRootArg = argument("--desktop-root");
  if (!desktopRootArg) throw new Error("Usage: node apply-rdw-vag-research-verification-run31.cjs --desktop-root <desktop-source>");
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

  if (!verifier.includes("astraTargaSummary")) throw new Error("TARGA-enhanced verifier must be applied before the RDW verifier patch.");
  const packCountMatches = [...verifier.matchAll(/manifest\.packs\.length === (\d+)/g)];
  if (packCountMatches.length !== 1) throw new Error("RDW research pack manifest cardinality: expected exactly one numeric pack-count assertion, found " + packCountMatches.length);
  const currentPackCount = Number(packCountMatches[0][1]);
  let expectedPackCount = currentPackCount;
  if (!verifier.includes('rdwSummary.id === rdw.id')) {
    if (!Number.isSafeInteger(currentPackCount) || currentPackCount < 11 || currentPackCount > 30) throw new Error("RDW research pack manifest cardinality: unexpected pre-RDW pack count " + currentPackCount);
    expectedPackCount = currentPackCount + 1;
    const messageMatch = verifier.match(/"Expected [^"]*research packs[^"]*"/);
    if (!messageMatch) throw new Error("RDW research pack manifest cardinality: assertion message anchor missing");
    verifier = verifier.replace(/manifest\.packs\.length === \d+/, "manifest.packs.length === " + expectedPackCount);
    verifier = verifier.replace(messageMatch[0], '"Expected ' + expectedPackCount + ' separately licensed research packs, including the NL-only RDW approval research pack"');
  }

  const astraBinding = '  const astra = byId["astra-fedro-tas-type-approvals-open-data-ch"];';
  const targaBinding = '  const targa = byId["astra-fedro-targa-emissionen-approval-variants-ch"];';
  const rdwBinding = '  const rdw = byId["rdw-vag-nl-eu-type-approval-research"];';
  if (!verifier.includes(rdwBinding)) {
    if (!verifier.includes(astraBinding)) throw new Error("RDW pack registration: ASTRA TAS binding anchor missing");
    if (!verifier.includes(targaBinding)) verifier = replaceExactly(verifier, astraBinding, astraBinding + "\n" + targaBinding, "RDW TARGA binding");
    const insertionAnchor = verifier.includes(targaBinding) ? targaBinding : astraBinding;
    verifier = replaceExactly(verifier, insertionAnchor, insertionAnchor + "\n" + rdwBinding, "RDW pack binding");
  }
  const requiredPackAssert = verifier.split("\n").find((line) => line.includes("assert(ob && vag && obdb && vehiclesdb && mechanicdb && wikidata && astra"));
  if (!requiredPackAssert) throw new Error("RDW pack registration: required research-pack assertion anchor missing");
  if (!requiredPackAssert.includes("rdw")) {
    const updatedPackAssert = requiredPackAssert.replace(/&& astra(?: && targa)?/, "&& astra && targa && rdw");
    if (updatedPackAssert === requiredPackAssert) throw new Error("RDW pack registration: could not extend required-pack assertion");
    verifier = replaceExactly(verifier, requiredPackAssert, updatedPackAssert, "RDW required-pack assertion");
  }

  const targaAssertion = '  assert(astraTargaSummary.id === "astra-fedro-targa-emissionen-approval-variants-ch" && astraTargaSummary.marketScope === "CH" && astraTargaSummary.productionImport === false && astraTargaSummary.productImportAllowed === false && astraTargaSummary.ruEaeuApplicability === false && astraTargaSummary.exactVagFactoryCodePair === false && astraTargaSummary.counts.approvalPowertrainVariantRows === 53240 && astraTargaSummary.counts.exactVagFactoryCodePairRows === 0, "ASTRA TARGA must remain separately namespaced CH-only research, never factory fitment");';
  const rdwRuntime = [
    '  const rdwSummary = require(path.join(ROOT, "lib", "rdw-vag-research-db.cjs")).getRdwSummary(RESEARCH);',
    '  const rdwPackManifest = require(path.join(ROOT, "data", "research", "rdw-vag-nl-eu-type-approval-research", "manifest.json"));',
    '  assert(rdwSummary.id === rdw.id && rdwSummary.marketScope === "NL" && rdwSummary.productionImport === false && rdwSummary.ruEaeuApplicability === false && rdwSummary.exactVehicleFitment === false && rdwSummary.exactEngineGearboxPair === false && rdwSummary.repairApplicability === false && rdwSummary.diagnosticExecutionAllowed === false, "RDW pack must remain separate NL-only approval research, never VAG production fitment");',
    '  assert(rdwSummary.counts.approvalScopes === rdwPackManifest.counts.approval_scopes && rdwSummary.counts.registrationObservations === rdwPackManifest.counts.registration_observations && rdwSummary.counts.engineDesignationCandidates === rdwPackManifest.counts.engine_candidates && rdwSummary.counts.gearboxClassifications === rdwPackManifest.counts.gearbox_classifications && rdwSummary.counts.sourceRows === rdwPackManifest.counts.source_rows && rdwSummary.counts.sourceFiles === rdwPackManifest.counts.source_files, "RDW SQLite counts differ from the verified pack manifest");',
    '  assert(rdwSummary.sourceSnapshotSha256 === rdwPackManifest.source_snapshot_sha256 && rdwSummary.databaseSha256 === rdwPackManifest.database.sha256 && rdwSummary.sourceManifestSha256 === rdwPackManifest.source_manifest_sha256 && rdwSummary.databaseSha256 === rdw.database_sha256 && rdwSummary.sourceManifestSha256 === rdw.source_manifest_sha256, "RDW snapshot, database or source-manifest provenance changed");'
  ].join("\\n");
  if (!verifier.includes('const rdwSummary = require(path.join(ROOT, "lib", "rdw-vag-research-db.cjs"))')) {
    verifier = replaceExactly(verifier, targaAssertion, targaAssertion + "\n" + rdwRuntime, "RDW runtime rights/provenance/count verification");
  }

  const rdwReport = [
    '      rdw_nl_eu: {',
    '        marketScope: rdwSummary.marketScope,',
    '        approvalScopes: rdwSummary.counts.approvalScopes,',
    '        registrationObservations: rdwSummary.counts.registrationObservations,',
    '        engineDesignationCandidates: rdwSummary.counts.engineDesignationCandidates,',
    '        gearboxClassifications: rdwSummary.counts.gearboxClassifications,',
    '        sourceRows: rdwSummary.counts.sourceRows,',
    '        sourceFiles: rdwSummary.counts.sourceFiles,',
    '        productionImport: rdwSummary.productionImport,',
    '        ruEaeuApplicability: rdwSummary.ruEaeuApplicability,',
    '        exactVehicleFitment: rdwSummary.exactVehicleFitment,',
    '        exactEngineGearboxPair: rdwSummary.exactEngineGearboxPair,',
    '        repairApplicability: rdwSummary.repairApplicability,',
    '        diagnosticExecutionAllowed: rdwSummary.diagnosticExecutionAllowed,',
    '        sourceSnapshotSha256: rdwSummary.sourceSnapshotSha256,',
    '        sourceManifestSha256: rdwSummary.sourceManifestSha256,',
    '        databaseSha256: rdwSummary.databaseSha256,',
    '      },'
  ].join("\n");
  const productionReportLines = verifier.split("\n").filter((line) => /^\s*production_fitment_rows_added: 0,$/.test(line));
  if (productionReportLines.length !== 1) throw new Error("RDW verification report: expected exactly one production-fitment summary anchor, found " + productionReportLines.length);
  const productionReportAnchor = productionReportLines[0];
  const reportIndent = productionReportAnchor.match(/^\s*/)[0];
  const rdwReportBaseIndent = rdwReport.match(/^\s*/)[0].length;
  const rdwReportAtIndent = rdwReport.split("\n").map((line) => reportIndent + line.slice(rdwReportBaseIndent)).join("\n");
  if (!verifier.includes("rdw_nl_eu:")) verifier = replaceExactly(verifier, productionReportAnchor, rdwReportAtIndent + "\n" + productionReportAnchor, "RDW verification report");

  if (!test.includes("result.rdw_nl_eu")) {
    const rdwTestBefore = [
      '  assert.deepEqual(result.astra_ch_tas, {',
      '    marketScope: "CH",',
      '    approvals: 45215,',
      '    emissionsGearboxRows: 53414,',
      '    linkedScopeRows: 33909,',
      '    exactScopeLinks: 5420,',
      '    wildcardScopeLinks: 28489,',
      '    unlinkedScopeRows: 19505,',
      '    productionImport: false,',
      '    ruEaeuApplicability: false,',
      '    exactVehicleFitment: false,',
      '    repairApplicability: false,',
      '    diagnosticExecutionAllowed: false,',
      '    databaseSha256: "161800c884f6cdcc3b52c8cc87df51a2d853e7cbc640dea18847f40c0576b7f5"',
      '  });',
      '  assert.equal(result.mechanicdb_vag_dtc_candidates.displayStatus, "candidate_reference_visible_separate_namespace");'
    ].join("\\n");
    const rdwTestAfter = [
      '  assert.deepEqual(result.astra_ch_tas, {',
      '    marketScope: "CH",',
      '    approvals: 45215,',
      '    emissionsGearboxRows: 53414,',
      '    linkedScopeRows: 33909,',
      '    exactScopeLinks: 5420,',
      '    wildcardScopeLinks: 28489,',
      '    unlinkedScopeRows: 19505,',
      '    productionImport: false,',
      '    ruEaeuApplicability: false,',
      '    exactVehicleFitment: false,',
      '    repairApplicability: false,',
      '    diagnosticExecutionAllowed: false,',
      '    databaseSha256: "161800c884f6cdcc3b52c8cc87df51a2d853e7cbc640dea18847f40c0576b7f5"',
      '  });',
      '  const rdwPackManifest = require(path.join(ROOT, "data", "research", "rdw-vag-nl-eu-type-approval-research", "manifest.json"));',
      '  assert.equal(result.rdw_nl_eu.marketScope, "NL");',
      '  assert.equal(result.rdw_nl_eu.approvalScopes, rdwPackManifest.counts.approval_scopes);',
      '  assert.equal(result.rdw_nl_eu.registrationObservations, rdwPackManifest.counts.registration_observations);',
      '  assert.equal(result.rdw_nl_eu.engineDesignationCandidates, rdwPackManifest.counts.engine_candidates);',
      '  assert.equal(result.rdw_nl_eu.gearboxClassifications, rdwPackManifest.counts.gearbox_classifications);',
      '  assert.equal(result.rdw_nl_eu.sourceRows, rdwPackManifest.counts.source_rows);',
      '  assert.equal(result.rdw_nl_eu.sourceFiles, rdwPackManifest.counts.source_files);',
      '  assert.equal(result.rdw_nl_eu.productionImport, false);',
      '  assert.equal(result.rdw_nl_eu.ruEaeuApplicability, false);',
      '  assert.equal(result.rdw_nl_eu.exactVehicleFitment, false);',
      '  assert.equal(result.rdw_nl_eu.exactEngineGearboxPair, false);',
      '  assert.equal(result.rdw_nl_eu.repairApplicability, false);',
      '  assert.equal(result.rdw_nl_eu.diagnosticExecutionAllowed, false);',
      '  assert.equal(result.rdw_nl_eu.sourceSnapshotSha256, rdwPackManifest.source_snapshot_sha256);',
      '  assert.equal(result.rdw_nl_eu.databaseSha256, rdwPackManifest.database.sha256);',
      '  assert.equal(result.rdw_nl_eu.sourceManifestSha256, rdwPackManifest.source_manifest_sha256);',
      '  assert.equal(result.mechanicdb_vag_dtc_candidates.displayStatus, "candidate_reference_visible_separate_namespace");'
    ].join("\\n");
    test = replaceExactly(test, rdwTestBefore, rdwTestAfter, "RDW regression assertions");
  }

  const legacyRdwRuntime = /  assert\(rdwSummary\.counts\.approvalScopes === 96519[\s\S]*?RDW snapshot, database or source manifest provenance\/counts changed"\);/;
  if (legacyRdwRuntime.test(verifier)) {
    verifier = verifier.replace(legacyRdwRuntime, [
      '  const rdwPackManifest = require(path.join(ROOT, "data", "research", "rdw-vag-nl-eu-type-approval-research", "manifest.json"));',
      '  assert(rdwSummary.counts.approvalScopes === rdwPackManifest.counts.approval_scopes && rdwSummary.counts.registrationObservations === rdwPackManifest.counts.registration_observations && rdwSummary.counts.engineDesignationCandidates === rdwPackManifest.counts.engine_candidates && rdwSummary.counts.gearboxClassifications === rdwPackManifest.counts.gearbox_classifications && rdwSummary.counts.sourceRows === rdwPackManifest.counts.source_rows && rdwSummary.counts.sourceFiles === rdwPackManifest.counts.source_files, "RDW SQLite counts differ from the verified pack manifest");',
      '  assert(rdwSummary.sourceSnapshotSha256 === rdwPackManifest.source_snapshot_sha256 && rdwSummary.databaseSha256 === rdwPackManifest.database.sha256 && rdwSummary.sourceManifestSha256 === rdwPackManifest.source_manifest_sha256 && rdwSummary.databaseSha256 === rdw.database_sha256 && rdwSummary.sourceManifestSha256 === rdw.source_manifest_sha256, "RDW snapshot, database or source-manifest provenance changed");'
    ].join("\\n"));
  }
  const legacyRdwTestStart = test.indexOf('  assert.deepEqual(result.rdw_nl_eu, {');
  if (legacyRdwTestStart >= 0 && test.slice(legacyRdwTestStart, legacyRdwTestStart + 1400).includes("896a34b9b8377f2ed20c34d7e0e33b4cf2ce1958e2cdd2b7326ee8c3157b0706")) {
    const legacyRdwTestEnd = test.indexOf('  assert.equal(result.mechanicdb_vag_dtc_candidates.displayStatus, "candidate_reference_visible_separate_namespace");', legacyRdwTestStart);
    if (legacyRdwTestEnd < 0) throw new Error("Legacy RDW test assertion end anchor missing");
    const legacyRdwDynamicTest = [
      '  const rdwPackManifest = require(path.join(ROOT, "data", "research", "rdw-vag-nl-eu-type-approval-research", "manifest.json"));',
      '  assert.equal(result.rdw_nl_eu.marketScope, "NL");',
      '  assert.equal(result.rdw_nl_eu.approvalScopes, rdwPackManifest.counts.approval_scopes);',
      '  assert.equal(result.rdw_nl_eu.registrationObservations, rdwPackManifest.counts.registration_observations);',
      '  assert.equal(result.rdw_nl_eu.engineDesignationCandidates, rdwPackManifest.counts.engine_candidates);',
      '  assert.equal(result.rdw_nl_eu.gearboxClassifications, rdwPackManifest.counts.gearbox_classifications);',
      '  assert.equal(result.rdw_nl_eu.sourceRows, rdwPackManifest.counts.source_rows);',
      '  assert.equal(result.rdw_nl_eu.sourceFiles, rdwPackManifest.counts.source_files);',
      '  assert.equal(result.rdw_nl_eu.productionImport, false);',
      '  assert.equal(result.rdw_nl_eu.ruEaeuApplicability, false);',
      '  assert.equal(result.rdw_nl_eu.exactVehicleFitment, false);',
      '  assert.equal(result.rdw_nl_eu.exactEngineGearboxPair, false);',
      '  assert.equal(result.rdw_nl_eu.repairApplicability, false);',
      '  assert.equal(result.rdw_nl_eu.diagnosticExecutionAllowed, false);',
      '  assert.equal(result.rdw_nl_eu.sourceSnapshotSha256, rdwPackManifest.source_snapshot_sha256);',
      '  assert.equal(result.rdw_nl_eu.databaseSha256, rdwPackManifest.database.sha256);',
      '  assert.equal(result.rdw_nl_eu.sourceManifestSha256, rdwPackManifest.source_manifest_sha256);',
      '  assert.equal(result.mechanicdb_vag_dtc_candidates.displayStatus, "candidate_reference_visible_separate_namespace");'
    ].join("\\n");
    const legacyLine = '  assert.equal(result.mechanicdb_vag_dtc_candidates.displayStatus, "candidate_reference_visible_separate_namespace");';
    test = test.slice(0, legacyRdwTestStart) + legacyRdwDynamicTest + test.slice(legacyRdwTestEnd + legacyLine.length);
  }
  fs.writeFileSync(verifierPath, verifier.replace(/\n/g, verifierNewline), "utf8");
  fs.writeFileSync(testPath, test.replace(/\n/g, testNewline), "utf8");
  console.log(JSON.stringify({ status: "patched", patch: "run31-rdw-nl-eu-research-pack-verification", manifestPackCount: expectedPackCount, rdwPackId: "rdw-vag-nl-eu-type-approval-research", files: ["scripts/verify-local-research-packs.cjs", "tests/local-research-packs.test.cjs"] }));
}
try { main(); }
catch (error) { console.error("Run31 RDW research-pack verifier patch failed: " + error.message); process.exitCode = 1; }
