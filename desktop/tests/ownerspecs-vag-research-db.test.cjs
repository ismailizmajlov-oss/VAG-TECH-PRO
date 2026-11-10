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
  assert.equal(summary.sourceFileBytes, 683641);
  assert.match(summary.sourceSnapshotSha256, /^[a-f0-9]{64}$/);
  assert.match(summary.sourceSnapshotFileSha256, /^[a-f0-9]{64}$/);
  assert.match(summary.sourceManifestSha256, /^[a-f0-9]{64}$/);
  assert.equal(summary.sourceFileSha256, "7b39e1183bd2a7617d43fdbe1f2ae64662520cb62f89ba8fec4dadbcce79204d");
  assert.equal(summary.sourceSnapshotSha256, "7b39e1183bd2a7617d43fdbe1f2ae64662520cb62f89ba8fec4dadbcce79204d");
  assert.equal(summary.sourceSnapshotFileSha256, "07441a2d7bb098b394a516cbb02e78d5a19dac0aa98baa66036f0014c6070c7a");
  assert.equal(summary.sourceManifestSha256, "3cccc31845fad9328db2e81dc70e787552ec192c780c140904baa6c9132abdeb");
  assert.equal(summary.databaseSha256, "eba46aace1e2a28d288e64b2dcb179177ddc577a9b90771d6908d18319c96ecf");
  assert.equal(summary.packManifestSha256, "7d47964b15d787c9ae1ebf5a16b5f0fa2082d9bc64c0fbe7e44a660b8c299a57");
  assert.equal(summary.artifactSha256, "441e5626796acb315ebf428e7e6acf5bdab93276335267fac639c23d21cdefe3");
  assert.equal(summary.sourceRetrievedAtUtc, "2026-11-10T01:29:53.763466+00:00");
  assert.equal(summary.acquisitionRetrievedAtUtc, "2026-11-10T03:57:09.290754+00:00");
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
