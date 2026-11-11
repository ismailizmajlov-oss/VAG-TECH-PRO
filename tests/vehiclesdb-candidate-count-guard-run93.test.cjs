"use strict";

const assert = require("node:assert/strict");
const crypto = require("node:crypto");
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
  const candidateFunction = [
    "function searchVehiclesDbCandidates() {",
    "  const marketEvidence = [{ attributionRequired: true, attribution: \"market evidence\" }];",
    "      return {",
    "        sourceModelId: row.source_model_id,",
    "        attributionRequired: true,",
    '        attribution: packManifest.attribution?.display_form || "Vehicle data by VehiclesDB (vehiclesdb.com)",',
    "      };",
    "}",
    "",
    "function getWikidataGenerationSummary() {",
    "  return { attributionRequired: true, attribution: \"Wikidata attribution\" };",
    "}",
    "",
    "module.exports = {};"
  ].join("\n");
  fs.writeFileSync(path.join(root, "lib", "local-research-db.cjs"), oldCountGate + "\n" + candidateFunction + "\n");
  const tick = String.fromCharCode(96);
  const dollar = String.fromCharCode(36);
  const interpolation = dollar + "{JSON.stringify(vehiclesDbCounts)}";
  const oldVerifierCountGate = "assert(vehiclesDbCounts.sources === 14 && vehiclesDbCounts.models === 260 && vehiclesDbCounts.marketEvidence === 1524 && vehiclesDbCounts.russianEvidence === 0, " + tick + "VehiclesDB foreign-market-only count gate failed: " + interpolation + tick + ");";
  const oldVerifierBoundary = 'assert(vehiclesDbSnapshot.attribution?.required === true && /Vehicle data by VehiclesDB/i.test(vehiclesDbAttribution) && /UNCONDITIONAL/i.test(vehiclesDbAttribution), "VehiclesDB attribution and upstream notices are incomplete");';
  fs.writeFileSync(path.join(root, "scripts", "verify-local-research-packs.cjs"), oldVerifierCountGate + "\n" + oldVerifierBoundary + "\n");
  fs.writeFileSync(path.join(root, "tests", "local-research-db.test.cjs"),
    '  assert.equal(golf.sourceRevision, vehiclesDbManifest.source_revision);\n');
  fs.writeFileSync(path.join(root, "tests", "local-research-packs.test.cjs"), [
    "  assert.equal(result.vehiclesdb_identity.sources, 14);",
    "  assert.equal(result.vehiclesdb_identity.models, 260);",
    "  assert.equal(result.vehiclesdb_identity.marketEvidence, 1524);"
  ].join("\n") + "\n");
  return root;
}

function run(root) {
  return spawnSync(process.execPath, [PATCH, "--desktop-root", root], { encoding: "utf8" });
}

test("run93 binds current VehiclesDB counts and safety policy into desktop search, verifiers and research-pack test", () => {
  const root = fixture();
  try {
    const first = run(root);
    assert.equal(first.status, 0, first.stderr);
    const db = fs.readFileSync(path.join(root, "lib", "local-research-db.cjs"), "utf8");
    const verifier = fs.readFileSync(path.join(root, "scripts", "verify-local-research-packs.cjs"), "utf8");
    const tests = fs.readFileSync(path.join(root, "tests", "local-research-db.test.cjs"), "utf8");
    const researchPacksTest = fs.readFileSync(path.join(root, "tests", "local-research-packs.test.cjs"), "utf8");
    assert.match(db, /vehiclesDbCounts\.models !== vehiclesDbPackManifest\.counts\?\.models/);
    assert.match(db, /vehiclesDbCounts\.marketEvidence !== vehiclesDbPackManifest\.counts\?\.market_evidence/);
    assert.match(db, /safety_critical_reliance !== false/);
    assert.match(db, /identityOnlyUse: packManifest\.identity_only_use/);
    assert.match(db, /sourceModelId: row\.source_model_id/);
    assert.match(db, /marketEvidence = \[\{ attributionRequired: true, attribution: "market evidence" \}\]/);
    assert.match(db, /function getWikidataGenerationSummary\(\) \{\s*return \{ attributionRequired: true, attribution: "Wikidata attribution" \}/);
    assert.match(db, /safetyCriticalReliance: packManifest\.safety_critical_reliance/);
    assert.match(db, /repairDecisionUse: packManifest\.repair_decision_use/);
    assert.match(verifier, /VehiclesDB safety-critical and repair-decision boundary failed/);
    assert.match(verifier, /vehiclesDbCounts\.models === vehiclesDbSnapshot\.counts\?\.models/);
    assert.match(verifier, /vehiclesDbCounts\.marketEvidence === vehiclesDbSnapshot\.counts\?\.market_evidence/);
    assert.match(tests, /assert\.equal\(golf\.safetyCriticalReliance, false\)/);
    assert.match(researchPacksTest, /vehiclesDbPackManifest\.counts\.sources/);
    assert.match(researchPacksTest, /vehiclesDbPackManifest\.counts\.models/);
    assert.match(researchPacksTest, /vehiclesDbPackManifest\.counts\.market_evidence/);
    assert.doesNotMatch(researchPacksTest, /vehiclesdb_identity\.models, 260/);
    assert.doesNotMatch(researchPacksTest, /vehiclesdb_identity\.marketEvidence, 1524/);
    const evidence = JSON.parse(fs.readFileSync(path.join(root, "data", "research", "vehiclesdb-vag-identity", "desktop-candidate-boundary-verification.json"), "utf8"));
    assert.equal(evidence.status, "vehiclesdb_identity_only_dynamic_count_gate_applied");
    assert.deepEqual(evidence.counts, { sources: 14, models: 307, market_evidence: 1621 });
    assert.equal(evidence.safety_critical_reliance, false);
    assert.match(evidence.research_packs_test_sha256, /^[a-f0-9]{64}$/);
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
      "typeof vehiclesDbPackManifest.open_data_policy_notice !== \"string\" ||",
      "!vehiclesDbPackManifest.open_data_policy_notice.includes(\"not designed or warranted for safety-critical\") ||"
    ].join("\n        ");
    assert.equal(before.split(legacy).length - 1, 1);
    fs.writeFileSync(dbPath, before.replace(legacy, dynamic));
    const afterRun68 = fs.readFileSync(dbPath, "utf8");
    const verifierPath = path.join(root, "scripts", "verify-local-research-packs.cjs");
    const verifierBefore = fs.readFileSync(verifierPath, "utf8");
    const legacyAttribution = 'assert(vehiclesDbSnapshot.attribution?.required === true && /Vehicle data by VehiclesDB/i.test(vehiclesDbAttribution) && /UNCONDITIONAL/i.test(vehiclesDbAttribution), "VehiclesDB attribution and upstream notices are incomplete");';
    const currentAttribution = 'assert(vehiclesDbSnapshot.attribution_required === true && /Vehicle data by VehiclesDB/i.test(vehiclesDbAttribution) && /UNCONDITIONAL/i.test(vehiclesDbAttribution), "VehiclesDB attribution and upstream notices are incomplete");';
    assert.equal(verifierBefore.split(legacyAttribution).length - 1, 1);
    const verifierWithCurrentSchema = verifierBefore.replace(legacyAttribution, currentAttribution);
    const tick = String.fromCharCode(96);
    const dollar = String.fromCharCode(36);
    const interpolation = dollar + "{JSON.stringify(vehiclesDbCounts)}";
    const oldVerifierCountGate = "assert(vehiclesDbCounts.sources === 14 && vehiclesDbCounts.models === 260 && vehiclesDbCounts.marketEvidence === 1524 && vehiclesDbCounts.russianEvidence === 0, " + tick + "VehiclesDB foreign-market-only count gate failed: " + interpolation + tick + ");";
    const run68VerifierCountGate = "assert(vehiclesDbCounts.sources === vehiclesDbSnapshot.counts?.sources && vehiclesDbCounts.models === vehiclesDbSnapshot.counts?.models && vehiclesDbCounts.marketEvidence === vehiclesDbSnapshot.counts?.market_evidence && vehiclesDbCounts.russianEvidence === 0, " + tick + "VehiclesDB foreign-market-only count gate failed: " + interpolation + tick + ");";
    assert.equal(verifierWithCurrentSchema.split(oldVerifierCountGate).length - 1, 1);
    fs.writeFileSync(verifierPath, verifierWithCurrentSchema.replace(oldVerifierCountGate, run68VerifierCountGate));
    const first = run(root);
    assert.equal(first.status, 0, first.stderr);
    const afterRun93 = fs.readFileSync(dbPath, "utf8");
    assert.equal(afterRun93.split(dynamic).length - 1, 1, "run93 must preserve run68's already-aligned predicate");
    assert.match(afterRun93, /identityOnlyUse: packManifest\.identity_only_use/);
    assert.match(afterRun93, /safetyCriticalReliance: packManifest\.safety_critical_reliance/);
    assert.match(afterRun93, /repairDecisionUse: packManifest\.repair_decision_use/);
    const verifier = fs.readFileSync(verifierPath, "utf8");
    assert.equal(verifier.split(run68VerifierCountGate).length - 1, 1, "run93 must preserve run68's already-aligned independent-verifier count predicate");
    assert.equal(verifier.split(currentAttribution).length - 1, 1, "run93 must preserve the current snake_case attribution predicate");
    assert.match(verifier, /vehiclesDbCounts\.models === vehiclesDbSnapshot\.counts\?\.models/);
    assert.match(verifier, /vehiclesDbCounts\.marketEvidence === vehiclesDbSnapshot\.counts\?\.market_evidence/);
    assert.match(verifier, /VehiclesDB safety-critical and repair-decision boundary failed/);
    assert.notEqual(afterRun93, afterRun68, "run93 must still add the returned identity-only policy fields");
    const evidence = JSON.parse(fs.readFileSync(path.join(root, "data", "research", "vehiclesdb-vag-identity", "desktop-candidate-boundary-verification.json"), "utf8"));
    assert.equal(evidence.status, "vehiclesdb_identity_only_dynamic_count_gate_applied");
    assert.match(evidence.research_packs_test_sha256, /^[a-f0-9]{64}$/);
    const second = run(root);
    assert.equal(second.status, 0, second.stderr);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test("run93 repairs a downstream legacy count assertion and refreshes only desktop evidence hashes", () => {
  const root = fixture();
  try {
    const first = run(root);
    assert.equal(first.status, 0, first.stderr);
    const evidencePath = path.join(root, "data", "research", "vehiclesdb-vag-identity", "desktop-candidate-boundary-verification.json");
    const firstEvidence = JSON.parse(fs.readFileSync(evidencePath, "utf8"));
    const priorEvidence = { ...firstEvidence, patch_sha256: "0".repeat(64) };
    fs.writeFileSync(evidencePath, JSON.stringify(priorEvidence, null, 2) + "\n");
    const testPath = path.join(root, "tests", "local-research-packs.test.cjs");
    const dynamicBlock = [
      '  const vehiclesDbPackManifest = JSON.parse(require("node:fs").readFileSync(require("node:path").join(__dirname, "../data/research/vehiclesdb-vag-identity/manifest.json"), "utf8"));',
      "  assert.equal(result.vehiclesdb_identity.sources, vehiclesDbPackManifest.counts.sources);",
      "  assert.equal(result.vehiclesdb_identity.models, vehiclesDbPackManifest.counts.models);",
      "  assert.equal(result.vehiclesdb_identity.marketEvidence, vehiclesDbPackManifest.counts.market_evidence);"
    ].join("\n");
    const legacyBlock = [
      "  assert.equal(result.vehiclesdb_identity.sources, 14);",
      "  assert.equal(result.vehiclesdb_identity.models, 260);",
      "  assert.equal(result.vehiclesdb_identity.marketEvidence, 1524);"
    ].join("\n");
    const beforeDownstream = fs.readFileSync(testPath, "utf8");
    assert.ok(beforeDownstream.includes(dynamicBlock));
    fs.writeFileSync(testPath, beforeDownstream.replace(
      dynamicBlock,
      legacyBlock + '\n  assert.equal(result.kba_de_vag_stock.marketScope, "DE");'
    ));
    const verifierPath = path.join(root, "scripts", "verify-local-research-packs.cjs");
    fs.appendFileSync(verifierPath, "\n// downstream licensed-pack verifier extension\n");

    const second = run(root);
    assert.equal(second.status, 0, second.stderr);
    const repairedTest = fs.readFileSync(testPath, "utf8");
    assert.ok(repairedTest.includes(dynamicBlock));
    assert.ok(repairedTest.includes('assert.equal(result.kba_de_vag_stock.marketScope, "DE");'));
    assert.doesNotMatch(repairedTest, /vehiclesdb_identity\.models, 260/);
    const secondEvidence = JSON.parse(fs.readFileSync(evidencePath, "utf8"));
    const digest = (value) => crypto.createHash("sha256").update(value).digest("hex");
    assert.equal(secondEvidence.research_packs_test_sha256, digest(fs.readFileSync(testPath)));
    assert.equal(secondEvidence.verifier_sha256, digest(fs.readFileSync(verifierPath)));
    assert.notEqual(firstEvidence.research_packs_test_sha256, secondEvidence.research_packs_test_sha256);
    assert.notEqual(firstEvidence.verifier_sha256, secondEvidence.verifier_sha256);
    assert.equal(secondEvidence.source_manifest_sha256, firstEvidence.source_manifest_sha256);
    assert.equal(secondEvidence.patch_sha256, digest(fs.readFileSync(PATCH)));
    assert.deepEqual(secondEvidence.counts, firstEvidence.counts);

    const third = run(root);
    assert.equal(third.status, 0, third.stderr);
    assert.deepEqual(JSON.parse(fs.readFileSync(evidencePath, "utf8")), secondEvidence);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test("run93 remains idempotent after downstream candidate-object extensions and repairs a missing policy field", () => {
  const root = fixture();
  try {
    const first = run(root);
    assert.equal(first.status, 0, first.stderr);
    const dbPath = path.join(root, "lib", "local-research-db.cjs");
    let db = fs.readFileSync(dbPath, "utf8");
    const oldAttribution = '    attribution: packManifest.attribution?.display_form || "Vehicle data by VehiclesDB (vehiclesdb.com)",';
    const downstreamAttribution = [
      '    downstreamResearchEvidence: "ownerspecs-cardir",',
      '    attribution: typeof packManifest.attribution === "string" ? packManifest.attribution : "Vehicle data by VehiclesDB (vehiclesdb.com)",'
    ].join("\n");
    assert.equal(db.split(oldAttribution).length - 1, 1);
    db = db.replace(oldAttribution, downstreamAttribution);
    db = db.replace("    repairDecisionUse: packManifest.repair_decision_use === true,\n", "");
    fs.writeFileSync(dbPath, db);
    const second = run(root);
    assert.equal(second.status, 0, second.stderr);
    const repaired = fs.readFileSync(dbPath, "utf8");
    assert.match(repaired, /downstreamResearchEvidence: "ownerspecs-cardir"/);
    assert.match(repaired, /attribution: typeof packManifest\.attribution === "string"/);
    assert.equal(repaired.split("repairDecisionUse: packManifest.repair_decision_use === true,").length - 1, 1);
    assert.equal(repaired.split("identityOnlyUse: packManifest.identity_only_use === true,").length - 1, 1);
    assert.equal(repaired.split("safetyCriticalReliance: packManifest.safety_critical_reliance === true,").length - 1, 1);
    assert.equal(repaired.split("openDataPolicyNotice: packManifest.open_data_policy_notice,").length - 1, 1);
    const third = run(root);
    assert.equal(third.status, 0, third.stderr);
    assert.equal(fs.readFileSync(dbPath, "utf8"), repaired);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test("run93 rejects a VehiclesDB pack that permits safety-critical reliance without modifying desktop files", () => {
  const root = fixture({ safety_critical_reliance: true });
  try {
    const dbPath = path.join(root, "lib", "local-research-db.cjs");
    const before = fs.readFileSync(dbPath, "utf8");
    const researchPacksTestBefore = fs.readFileSync(path.join(root, "tests", "local-research-packs.test.cjs"), "utf8");
    const result = run(root);
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /identity-only, market, count or safety-use boundary/);
    assert.equal(fs.readFileSync(dbPath, "utf8"), before);
    assert.equal(fs.readFileSync(path.join(root, "tests", "local-research-packs.test.cjs"), "utf8"), researchPacksTestBefore);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});
