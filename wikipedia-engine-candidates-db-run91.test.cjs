"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const reader = require("../lib/wikipedia-engine-candidates-db.cjs");
const researchRoot = path.join(__dirname, "..", "data", "research");

test("Wikipedia engine-code candidate pack is licensed, pinned and non-actionable", () => {
  const summary = reader.getSummary(researchRoot);
  assert.equal(summary.packId, "wikipedia-vag-engine-code-candidates-cc-by-sa-4-0");
  assert.equal(summary.license, "CC-BY-SA-4.0");
  assert.equal(summary.marketScope, "UNKNOWN");
  assert.equal(summary.applicabilityPrecision, "community_engine_code_candidate_only");
  assert.equal(summary.qualityReviewStatus, "not_approved_for_technical_use");
  assert.deepEqual(summary.counts, {
    sourceDocuments: 4,
    candidateRows: 241,
    uniqueCandidateCodes: 241,
    sourceRowsWithCodes: 64,
  });
  assert.equal(Object.keys(summary.sourceRevisions).length, 4);
  assert.equal(summary.productImportAllowed, false);
  assert.equal(summary.exactVehicleFitment, false);
  assert.equal(summary.generationYearFitment, false);
  assert.equal(summary.engineGearboxFitment, false);
  assert.equal(summary.ecuFitment, false);
  assert.equal(summary.dtcFitment, false);
  assert.equal(summary.repairUseAllowed, false);
  assert.equal(summary.diagnosticExecutionAllowed, false);
  assert.match(summary.attributionText, /CC BY-SA 4\.0/);
  assert.match(summary.licenseNoticeText, /CC BY-SA 4\.0/);
  assert.equal(summary.qualityWarnings.length >= 4, true);
});

test("Wikipedia candidate search returns row-level provenance and never fitment claims", () => {
  const rows = reader.searchCandidates("CHYA", 10, researchRoot);
  assert.ok(rows.length >= 1);
  const row = rows[0];
  assert.equal(row.candidateCode, "CHYA");
  assert.equal(row.marketScope, "UNKNOWN");
  assert.equal(row.applicabilityPrecision, "community_engine_code_candidate_only");
  assert.equal(row.reviewStatus, "candidate");
  assert.match(row.sourceUrl, /^https:\/\/en\.wikipedia\.org\/w\/index\.php\?oldid=\d+$/);
  assert.match(row.sourceRowSha256, /^[a-f0-9]{64}$/);
  assert.match(row.sourceSnapshotSha256, /^[a-f0-9]{64}$/);
  assert.match(row.sourceManifestSha256, /^[a-f0-9]{64}$/);
  for (const field of [
    "productImportAllowed", "exactVehicleFitment", "generationYearFitment",
    "engineGearboxFitment", "ecuFitment", "dtcFitment", "repairUseAllowed",
    "diagnosticExecutionAllowed",
  ]) assert.equal(row[field], false, field);
});

test("Wikipedia candidate search validates query and result limit", () => {
  assert.throws(() => reader.searchCandidates("x", 10, researchRoot), TypeError);
  assert.throws(() => reader.searchCandidates("CHYA", 51, researchRoot), TypeError);
  assert.deepEqual(reader.searchCandidates("NO-SUCH-VAG-ENGINE-CODE-999", 10, researchRoot), []);
});

test("Wikipedia candidate pack rejects a modified SQLite database", (t) => {
  const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), "vag-wikipedia-candidate-"));
  t.after(() => fs.rmSync(tempRoot, { recursive: true, force: true }));
  const source = path.join(researchRoot, "wikipedia-vag-engine-code-candidates-cc-by-sa-4-0");
  const target = path.join(tempRoot, "wikipedia-vag-engine-code-candidates-cc-by-sa-4-0");
  fs.cpSync(source, target, { recursive: true });
  fs.appendFileSync(path.join(target, "wikipedia-vag-engine-candidates.sqlite"), Buffer.from([0x00]));
  assert.throws(() => reader.getSummary(tempRoot), /SHA-256 mismatch/);
});
