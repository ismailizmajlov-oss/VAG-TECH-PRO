"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");
const { getOwnerSpecsSummary, searchOwnerSpecsFacts } = require("../lib/ownerspecs-vag-research-db.cjs");
const researchRoot = path.resolve(__dirname, "../data/research");

test("OwnerSpecs pack is a hash-verified, isolated CC BY-SA research-only SQLite", () => {
  const summary = getOwnerSpecsSummary(researchRoot);
  assert.deepEqual(summary.counts, { sourceGenerations: 111, sourceFacts: 2369, vagGenerations: 20, vagFacts: 233 });
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
  assert.equal(summary.sourceFileBytes, 683533);
  assert.match(summary.sourceSnapshotSha256, /^[a-f0-9]{64}$/);
  assert.match(summary.sourceSnapshotFileSha256, /^[a-f0-9]{64}$/);
  assert.match(summary.sourceManifestSha256, /^[a-f0-9]{64}$/);
  assert.equal(summary.sourceFileSha256, "6ed73e4cd634e64501edd3b0e03405afa0aad3b8d1a103f78b839c87c8588c95");
  assert.equal(summary.sourceSnapshotSha256, "6ed73e4cd634e64501edd3b0e03405afa0aad3b8d1a103f78b839c87c8588c95");
  assert.equal(summary.sourceSnapshotFileSha256, "c5c17ffb46dc2300a0b5eb9ef57a2877ea8be52a40cc657fccc38f3b1c45b01c");
  assert.equal(summary.sourceManifestSha256, "3d744c8b813508daefaebcd690d10c2cef6d0a731e87eda59015622bffeabbdc");
  assert.equal(summary.databaseSha256, "572455b8054bd93600fb5ef25d38c6aa478a5bc98a0d26d678a220b008d4d683");
  assert.equal(summary.packManifestSha256, "35bbe697d046891c1f49e8f5a318fa2f6f1afab087a7c20d8718ab4c02c9f6dd");
  assert.equal(summary.artifactSha256, "93c4050130a8d372888ffd3126e18d4ef03de434558adfc98f7bb51e0a6918d1");
  assert.equal(summary.sourceRetrievedAtUtc, "2026-11-10T06:28:05.310530+00:00");
  assert.equal(summary.acquisitionRetrievedAtUtc, "2026-11-10T06:43:59.091416+00:00");
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
