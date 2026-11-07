"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");
const { getKbaSummary, searchKbaStock, clearCache } = require("../kba-de-stock-research-db.cjs");


test("KBA pack verifies DL-DE BY 2.0 provenance, source hashes and DE-only research boundary", () => {
  clearCache();
  const root = process.env.VAG_TECH_PRO_KBA_TEST_ROOT || path.join(__dirname, "..", "data", "research");
  const summary = getKbaSummary(root);
  assert.equal(summary.marketScope, "DE");
  assert.equal(summary.license, "DL-DE-BY-2.0");
  assert.equal(summary.rightsStatus, "approved_by_published_DL_DE_BY_2_0");
  assert.equal(summary.reviewStatus, "verified_research_only");
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
  assert.equal(summary.counts.sourceRows, 1047991);
  assert.equal(summary.counts.vagStockObservations, 264847);
  assert.equal(summary.counts.manufacturerLabels, 8);
  assert.equal(summary.counts.uniqueMakeTradeNamePairs, 802);
  assert.equal(summary.counts.uniqueMakeTypeKeyPairs, 4155);
  assert.equal(summary.counts.uniqueMakeTradeTypeReferenceDateTuples, 16301);
  assert.equal(summary.counts.federalStates, 17);
  assert.equal(summary.counts.referenceDates, 4);
  assert.match(summary.databaseSha256, /^[a-f0-9]{64}$/);
  assert.match(summary.sourceSnapshotSha256, /^[a-f0-9]{64}$/);
  assert.match(summary.sourceManifestSha256, /^[a-f0-9]{64}$/);
  assert.match(summary.attributionText, /Kraftfahrt-Bundesamt \(KBA\)/);
  assert.match(summary.attributionText, /Modified data/);
});

test("KBA search returns raw German stock observations, not fitment claims", () => {
  const root = process.env.VAG_TECH_PRO_KBA_TEST_ROOT || path.join(__dirname, "..", "data", "research");
  const rows = searchKbaStock("Golf", 10, root);
  assert.ok(rows.length > 0);
  assert.ok(rows.every((row) => row.marketScope === "DE"));
  assert.ok(rows.every((row) => row.applicabilityPrecision === "aggregate_stock_observation"));
  assert.ok(rows.every((row) => row.reviewStatus === "research_only"));
  assert.ok(rows.every((row) => row.exactVehicleFitment === false));
  assert.ok(rows.every((row) => row.exactEngineGearboxPair === false));
  assert.ok(rows.every((row) => row.ruEaeuApplicability === false));
  assert.ok(rows.every((row) => row.engineCode === null && row.gearboxCode === null));
  assert.ok(rows.every((row) => row.modelYear === null && row.generation === null));
  assert.ok(rows.every((row) => /^[a-f0-9]{64}$/.test(row.sourceRecordSha256)));
  assert.ok(rows.every((row) => /^[a-f0-9]{64}$/.test(row.sourceSnapshotSha256)));
  assert.ok(rows.some((row) => row.tradeName.toLowerCase().includes("golf")));
  assert.match(rows[0].warning, /не подтверждён как TSN/);
});

test("KBA exact raw type-key search works offline and rejects undersized queries", () => {
  const root = process.env.VAG_TECH_PRO_KBA_TEST_ROOT || path.join(__dirname, "..", "data", "research");
  const rows = searchKbaStock("0603", 10, root);
  assert.ok(rows.length > 0);
  assert.ok(rows.every((row) => row.marketScope === "DE" && row.exactEngineGearboxPair === false));
  assert.throws(() => searchKbaStock("A", 10, root), /минимум два символа/);
});
