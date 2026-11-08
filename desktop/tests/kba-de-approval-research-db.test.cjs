"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");
const { getKbaApprovalSummary, searchKbaApprovals } = require("../lib/kba-de-approval-research-db.cjs");

const ROOT = process.env.VAG_TECH_PRO_KBA_APPROVAL_TEST_ROOT || path.join(__dirname, "..", "data", "research");

test("KBA whole-vehicle approval pack verifies DL-DE BY 2.0 provenance and DE-only metadata scope", () => {
  const summary = getKbaApprovalSummary(ROOT);
  assert.equal(summary.id, "kba-de-vag-type-approval-research");
  assert.equal(summary.sourceId, "kba-de-whole-vehicle-type-approvals");
  assert.equal(summary.marketScope, "DE");
  assert.equal(summary.license, "DL-DE-BY-2.0");
  assert.equal(summary.rightsStatus, "approved_by_published_DL_DE_BY_2_0");
  assert.equal(summary.applicabilityPrecision, "type_approval_document_metadata_only");
  assert.equal(summary.reviewStatus, "verified_research_only");
  assert.equal(summary.researchPackIngested, true);
  assert.equal(summary.productDatabaseIngested, false);
  assert.equal(summary.productionImport, false);
  assert.equal(summary.productImportAllowed, false);
  assert.equal(summary.ruEaeuApplicability, false);
  assert.equal(summary.exactVehicleFitment, false);
  assert.equal(summary.exactEngineGearboxPair, false);
  assert.equal(summary.modelYearInferred, false);
  assert.equal(summary.generationInferred, false);
  assert.equal(summary.engineCodesIncluded, false);
  assert.equal(summary.gearboxCodesIncluded, false);
  assert.equal(summary.ecuFitment, false);
  assert.equal(summary.dtcFitment, false);
  assert.equal(summary.repairApplicability, false);
  assert.deepEqual(summary.counts, {
    sourceRows: 3782,
    approvalRecords: 918,
    manufacturerLabels: 8,
    distinctApprovalNumbers: 918,
    sourceLabelPolicyRows: 9
  });
  for (const key of ["sourceSnapshotSha256","sourceFileSha256","databaseSha256","sourceManifestSha256","packManifestSha256","licenseSha256","attributionSha256","rightsEvidenceSha256","buildReportSha256","integrationReportSha256","sourceArtifactSha256"]) {
    assert.match(summary[key], /^[a-f0-9]{64}$/);
  }
  assert.match(summary.attributionText, /Kraftfahrt-Bundesamt \(KBA\)/);
  assert.match(summary.attributionText, /DL-DE BY 2\.0/);
  assert.match(summary.warning, /не распространяются на RU\/ЕАЭС/);
});

test("KBA approval search returns raw approval metadata with row-level provenance and no fitment", () => {
  const rows = searchKbaApprovals("e1*2007/46*1892*04", 10, ROOT);
  assert.equal(rows.length, 1);
  const row = rows[0];
  assert.equal(row.manufacturerLabel, "AUDI AG");
  assert.equal(row.tradeName, "A1 Sportback");
  assert.equal(row.typeDesignation, "GB");
  assert.equal(row.approvalNumber, "e1*2007/46*1892*04");
  assert.equal(row.approvalDate, "2019-01-08");
  assert.equal(row.marketScope, "DE");
  assert.equal(row.applicabilityPrecision, "type_approval_document_metadata_only");
  assert.equal(row.reviewStatus, "research_only");
  assert.equal(row.exactVehicleFitment, false);
  assert.equal(row.exactEngineGearboxPair, false);
  assert.equal(row.ruEaeuApplicability, false);
  assert.equal(row.modelYear, null);
  assert.equal(row.generation, null);
  assert.equal(row.engineCode, null);
  assert.equal(row.gearboxCode, null);
  assert.equal(row.ecuFitment, false);
  assert.equal(row.dtcFitment, false);
  assert.equal(row.repairApplicability, false);
  assert.match(row.sourceRecordSha256, /^[a-f0-9]{64}$/);
  assert.match(row.sourceSnapshotSha256, /^[a-f0-9]{64}$/);
  assert.match(row.sourceManifestSha256, /^[a-f0-9]{64}$/);
  assert.equal(row.license, "DL-DE-BY-2.0");
  assert.match(row.warning, /не распространяются на RU\/ЕАЭС/);
});

test("KBA approval search supports make/model queries and bounds result limits", () => {
  const rows = searchKbaApprovals("Volkswagen", 500, ROOT);
  assert.ok(rows.length > 0);
  assert.ok(rows.length <= 50);
  assert.ok(rows.every((row) => row.manufacturerLabel === "Volkswagen AG"));
  assert.ok(rows.every((row) => row.marketScope === "DE"));
  assert.ok(rows.every((row) => row.exactVehicleFitment === false && row.exactEngineGearboxPair === false));
  assert.ok(rows.every((row) => row.ruEaeuApplicability === false && row.engineCode === null && row.gearboxCode === null));
  assert.throws(() => searchKbaApprovals("A", 10, ROOT), /минимум два символа/);
  assert.throws(() => searchKbaApprovals("x".repeat(101), 10, ROOT), /Слишком длинный/);
});
