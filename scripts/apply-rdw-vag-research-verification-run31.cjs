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
  verifier = replaceExactly(verifier,
    '  assert(manifest.schema_version === 1 && Array.isArray(manifest.packs) && manifest.packs.length === 11, "Expected eleven registered research packs, including separate CH-only ASTRA TAS and TARGA packs");\\n  const packIds = manifest.packs.map((pack) => pack.id);\\n  assert(packIds.every((id) => typeof id === "string" && id.length > 0) && new Set(packIds).size === packIds.length, "Research pack IDs must be non-empty and unique");\\n  const byId = Object.fromEntries(manifest.packs.map((pack) => [pack.id, pack]));\\n',
    '  assert(manifest.schema_version === 1 && Array.isArray(manifest.packs) && manifest.packs.length === 12, "Expected twelve separately licensed research packs, including CH-only ASTRA TAS/TARGA and NL-only RDW approval research");\\n  const packIds = manifest.packs.map((pack) => pack.id);\\n  assert(packIds.every((id) => typeof id === "string" && id.length > 0) && new Set(packIds).size === packIds.length, "Research pack IDs must be non-empty and unique");\\n  const byId = Object.fromEntries(manifest.packs.map((pack) => [pack.id, pack]));\\n',
    "RDW research pack manifest cardinality");

  verifier = replaceExactly(verifier,
    '  const astra = byId["astra-fedro-tas-type-approvals-open-data-ch"];\\n  assert(wikidataGenerations, "Wikidata generation candidate pack must be registered");\\n  assert(ob && vag && obdb && vehiclesdb && mechanicdb && wikidata && astra, "Required generic, candidate and CH-only research packs must be registered");\\n',
    '  const astra = byId["astra-fedro-tas-type-approvals-open-data-ch"];\\n  const targa = byId["astra-fedro-targa-emissionen-approval-variants-ch"];\\n  const rdw = byId["rdw-vag-nl-eu-type-approval-research"];\\n  assert(wikidataGenerations, "Wikidata generation candidate pack must be registered");\\n  assert(ob && vag && obdb && vehiclesdb && mechanicdb && wikidata && astra && targa && rdw, "Required generic, candidate, CH-only ASTRA TAS/TARGA and NL-only RDW packs must be registered");\\n',
    "RDW pack registration");

  const targaAssertion = '  assert(astraTargaSummary.id === "astra-fedro-targa-emissionen-approval-variants-ch" && astraTargaSummary.marketScope === "CH" && astraTargaSummary.productionImport === false && astraTargaSummary.productImportAllowed === false && astraTargaSummary.ruEaeuApplicability === false && astraTargaSummary.exactVagFactoryCodePair === false && astraTargaSummary.counts.approvalPowertrainVariantRows === 53240 && astraTargaSummary.counts.exactVagFactoryCodePairRows === 0, "ASTRA TARGA must remain separately namespaced CH-only research, never factory fitment");';
  const rdwRuntime = [
    '  const rdwSummary = require(path.join(ROOT, "lib", "rdw-vag-research-db.cjs")).getRdwSummary(RESEARCH);',
    '  assert(rdwSummary.id === rdw.id && rdwSummary.marketScope === "NL" && rdwSummary.productionImport === false && rdwSummary.ruEaeuApplicability === false && rdwSummary.exactVehicleFitment === false && rdwSummary.exactEngineGearboxPair === false && rdwSummary.repairApplicability === false && rdwSummary.diagnosticExecutionAllowed === false, "RDW pack must remain separate NL-only approval research, never VAG production fitment");',
    '  assert(rdwSummary.counts.approvalScopes === 96519 && rdwSummary.counts.registrationObservations === 102662 && rdwSummary.counts.engineDesignationCandidates === 93836 && rdwSummary.counts.gearboxClassifications === 93548 && rdwSummary.counts.sourceRows === 604785 && rdwSummary.sourceSnapshotSha256 === "896a34b9b8377f2ed20c34d7e0e33b4cf2ce1958e2cdd2b7326ee8c3157b0706" && rdwSummary.databaseSha256 === rdw.database_sha256 && rdwSummary.sourceManifestSha256 === rdw.source_manifest_sha256, "RDW snapshot, database or source manifest provenance/counts changed");'
  ].join("\\n");
  verifier = replaceExactly(verifier, targaAssertion, targaAssertion + "\\n" + rdwRuntime, "RDW runtime rights/provenance/count verification");

  verifier = replaceExactly(verifier,
    '      astra_ch_tas: {\n        marketScope: astraSummary.marketScope,\n        approvals: astraSummary.counts.approvals,\n        emissionsGearboxRows: astraSummary.counts.emissionsGearboxRows,\n        linkedScopeRows: astraSummary.counts.linkedScopeRows,\n        exactScopeLinks: astraSummary.counts.exactScopeLinks,\n        wildcardScopeLinks: astraSummary.counts.wildcardScopeLinks,\n        unlinkedScopeRows: astraSummary.counts.unlinkedScopeRows,\n        productionImport: astraSummary.productionImport,\n        ruEaeuApplicability: astraSummary.ruEaeuApplicability,\n        exactVehicleFitment: astraSummary.exactVehicleFitment,\n        repairApplicability: astraSummary.repairApplicability,\n        diagnosticExecutionAllowed: astraSummary.diagnosticExecutionAllowed,\n        databaseSha256: astraSummary.databaseSha256,\n      },\n      production_fitment_rows_added: 0,\n',
    '      astra_ch_tas: {\n        marketScope: astraSummary.marketScope,\n        approvals: astraSummary.counts.approvals,\n        emissionsGearboxRows: astraSummary.counts.emissionsGearboxRows,\n        linkedScopeRows: astraSummary.counts.linkedScopeRows,\n        exactScopeLinks: astraSummary.counts.exactScopeLinks,\n        wildcardScopeLinks: astraSummary.counts.wildcardScopeLinks,\n        unlinkedScopeRows: astraSummary.counts.unlinkedScopeRows,\n        productionImport: astraSummary.productionImport,\n        ruEaeuApplicability: astraSummary.ruEaeuApplicability,\n        exactVehicleFitment: astraSummary.exactVehicleFitment,\n        repairApplicability: astraSummary.repairApplicability,\n        diagnosticExecutionAllowed: astraSummary.diagnosticExecutionAllowed,\n        databaseSha256: astraSummary.databaseSha256,\n      },\n      rdw_nl_eu: {\n        marketScope: rdwSummary.marketScope,\n        approvalScopes: rdwSummary.counts.approvalScopes,\n        registrationObservations: rdwSummary.counts.registrationObservations,\n        engineDesignationCandidates: rdwSummary.counts.engineDesignationCandidates,\n        gearboxClassifications: rdwSummary.counts.gearboxClassifications,\n        sourceRows: rdwSummary.counts.sourceRows,\n        sourceFiles: rdwSummary.counts.sourceFiles,\n        productionImport: rdwSummary.productionImport,\n        ruEaeuApplicability: rdwSummary.ruEaeuApplicability,\n        exactVehicleFitment: rdwSummary.exactVehicleFitment,\n        exactEngineGearboxPair: rdwSummary.exactEngineGearboxPair,\n        repairApplicability: rdwSummary.repairApplicability,\n        diagnosticExecutionAllowed: rdwSummary.diagnosticExecutionAllowed,\n        sourceSnapshotSha256: rdwSummary.sourceSnapshotSha256,\n        sourceManifestSha256: rdwSummary.sourceManifestSha256,\n        databaseSha256: rdwSummary.databaseSha256,\n      },\n      production_fitment_rows_added: 0,\n',
    "RDW verification report");

  test = replaceExactly(test,
    '  assert.deepEqual(result.astra_ch_tas, {\n    marketScope: "CH",\n    approvals: 45215,\n    emissionsGearboxRows: 53414,\n    linkedScopeRows: 33909,\n    exactScopeLinks: 5420,\n    wildcardScopeLinks: 28489,\n    unlinkedScopeRows: 19505,\n    productionImport: false,\n    ruEaeuApplicability: false,\n    exactVehicleFitment: false,\n    repairApplicability: false,\n    diagnosticExecutionAllowed: false,\n    databaseSha256: "161800c884f6cdcc3b52c8cc87df51a2d853e7cbc640dea18847f40c0576b7f5"\n  });\n  assert.equal(result.mechanicdb_vag_dtc_candidates.displayStatus, "candidate_reference_visible_separate_namespace");\n',
    '  assert.deepEqual(result.astra_ch_tas, {\n    marketScope: "CH",\n    approvals: 45215,\n    emissionsGearboxRows: 53414,\n    linkedScopeRows: 33909,\n    exactScopeLinks: 5420,\n    wildcardScopeLinks: 28489,\n    unlinkedScopeRows: 19505,\n    productionImport: false,\n    ruEaeuApplicability: false,\n    exactVehicleFitment: false,\n    repairApplicability: false,\n    diagnosticExecutionAllowed: false,\n    databaseSha256: "161800c884f6cdcc3b52c8cc87df51a2d853e7cbc640dea18847f40c0576b7f5"\n  });\n  assert.deepEqual(result.rdw_nl_eu, {\n    marketScope: "NL",\n    approvalScopes: 96519,\n    registrationObservations: 102662,\n    engineDesignationCandidates: 93836,\n    gearboxClassifications: 93548,\n    sourceRows: 604785,\n    sourceFiles: 6,\n    productionImport: false,\n    ruEaeuApplicability: false,\n    exactVehicleFitment: false,\n    exactEngineGearboxPair: false,\n    repairApplicability: false,\n    diagnosticExecutionAllowed: false,\n    sourceSnapshotSha256: "896a34b9b8377f2ed20c34d7e0e33b4cf2ce1958e2cdd2b7326ee8c3157b0706",\n    sourceManifestSha256: result.rdw_nl_eu.sourceManifestSha256,\n    databaseSha256: result.rdw_nl_eu.databaseSha256\n  });\n  assert.match(result.rdw_nl_eu.sourceManifestSha256, /^[a-f0-9]{64}$/);\n  assert.match(result.rdw_nl_eu.databaseSha256, /^[a-f0-9]{64}$/);\n  assert.equal(result.mechanicdb_vag_dtc_candidates.displayStatus, "candidate_reference_visible_separate_namespace");\n',
    "RDW regression assertions");

  fs.writeFileSync(verifierPath, verifier.replace(/\n/g, verifierNewline), "utf8");
  fs.writeFileSync(testPath, test.replace(/\n/g, testNewline), "utf8");
  console.log(JSON.stringify({ status: "patched", patch: "run31-rdw-nl-eu-research-pack-verification", manifestPackCount: 11, rdwPackId: "rdw-vag-nl-eu-type-approval-research", files: ["scripts/verify-local-research-packs.cjs", "tests/local-research-packs.test.cjs"] }));
}
try { main(); }
catch (error) { console.error("Run31 RDW research-pack verifier patch failed: " + error.message); process.exitCode = 1; }
