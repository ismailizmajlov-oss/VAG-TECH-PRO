"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const { getAstraTargaSummary, searchAstraTargaRows } = require("../lib/astra-targa-emissionen-db.cjs");

test("ASTRA TARGA pack verifies rights, provenance and CH-only boundaries", () => {
  const summary = getAstraTargaSummary();
  assert.equal(summary.marketScope, "CH");
  assert.equal(summary.rightsStatus, "approved_by_published_ogd_terms");
  assert.equal(summary.reviewStatus, "verified_research_only");
  assert.equal(summary.productionImport, false);
  assert.equal(summary.productImportAllowed, false);
  assert.equal(summary.ruEaeuApplicability, false);
  assert.equal(summary.exactVagFactoryCodePair, false);
  assert.equal(summary.counts.approvalPowertrainVariantRows, 53240);
  assert.equal(summary.counts.sourceDefinedVariantLinkRows, 53240);
  assert.equal(summary.counts.exactVagFactoryCodePairRows, 0);
  assert.equal(summary.counts.exactVehicleFitmentRows, 0);
  assert.equal(summary.counts.ruEaeuApplicabilityRows, 0);
  assert.match(summary.databaseSha256, /^[a-f0-9]{64}$/);
  assert.match(summary.sourceFileSha256, /^[a-f0-9]{64}$/);
  assert.match(summary.note, /не подтверждённый заводской код VAG/);
});

test("ASTRA TARGA search returns a source row without promoting raw engine or gearbox labels", () => {
  const rows = searchAstraTargaRows("1AB701", 10);
  const row = rows.find((item) => item.approvalNumber === "1AB701" && item.make === "AUDI");
  assert.ok(row);
  assert.equal(row.engineType, "AEL");
  assert.equal(row.gearboxClassification, "m6");
  assert.equal(row.marketScope, "CH");
  assert.equal(row.applicabilityPrecision, "CH_type_approval_gearbox_variant_row");
  assert.equal(row.sourceDefinedVariantLink, true);
  assert.equal(row.exactVagFactoryCodePair, false);
  assert.equal(row.exactVehicleFitment, false);
  assert.equal(row.ruEaeuApplicability, false);
  assert.equal(row.modelYear, null);
  assert.equal(row.generation, null);
  assert.match(row.sourceRecordSha256, /^[a-f0-9]{64}$/);
  assert.match(row.warning, /не подтверждённый заводской код VAG/);
});

test("ASTRA TARGA search validates query and bounds", () => {
  assert.throws(() => searchAstraTargaRows("x"), /минимум два символа/);
  assert.throws(() => searchAstraTargaRows("x".repeat(101)), /Слишком длинный/);
});
