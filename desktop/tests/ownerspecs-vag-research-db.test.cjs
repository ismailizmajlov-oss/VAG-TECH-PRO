"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");
const { getOwnerSpecsSummary, searchOwnerSpecsFacts } = require("../lib/ownerspecs-vag-research-db.cjs");
const researchRoot = path.resolve(__dirname, "../data/research");

test("OwnerSpecs pack is a hash-verified, isolated CC BY-SA research-only SQLite", () => {
  const summary = getOwnerSpecsSummary(researchRoot);
  assert.deepEqual(summary.counts, { sourceGenerations: 111, sourceFacts: 2273, vagGenerations: 20, vagFacts: 186 });
  assert.equal(summary.marketScope, "UNKNOWN");
  assert.equal(summary.schemaVersion, 1);
  assert.equal(summary.status, "verified_research_only");
  assert.equal(summary.packBuildStatus, "verified_research_only");
  assert.equal(summary.license, "CC BY-SA 4.0");
  assert.equal(summary.productionImport, false);
  assert.equal(summary.productImportAllowed, false);
  assert.equal(summary.criticalTechnicalValuesPublishable, false);
  assert.equal(summary.exactEngineGearboxPair, false);
  assert.equal(summary.ruEaeuApplicability, false);
  assert.match(summary.databaseSha256, /^[a-f0-9]{64}$/);
  assert.match(summary.sourceFileSha256, /^[a-f0-9]{64}$/);
  assert.equal(summary.sourceFileBytes, 659973);
  assert.match(summary.sourceSnapshotSha256, /^[a-f0-9]{64}$/);
  assert.match(summary.sourceSnapshotFileSha256, /^[a-f0-9]{64}$/);
  assert.match(summary.sourceManifestSha256, /^[a-f0-9]{64}$/);
  assert.equal(summary.sourceFileSha256, "d702e4572a4e640c0295c40970ef3c0da2db3703c829c5e3d96cebb4acccacc9");
  assert.equal(summary.sourceSnapshotSha256, "d702e4572a4e640c0295c40970ef3c0da2db3703c829c5e3d96cebb4acccacc9");
  assert.equal(summary.sourceSnapshotFileSha256, "77ea356babebed51fd9f6f6b1afad75aaed69038b4f27a2d67621fb37c1ad195");
  assert.equal(summary.sourceManifestSha256, "ed221369ae9195cad18194602a75b17d4ab8aa5908dceb503fc2ca0bfa725697");
  assert.equal(summary.databaseSha256, "9b7da5b490d3dd805865f23389cb8cc7ca9b368137be8307adb07e0c8e683c4a");
  assert.equal(summary.packManifestSha256, "21c94e2ec39ea1b231b96d3fe5f830e5ac62ae5cfc1d8e91312de977d8819fd4");
  assert.equal(summary.artifactSha256, "66c764501b3071958b9c1949f3be15908a27ee280c1e2fdd1985c5b934be8c77");
  assert.equal(summary.sourceRetrievedAtUtc, "2026-11-11T05:56:12+00:00");
  assert.equal(summary.acquisitionRetrievedAtUtc, "2026-11-11T06:19:19.940448+00:00");
});

test("OwnerSpecs search returns raw candidate facts with row-level provenance", () => {
  const rows = searchOwnerSpecsFacts("A1", 20, researchRoot);
  assert.ok(rows.length > 0);
  const row = rows.find((item) => item.brand === "Audi" && item.model === "A1");
  assert.ok(row);
  assert.equal(row.marketScope, "UNKNOWN");
  assert.equal(row.publisherVerificationStatus, "publisher_verified");
  assert.equal(row.technicalReviewStatus, "not_independently_reviewed");
  assert.equal(row.applicabilityPrecision, "publisher_generation_candidate_only");
  assert.equal(row.criticalValuePublishable, 0);
  assert.equal(row.exactVehicleFitment, false);
  assert.equal(row.exactEngineGearboxPair, false);
  assert.equal(row.ruEaeuApplicability, false);
  assert.equal(row.primaryDocumentUrl, null);
  assert.equal(row.primaryDocumentRevision, null);
  assert.match(row.sourceRowSha256, /^[a-f0-9]{64}$/);
  assert.match(row.generationSha256, /^[a-f0-9]{64}$/);
  assert.match(row.sourceSnapshotSha256, /^[a-f0-9]{64}$/);
  assert.match(row.databaseSha256, /^[a-f0-9]{64}$/);
  assert.match(row.warning, /not independently reviewed|not independently reviewed|not independently reviewed/i);
});

test("OwnerSpecs torque and fluid values remain non-publishable candidates", () => {
  const rows = searchOwnerSpecsFacts("torque_lug_nut", 20, researchRoot);
  assert.ok(rows.length > 0);
  assert.ok(rows.every((row) => row.criticalValuePublishable === 0 && row.marketScope === "UNKNOWN" &&
    row.exactEngineGearboxPair === false && row.ruEaeuApplicability === false));
});

test("OwnerSpecs search validates query and result limit", () => {
  assert.throws(() => searchOwnerSpecsFacts("x", 10, researchRoot), /минимум два символа/);
  assert.throws(() => searchOwnerSpecsFacts("A1", 0, researchRoot), /от 1 до 50/);
  assert.throws(() => searchOwnerSpecsFacts("A1", 51, researchRoot), /от 1 до 50/);
});
