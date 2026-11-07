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
    '  assert(rdwSummary.id === rdw.id && rdwSummary.marketScope === "NL" && rdwSummary.productionImport === false && rdwSummary.ruEaeuApplicability === false && rdwSummary.exactVehicleFitment === false && rdwSummary.exactEngineGearboxPair === false && rdwSummary.repairApplicability === false && rdwSummary.diagnosticExecutionAllowed === false, "RDW pack must remain separate NL-only approval research, never VAG production fitment");',
    '  assert(rdwSummary.counts.approvalScopes === rdw.counts.approval_scopes && rdwSummary.counts.registrationObservations === rdw.counts.registration_observations && rdwSummary.counts.engineDesignationCandidates === rdw.counts.engine_candidates && rdwSummary.counts.gearboxClassifications === rdw.counts.gearbox_classifications && rdwSummary.counts.sourceRows === rdw.counts.source_rows && rdwSummary.counts.sourceFiles === rdw.counts.source_files && rdwSummary.sourceSnapshotSha256 === rdw.source_snapshot_sha256 && rdwSummary.databaseSha256 === rdw.database_sha256 && rdwSummary.sourceManifestSha256 === rdw.source_manifest_sha256, "RDW snapshot counts and provenance must match the pinned pack manifest");'
  ].join("\n");
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

  if (!test.includes("rdwPack.counts.approval_scopes")) {
    const rdwTestAnchor = '  assert.equal(result.mechanicdb_vag_dtc_candidates.displayStatus, "candidate_reference_visible_separate_namespace");';
    const rdwTestAssertions = [
      '  const rdwManifest = JSON.parse(require("node:fs").readFileSync(require("node:path").join(__dirname, "../data/research/manifest.json"), "utf8"));',
      '  const rdwPack = rdwManifest.packs.find((item) => item.id === "rdw-vag-nl-eu-type-approval-research");',
      '  assert.ok(rdwPack, "RDW research pack must be registered");',
      '  assert.equal(rdwPack.market_scope[0], "NL");',
      '  assert.deepEqual(result.rdw_nl_eu, {',
      '    marketScope: "NL",',
      '    approvalScopes: rdwPack.counts.approval_scopes,',
      '    registrationObservations: rdwPack.counts.registration_observations,',
      '    engineDesignationCandidates: rdwPack.counts.engine_candidates,',
      '    gearboxClassifications: rdwPack.counts.gearbox_classifications,',
      '    sourceRows: rdwPack.counts.source_rows,',
      '    sourceFiles: rdwPack.counts.source_files,',
      '    productionImport: false,',
      '    ruEaeuApplicability: false,',
      '    exactVehicleFitment: false,',
      '    exactEngineGearboxPair: false,',
      '    repairApplicability: false,',
      '    diagnosticExecutionAllowed: false,',
      '    sourceSnapshotSha256: rdwPack.source_snapshot_sha256,',
      '    sourceManifestSha256: rdwPack.source_manifest_sha256,',
      '    databaseSha256: rdwPack.database_sha256',
      '  });',
      '  assert.match(result.rdw_nl_eu.sourceSnapshotSha256, /^[a-f0-9]{64}$/);',
      '  assert.match(result.rdw_nl_eu.sourceManifestSha256, /^[a-f0-9]{64}$/);',
      '  assert.match(result.rdw_nl_eu.databaseSha256, /^[a-f0-9]{64}$/);'
    ].join("\n");
    test = replaceExactly(test, rdwTestAnchor, rdwTestAnchor + "\n" + rdwTestAssertions, "RDW regression assertions");
  }

  fs.writeFileSync(verifierPath, verifier.replace(/\n/g, verifierNewline), "utf8");
  fs.writeFileSync(testPath, test.replace(/\n/g, testNewline), "utf8");
  console.log(JSON.stringify({ status: "patched", patch: "run31-rdw-nl-eu-research-pack-verification", manifestPackCount: expectedPackCount, rdwPackId: "rdw-vag-nl-eu-type-approval-research", files: ["scripts/verify-local-research-packs.cjs", "tests/local-research-packs.test.cjs"] }));
}
try { main(); }
catch (error) { console.error("Run31 RDW research-pack verifier patch failed: " + error.message); process.exitCode = 1; }
