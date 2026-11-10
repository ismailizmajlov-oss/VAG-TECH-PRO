"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawnSync } = require("node:child_process");
const test = require("node:test");

const PATCH = path.join(__dirname, "..", "apply-vehiclesdb-candidate-count-guard-run93.cjs");

function fixture(overrides = {}) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "vag-vehiclesdb-run93-"));
  const research = path.join(root, "data", "research", "vehiclesdb-vag-identity");
  fs.mkdirSync(research, { recursive: true });
  fs.mkdirSync(path.join(root, "lib"), { recursive: true });
  fs.mkdirSync(path.join(root, "scripts"), { recursive: true });
  fs.mkdirSync(path.join(root, "tests"), { recursive: true });
  const manifest = {
    pack_id: "vehiclesdb-vag-identity",
    source_revision: "v2026.11.3",
    dataset_license: "CC-BY-4.0",
    market_scope: "foreign_market_presence_only",
    fitment_status: "not_established",
    fitment_claim: false,
    exact_fitment: false,
    ru_evidence_present: false,
    engine_codes_included: false,
    gearbox_codes_included: false,
    ecu_fitment_included: false,
    identity_only_use: true,
    safety_critical_reliance: false,
    repair_decision_use: false,
    open_data_policy_notice: "VehiclesDB is not designed or warranted for safety-critical reliance; identity-only and not for repair decisions.",
    counts: { sources: 14, models: 307, market_evidence: 1621 },
    ...overrides
  };
  fs.writeFileSync(path.join(research, "manifest.json"), JSON.stringify(manifest, null, 2));
  const oldCountGate = "vehiclesDbCounts.sources !== 14 || vehiclesDbCounts.models !== 260 || vehiclesDbCounts.marketEvidence !== 1524 || vehiclesDbCounts.russianEvidence !== 0 ||";
  const oldReturn = [
    "attributionRequired: true,",
    '        attribution: packManifest.attribution?.display_form || "Vehicle data by VehiclesDB (vehiclesdb.com)",'
  ].join("\n");
  fs.writeFileSync(path.join(root, "lib", "local-research-db.cjs"), oldCountGate + "\n" + oldReturn + "\n");
  fs.writeFileSync(path.join(root, "scripts", "verify-local-research-packs.cjs"),
    'assert(vehiclesDbSnapshot.attribution?.required === true && /Vehicle data by VehiclesDB/i.test(vehiclesDbAttribution) && /UNCONDITIONAL/i.test(vehiclesDbAttribution), "VehiclesDB attribution and upstream notices are incomplete");\n');
  fs.writeFileSync(path.join(root, "tests", "local-research-db.test.cjs"),
    '  assert.equal(golf.sourceRevision, vehiclesDbManifest.source_revision);\n');
  return root;
}

function run(root) {
  return spawnSync(process.execPath, [PATCH, "--desktop-root", root], { encoding: "utf8" });
}

test("run93 binds current VehiclesDB counts and safety policy into desktop search and verifier", () => {
  const root = fixture();
  try {
    const first = run(root);
    assert.equal(first.status, 0, first.stderr);
    const db = fs.readFileSync(path.join(root, "lib", "local-research-db.cjs"), "utf8");
    const verifier = fs.readFileSync(path.join(root, "scripts", "verify-local-research-packs.cjs"), "utf8");
    const tests = fs.readFileSync(path.join(root, "tests", "local-research-db.test.cjs"), "utf8");
    assert.match(db, /vehiclesDbCounts\.models !== vehiclesDbPackManifest\.counts\?\.models/);
    assert.match(db, /vehiclesDbCounts\.marketEvidence !== vehiclesDbPackManifest\.counts\?\.market_evidence/);
    assert.match(db, /safety_critical_reliance !== false/);
    assert.match(db, /identityOnlyUse: packManifest\.identity_only_use/);
    assert.match(db, /safetyCriticalReliance: packManifest\.safety_critical_reliance/);
    assert.match(db, /repairDecisionUse: packManifest\.repair_decision_use/);
    assert.match(verifier, /VehiclesDB safety-critical and repair-decision boundary failed/);
    assert.match(tests, /assert\.equal\(golf\.safetyCriticalReliance, false\)/);
    const evidence = JSON.parse(fs.readFileSync(path.join(root, "data", "research", "vehiclesdb-vag-identity", "desktop-candidate-boundary-verification.json"), "utf8"));
    assert.equal(evidence.status, "vehiclesdb_identity_only_dynamic_count_gate_applied");
    assert.deepEqual(evidence.counts, { sources: 14, models: 307, market_evidence: 1621 });
    assert.equal(evidence.safety_critical_reliance, false);
    const second = run(root);
    assert.equal(second.status, 0, second.stderr);
    assert.equal(JSON.parse(second.stdout).status, "vehiclesdb_identity_only_dynamic_count_gate_applied");
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test("run93 composes after run68's manifest-driven count guard without rewriting it", () => {
  const root = fixture();
  try {
    const dbPath = path.join(root, "lib", "local-research-db.cjs");
    const before = fs.readFileSync(dbPath, "utf8");
    const legacy = "vehiclesDbCounts.sources !== 14 || vehiclesDbCounts.models !== 260 || vehiclesDbCounts.marketEvidence !== 1524 || vehiclesDbCounts.russianEvidence !== 0 ||";
    const dynamic = [
      "vehiclesDbCounts.sources !== 14 ||",
      "vehiclesDbCounts.models !== vehiclesDbPackManifest.counts?.models ||",
      "vehiclesDbCounts.marketEvidence !== vehiclesDbPackManifest.counts?.market_evidence ||",
      "vehiclesDbCounts.russianEvidence !== 0 ||",
      "vehiclesDbPackManifest.identity_only_use !== true ||",
      "vehiclesDbPackManifest.safety_critical_reliance !== false ||",
      "vehiclesDbPackManifest.repair_decision_use !== false ||",
      "typeof vehiclesDbPackManifest.open_data_policy_notice !== \\"string\\" ||",
      "!vehiclesDbPackManifest.open_data_policy_notice.includes(\\"not designed or warranted for safety-critical\\") ||"
    ].join("\\n        ");
    assert.equal(before.split(legacy).length - 1, 1);
    fs.writeFileSync(dbPath, before.replace(legacy, dynamic));
    const afterRun68 = fs.readFileSync(dbPath, "utf8");
    const first = run(root);
    assert.equal(first.status, 0, first.stderr);
    const afterRun93 = fs.readFileSync(dbPath, "utf8");
    assert.equal(afterRun93.split(dynamic).length - 1, 1, "run93 must preserve run68's already-aligned predicate");
    assert.match(afterRun93, /identityOnlyUse: packManifest\\.identity_only_use/);
    assert.match(afterRun93, /safetyCriticalReliance: packManifest\\.safety_critical_reliance/);
    assert.match(afterRun93, /repairDecisionUse: packManifest\\.repair_decision_use/);
    assert.notEqual(afterRun93, afterRun68, "run93 must still add the returned identity-only policy fields");
    const evidence = JSON.parse(fs.readFileSync(path.join(root, "data", "research", "vehiclesdb-vag-identity", "desktop-candidate-boundary-verification.json"), "utf8"));
    assert.equal(evidence.status, "vehiclesdb_identity_only_dynamic_count_gate_applied");
    const second = run(root);
    assert.equal(second.status, 0, second.stderr);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test("run93 rejects a VehiclesDB pack that permits safety-critical reliance without modifying desktop files", () => {
  const root = fixture({ safety_critical_reliance: true });
  try {
    const dbPath = path.join(root, "lib", "local-research-db.cjs");
    const before = fs.readFileSync(dbPath, "utf8");
    const result = run(root);
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /identity-only, market, count or safety-use boundary/);
    assert.equal(fs.readFileSync(dbPath, "utf8"), before);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});
