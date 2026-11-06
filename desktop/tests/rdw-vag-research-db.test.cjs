"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { DatabaseSync } = require("node:sqlite");
const { getRdwSummary, searchRdwApprovals } = require("../lib/rdw-vag-research-db.cjs");

const root = process.env.VAG_TECH_PRO_RESEARCH_DIR || path.resolve(__dirname, "../data/research");
const PACK_ID = "rdw-vag-nl-eu-type-approval-research";

function openPack() {
  const desktopManifest = JSON.parse(fs.readFileSync(path.join(root, "manifest.json"), "utf8"));
  const entry = desktopManifest.packs.find((item) => item.id === PACK_ID);
  assert.ok(entry, "RDW NL/EU pack must be present in the packaged research manifest");
  return new DatabaseSync(path.resolve(root, entry.database), { readOnly: true });
}

test("RDW NL/EU pack verifies CC0 rights, source hashes, SQLite integrity and market boundary", () => {
  const summary = getRdwSummary(root);
  assert.equal(summary.marketScope, "NL");
  assert.equal(summary.license, "CC0-1.0");
  assert.equal(summary.rightsStatus, "approved_by_published_CC0_license");
  assert.equal(summary.productionImport, false);
  assert.equal(summary.productImportAllowed, false);
  assert.equal(summary.ruEaeuApplicability, false);
  assert.equal(summary.exactVehicleFitment, false);
  assert.equal(summary.exactEngineGearboxPair, false);
  assert.equal(summary.repairApplicability, false);
  assert.equal(summary.diagnosticExecutionAllowed, false);
  assert.equal(summary.counts.sourceFiles, 6);
  assert.ok(summary.counts.approvalScopes > 0);
  assert.ok(summary.counts.registrationObservations > 0);
  assert.ok(summary.counts.engineCandidates > 0);
  assert.ok(summary.counts.gearboxClassifications > 0);
  assert.match(summary.databaseSha256, /^[a-f0-9]{64}$/);
  assert.match(summary.sourceManifestSha256, /^[a-f0-9]{64}$/);
  assert.match(summary.sourceSnapshotSha256, /^[a-f0-9]{64}$/);
  assert.match(summary.attributionText, /RDW Open Data/);
  assert.match(summary.warning, /not Russian\/EAEU/i);
});

test("RDW search keeps approval scopes, engine designations and gearbox classifications separate", () => {
  const db = openPack();
  let approvalNumber;
  let engineDesignation;
  let gearboxClassification;
  try {
    approvalNumber = db.prepare("SELECT type_approval_number FROM approval_scope ORDER BY type_approval_number LIMIT 1").get()?.type_approval_number;
    engineDesignation = db.prepare("SELECT engine_designation FROM engine_designation_candidates WHERE engine_designation IS NOT NULL AND trim(engine_designation)<>'' ORDER BY engine_designation LIMIT 1").get()?.engine_designation;
    gearboxClassification = db.prepare("SELECT gearbox_type_classification FROM gearbox_classifications WHERE gearbox_type_classification IS NOT NULL AND trim(gearbox_type_classification)<>'' ORDER BY gearbox_type_classification LIMIT 1").get()?.gearbox_type_classification;
  } finally {
    db.close();
  }
  assert.ok(approvalNumber);
  assert.ok(engineDesignation);
  assert.ok(gearboxClassification);

  const approvalRows = searchRdwApprovals(approvalNumber, 10, root);
  const approval = approvalRows.find((row) => row.recordKind === "approval_scope" && row.approvalNumber === approvalNumber);
  assert.ok(approval);
  assert.equal(approval.marketScope, "NL");
  assert.equal(approval.exactVehicleFitment, false);
  assert.equal(approval.ruEaeuApplicability, false);
  assert.equal(approval.modelYear, null);
  assert.equal(approval.generation, null);

  const engineRows = searchRdwApprovals(engineDesignation, 10, root);
  const engine = engineRows.find((row) => row.recordKind === "engine_candidate" && row.engineDesignation === engineDesignation);
  assert.ok(engine);
  assert.equal(engine.marketScope, "NL");
  assert.equal(engine.engineCode, null);
  assert.equal(engine.factoryVagEngineCodeClaim, false);
  assert.equal(engine.exactEngineGearboxPair, false);
  assert.equal(engine.repairApplicability, false);
  assert.equal(engine.diagnosticExecutionAllowed, false);

  const gearboxRows = searchRdwApprovals(gearboxClassification, 10, root);
  const gearbox = gearboxRows.find((row) => row.recordKind === "gearbox_classification" && row.gearboxTypeClassification === gearboxClassification);
  assert.ok(gearbox);
  assert.equal(gearbox.marketScope, "NL");
  assert.equal(gearbox.gearboxCode, null);
  assert.equal(gearbox.factoryVagGearboxCodeClaim, false);
  assert.equal(gearbox.exactEngineGearboxPair, false);
  assert.equal(gearbox.repairApplicability, false);
  assert.equal(gearbox.diagnosticExecutionAllowed, false);

  assert.notEqual(engine.recordKind, gearbox.recordKind);
  assert.equal(Object.hasOwn(engine, "engineGearboxPair"), false);
  assert.equal(Object.hasOwn(gearbox, "engineGearboxPair"), false);
  assert.match(engine.warning, /не OEM-подтверждённый код VAG/);
  assert.match(gearbox.warning, /не VAG-код КПП/);
});

test("RDW search rejects undersized and oversized queries", () => {
  assert.throws(() => searchRdwApprovals("A", 10, root), /минимум два символа/);
  assert.throws(() => searchRdwApprovals("x".repeat(101), 10, root), /длинный/);
});
