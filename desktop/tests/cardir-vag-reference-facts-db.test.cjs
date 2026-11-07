"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");
const { getCardirSummary, searchCardirFacts } = require("../lib/cardir-vag-reference-facts-db.cjs");
const researchRoot = path.resolve(__dirname, "../data/research");

test("CarDir pack is a hash-verified CC BY 4.0 research-only SQLite resource", () => {
  const summary = getCardirSummary(researchRoot);
  assert.equal(summary.counts.sourceRows, 41649);
  assert.equal(summary.counts.vagFacts, 773);
  assert.equal(summary.counts.vagBrands, 4);
  assert.equal(summary.counts.vagModels, 24);
  assert.equal(summary.counts.parameterKeys, 19);
  assert.equal(summary.marketScope, "UNKNOWN");
  assert.equal(summary.rightsStatus, "approved_by_published_CC_BY_4_0");
  assert.equal(summary.productionImport, false);
  assert.equal(summary.productImportAllowed, false);
  assert.equal(summary.ruEaeuApplicability, false);
  assert.equal(summary.exactEngineGearboxPair, false);
  assert.equal(summary.exactVehicleFitment, false);
  assert.equal(summary.repairProcedure, false);
  assert.match(summary.databaseSha256, /^[a-f0-9]{64}$/);
  assert.match(summary.sourceSnapshotSha256, /^[a-f0-9]{64}$/);
  assert.match(summary.sourceManifestSha256, /^[a-f0-9]{64}$/);
});

test("CarDir search returns publisher facts with raw qualifiers and complete provenance", () => {
  const rows = searchCardirFacts("Octavia", 10, researchRoot);
  assert.ok(rows.length > 0);
  const row = rows.find((item) => item.model === "Octavia");
  assert.ok(row);
  assert.equal(row.marketScope, "UNKNOWN");
  assert.equal(row.publisherVerificationStatus, "publisher_verified");
  assert.equal(row.technicalReviewStatus, "not_independently_reviewed");
  assert.equal(row.modelGeneration, null);
  assert.equal(row.modelYearFrom, null);
  assert.equal(row.modelYearTo, null);
  assert.equal(row.engineCode, null);
  assert.equal(row.transmissionCode, null);
  assert.equal(row.exactEngineGearboxPair, 0);
  assert.equal(row.productionFitment, 0);
  assert.equal(row.exactVehicleFitment, false);
  assert.equal(row.repairProcedure, 0);
  assert.match(row.sourceRowSha256, /^[a-f0-9]{64}$/);
  assert.match(row.sourceSnapshotSha256, /^[a-f0-9]{64}$/);
  assert.match(row.databaseSha256, /^[a-f0-9]{64}$/);
  assert.ok(row.sourceTitle);
  assert.ok(row.sourcePage);
  assert.ok(row.sourceUrl);
  assert.ok(row.pageUrl);
  assert.ok(row.verifiedAt);
  assert.match(row.warning, /Рынок UNKNOWN/);
});

test("CarDir search uses the normalized Russian and Latin search index", () => {
  const russian = searchCardirFacts("объём моторного масла", 10, researchRoot);
  const latin = searchCardirFacts("Volkswagen", 10, researchRoot);
  assert.ok(russian.length > 0);
  assert.ok(latin.length > 0);
  assert.ok(russian.every((row) => row.sourceRowSha256.length === 64));
  assert.ok(latin.every((row) => row.marketScope === "UNKNOWN"));
});

test("CarDir search validates query and limit", () => {
  assert.throws(() => searchCardirFacts("x", 10), /минимум два символа/);
  assert.throws(() => searchCardirFacts("Octavia", 0), /от 1 до 50/);
  assert.throws(() => searchCardirFacts("Octavia", 51), /от 1 до 50/);
});
