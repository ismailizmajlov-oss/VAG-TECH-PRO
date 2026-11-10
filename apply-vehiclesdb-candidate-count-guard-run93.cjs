#!/usr/bin/env node
"use strict";

const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");

function fail(message) { throw new Error(message); }
function sha256(bytes) { return crypto.createHash("sha256").update(bytes).digest("hex"); }
function parseArgs(argv) {
  let desktopRoot = null;
  for (let i = 2; i < argv.length; i += 1) {
    if (argv[i] !== "--desktop-root" || !argv[i + 1]) fail("Usage: node apply-vehiclesdb-candidate-count-guard-run93.cjs --desktop-root <path>");
    desktopRoot = path.resolve(argv[++i]);
  }
  if (!desktopRoot) fail("Missing --desktop-root");
  return { desktopRoot };
}
function readRegular(root, relative) {
  const file = path.join(root, relative);
  const stat = fs.lstatSync(file);
  if (!stat.isFile() || stat.isSymbolicLink()) fail("Expected regular non-symlink file: " + relative);
  return { file, stat, text: fs.readFileSync(file, "utf8") };
}
function writeAtomic(file, content, mode = 0o644) {
  const temp = path.join(path.dirname(file), "." + path.basename(file) + "." + process.pid + ".run93.tmp");
  const backup = path.join(path.dirname(file), "." + path.basename(file) + "." + process.pid + ".run93.bak");
  let movedOld = false;
  try {
    fs.writeFileSync(temp, content, { flag: "wx", mode: mode & 0o777 });
    fs.chmodSync(temp, mode & 0o777);
    if (fs.existsSync(file)) {
      const current = fs.lstatSync(file);
      if (!current.isFile() || current.isSymbolicLink()) fail("Refusing to replace non-regular file: " + file);
      fs.renameSync(file, backup);
      movedOld = true;
    }
    fs.renameSync(temp, file);
    if (movedOld) fs.unlinkSync(backup);
  } catch (error) {
    if (movedOld && !fs.existsSync(file) && fs.existsSync(backup)) fs.renameSync(backup, file);
    throw error;
  } finally {
    if (fs.existsSync(temp)) fs.unlinkSync(temp);
    if (fs.existsSync(backup) && fs.existsSync(file)) fs.unlinkSync(backup);
  }
}
function replaceExactlyOnce(source, before, after, label) {
  const afterCount = source.split(after).length - 1;
  if (afterCount === 1) return { text: source, changed: false };
  if (afterCount > 1) fail(label + ": patched anchor appears more than once");
  const beforeCount = source.split(before).length - 1;
  if (beforeCount !== 1) {
    fail(label + ": expected exactly one legacy anchor or one already-patched anchor (legacy=" + beforeCount + ", patched=" + afterCount + ")");
  }
  return { text: source.replace(before, after), changed: true };
}
function main() {
  const { desktopRoot } = parseArgs(process.argv);
  const rootStat = fs.lstatSync(desktopRoot);
  if (!rootStat.isDirectory() || rootStat.isSymbolicLink()) fail("Desktop root must be a regular non-symlink directory");

  const manifestRelative = "data/research/vehiclesdb-vag-identity/manifest.json";
  const manifestItem = readRegular(desktopRoot, manifestRelative);
  const manifest = JSON.parse(manifestItem.text);
  const policyNotice = manifest.open_data_policy_notice;
  if (manifest.pack_id !== "vehiclesdb-vag-identity" ||
      manifest.source_revision !== "v2026.11.3" ||
      manifest.dataset_license !== "CC-BY-4.0" ||
      manifest.market_scope !== "foreign_market_presence_only" ||
      manifest.fitment_status !== "not_established" ||
      manifest.fitment_claim !== false ||
      manifest.exact_fitment !== false ||
      manifest.ru_evidence_present !== false ||
      manifest.engine_codes_included !== false ||
      manifest.gearbox_codes_included !== false ||
      manifest.ecu_fitment_included !== false ||
      manifest.identity_only_use !== true ||
      manifest.safety_critical_reliance !== false ||
      manifest.repair_decision_use !== false ||
      typeof policyNotice !== "string" ||
      !policyNotice.includes("not designed or warranted for safety-critical") ||
      manifest.counts?.sources !== 14 ||
      manifest.counts?.models !== 307 ||
      manifest.counts?.market_evidence !== 1621) {
    fail("VehiclesDB v2026.11.3 manifest failed identity-only, market, count or safety-use boundary");
  }

  const dbRelative = "lib/local-research-db.cjs";
  const verifierRelative = "scripts/verify-local-research-packs.cjs";
  const testRelative = "tests/local-research-db.test.cjs";
  const researchPacksTestRelative = "tests/local-research-packs.test.cjs";
  const dbItem = readRegular(desktopRoot, dbRelative);
  const verifierItem = readRegular(desktopRoot, verifierRelative);
  const testItem = readRegular(desktopRoot, testRelative);
  const researchPacksTestItem = readRegular(desktopRoot, researchPacksTestRelative);

  const oldCountGate = "vehiclesDbCounts.sources !== 14 || vehiclesDbCounts.models !== 260 || vehiclesDbCounts.marketEvidence !== 1524 || vehiclesDbCounts.russianEvidence !== 0 ||";
  const newCountGate = [
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
  let dbText = dbItem.text;
  const countPatch = replaceExactlyOnce(dbText, oldCountGate, newCountGate, "VehiclesDB dynamic count/safety gate");
  dbText = countPatch.text;

  const oldReturn = [
    "attributionRequired: true,",
    "        attribution: packManifest.attribution?.display_form || \"Vehicle data by VehiclesDB (vehiclesdb.com)\","
  ].join("\n");
  const newReturn = [
    "attributionRequired: true,",
    "        identityOnlyUse: packManifest.identity_only_use,",
    "        safetyCriticalReliance: packManifest.safety_critical_reliance,",
    "        repairDecisionUse: packManifest.repair_decision_use,",
    "        openDataPolicyNotice: packManifest.open_data_policy_notice,",
    "        attribution: packManifest.attribution?.display_form || \"Vehicle data by VehiclesDB (vehiclesdb.com)\","
  ].join("\n");
  const returnPatch = replaceExactlyOnce(dbText, oldReturn, newReturn, "VehiclesDB identity-only fields in candidate result");
  dbText = returnPatch.text;

  const tick = String.fromCharCode(96);
  const dollar = String.fromCharCode(36);
  const interpolation = dollar + "{JSON.stringify(vehiclesDbCounts)}";
  const oldVerifierCountGate = "assert(vehiclesDbCounts.sources === 14 && vehiclesDbCounts.models === 260 && vehiclesDbCounts.marketEvidence === 1524 && vehiclesDbCounts.russianEvidence === 0, " + tick + "VehiclesDB foreign-market-only count gate failed: " + interpolation + tick + ");";
  const newVerifierCountGate = "assert(vehiclesDbCounts.sources === vehiclesDbSnapshot.counts?.sources && vehiclesDbCounts.models === vehiclesDbSnapshot.counts?.models && vehiclesDbCounts.marketEvidence === vehiclesDbSnapshot.counts?.market_evidence && vehiclesDbCounts.russianEvidence === 0, " + tick + "VehiclesDB foreign-market-only count gate failed: " + interpolation + tick + ");";
  const verifierCountPatch = replaceExactlyOnce(verifierItem.text, oldVerifierCountGate, newVerifierCountGate, "VehiclesDB manifest-driven count gate in independent verifier");

  const oldVerifier = 'assert(vehiclesDbSnapshot.attribution?.required === true && /Vehicle data by VehiclesDB/i.test(vehiclesDbAttribution) && /UNCONDITIONAL/i.test(vehiclesDbAttribution), "VehiclesDB attribution and upstream notices are incomplete");';
  const newVerifier = oldVerifier + '\n    assert(vehiclesDbSnapshot.identity_only_use === true && vehiclesDbSnapshot.safety_critical_reliance === false && vehiclesDbSnapshot.repair_decision_use === false && typeof vehiclesDbSnapshot.open_data_policy_notice === "string" && vehiclesDbSnapshot.open_data_policy_notice.includes("not designed or warranted for safety-critical"), "VehiclesDB safety-critical and repair-decision boundary failed");';
  const verifierPatch = replaceExactlyOnce(verifierCountPatch.text, oldVerifier, newVerifier, "VehiclesDB independent verifier safety boundary");

  const oldTest = "  assert.equal(golf.sourceRevision, vehiclesDbManifest.source_revision);";
  const newTest = [
    oldTest,
    "  assert.equal(golf.identityOnlyUse, true);",
    "  assert.equal(golf.safetyCriticalReliance, false);",
    "  assert.equal(golf.repairDecisionUse, false);",
    "  assert.match(golf.openDataPolicyNotice, /not designed or warranted for safety-critical/);"
  ].join("\n");
  const testPatch = replaceExactlyOnce(testItem.text, oldTest, newTest, "VehiclesDB desktop candidate safety assertions");

  const oldResearchPacksCounts = [
    "  assert.equal(result.vehiclesdb_identity.sources, 14);",
    "  assert.equal(result.vehiclesdb_identity.models, 260);",
    "  assert.equal(result.vehiclesdb_identity.marketEvidence, 1524);"
  ].join("\n");
  const newResearchPacksCounts = [
    "  const vehiclesDbPackManifest = JSON.parse(require(\"node:fs\").readFileSync(require(\"node:path\").join(__dirname, \"../data/research/vehiclesdb-vag-identity/manifest.json\"), \"utf8\"));",
    "  assert.equal(result.vehiclesdb_identity.sources, vehiclesDbPackManifest.counts.sources);",
    "  assert.equal(result.vehiclesdb_identity.models, vehiclesDbPackManifest.counts.models);",
    "  assert.equal(result.vehiclesdb_identity.marketEvidence, vehiclesDbPackManifest.counts.market_evidence);"
  ].join("\n");
  const researchPacksTestPatch = replaceExactlyOnce(researchPacksTestItem.text, oldResearchPacksCounts, newResearchPacksCounts, "VehiclesDB manifest-driven count assertions in central research-pack test");

  if (countPatch.changed || returnPatch.changed) writeAtomic(dbItem.file, dbText, dbItem.stat.mode);
  if (verifierCountPatch.changed || verifierPatch.changed) writeAtomic(verifierItem.file, verifierPatch.text, verifierItem.stat.mode);
  if (testPatch.changed) writeAtomic(testItem.file, testPatch.text, testItem.stat.mode);
  if (researchPacksTestPatch.changed) writeAtomic(researchPacksTestItem.file, researchPacksTestPatch.text, researchPacksTestItem.stat.mode);

  const finalDb = readRegular(desktopRoot, dbRelative);
  const finalVerifier = readRegular(desktopRoot, verifierRelative);
  const finalTest = readRegular(desktopRoot, testRelative);
  const finalResearchPacksTest = readRegular(desktopRoot, researchPacksTestRelative);
  const patchHash = sha256(fs.readFileSync(__filename));
  const evidence = {
    schema_version: 1,
    status: "vehiclesdb_identity_only_dynamic_count_gate_applied",
    patch_id: "run93-vehiclesdb-identity-only-dynamic-count-gate",
    source_revision: manifest.source_revision,
    data_license: manifest.dataset_license,
    market_scope: manifest.market_scope,
    counts: manifest.counts,
    identity_only_use: manifest.identity_only_use,
    safety_critical_reliance: manifest.safety_critical_reliance,
    repair_decision_use: manifest.repair_decision_use,
    open_data_policy_notice: policyNotice,
    fitment_claim: manifest.fitment_claim,
    ru_evidence_present: manifest.ru_evidence_present,
    source_manifest_sha256: sha256(Buffer.from(manifestItem.text, "utf8")),
    patch_sha256: patchHash,
    desktop_db_sha256: sha256(Buffer.from(finalDb.text, "utf8")),
    verifier_sha256: sha256(Buffer.from(finalVerifier.text, "utf8")),
    test_sha256: sha256(Buffer.from(finalTest.text, "utf8")),
    research_packs_test_sha256: sha256(Buffer.from(finalResearchPacksTest.text, "utf8"))
  };
  const evidencePath = path.join(desktopRoot, "data/research/vehiclesdb-vag-identity/desktop-candidate-boundary-verification.json");
  fs.mkdirSync(path.dirname(evidencePath), { recursive: true });
  if (fs.existsSync(evidencePath)) {
    const current = readRegular(desktopRoot, "data/research/vehiclesdb-vag-identity/desktop-candidate-boundary-verification.json");
    const currentEvidence = JSON.parse(current.text);
    const identityKeys = [
      "schema_version", "status", "patch_id", "source_revision", "data_license",
      "market_scope", "counts", "identity_only_use", "safety_critical_reliance",
      "repair_decision_use", "open_data_policy_notice", "fitment_claim",
      "ru_evidence_present", "source_manifest_sha256"
    ];
    const currentKeys = Object.keys(currentEvidence).sort();
    const expectedKeys = Object.keys(evidence).sort();
    if (JSON.stringify(currentKeys) !== JSON.stringify(expectedKeys)) {
      fail("Existing VehiclesDB candidate-boundary evidence has an unexpected schema");
    }
    for (const key of identityKeys) {
      if (JSON.stringify(currentEvidence[key]) !== JSON.stringify(evidence[key])) {
        fail("Existing VehiclesDB candidate-boundary source/policy identity changed: " + key);
      }
    }
    // Later, separately licensed research-pack integrations may legitimately
    // extend the shared verifier/test files. Refresh only their content hashes;
    // never refresh or weaken the pinned source identity and safety boundary.
    if (JSON.stringify(currentEvidence) !== JSON.stringify(evidence)) {
      writeAtomic(current.file, JSON.stringify(evidence, null, 2) + "\n", current.stat.mode);
    }
  } else {
    writeAtomic(evidencePath, JSON.stringify(evidence, null, 2) + "\n");
  }
  process.stdout.write(JSON.stringify({
    status: evidence.status,
    source_revision: evidence.source_revision,
    counts: evidence.counts,
    patch_sha256: evidence.patch_sha256,
    source_manifest_sha256: evidence.source_manifest_sha256,
    research_packs_test_sha256: evidence.research_packs_test_sha256,
    evidence_sha256: sha256(fs.readFileSync(evidencePath))
  }, null, 2) + "\n");
}
try { main(); } catch (error) {
  process.stderr.write("run93-vehiclesdb-candidate-gate-error: " + (error && error.message ? error.message : String(error)) + "\n");
  process.exitCode = 1;
}
