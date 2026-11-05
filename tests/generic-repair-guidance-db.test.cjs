"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { DatabaseSync } = require("node:sqlite");
const guidance = require("../lib/generic-repair-guidance-db.cjs");
const localResearch = require("../lib/local-research-db.cjs");

const root = path.resolve(__dirname, "../data/research");
const packDir = path.join(root, "mechanicdb-generic-repair-guidance-odbl");

test("generic MechanicDB guidance is licensed, attributed and candidate-only", () => {
  const summary = guidance.getSummary(root);
  assert.equal(summary.id, "mechanicdb-generic-repair-guidance-odbl");
  assert.equal(summary.license, "ODbL-1.0");
  assert.equal(summary.attributionRequired, true);
  assert.equal(summary.shareAlikeRequired, true);
  assert.equal(summary.counts.genericDtcReferences, 75);
  assert.equal(summary.counts.genericRepairGuidance, 275);
  assert.equal(summary.counts.manufacturerLabelledDtcRowsExcluded, 15);
  assert.equal(summary.counts.manufacturerLabelledGuidanceRowsExcluded, 51);
  assert.equal(summary.marketScope, "UNKNOWN");
  assert.equal(summary.applicabilityPrecision, "generic_code_only");
  assert.equal(summary.vagSpecific, false);
  assert.equal(summary.exactVehicleFitment, false);
  assert.equal(summary.modelGenerationYearFitment, false);
  assert.equal(summary.engineGearboxFitment, false);
  assert.equal(summary.ecuFitment, false);
  assert.equal(summary.diagnosticExecutionAllowed, false);
  assert.equal(summary.oemRepairProcedure, false);
  assert.equal(summary.technicalReviewStatus, "not_independently_reviewed");
  assert.equal(summary.safetyReviewStatus, "not_assessed");
  assert.match(summary.databaseSha256, /^[a-f0-9]{64}$/);
  assert.match(summary.sourceManifestSha256, /^[a-f0-9]{64}$/);
});

test("generic repair guidance stays in its own namespace with complete row provenance", () => {
  const rows = guidance.search("P0011", 25, root);
  assert.ok(rows.length >= 2);
  for (const row of rows) {
    assert.equal(row.dtcCode, "P0011");
    assert.equal(row.namespace, "generic_sae_iso");
    assert.equal(row.manufacturer, "UNKNOWN");
    assert.equal(row.marketScope, "UNKNOWN");
    assert.equal(row.applicabilityLevel, "generic_only");
    assert.equal(row.vagSpecific, false);
    assert.equal(row.exactVehicleFitment, false);
    assert.equal(row.modelGenerationYearFitment, false);
    assert.equal(row.engineGearboxFitment, false);
    assert.equal(row.ecuFitment, false);
    assert.equal(row.diagnosticExecutionAllowed, false);
    assert.equal(row.oemRepairProcedure, false);
    assert.equal(row.considerationOrderIsProbability, false);
    assert.equal(row.technicalReviewStatus, "not_independently_reviewed");
    assert.equal(row.safetyReviewStatus, "not_assessed");
    assert.match(row.sourceFileSha256, /^[a-f0-9]{64}$/);
    assert.match(row.sourceLineSha256, /^[a-f0-9]{64}$/);
    assert.match(row.sourceSnapshotSha256, /^[a-f0-9]{64}$/);
    assert.match(row.sourceManifestSha256, /^[a-f0-9]{64}$/);
    assert.match(row.databaseSha256, /^[a-f0-9]{64}$/);
    assert.ok(row.sourceFileUrl.startsWith("https://raw.githubusercontent.com/"));
  }
});

test("generic guidance does not leak into other DTC or manufacturer-candidate searches", () => {
  const genericRows = localResearch.searchGenericDtcs("P0011", 10, root);
  assert.ok(genericRows.length > 0);
  assert.ok(genericRows.every((row) => !Object.hasOwn(row, "instructions")));
  assert.ok(genericRows.every((row) => row.license === "CC0-1.0"));
  if (typeof localResearch.searchMechanicDbCandidates === "function") {
    assert.deepEqual(localResearch.searchMechanicDbCandidates("P0011", 10, root), []);
  }
});

test("generic guidance search validates query length and bounds result count", () => {
  assert.throws(() => guidance.search("P", 10, root), /at least 2 characters/);
  assert.throws(() => guidance.search("x".repeat(101), 10, root), /too long/);
  assert.ok(guidance.search("P0", 500, root).length <= 50);
});

test("generic guidance database is opened read-only", () => {
  const db = new DatabaseSync(path.join(packDir, "generic-repair-guidance.sqlite"), { readOnly: true });
  assert.throws(() => db.exec("DELETE FROM generic_repair_guidance WHERE guidance_id=(SELECT guidance_id FROM generic_repair_guidance LIMIT 1)"), /readonly|read-only|query only/i);
  db.close();
});

test("generic guidance verifier rejects a tampered SQLite file", () => {
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), "vag-generic-guidance-tamper-"));
  try {
    fs.cpSync(root, temp, { recursive: true });
    const target = path.join(temp, "mechanicdb-generic-repair-guidance-odbl", "generic-repair-guidance.sqlite");
    fs.appendFileSync(target, Buffer.from([0]));
    assert.throws(() => guidance.verifyPack(temp), /SHA-256 mismatch/);
  } finally {
    fs.rmSync(temp, { recursive: true, force: true });
  }
});

test("generic guidance verifier rejects root-manifest path traversal", () => {
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), "vag-generic-guidance-path-"));
  try {
    fs.cpSync(root, temp, { recursive: true });
    const manifestPath = path.join(temp, "manifest.json");
    const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
    const entry = manifest.packs.find((item) => item.id === "mechanicdb-generic-repair-guidance-odbl");
    entry.source_manifest_file = "../../outside.json";
    fs.writeFileSync(manifestPath, JSON.stringify(manifest));
    assert.throws(() => guidance.verifyPack(temp), /escaped its root|Unsafe research path/);
  } finally {
    fs.rmSync(temp, { recursive: true, force: true });
  }
});
