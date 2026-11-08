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
  const target = path.resolve(root, relative);
  const rel = path.relative(root, target);
  if (!rel || rel === ".." || rel.startsWith(".." + path.sep) || path.isAbsolute(rel)) fail("Target escaped desktop root: " + relative);
  return target;
}
function patch(desktopRoot) {
  const root = path.resolve(desktopRoot);
  if (!fs.statSync(root).isDirectory()) fail("Desktop source root is not a directory");
  const verifierPath = safeTarget(root, "scripts/verify-local-research-packs.cjs");
  const testPath = safeTarget(root, "tests/local-research-packs.test.cjs");
  let verifier = fs.readFileSync(verifierPath, "utf8").replace(/\r\n/g, "\n");
  let tests = fs.readFileSync(testPath, "utf8").replace(/\r\n/g, "\n");

  const countMatches = [...verifier.matchAll(/manifest\.packs\.length === (\d+)/g)];
  if (countMatches.length !== 1) fail("KBA approval pack cardinality: expected exactly one numeric assertion, found " + countMatches.length);
  const currentCount = Number(countMatches[0][1]);
  if (currentCount !== 13 && currentCount !== 14) fail("KBA approval pack cardinality: expected 13 before patch or 14 after patch, found " + currentCount);
  if (currentCount === 13) {
    verifier = verifier.replace("manifest.packs.length === 13", "manifest.packs.length === 14");
    const message = verifier.match(/"Expected 13 separately licensed research packs[^"]*"/);
    if (!message) fail("KBA approval pack cardinality message anchor missing");
    verifier = verifier.replace(message[0], '"Expected 14 separately licensed research packs, including the DE-only KBA approval metadata research pack"');
  }

  const stockBinding = '  const kbaDe = byId["kba-de-vag-stock-research"];';
  const approvalBinding = '  const kbaApproval = byId["kba-de-vag-type-approval-research"];';
  if (!verifier.includes(approvalBinding)) verifier = replaceExactly(verifier, stockBinding, stockBinding + "\n" + approvalBinding, "KBA approval pack binding");

  const requiredLine = verifier.split("\n").find((line) =>
    line.includes("assert(ob && vag && obdb && vehiclesdb && mechanicdb && wikidata") &&
    line.includes("kbaDe") &&
    line.includes("Required generic")
  );
  if (!requiredLine) fail("KBA approval required-pack assertion anchor missing");
  if (!requiredLine.includes("kbaApproval")) {
    const updated = requiredLine.replace("&& kbaDe,", "&& kbaDe && kbaApproval,");
    if (updated === requiredLine) fail("KBA approval required-pack assertion could not be extended");
    verifier = replaceExactly(verifier, requiredLine, updated, "KBA approval required-pack assertion");
  }

  const stockReader = '  const kbaDeSummary = require(path.join(ROOT, "lib", "kba-de-stock-research-db.cjs")).getKbaSummary(RESEARCH);';
  const approvalReader = '  const kbaApprovalSummary = require(path.join(ROOT, "lib", "kba-de-approval-research-db.cjs")).getKbaApprovalSummary(RESEARCH);';
  const approvalAssertions = [
    '  assert(kbaApprovalSummary.id === kbaApproval.id && kbaApprovalSummary.sourceId === "kba-de-whole-vehicle-type-approvals" && kbaApprovalSummary.marketScope === "DE" && kbaApprovalSummary.license === "DL-DE-BY-2.0" && kbaApprovalSummary.rightsStatus === "approved_by_published_DL_DE_BY_2_0" && kbaApprovalSummary.applicabilityPrecision === "type_approval_document_metadata_only" && kbaApprovalSummary.researchPackIngested === true && kbaApprovalSummary.productDatabaseIngested === false && kbaApprovalSummary.productionImport === false && kbaApprovalSummary.productImportAllowed === false && kbaApprovalSummary.ruEaeuApplicability === false && kbaApprovalSummary.exactVehicleFitment === false && kbaApprovalSummary.exactEngineGearboxPair === false && kbaApprovalSummary.repairApplicability === false && kbaApprovalSummary.diagnosticExecutionAllowed === false, "KBA approval pack must remain separately namespaced DE-only document metadata, never vehicle fitment");',
    '  assert(kbaApprovalSummary.counts.sourceRows === 3782 && kbaApprovalSummary.counts.approvalRecords === 918 && kbaApprovalSummary.counts.manufacturerLabels === 8 && kbaApprovalSummary.counts.distinctApprovalNumbers === 918 && kbaApprovalSummary.counts.distinctRowHashes === 918 && kbaApprovalSummary.counts.sourceLabelPolicyRows === 9 && kbaApprovalSummary.sourceSnapshotSha256 === kbaApproval.source_snapshot_sha256 && kbaApprovalSummary.databaseSha256 === kbaApproval.database_sha256 && kbaApprovalSummary.sourceManifestSha256 === kbaApproval.source_manifest_sha256, "KBA approval snapshot, SQLite, source manifest or research counts changed");'
  ].join("\n");
  if (!verifier.includes(approvalReader)) {
    verifier = replaceExactly(verifier, stockReader, stockReader + "\n" + approvalReader + "\n" + approvalAssertions, "KBA approval runtime reader/rights/provenance/count verification");
  } else if (!verifier.includes(approvalAssertions)) {
    verifier = replaceExactly(verifier, approvalReader, approvalReader + "\n" + approvalAssertions, "KBA approval runtime rights/provenance/count verification");
  }

  const approvalReport = [
    "      kba_de_vag_approvals: {",
    "        marketScope: kbaApprovalSummary.marketScope,",
    "        approvalRecords: kbaApprovalSummary.counts.approvalRecords,",
    "        manufacturerLabels: kbaApprovalSummary.counts.manufacturerLabels,",
    "        distinctApprovalNumbers: kbaApprovalSummary.counts.distinctApprovalNumbers,",
    "        distinctRowHashes: kbaApprovalSummary.counts.distinctRowHashes,",
    "        sourceRows: kbaApprovalSummary.counts.sourceRows,",
    "        productionImport: kbaApprovalSummary.productionImport,",
    "        productImportAllowed: kbaApprovalSummary.productImportAllowed,",
    "        ruEaeuApplicability: kbaApprovalSummary.ruEaeuApplicability,",
    "        exactVehicleFitment: kbaApprovalSummary.exactVehicleFitment,",
    "        exactEngineGearboxPair: kbaApprovalSummary.exactEngineGearboxPair,",
    "        repairApplicability: kbaApprovalSummary.repairApplicability,",
    "        diagnosticExecutionAllowed: kbaApprovalSummary.diagnosticExecutionAllowed,",
    "        sourceSnapshotSha256: kbaApprovalSummary.sourceSnapshotSha256,",
    "        sourceManifestSha256: kbaApprovalSummary.sourceManifestSha256,",
    "        databaseSha256: kbaApprovalSummary.databaseSha256,",
    "      },"
  ].join("\n");
  const reportAnchor = verifier.split("\n").find((line) => /^\s*production_fitment_rows_added: 0,$/.test(line));
  if (!reportAnchor) fail("KBA approval verifier report insertion anchor missing");
  if (!verifier.includes("kba_de_vag_approvals:")) {
    const indent = reportAnchor.match(/^\s*/)[0];
    const adjusted = approvalReport.split("\n").map((line) => indent + line.replace(/^\s+/, "")).join("\n");
    verifier = replaceExactly(verifier, reportAnchor, adjusted + "\n" + reportAnchor, "KBA approval verifier report");
  }

  const candidateAssertion = '  assert.equal(result.mechanicdb_vag_dtc_candidates.displayStatus, "candidate_reference_visible_separate_namespace");';
  const approvalTestAssertions = [
    "  assert.deepEqual(result.kba_de_vag_approvals, {",
    '    marketScope: "DE", approvalRecords: 918, manufacturerLabels: 8, distinctApprovalNumbers: 918, sourceRows: 3782,',
    "    productionImport: false, productImportAllowed: false, ruEaeuApplicability: false,",
    "    exactVehicleFitment: false, exactEngineGearboxPair: false, repairApplicability: false, diagnosticExecutionAllowed: false,",
    "    sourceSnapshotSha256: result.kba_de_vag_approvals.sourceSnapshotSha256,",
    "    sourceManifestSha256: result.kba_de_vag_approvals.sourceManifestSha256,",
    "    databaseSha256: result.kba_de_vag_approvals.databaseSha256",
    "  });",
    "  assert.match(result.kba_de_vag_approvals.sourceSnapshotSha256, /^[a-f0-9]{64}$/);",
    "  assert.match(result.kba_de_vag_approvals.sourceManifestSha256, /^[a-f0-9]{64}$/);",
    "  assert.match(result.kba_de_vag_approvals.databaseSha256, /^[a-f0-9]{64}$/);"
  ].join("\n");
  if (!tests.includes("result.kba_de_vag_approvals")) {
    tests = replaceExactly(tests, candidateAssertion, approvalTestAssertions + "\n" + candidateAssertion, "KBA approval verifier regression assertions");
  }

  fs.writeFileSync(verifierPath, verifier, "utf8");
  fs.writeFileSync(testPath, tests, "utf8");
  return { status: "patched", files: ["scripts/verify-local-research-packs.cjs","tests/local-research-packs.test.cjs"], manifestPackCount: 14 };
}

function main() {
  const index = process.argv.indexOf("--desktop-root");
  if (index < 0 || !process.argv[index + 1]) fail("Usage: node apply-kba-de-approval-research-verification-run1.cjs --desktop-root <desktop-source>");
  const result = patch(process.argv[index + 1]);
  process.stdout.write(JSON.stringify({ patch: "run1-kba-de-approval-research-verification", ...result }) + "\n");
}

if (require.main === module) {
  try { main(); }
  catch (error) { console.error("KBA approval research verifier patch failed: " + error.message); process.exitCode = 1; }
}
module.exports = { patch };
