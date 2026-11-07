"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");
const { getRdwSummary, searchRdwApprovals, clearCache } = require("../lib/rdw-vag-research-db.cjs");

const RESEARCH_ROOT = path.join(__dirname, "..", "data", "research");
const APPROVAL = "e1*2018/858*00403*07";

test("RDW pack verifies CC0 provenance, hashes, NL scope and research-only boundaries", () => {
  clearCache();
  const summary = getRdwSummary(RESEARCH_ROOT);
  const packManifest = require(path.join(RESEARCH_ROOT, "rdw-vag-nl-eu-type-approval-research", "manifest.json"));
  assert.equal(summary.marketScope, "NL");
  assert.equal(summary.license, "CC0 1.0");
  assert.equal(summary.rightsStatus, "approved_by_published_CC0_license");
  assert.equal(summary.reviewStatus, "verified_research_only");
  assert.equal(summary.productionImport, false);
  assert.equal(summary.ruEaeuApplicability, false);
  assert.equal(summary.exactVehicleFitment, false);
  assert.equal(summary.exactEngineGearboxPair, false);
  assert.equal(summary.repairApplicability, false);
  assert.equal(summary.diagnosticExecutionAllowed, false);
  assert.equal(summary.sourceSnapshotSha256, packManifest.source_snapshot_sha256);
  assert.equal(summary.counts.approvalScopes, packManifest.counts.approval_scopes);
  assert.equal(summary.counts.registrationObservations, packManifest.counts.registration_observations);
  assert.equal(summary.counts.engineDesignationCandidates, packManifest.counts.engine_candidates);
  assert.equal(summary.counts.gearboxClassifications, packManifest.counts.gearbox_classifications);
  assert.equal(summary.counts.sourceRows, packManifest.counts.source_rows);
  assert.equal(summary.counts.sourceFiles, packManifest.counts.source_files);
  assert.equal(summary.databaseSha256, packManifest.database.sha256);
  assert.equal(summary.sourceManifestSha256, packManifest.source_manifest_sha256);
  assert.match(summary.databaseSha256, /^[a-f0-9]{64}$/);
  assert.match(summary.sourceManifestSha256, /^[a-f0-9]{64}$/);
  assert.match(summary.attributionText, /RDW Open Data \(Netherlands\)/);
});

test("exact RDW approval scope keeps engine and gearbox observations separate", () => {
  const rows = searchRdwApprovals(APPROVAL, 50, RESEARCH_ROOT);
  const row = rows.find((item) =>
    item.typeApprovalNumber === APPROVAL &&
    item.variant === "ACDUCAX0" &&
    item.version === "FD6FD6DD002PR4VNB50OO" &&
    item.revision === "0"
  );
  assert.ok(row, "expected reviewed RDW approval scope was not found");
  assert.equal(row.marketScope, "NL");
  assert.equal(row.applicabilityPrecision, "exact_RDW_approval_variant_version_revision_scope");
  assert.deepEqual(row.exactScopeKey, {
    typeApprovalNumber: APPROVAL,
    variant: "ACDUCAX0",
    version: "FD6FD6DD002PR4VNB50OO",
    revision: "0"
  });
  assert.ok(row.engineDesignationCandidates.some((item) => item.engineDesignation === "DUC"));
  assert.ok(row.gearboxClassifications.some((item) => item.gearboxTypeClassification === "A"));
  assert.ok(row.engineDesignationCandidates.every((item) => /^[a-f0-9]{64}$/.test(item.sourceRowSha256)));
  assert.ok(row.gearboxClassifications.every((item) => /^[a-f0-9]{64}$/.test(item.sourceRowSha256)));
  assert.ok(row.engineDesignationCandidates.every((item) => item.sourceRevision && /^[a-f0-9]{64}$/.test(item.sourceFileSha256)));
  assert.ok(row.gearboxClassifications.every((item) => item.sourceRevision && /^[a-f0-9]{64}$/.test(item.sourceFileSha256)));
  assert.equal(row.engineCode, null);
  assert.equal(row.gearboxCode, null);
  assert.equal(row.modelYear, null);
  assert.equal(row.generation, null);
  assert.equal(row.exactEngineGearboxPair, false);
  assert.equal(row.exactVehicleFitment, false);
  assert.equal(row.productionFitment, false);
  assert.equal(row.ruEaeuApplicability, false);
  assert.equal(row.repairApplicability, false);
  assert.equal(row.diagnosticExecutionAllowed, false);
  assert.match(row.warning, /separate source observations/);
});

test("RDW trade-name search works offline and rejects undersized queries", () => {
  const rows = searchRdwApprovals("TAYRON", 10, RESEARCH_ROOT);
  assert.ok(rows.length > 0);
  assert.ok(rows.every((row) => row.marketScope === "NL" && row.exactEngineGearboxPair === false));
  assert.throws(() => searchRdwApprovals("A", 10, RESEARCH_ROOT), /минимум два символа/);
});
