#!/usr/bin/env node
"use strict";

const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");

function fail(message) { throw new Error(message); }
function parseArgs(argv) {
  let desktopRoot = null;
  for (let i = 2; i < argv.length; i += 1) {
    if (argv[i] !== "--desktop-root" || !argv[i + 1]) fail("Usage: node apply-vehiclesdb-revision-manifest-run89.cjs --desktop-root <path>");
    desktopRoot = path.resolve(argv[++i]);
  }
  if (!desktopRoot) fail("Missing --desktop-root");
  return { desktopRoot };
}
function sha256(value) { return crypto.createHash("sha256").update(value).digest("hex"); }
function readRegular(root, relativePath, readText = true) {
  const file = path.join(root, relativePath);
  const stat = fs.lstatSync(file);
  if (!stat.isFile() || stat.isSymbolicLink()) fail("Expected a regular non-symlink file: " + relativePath);
  return { file, stat, text: readText ? fs.readFileSync(file, "utf8") : undefined };
}
function atomicWrite(file, content, mode) {
  const temp = path.join(path.dirname(file), "." + path.basename(file) + "." + process.pid + ".run89.tmp");
  try {
    fs.writeFileSync(temp, content, { flag: "wx", mode: mode & 0o777 });
    fs.chmodSync(temp, mode & 0o777);
    fs.renameSync(temp, file);
  } finally {
    if (fs.existsSync(temp)) fs.unlinkSync(temp);
  }
}
function main() {
  const { desktopRoot } = parseArgs(process.argv);
  const rootStat = fs.lstatSync(desktopRoot);
  if (!rootStat.isDirectory() || rootStat.isSymbolicLink()) fail("Desktop root must be a regular non-symlink directory");
  const manifestItem = readRegular(desktopRoot, "data/research/vehiclesdb-vag-identity/manifest.json");
  const manifest = JSON.parse(manifestItem.text);
  if (manifest.pack_id !== "vehiclesdb-vag-identity" ||
      manifest.data_license !== "CC-BY-4.0" ||
      manifest.rights_status !== "approved_by_published_license" ||
      manifest.source_revision !== manifest.upstream_tag ||
      manifest.dataset_version !== String(manifest.source_revision).replace(/^v/, "") ||
      manifest.market_scope !== "foreign_market_presence_only" ||
      manifest.applicability_precision !== "make_model_name_only" ||
      manifest.fitment_status !== "not_established" ||
      manifest.fitment_claim !== false ||
      manifest.exact_fitment !== false ||
      manifest.identity_only_use !== true ||
      manifest.safety_critical_reliance !== false ||
      manifest.repair_decision_use !== false ||
      typeof manifest.open_data_policy_notice !== "string" ||
      !manifest.open_data_policy_notice.includes("not designed or warranted for safety-critical") ||
      manifest.ru_evidence_present !== false ||
      manifest.engine_codes_included !== false ||
      manifest.gearbox_codes_included !== false ||
      manifest.ecu_fitment_included !== false ||
      !/^[a-f0-9]{64}$/.test(manifest.database_sha256 || "")) {
    fail("VehiclesDB manifest rights, revision or candidate-only scope gate failed");
  }
  const testRelative = "tests/local-research-db.test.cjs";
  const testItem = readRegular(desktopRoot, testRelative);
  const oldText = '  assert.equal(golf.sourceRevision, "v2026.10.3");';
  const newText = '  const vehiclesDbManifest = JSON.parse(fs.readFileSync(path.join(root, "vehiclesdb-vag-identity", "manifest.json"), "utf8"));\n  assert.equal(golf.sourceRevision, vehiclesDbManifest.source_revision);';
  const oldCount = testItem.text.split(oldText).length - 1;
  const newCount = testItem.text.split(newText).length - 1;
  let updated = testItem.text;
  let patchStatus;
  if (oldCount === 1 && newCount === 0) {
    updated = testItem.text.replace(oldText, newText);
    atomicWrite(testItem.file, updated, testItem.stat.mode);
    patchStatus = "updated";
  } else if (oldCount === 0 && newCount === 1) {
    patchStatus = "already_current";
  } else {
    fail("Run89 exact revision assertion is stale or ambiguous (old=" + oldCount + ", new=" + newCount + ")");
  }
  const finalTest = readRegular(desktopRoot, testRelative, false);
  const evidence = {
    schema_version: 1,
    status: "desktop_test_revision_bound_to_manifest",
    patch_id: "run89-vehiclesdb-revision-manifest-binding",
    source_manifest_sha256: sha256(Buffer.from(manifestItem.text, "utf8")),
    database_sha256: manifest.database_sha256,
    source_revision: manifest.source_revision,
    data_license: manifest.data_license,
    rights_status: manifest.rights_status,
    market_scope: manifest.market_scope,
    applicability_precision: manifest.applicability_precision,
    fitment_claim: manifest.fitment_claim,
    exact_fitment: manifest.exact_fitment,
    identity_only_use: manifest.identity_only_use,
    safety_critical_reliance: manifest.safety_critical_reliance,
    repair_decision_use: manifest.repair_decision_use,
    open_data_policy_notice: manifest.open_data_policy_notice,
    ru_evidence_present: manifest.ru_evidence_present,
    test_file_sha256: sha256(fs.readFileSync(finalTest.file)),
  };
  const evidencePath = path.join(desktopRoot, "data/research/vehiclesdb-vag-identity/desktop-test-revision-verification.json");
  if (fs.existsSync(evidencePath)) {
    const current = fs.lstatSync(evidencePath);
    if (!current.isFile() || current.isSymbolicLink()) fail("Run89 evidence path is not a regular file");
    const existing = JSON.parse(fs.readFileSync(evidencePath, "utf8"));
    if (JSON.stringify(existing) !== JSON.stringify(evidence)) fail("Existing Run89 evidence does not match the pinned VehiclesDB manifest and test file");
  } else {
    atomicWrite(evidencePath, JSON.stringify(evidence, null, 2) + "\n", 0o644);
  }
  process.stdout.write(JSON.stringify({ status: evidence.status, patch_status: patchStatus, source_revision: evidence.source_revision, source_manifest_sha256: evidence.source_manifest_sha256, test_file_sha256: evidence.test_file_sha256 }, null, 2) + "\n");
}
try { main(); } catch (error) {
  process.stderr.write("run89-vehiclesdb-revision-sync-error: " + (error && error.message ? error.message : String(error)) + "\n");
  process.exitCode = 1;
}
